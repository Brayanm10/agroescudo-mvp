#include <Arduino.h>
#include <ArduinoJson.h>
#include <HTTPClient.h>
#include <LittleFS.h>
#include <LoRa.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <time.h>
#include "mbedtls/md.h"
#include "mbedtls/sha256.h"

#include "../shared/agro_crypto.h"

static const char* WIFI_SSID = "CONFIGURAR_EN_PROVISIONAMIENTO";
static const char* WIFI_PASSWORD = "CONFIGURAR_EN_PROVISIONAMIENTO";
static const char* API_URL = "https://agroescudo-api.onrender.com/api/iot/v1/ingest/batch";
static const char* GATEWAY_ID = "GW-CBBA-001";
static const char* GATEWAY_SECRET = "CONFIGURAR_EN_NVS";
static const char* ROOT_CA = "-----BEGIN CERTIFICATE-----\nCONFIGURAR_CA_REAL\n-----END CERTIFICATE-----\n";
static constexpr uint32_t QUEUE_MAGIC_V3 = 0x33475241;
static constexpr time_t MIN_VALID_EPOCH = 1704067200;
static constexpr uint8_t NODE_KEY[16] = {
  0x00, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77,
  0x88, 0x99, 0xaa, 0xbb, 0xcc, 0xdd, 0xee, 0xff
};

struct PendingReading {
  uint16_t device_id;
  uint32_t boot_id;
  uint32_t sequence;
  uint8_t protocol_version;
  uint32_t sample_counter;
  uint32_t timestamp_utc;
  uint8_t time_quality;
  uint8_t sensor_profile;
  uint16_t metric_flags;
  int16_t grain_temp_c_x100;
  int16_t air_temp_c_x100;
  uint16_t rh_x100;
  uint16_t soil_moisture_x100;
  uint16_t soil_moisture_raw;
  int16_t soil_temp_c_x100;
  uint32_t level_distance_mm;
  uint16_t battery_mv;
  uint16_t sensor_status;
  uint16_t firmware_version;
  int rssi;
  float snr;
};

static bool persistReading(const PendingReading& reading) {
  File file = LittleFS.open("/queue.bin", FILE_APPEND);
  if (!file) return false;
  uint32_t magic = QUEUE_MAGIC_V3;
  uint16_t len = sizeof(PendingReading);
  file.write(reinterpret_cast<uint8_t*>(&magic), sizeof(magic));
  file.write(reinterpret_cast<uint8_t*>(&len), sizeof(len));
  file.write(reinterpret_cast<const uint8_t*>(&reading), sizeof(reading));
  file.close();
  return true;
}

static bool isDuplicate(const PendingReading& reading) {
  File file = LittleFS.open("/seen.bin", FILE_READ);
  if (!file) return false;
  PendingReading current{};
  while (file.read(reinterpret_cast<uint8_t*>(&current), sizeof(current)) == sizeof(current)) {
    if (current.device_id == reading.device_id &&
        current.boot_id == reading.boot_id &&
        current.sequence == reading.sequence) {
      file.close();
      return true;
    }
  }
  file.close();
  return false;
}

static void rememberSeen(const PendingReading& reading) {
  File file = LittleFS.open("/seen.bin", FILE_APPEND);
  if (!file) return;
  file.write(reinterpret_cast<const uint8_t*>(&reading), sizeof(reading));
  file.close();
}

static void sendAck(uint8_t protocolVersion, uint16_t deviceId, uint32_t bootId, uint32_t sequence) {
  AgroFrameHeader header{};
  header.magic = AGRO_MAGIC;
  header.protocol_version = protocolVersion;
  header.message_type = AGRO_MSG_ACK;
  header.device_id = deviceId;
  header.boot_id = bootId;
  header.sequence = sequence;
  header.payload_len = sizeof(AgroAckPayload);
  AgroAckPayload ack{deviceId, bootId, sequence, 1};
  LoRa.beginPacket();
  LoRa.write(reinterpret_cast<uint8_t*>(&header), sizeof(header));
  LoRa.write(reinterpret_cast<uint8_t*>(&ack), sizeof(ack));
  LoRa.endPacket();
}

