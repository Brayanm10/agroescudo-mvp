#include <AgroEscudoProtocol.h>
#include <ArduinoJson.h>
#include <HTTPClient.h>
#include <LittleFS.h>
#include <LoRa.h>
#include <SPI.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <WiFiManager.h>
#include <Wire.h>
#include <time.h>

#define XPOWERS_CHIP_AXP2101
#include <XPowersLib.h>
#include "mbedtls/md.h"
#include "mbedtls/sha256.h"

struct AgroNodeKeyConfig {
  uint16_t device_id;
  uint8_t key_version;
  uint8_t key[16];
};

#include "secrets.h"

// LILYGO T-Beam V1.2 AXP2101 + SX1276.
static constexpr int I2C_SDA = 21;
static constexpr int I2C_SCL = 22;
static constexpr int AGRO_LORA_SCK_PIN = 5;
static constexpr int AGRO_LORA_MISO_PIN = 19;
static constexpr int AGRO_LORA_MOSI_PIN = 27;
static constexpr int AGRO_LORA_SS_PIN = 18;
static constexpr int AGRO_LORA_RST_PIN = 23;
static constexpr int AGRO_LORA_DIO0_PIN = 26;
static constexpr long LORA_FREQUENCY_HZ = 915E6;
static constexpr uint8_t LORA_SYNC_WORD = 0x12;
static constexpr char WIFI_PORTAL_NAME[] = "AgroEscudo-Gateway";
static constexpr char QUEUE_FILE[] = "/events-v4.bin";
static constexpr char QUEUE_NEXT_FILE[] = "/events-v4.next";
static constexpr char DEAD_LETTER_FILE[] = "/events-v4-dead.bin";
static constexpr char SEEN_FILE[] = "/seen-v4.bin";
static constexpr uint32_t QUEUE_MAGIC = 0x34475141;
static constexpr uint32_t UPLOAD_INTERVAL_MS = 15000;
static constexpr time_t MIN_VALID_EPOCH = 1704067200;

struct PendingEvent {
  uint32_t magic;
  uint16_t device_id;
  uint32_t boot_id;
  uint32_t sequence;
  uint32_t sample_counter;
  uint32_t timestamp_utc;
  uint8_t time_quality;
  uint16_t firmware_version;
  uint16_t capabilities_version;
  uint16_t sensor_status_flags;
  uint8_t metric_count;
  AgroMetricTlv metrics[AGRO_TLV_MAX_METRICS];
  int16_t rssi_dbm;
  int16_t snr_db_x10;
};

struct SeenKey {
  uint16_t device_id;
  uint32_t boot_id;
  uint32_t sequence;
};

enum UploadResult {
  UPLOAD_NOT_READY,
  UPLOAD_ACCEPTED,
  UPLOAD_PERMANENT_REJECTION,
  UPLOAD_TEMPORARY_FAILURE,
};

XPowersPMU pmu;
uint32_t lastUploadAttempt = 0;

static const AgroNodeKeyConfig* findNodeKey(uint16_t deviceId, uint8_t keyVersion) {
  for (size_t index = 0; index < AGRO_NODE_KEY_COUNT; index++) {
    if (AGRO_NODE_KEYS[index].device_id == deviceId &&
        AGRO_NODE_KEYS[index].key_version == keyVersion) {
      return &AGRO_NODE_KEYS[index];
    }
  }
  return nullptr;
}

static bool appendEvent(const char* path, const PendingEvent& event) {
  File file = LittleFS.open(path, FILE_APPEND);
  if (!file) return false;
  const size_t written = file.write(reinterpret_cast<const uint8_t*>(&event), sizeof(event));
  file.flush();
  file.close();
  return written == sizeof(event);
}

static bool readFirstEvent(PendingEvent& event) {
  File file = LittleFS.open(QUEUE_FILE, FILE_READ);
  if (!file || file.size() < sizeof(event)) {
    if (file) file.close();
    return false;
  }
  const bool ok = file.read(reinterpret_cast<uint8_t*>(&event), sizeof(event)) == sizeof(event) &&
                  event.magic == QUEUE_MAGIC &&
                  event.metric_count > 0 && event.metric_count <= AGRO_TLV_MAX_METRICS;
  file.close();
  return ok;
}

