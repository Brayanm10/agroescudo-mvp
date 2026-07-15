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
static constexpr uint8_t NODE_KEY[16] = {
  0x00, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77,
  0x88, 0x99, 0xaa, 0xbb, 0xcc, 0xdd, 0xee, 0xff
};

struct PendingReading {
  uint16_t device_id;
  uint32_t boot_id;
  uint32_t sequence;
  AgroReadingPayload payload;
  int rssi;
  float snr;
};

static bool persistReading(const PendingReading& reading) {
  File file = LittleFS.open("/queue.bin", FILE_APPEND);
  if (!file) return false;
  uint32_t magic = 0x51475241;
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

static void sendAck(uint16_t deviceId, uint32_t bootId, uint32_t sequence) {
  AgroFrameHeader header{};
  header.magic = AGRO_MAGIC;
  header.protocol_version = AGRO_PROTOCOL_VERSION;
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
      magic != 0x51475241 ||
      len != sizeof(PendingReading) ||
      file.read(reinterpret_cast<uint8_t*>(&reading), sizeof(reading)) != sizeof(reading)) {
    file.close();
    return false;
  }
  file.close();
  return true;
}

static bool uploadFirstQueued() {
  if (WiFi.status() != WL_CONNECTED) return false;

  PendingReading reading{};
  if (!readFirstQueued(reading)) return false;

  StaticJsonDocument<768> doc;
  doc["gateway_id"] = GATEWAY_ID;
  doc["firmware_version"] = "1.0.0";
  doc["sent_at"] = "2026-07-01T20:30:00Z";
  doc["batch_id"] = String(GATEWAY_ID) + "-" + String(reading.boot_id) + "-" + String(reading.sequence);
  JsonArray readings = doc["readings"].to<JsonArray>();
  JsonObject item = readings.add<JsonObject>();
  item["device_id"] = reading.device_id;
  item["boot_id"] = reading.boot_id;
  item["sequence"] = reading.sequence;
  item["sample_counter"] = reading.payload.sample_counter;
  item["timestamp_utc"] = reading.payload.timestamp_utc;
  item["time_quality"] = reading.payload.time_quality;
  item["grain_temp_c_x100"] = reading.payload.grain_temp_c_x100;
  item["air_temp_c_x100"] = reading.payload.air_temp_c_x100;
  item["rh_x100"] = reading.payload.rh_x100;
  item["battery_mv"] = reading.payload.battery_mv;
  item["sensor_status"] = reading.payload.sensor_status;
  item["firmware_version"] = reading.payload.firmware_version;
  item["rssi_dbm"] = reading.rssi;
  item["snr_db_x10"] = static_cast<int>(reading.snr * 10);

  String body;
  serializeJson(doc, body);
  String timestamp = String(time(nullptr));
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
    LittleFS.remove("/queue.bin");
    return true;
  }
  return false;
}

void setup() {
  Serial.begin(115200);
  LittleFS.begin(true);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  LoRa.begin(AGRO_LORA_FREQUENCY);
}

void loop() {
  int packetSize = LoRa.parsePacket();
  if (packetSize > 0) {
    AgroFrameHeader header{};
    LoRa.readBytes(reinterpret_cast<uint8_t*>(&header), sizeof(header));
    if (header.magic == AGRO_MAGIC && header.message_type == AGRO_MSG_READING && header.payload_len == sizeof(AgroReadingPayload)) {
      uint8_t encrypted[sizeof(AgroReadingPayload)]{};
      uint8_t tag[AGRO_CCM_TAG_LEN]{};
      AgroReadingPayload payload{};
      LoRa.readBytes(encrypted, sizeof(encrypted));
      LoRa.readBytes(tag, sizeof(tag));
      if (agroDecryptPayload(header, NODE_KEY, encrypted, sizeof(encrypted), tag, reinterpret_cast<uint8_t*>(&payload)) && agroValidReadingRanges(payload)) {
        PendingReading pending{header.device_id, header.boot_id, header.sequence, payload, LoRa.packetRssi(), LoRa.packetSnr()};
        if (isDuplicate(pending) || persistReading(pending)) {
          rememberSeen(pending);
          sendAck(header.device_id, header.boot_id, header.sequence);
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