static String sha256Hex(const String& body) {
  uint8_t digest[32];
  mbedtls_sha256_context ctx;
  mbedtls_sha256_init(&ctx);
  mbedtls_sha256_starts(&ctx, 0);
  mbedtls_sha256_update(&ctx, reinterpret_cast<const unsigned char*>(body.c_str()), body.length());
  mbedtls_sha256_finish(&ctx, digest);
  mbedtls_sha256_free(&ctx);
  char hex[65];
  for (int i = 0; i < 32; i++) sprintf(&hex[i * 2], "%02x", digest[i]);
  hex[64] = 0;
  return String(hex);
}

static String hmacSignature(const String& timestamp, const String& nonce, const String& bodyHash) {
  String message = String(GATEWAY_ID) + timestamp + nonce + bodyHash;
  uint8_t output[32];
  mbedtls_md_context_t ctx;
  mbedtls_md_init(&ctx);
  const mbedtls_md_info_t* info = mbedtls_md_info_from_type(MBEDTLS_MD_SHA256);
  mbedtls_md_setup(&ctx, info, 1);
  mbedtls_md_hmac_starts(&ctx, reinterpret_cast<const unsigned char*>(GATEWAY_SECRET), strlen(GATEWAY_SECRET));
  mbedtls_md_hmac_update(&ctx, reinterpret_cast<const unsigned char*>(message.c_str()), message.length());
  mbedtls_md_hmac_finish(&ctx, output);
  mbedtls_md_free(&ctx);
  char hex[65];
  for (int i = 0; i < 32; i++) sprintf(&hex[i * 2], "%02x", output[i]);
  hex[64] = 0;
  return String(hex);
}

static bool readFirstQueued(PendingReading& reading) {
  File file = LittleFS.open("/queue.bin", FILE_READ);
  if (!file) return false;
  uint32_t magic = 0;
  uint16_t len = 0;
  if (file.read(reinterpret_cast<uint8_t*>(&magic), sizeof(magic)) != sizeof(magic) ||
      file.read(reinterpret_cast<uint8_t*>(&len), sizeof(len)) != sizeof(len) ||
      magic != QUEUE_MAGIC_V3 ||
      len != sizeof(PendingReading) ||
      file.read(reinterpret_cast<uint8_t*>(&reading), sizeof(reading)) != sizeof(reading)) {
    file.close();
    return false;
  }
  file.close();
  return true;
}

static bool removeFirstQueued() {
  File source = LittleFS.open("/queue.bin", FILE_READ);
  if (!source) return false;
  const size_t recordSize = sizeof(uint32_t) + sizeof(uint16_t) + sizeof(PendingReading);
  if (source.size() < recordSize) {
    source.close();
    return false;
  }
  source.seek(recordSize);
  LittleFS.remove("/queue.next");
  File replacement = LittleFS.open("/queue.next", FILE_WRITE);
  if (!replacement) {
    source.close();
    return false;
  }
  uint8_t buffer[128];
  while (source.available()) {
    const size_t readCount = source.read(buffer, sizeof(buffer));
    if (readCount == 0 || replacement.write(buffer, readCount) != readCount) {
      source.close();
      replacement.close();
      LittleFS.remove("/queue.next");
      return false;
    }
  }
  source.close();
  replacement.close();
  File pending = LittleFS.open("/queue.next", FILE_READ);
  const size_t pendingSize = pending ? pending.size() : 0;
  if (pending) pending.close();
  if (pendingSize == 0) {
    LittleFS.remove("/queue.bin");
    LittleFS.remove("/queue.next");
    return true;
  }
  LittleFS.remove("/queue.previous");
  if (!LittleFS.rename("/queue.bin", "/queue.previous")) return false;
  if (!LittleFS.rename("/queue.next", "/queue.bin")) {
    LittleFS.rename("/queue.previous", "/queue.bin");
    return false;
  }
  LittleFS.remove("/queue.previous");
  return true;
}