static bool removeFirstEvent() {
  File source = LittleFS.open(QUEUE_FILE, FILE_READ);
  if (!source || source.size() < sizeof(PendingEvent)) {
    if (source) source.close();
    return false;
  }
  source.seek(sizeof(PendingEvent));
  LittleFS.remove(QUEUE_NEXT_FILE);
  File replacement = LittleFS.open(QUEUE_NEXT_FILE, FILE_WRITE);
  if (!replacement) {
    source.close();
    return false;
  }
  uint8_t buffer[256];
  bool ok = true;
  while (source.available()) {
    const size_t count = source.read(buffer, sizeof(buffer));
    if (count == 0 || replacement.write(buffer, count) != count) {
      ok = false;
      break;
    }
  }
  source.close();
  replacement.flush();
  replacement.close();
  if (!ok) {
    LittleFS.remove(QUEUE_NEXT_FILE);
    return false;
  }
  LittleFS.remove(QUEUE_FILE);
  File next = LittleFS.open(QUEUE_NEXT_FILE, FILE_READ);
  const size_t pendingBytes = next ? next.size() : 0;
  if (next) next.close();
  if (pendingBytes == 0) {
    LittleFS.remove(QUEUE_NEXT_FILE);
    return true;
  }
  return LittleFS.rename(QUEUE_NEXT_FILE, QUEUE_FILE);
}

static bool isSeen(const PendingEvent& event) {
  File file = LittleFS.open(SEEN_FILE, FILE_READ);
  if (!file) return false;
  SeenKey key{};
  while (file.read(reinterpret_cast<uint8_t*>(&key), sizeof(key)) == sizeof(key)) {
    if (key.device_id == event.device_id && key.boot_id == event.boot_id &&
        key.sequence == event.sequence) {
      file.close();
      return true;
    }
  }
  file.close();
  return false;
}

static void rememberSeen(const PendingEvent& event) {
  File current = LittleFS.open(SEEN_FILE, FILE_READ);
  const size_t size = current ? current.size() : 0;
  if (current) current.close();
  if (size > 4096) LittleFS.remove(SEEN_FILE);  // Cache acotada; la nube conserva idempotencia final.
  File file = LittleFS.open(SEEN_FILE, FILE_APPEND);
  if (!file) return;
  const SeenKey key{event.device_id, event.boot_id, event.sequence};
  file.write(reinterpret_cast<const uint8_t*>(&key), sizeof(key));
  file.close();
}

static void sendAck(const AgroFrameHeader& received) {
  AgroFrameHeader header{};
  header.magic = AGRO_MAGIC;
  header.protocol_version = AGRO_PROTOCOL_V4;
  header.message_type = AGRO_MSG_ACK;
  header.key_version = received.key_version;
  header.device_id = received.device_id;
  header.boot_id = received.boot_id;
  header.sequence = received.sequence;
  header.payload_len = sizeof(AgroAckPayload);
  const AgroAckPayload ack{received.device_id, received.boot_id, received.sequence, 1};
  LoRa.beginPacket();
  LoRa.write(reinterpret_cast<const uint8_t*>(&header), sizeof(header));
  LoRa.write(reinterpret_cast<const uint8_t*>(&ack), sizeof(ack));
  LoRa.endPacket();
  LoRa.receive();
}

static String isoTimestamp(time_t timestamp) {
  struct tm utc{};
  gmtime_r(&timestamp, &utc);
  char value[25];
  strftime(value, sizeof(value), "%Y-%m-%dT%H:%M:%SZ", &utc);
  return String(value);
}

