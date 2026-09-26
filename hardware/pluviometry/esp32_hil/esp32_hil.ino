/*
  AGROESCUDO HIL BENCH TEST

  Valida exclusivamente ESP32 -> WiFi -> HTTP -> API -> DB -> web.
  NO es firmware de campo: no incluye LoRa, gateway final, buffer offline,
  store-and-forward, cifrado final, Secure Boot, sensores físicos ni batería real.
*/

#include <Arduino.h>
#include <ArduinoJson.h>
#include <HTTPClient.h>
#include <WiFi.h>
#include <time.h>
#include <mbedtls/md.h>
#include <mbedtls/sha256.h>
#include <mbedtls/version.h>

#include "secrets.h"

namespace {
constexpr uint32_t kSendIntervalMs = 15000;
constexpr uint32_t kWifiRetryMs = 5000;
constexpr uint32_t kHeapLogEverySuccessfulSends = 20;
constexpr time_t kMinimumValidEpoch = 1700000000;
constexpr char kFirmwareVersion[] = "hil-esp32-0.1.0";

uint32_t bootId = 0;
uint32_t sequenceNumber = 0;
uint32_t lastSendAt = 0;
uint32_t lastWifiAttemptAt = 0;
int lastHttpStatus = 0;
bool wifiEnabled = true;
bool wifiConnectedAnnounced = false;
bool ntpSyncedAnnounced = false;
String serialCommand;

String toHex(const unsigned char* bytes, size_t length) {
  static const char* digits = "0123456789abcdef";
  String result;
  result.reserve(length * 2);
  for (size_t index = 0; index < length; ++index) {
    result += digits[(bytes[index] >> 4) & 0x0f];
    result += digits[bytes[index] & 0x0f];
  }
  return result;
}

String sha256Hex(const String& value) {
  unsigned char digest[32];
#if MBEDTLS_VERSION_MAJOR >= 3
  mbedtls_sha256(
      reinterpret_cast<const unsigned char*>(value.c_str()),
      value.length(), digest, 0);
#else
  mbedtls_sha256_ret(
      reinterpret_cast<const unsigned char*>(value.c_str()),
      value.length(), digest, 0);
#endif
  return toHex(digest, sizeof(digest));
}

String hmacSha256Hex(const String& key, const String& message) {
  unsigned char digest[32];
  const mbedtls_md_info_t* info = mbedtls_md_info_from_type(MBEDTLS_MD_SHA256);
  mbedtls_md_hmac(
      info,
      reinterpret_cast<const unsigned char*>(key.c_str()), key.length(),
      reinterpret_cast<const unsigned char*>(message.c_str()), message.length(),
      digest);
  return toHex(digest, sizeof(digest));
}

String utcIso8601(time_t epoch) {
  struct tm value;
  gmtime_r(&epoch, &value);
  char output[25];
  strftime(output, sizeof(output), "%Y-%m-%dT%H:%M:%SZ", &value);
  return String(output);
}

void connectWifi() {
  if (!wifiEnabled) return;
  if (WiFi.status() == WL_CONNECTED) return;
  const uint32_t now = millis();
  if (now - lastWifiAttemptAt < kWifiRetryMs) return;
  lastWifiAttemptAt = now;
  Serial.printf("Conectando WiFi a %s...\n", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
}

void printStatus() {
  const bool connected = WiFi.status() == WL_CONNECTED;
  Serial.println("--- HIL STATUS ---");
  Serial.printf("WiFi: %s\n", connected ? "conectado" : "desconectado");
  Serial.printf("WiFi habilitado: %s\n", wifiEnabled ? "si" : "no");
  Serial.printf("IP: %s\n", connected ? WiFi.localIP().toString().c_str() : "sin IP");
  Serial.printf("Boot ID: %lu\n", static_cast<unsigned long>(bootId));
  Serial.printf("Sequence pendiente: %lu\n", static_cast<unsigned long>(sequenceNumber));
  Serial.printf("Free heap: %lu bytes\n", static_cast<unsigned long>(ESP.getFreeHeap()));
  Serial.printf("Ultimo HTTP status: %d\n", lastHttpStatus);
}

void wifiOff() {
  wifiEnabled = false;
  WiFi.setAutoReconnect(false);
  WiFi.disconnect(true, false);
  WiFi.mode(WIFI_OFF);
  wifiConnectedAnnounced = false;
  ntpSyncedAnnounced = false;
  Serial.println("HIL WIFI DROP TEST: WiFi del ESP32 desactivado");
  Serial.println("No se generan ni recuperan muestras mientras WiFi esta desactivado.");
  printStatus();
}

void wifiOn() {
  wifiEnabled = true;
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  lastWifiAttemptAt = millis() - kWifiRetryMs;
  lastSendAt = millis() - kSendIntervalMs;
  configTime(0, 0, "pool.ntp.org", "time.nist.gov");
  Serial.println("HIL WIFI DROP TEST: WiFi del ESP32 activado; reconectando...");
  connectWifi();
}

void handleSerialCommand(String command) {
  command.trim();
  command.toLowerCase();
  if (command == "wifi_off") {
    wifiOff();
  } else if (command == "wifi_on") {
    wifiOn();
  } else if (command == "status") {
    printStatus();
  } else if (command.length() > 0) {
    Serial.println("Comando desconocido. Usa: wifi_off | wifi_on | status");
  }
}

void processSerialCommands() {
  while (Serial.available() > 0) {
    const char value = static_cast<char>(Serial.read());
    if (value == '\n' || value == '\r') {
      if (serialCommand.length() > 0) {
        handleSerialCommand(serialCommand);
        serialCommand = "";
      }
    } else if (serialCommand.length() < 48) {
      serialCommand += value;
    } else {
      serialCommand = "";
      Serial.println("Comando demasiado largo; descartado");
    }
  }
}

bool clockIsReady() {
  return time(nullptr) >= kMinimumValidEpoch;
}

float rainDelta(uint32_t sequence) {
  const uint32_t phase = sequence % 20;
  if (phase < 8) return 0.0f;
  if (phase < 15) return 0.2f + 0.1f * (phase % 3);
  return 0.7f + 0.2f * (phase % 3);
}

float windDirection(uint32_t sequence) {
  // Cruza Norte periódicamente: 350, 355, 359, 1, 5, 10.
  static const float directions[] = {350.0f, 355.0f, 359.0f, 1.0f, 5.0f, 10.0f};
  return directions[sequence % 6];
}

void addMetric(JsonArray metrics, const char* channel, const char* code,
               float value, const char* unit) {
  JsonObject metric = metrics.add<JsonObject>();
  metric["channel_key"] = channel;
  metric["metric_code"] = code;
  metric["raw_value"] = value;
  metric["unit"] = unit;
  metric["quality"] = "VALID";
}

String buildPayload(time_t epoch, const String& batchId) {
  JsonDocument document;
  document["gateway_id"] = AGRO_GATEWAY_ID;
  document["firmware_version"] = kFirmwareVersion;
  document["sent_at"] = utcIso8601(epoch);
  document["batch_id"] = batchId;
  document["protocol_version"] = 4;

  JsonArray events = document["events"].to<JsonArray>();
  JsonObject event = events.add<JsonObject>();
  event["device_id"] = AGRO_DEVICE_ID;
  event["boot_id"] = bootId;
  event["sequence"] = sequenceNumber;
  event["sample_counter"] = sequenceNumber;
  event["timestamp_utc"] = static_cast<uint32_t>(epoch);
  event["time_quality"] = "NTP_SYNCED";
  event["firmware_version"] = kFirmwareVersion;
  event["protocol_version"] = 4;
  event["capabilities_version"] = 1;
  event["sensor_profile"] = "rain_gauge";
  event["sensor_status_flags"] = 0;
  event["rssi_dbm"] = WiFi.RSSI();

  const float wave = sinf(sequenceNumber * 0.22f);
  const float slowWave = sinf(sequenceNumber * 0.08f);
  const float battery = max(80.0f, 96.0f - sequenceNumber * 0.01f);
  JsonArray metrics = event["metrics"].to<JsonArray>();
  addMetric(metrics, "rain_1", "RAIN_DELTA_MM", rainDelta(sequenceNumber), "mm");
  addMetric(metrics, "ambient_temp_1", "AMBIENT_TEMPERATURE_C", 22.8f + wave * 0.7f, "degC");
  addMetric(metrics, "ambient_rh_1", "AMBIENT_RELATIVE_HUMIDITY_PCT", 68.5f + slowWave * 2.0f, "percent");
  addMetric(metrics, "wind_speed_1", "WIND_SPEED_KMH", 10.5f + wave * 2.0f, "km/h");
  addMetric(metrics, "wind_direction_1", "WIND_DIRECTION_DEG", windDirection(sequenceNumber), "degree");
  addMetric(metrics, "battery_1", "BATTERY_PERCENT", battery, "percent");

  String body;
  serializeJson(document, body);
  return body;
}

void sendTelemetry() {
  if (WiFi.status() != WL_CONNECTED || !clockIsReady()) return;
  const time_t epoch = time(nullptr);
  const String identity = String(bootId) + "-" + String(sequenceNumber) + "-" + String(millis());
  const String nonce = "esp32-" + identity;
  const String batchId = "hil-" + identity;
  const String body = buildPayload(epoch, batchId);
  const String timestamp = String(static_cast<uint32_t>(epoch));
  const String signingMessage = String(AGRO_GATEWAY_ID) + timestamp + nonce + sha256Hex(body);
  const String signature = hmacSha256Hex(AGRO_GATEWAY_SECRET, signingMessage);

  Serial.printf("Device: %s\n", AGRO_DEVICE_ID);
  Serial.printf("Boot ID: %lu | Secuencia: %lu | Timestamp UTC: %s\n",
                static_cast<unsigned long>(bootId),
                static_cast<unsigned long>(sequenceNumber), timestamp.c_str());

  WiFiClient client;
  HTTPClient http;
  const String url = String(AGRO_BASE_URL) + "/api/iot/v1/ingest/batch";
  if (!http.begin(client, url)) {
    Serial.println("No se pudo iniciar HTTP");
    return;
  }
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-Agro-Gateway-ID", AGRO_GATEWAY_ID);
  http.addHeader("X-Agro-Timestamp", timestamp);
  http.addHeader("X-Agro-Nonce", nonce);
  http.addHeader("X-Agro-Signature", signature);

  const int status = http.POST(body);
  lastHttpStatus = status;
  const String response = status > 0 ? http.getString() : http.errorToString(status);
  Serial.printf("POST secuencia=%lu HTTP=%d\n", static_cast<unsigned long>(sequenceNumber), status);
  Serial.println(response);
  // Nunca imprimir WIFI_PASSWORD ni AGRO_GATEWAY_SECRET.
  http.end();
  if (status == HTTP_CODE_OK) {
    ++sequenceNumber;
    if (sequenceNumber % kHeapLogEverySuccessfulSends == 0) {
      Serial.printf("Free heap: %lu bytes despues de %lu envios\n",
                    static_cast<unsigned long>(ESP.getFreeHeap()),
                    static_cast<unsigned long>(sequenceNumber));
    }
  }
}
}  // namespace

void setup() {
  Serial.begin(115200);
  delay(300);
  Serial.println("AGROESCUDO HIL BENCH TEST");
  bootId = esp_random();
  Serial.printf("Device: %s\n", AGRO_DEVICE_ID);
  Serial.printf("Boot ID: %lu\n", static_cast<unsigned long>(bootId));
  Serial.println("HIL WIFI DROP TEST listo. Comandos: wifi_off | wifi_on | status");
  WiFi.setAutoReconnect(true);
  connectWifi();
  configTime(0, 0, "pool.ntp.org", "time.nist.gov");
}

void loop() {
  processSerialCommands();
  connectWifi();
  if (WiFi.status() != WL_CONNECTED) {
    wifiConnectedAnnounced = false;
    ntpSyncedAnnounced = false;
    delay(100);
    return;
  }

  if (!wifiConnectedAnnounced) {
    Serial.printf("WiFi conectado. IP: %s\n", WiFi.localIP().toString().c_str());
    wifiConnectedAnnounced = true;
  }

  if (clockIsReady()) {
    if (!ntpSyncedAnnounced) {
      Serial.printf("NTP sincronizado. UTC: %s\n", utcIso8601(time(nullptr)).c_str());
      ntpSyncedAnnounced = true;
    }
    const uint32_t now = millis();
    if (sequenceNumber == 0 || now - lastSendAt >= kSendIntervalMs) {
      lastSendAt = now;
      sendTelemetry();
    }
  }
  delay(100);
}