static void ensureQueueSchema() {
  File file = LittleFS.open("/queue.bin", FILE_READ);
  if (!file) return;
  uint32_t magic = 0;
  uint16_t len = 0;
  const bool compatible =
      file.read(reinterpret_cast<uint8_t*>(&magic), sizeof(magic)) == sizeof(magic) &&
      file.read(reinterpret_cast<uint8_t*>(&len), sizeof(len)) == sizeof(len) &&
      magic == QUEUE_MAGIC_V3 && len == sizeof(PendingReading);
  file.close();
  if (!compatible) {
    LittleFS.remove("/queue-incompatible.bak");
    LittleFS.rename("/queue.bin", "/queue-incompatible.bak");
  }
}

static String isoTimestamp(time_t timestamp) {
  struct tm utc{};
  gmtime_r(&timestamp, &utc);
  char value[25];
  strftime(value, sizeof(value), "%Y-%m-%dT%H:%M:%SZ", &utc);
  return String(value);
}

static bool uploadFirstQueued() {
  if (WiFi.status() != WL_CONNECTED) return false;
  const time_t now = time(nullptr);
  if (now < MIN_VALID_EPOCH) return false;

  PendingReading reading{};
  if (!readFirstQueued(reading)) return false;

  StaticJsonDocument<768> doc;
  doc["gateway_id"] = GATEWAY_ID;
  doc["firmware_version"] = "1.0.0";
  doc["sent_at"] = isoTimestamp(now);
  doc["batch_id"] = String(GATEWAY_ID) + "-" + String(reading.boot_id) + "-" + String(reading.sequence);
  JsonArray readings = doc["readings"].to<JsonArray>();
  JsonObject item = readings.add<JsonObject>();
  item["device_id"] = reading.device_id;
  item["boot_id"] = reading.boot_id;
  item["sequence"] = reading.sequence;
  item["protocol_version"] = reading.protocol_version;
  item["sample_counter"] = reading.sample_counter;
  item["timestamp_utc"] = reading.timestamp_utc > 0 ? reading.timestamp_utc : static_cast<uint32_t>(now);
  item["time_quality"] = reading.timestamp_utc > 0 ? reading.time_quality : 1;
  item["sensor_profile"] = reading.sensor_profile == AGRO_PROFILE_FIELD ? "field_sensor" : "silo_sensor";
  item["metric_flags"] = reading.metric_flags;
  if (reading.metric_flags & AGRO_HAS_GRAIN_TEMP) item["grain_temp_c_x100"] = reading.grain_temp_c_x100;
  if (reading.metric_flags & AGRO_HAS_AIR_TEMP) item["air_temp_c_x100"] = reading.air_temp_c_x100;
  if (reading.metric_flags & AGRO_HAS_AIR_HUMIDITY) item["rh_x100"] = reading.rh_x100;
  if (reading.metric_flags & AGRO_HAS_BATTERY) item["battery_mv"] = reading.battery_mv;
  if (reading.metric_flags & AGRO_HAS_SOIL_MOISTURE) item["soil_moisture_x100"] = reading.soil_moisture_x100;
  if (reading.metric_flags & AGRO_HAS_SOIL_MOISTURE_RAW) item["soil_moisture_raw"] = reading.soil_moisture_raw;
  if (reading.metric_flags & AGRO_HAS_SOIL_TEMP) item["soil_temp_c_x100"] = reading.soil_temp_c_x100;
  if (reading.metric_flags & AGRO_HAS_LEVEL_DISTANCE) item["level_distance_cm"] = reading.level_distance_mm / 10.0f;
  item["sensor_status"] = reading.sensor_status;
  item["firmware_version"] = reading.firmware_version;
  item["rssi_dbm"] = reading.rssi;
  item["snr_db_x10"] = static_cast<int>(reading.snr * 10);

  String body;
  serializeJson(doc, body);
  String timestamp = String(now);
  String nonce = String(GATEWAY_ID) + "-" + String(millis());
  String bodyHash = sha256Hex(body);
  String signature = hmacSignature(timestamp, nonce, bodyHash);

  WiFiClientSecure client;
  client.setCACert(ROOT_CA);
  HTTPClient http;
  if (!http.begin(client, API_URL)) return false;
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-Agro-Gateway-ID", GATEWAY_ID);
  http.addHeader("X-Agro-Timestamp", timestamp);
  http.addHeader("X-Agro-Nonce", nonce);
  http.addHeader("X-Agro-Signature", signature);
  int code = http.POST(body);
  String response = http.getString();
  http.end();

  if (code == 200 && (response.indexOf("accepted") >= 0 || response.indexOf("duplicate") >= 0)) {
    return removeFirstQueued();
  }
  return false;
}