static String sha256Hex(const String& body) {
  uint8_t digest[32];
  mbedtls_sha256_context context;
  mbedtls_sha256_init(&context);
  mbedtls_sha256_starts(&context, 0);
  mbedtls_sha256_update(&context,
    reinterpret_cast<const unsigned char*>(body.c_str()), body.length());
  mbedtls_sha256_finish(&context, digest);
  mbedtls_sha256_free(&context);
  char hex[65];
  for (uint8_t index = 0; index < 32; index++) sprintf(&hex[index * 2], "%02x", digest[index]);
  hex[64] = 0;
  return String(hex);
}

static String hmacSignature(const String& timestamp, const String& nonce, const String& body) {
  const String message = String(AGRO_GATEWAY_ID) + timestamp + nonce + sha256Hex(body);
  uint8_t digest[32];
  mbedtls_md_context_t context;
  mbedtls_md_init(&context);
  const mbedtls_md_info_t* info = mbedtls_md_info_from_type(MBEDTLS_MD_SHA256);
  mbedtls_md_setup(&context, info, 1);
  mbedtls_md_hmac_starts(&context,
    reinterpret_cast<const unsigned char*>(AGRO_GATEWAY_HMAC_SECRET),
    strlen(AGRO_GATEWAY_HMAC_SECRET));
  mbedtls_md_hmac_update(&context,
    reinterpret_cast<const unsigned char*>(message.c_str()), message.length());
  mbedtls_md_hmac_finish(&context, digest);
  mbedtls_md_free(&context);
  char hex[65];
  for (uint8_t index = 0; index < 32; index++) sprintf(&hex[index * 2], "%02x", digest[index]);
  hex[64] = 0;
  return String(hex);
}

static String buildBatch(const PendingEvent& event, time_t now) {
  JsonDocument document;
  document["gateway_id"] = AGRO_GATEWAY_ID;
  document["firmware_version"] = "2.0.0-arduino";
  document["sent_at"] = isoTimestamp(now);
  document["batch_id"] = String(AGRO_GATEWAY_ID) + "-v4-" + event.boot_id + "-" + event.sequence;
  document["protocol_version"] = AGRO_PROTOCOL_V4;
  JsonObject reading = document["events"].to<JsonArray>().add<JsonObject>();
  reading["device_id"] = event.device_id;
  reading["boot_id"] = event.boot_id;
  reading["sequence"] = event.sequence;
  reading["sample_counter"] = event.sample_counter;
  reading["timestamp_utc"] = event.timestamp_utc > 0 ? event.timestamp_utc : static_cast<uint32_t>(now);
  reading["time_quality"] = event.timestamp_utc > 0 ? event.time_quality : 1;
  reading["protocol_version"] = AGRO_PROTOCOL_V4;
  reading["firmware_version"] = event.firmware_version;
  reading["capabilities_version"] = event.capabilities_version;
  reading["sensor_status_flags"] = event.sensor_status_flags;
  reading["rssi_dbm"] = event.rssi_dbm;
  reading["snr_db_x10"] = event.snr_db_x10;
  JsonArray metrics = reading["metrics"].to<JsonArray>();
  for (uint8_t index = 0; index < event.metric_count; index++) {
    JsonObject metric = metrics.add<JsonObject>();
    metric["channel_key"] = agroChannelKey(event.metrics[index].channel_id);
    metric["metric_code"] = agroMetricCode(event.metrics[index].metric_id);
    metric["raw_value"] = agroScaledValue(event.metrics[index]);
    metric["unit"] = agroCanonicalUnit(event.metrics[index].metric_id);
    metric["quality"] = agroQualityCode(event.metrics[index].quality_code);
  }
  String body;
  serializeJson(document, body);
  return body;
}

static UploadResult uploadFirstEvent() {
  if (WiFi.status() != WL_CONNECTED || time(nullptr) < MIN_VALID_EPOCH) return UPLOAD_NOT_READY;
  PendingEvent event{};
  if (!readFirstEvent(event)) return UPLOAD_NOT_READY;
  const time_t now = time(nullptr);
  const String body = buildBatch(event, now);
  const String timestamp = String(now);
  const String nonce = String(AGRO_GATEWAY_ID) + "-" + event.boot_id + "-" + event.sequence + "-" + millis();

  WiFiClientSecure client;
  client.setCACert(AGRO_ROOT_CA_PEM);
  HTTPClient http;
  if (!http.begin(client, AGRO_API_URL)) return UPLOAD_TEMPORARY_FAILURE;
  http.setTimeout(30000);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-Agro-Gateway-ID", AGRO_GATEWAY_ID);
  http.addHeader("X-Agro-Timestamp", timestamp);
  http.addHeader("X-Agro-Nonce", nonce);
  http.addHeader("X-Agro-Signature", hmacSignature(timestamp, nonce, body));
  const int httpCode = http.POST(body);
  const String responseBody = http.getString();
  http.end();
  if (httpCode != 200) {
    Serial.printf("API HTTP %d; evento conservado.\n", httpCode);
    return httpCode >= 400 && httpCode < 500
      ? UPLOAD_PERMANENT_REJECTION : UPLOAD_TEMPORARY_FAILURE;
  }
  JsonDocument response;
  if (deserializeJson(response, responseBody)) return UPLOAD_TEMPORARY_FAILURE;
  const String status = response["results"][0]["canonical_status"] | "";
  if (status == "ACCEPTED" || status == "DUPLICATE") return UPLOAD_ACCEPTED;
  if (status == "REJECTED" || status == "QUARANTINED") return UPLOAD_PERMANENT_REJECTION;
  return UPLOAD_TEMPORARY_FAILURE;
}

static void processUploadQueue() {
  const UploadResult result = uploadFirstEvent();
  if (result == UPLOAD_ACCEPTED) {
    removeFirstEvent();
    Serial.println("Evento confirmado por AgroEscudo API.");
  } else if (result == UPLOAD_PERMANENT_REJECTION) {
    PendingEvent rejected{};
    if (readFirstEvent(rejected) && appendEvent(DEAD_LETTER_FILE, rejected)) {
      removeFirstEvent();
      Serial.println("Evento rechazado movido a dead-letter; no fue eliminado.");
    }
  }
}

static void receiveLoRa() {
  const int packetSize = LoRa.parsePacket();
  if (packetSize <= 0) return;
  if (packetSize < static_cast<int>(sizeof(AgroFrameHeader) + AGRO_CCM_TAG_LEN)) {
    while (LoRa.available()) LoRa.read();
    return;
  }
  AgroFrameHeader radioHeader{};
  LoRa.readBytes(reinterpret_cast<uint8_t*>(&radioHeader), sizeof(radioHeader));
  const bool envelopeValid =
    radioHeader.magic == AGRO_MAGIC &&
    radioHeader.protocol_version == AGRO_PROTOCOL_V4 &&
    radioHeader.message_type == AGRO_MSG_READING &&
    radioHeader.payload_len >= sizeof(AgroTelemetryHeaderV4) &&
    radioHeader.payload_len <= AGRO_TLV_MAX_PAYLOAD &&
    packetSize == static_cast<int>(sizeof(AgroFrameHeader) + radioHeader.payload_len + AGRO_CCM_TAG_LEN);
  const AgroNodeKeyConfig* node = findNodeKey(radioHeader.device_id, radioHeader.key_version);
  if (!envelopeValid || node == nullptr) {
    while (LoRa.available()) LoRa.read();
    Serial.println("Frame rechazado: envelope o nodo no autorizado.");
    return;
  }
  uint8_t encrypted[AGRO_TLV_MAX_PAYLOAD]{};
  uint8_t plain[AGRO_TLV_MAX_PAYLOAD]{};
  uint8_t tag[AGRO_CCM_TAG_LEN]{};
  LoRa.readBytes(encrypted, radioHeader.payload_len);
  LoRa.readBytes(tag, sizeof(tag));
  if (!agroDecryptPayload(radioHeader, node->key, encrypted, radioHeader.payload_len, tag, plain) ||
      !agroValidatePayload(plain, radioHeader.payload_len, radioHeader.device_id)) {
    Serial.println("Frame rechazado: autenticacion o metricas invalidas.");
    return;
  }
  const auto* payload = reinterpret_cast<const AgroTelemetryHeaderV4*>(plain);
  const auto* metrics = reinterpret_cast<const AgroMetricTlv*>(plain + sizeof(AgroTelemetryHeaderV4));
  PendingEvent event{};
  event.magic = QUEUE_MAGIC;
  event.device_id = radioHeader.device_id;
  event.boot_id = radioHeader.boot_id;
  event.sequence = radioHeader.sequence;
  event.sample_counter = payload->sample_counter;
  event.timestamp_utc = payload->timestamp_utc;
  event.time_quality = payload->time_quality;
  event.firmware_version = payload->firmware_version;
  event.capabilities_version = payload->capabilities_version;
  event.sensor_status_flags = payload->sensor_status_flags;
  event.metric_count = payload->metric_count;
  memcpy(event.metrics, metrics, event.metric_count * sizeof(AgroMetricTlv));
  event.rssi_dbm = LoRa.packetRssi();
  event.snr_db_x10 = static_cast<int16_t>(lroundf(LoRa.packetSnr() * 10));

  if (isSeen(event)) {
    sendAck(radioHeader);
    return;
  }
  if (appendEvent(QUEUE_FILE, event)) {
    rememberSeen(event);
    sendAck(radioHeader);  // ACK solo despues de persistir en flash.
    Serial.printf("Nodo %u, secuencia %lu persistida.\n", event.device_id, event.sequence);
  } else {
    Serial.println("ERROR: no se pudo persistir; no se envia ACK.");
  }
}