void setup() {
  Serial.begin(115200);
  LittleFS.begin(true);
  ensureQueueSchema();
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  configTime(0, 0, "pool.ntp.org", "time.google.com");
  LoRa.begin(AGRO_LORA_FREQUENCY);
}

void loop() {
  int packetSize = LoRa.parsePacket();
  if (packetSize > 0) {
    AgroFrameHeader header{};
    LoRa.readBytes(reinterpret_cast<uint8_t*>(&header), sizeof(header));
    if (header.magic == AGRO_MAGIC && header.message_type == AGRO_MSG_READING && header.protocol_version == AGRO_PROTOCOL_V1 && header.payload_len == sizeof(AgroReadingPayloadV1)) {
      uint8_t encrypted[sizeof(AgroReadingPayloadV1)]{};
      uint8_t tag[AGRO_CCM_TAG_LEN]{};
      AgroReadingPayloadV1 payload{};
      LoRa.readBytes(encrypted, sizeof(encrypted));
      LoRa.readBytes(tag, sizeof(tag));
      if (agroDecryptPayload(header, NODE_KEY, encrypted, sizeof(encrypted), tag, reinterpret_cast<uint8_t*>(&payload)) && agroValidReadingRanges(payload)) {
        PendingReading pending{};
        pending.device_id = header.device_id;
        pending.boot_id = header.boot_id;
        pending.sequence = header.sequence;
        pending.protocol_version = AGRO_PROTOCOL_V1;
        pending.sample_counter = payload.sample_counter;
        pending.timestamp_utc = payload.timestamp_utc;
        pending.time_quality = payload.time_quality;
        pending.sensor_profile = AGRO_PROFILE_SILO;
        pending.metric_flags = AGRO_HAS_GRAIN_TEMP | AGRO_HAS_AIR_TEMP | AGRO_HAS_AIR_HUMIDITY | AGRO_HAS_BATTERY;
        pending.grain_temp_c_x100 = payload.grain_temp_c_x100;
        pending.air_temp_c_x100 = payload.air_temp_c_x100;
        pending.rh_x100 = payload.rh_x100;
        pending.battery_mv = payload.battery_mv;
        pending.sensor_status = payload.sensor_status;
        pending.firmware_version = payload.firmware_version;
        pending.rssi = LoRa.packetRssi();
        pending.snr = LoRa.packetSnr();
        if (isDuplicate(pending) || persistReading(pending)) {
          rememberSeen(pending);
          sendAck(header.protocol_version, header.device_id, header.boot_id, header.sequence);
        }
      }
    } else if (header.magic == AGRO_MAGIC && header.message_type == AGRO_MSG_READING && header.protocol_version == AGRO_PROTOCOL_V2 && header.payload_len == sizeof(AgroReadingPayloadV2)) {
      uint8_t encrypted[sizeof(AgroReadingPayloadV2)]{};
      uint8_t tag[AGRO_CCM_TAG_LEN]{};
      AgroReadingPayloadV2 payload{};
      LoRa.readBytes(encrypted, sizeof(encrypted));
      LoRa.readBytes(tag, sizeof(tag));
      if (agroDecryptPayload(header, NODE_KEY, encrypted, sizeof(encrypted), tag, reinterpret_cast<uint8_t*>(&payload)) && agroValidReadingRanges(payload)) {
        PendingReading pending{};
        pending.device_id = header.device_id;
        pending.boot_id = header.boot_id;
        pending.sequence = header.sequence;
        pending.protocol_version = AGRO_PROTOCOL_V2;
        pending.sample_counter = payload.sample_counter;
        pending.timestamp_utc = payload.timestamp_utc;
        pending.time_quality = payload.time_quality;
        pending.sensor_profile = payload.sensor_profile;
        pending.metric_flags = payload.metric_flags;
        pending.grain_temp_c_x100 = payload.grain_temp_c_x100;
        pending.air_temp_c_x100 = payload.air_temp_c_x100;
        pending.rh_x100 = payload.rh_x100;
        pending.soil_moisture_x100 = payload.soil_moisture_x100;
        pending.soil_temp_c_x100 = payload.soil_temp_c_x100;
        pending.level_distance_mm = payload.level_distance_mm;
        pending.battery_mv = payload.battery_mv;
        pending.sensor_status = payload.sensor_status;
        pending.firmware_version = payload.firmware_version;
        pending.rssi = LoRa.packetRssi();
        pending.snr = LoRa.packetSnr();
        if (isDuplicate(pending) || persistReading(pending)) {
          rememberSeen(pending);
          sendAck(header.protocol_version, header.device_id, header.boot_id, header.sequence);
        }
      }
    } else if (header.magic == AGRO_MAGIC && header.message_type == AGRO_MSG_READING && header.protocol_version == AGRO_PROTOCOL_V3 && header.payload_len == sizeof(AgroReadingPayloadV3)) {
      uint8_t encrypted[sizeof(AgroReadingPayloadV3)]{};
      uint8_t tag[AGRO_CCM_TAG_LEN]{};
      AgroReadingPayloadV3 payload{};
      LoRa.readBytes(encrypted, sizeof(encrypted));
      LoRa.readBytes(tag, sizeof(tag));
      if (agroDecryptPayload(header, NODE_KEY, encrypted, sizeof(encrypted), tag, reinterpret_cast<uint8_t*>(&payload)) && agroValidReadingRanges(payload)) {
        PendingReading pending{};
        pending.device_id = header.device_id;
        pending.boot_id = header.boot_id;
        pending.sequence = header.sequence;
        pending.protocol_version = AGRO_PROTOCOL_V3;
        pending.sample_counter = payload.sample_counter;
        pending.timestamp_utc = payload.timestamp_utc;
        pending.time_quality = payload.time_quality;
        pending.sensor_profile = payload.sensor_profile;
        pending.metric_flags = payload.metric_flags;
        pending.grain_temp_c_x100 = payload.grain_temp_c_x100;
        pending.air_temp_c_x100 = payload.air_temp_c_x100;
        pending.rh_x100 = payload.rh_x100;
        pending.soil_moisture_raw = payload.soil_moisture_raw;
        pending.soil_temp_c_x100 = payload.soil_temp_c_x100;
        pending.level_distance_mm = payload.level_distance_mm;
        pending.battery_mv = payload.battery_mv;
        pending.sensor_status = payload.sensor_status;
        pending.firmware_version = payload.firmware_version;
        pending.rssi = LoRa.packetRssi();
        pending.snr = LoRa.packetSnr();
        if (isDuplicate(pending) || persistReading(pending)) {
          rememberSeen(pending);
          sendAck(header.protocol_version, header.device_id, header.boot_id, header.sequence);
        }
      }
    }
  }
  static uint32_t lastUpload = 0;
  if (millis() - lastUpload > 30000) {
    uploadFirstQueued();
    lastUpload = millis();
  }
  delay(50);
}