static void configurePower() {
  if (!pmu.begin(Wire, AXP2101_SLAVE_ADDRESS, I2C_SDA, I2C_SCL)) {
    Serial.println("ERROR: AXP2101 no detectado. Confirma que el gateway sea T-Beam V1.2.");
    while (true) delay(1000);
  }
  pmu.setALDO2Voltage(3300);
  pmu.enableALDO2();
  delay(100);
}

static void configureLoRa() {
  SPI.begin(AGRO_LORA_SCK_PIN, AGRO_LORA_MISO_PIN, AGRO_LORA_MOSI_PIN, AGRO_LORA_SS_PIN);
  LoRa.setPins(AGRO_LORA_SS_PIN, AGRO_LORA_RST_PIN, AGRO_LORA_DIO0_PIN);
  if (!LoRa.begin(LORA_FREQUENCY_HZ)) {
    Serial.println("ERROR: SX1276 no responde. Revisa antena, PMU, pines y frecuencia.");
    while (true) delay(1000);
  }
  LoRa.setSignalBandwidth(125E3);
  LoRa.setSpreadingFactor(7);
  LoRa.setCodingRate4(5);
  LoRa.setPreambleLength(8);
  LoRa.setSyncWord(LORA_SYNC_WORD);
  LoRa.disableCrc();
  LoRa.receive();
}

static void configureWiFi() {
  WiFi.mode(WIFI_STA);
  WiFiManager manager;
  manager.setConfigPortalTimeout(180);
  if (!manager.autoConnect(WIFI_PORTAL_NAME)) {
    Serial.println("WiFi no configurado; LoRa y cola local siguen activos.");
    return;
  }
  Serial.print("WiFi conectado: ");
  Serial.println(WiFi.localIP());
  configTime(0, 0, "pool.ntp.org", "time.google.com");
}

void setup() {
  Serial.begin(115200);
  Wire.begin(I2C_SDA, I2C_SCL);
  if (!LittleFS.begin(true)) {
    Serial.println("ERROR: LittleFS no disponible.");
    while (true) delay(1000);
  }
  configurePower();
  configureLoRa();
  configureWiFi();
  Serial.println("AgroEscudo Gateway V4 listo.");
}

void loop() {
  receiveLoRa();
  if (WiFi.status() != WL_CONNECTED) WiFi.reconnect();
  if (millis() - lastUploadAttempt >= UPLOAD_INTERVAL_MS) {
    lastUploadAttempt = millis();
    processUploadQueue();
  }
  delay(20);
}
