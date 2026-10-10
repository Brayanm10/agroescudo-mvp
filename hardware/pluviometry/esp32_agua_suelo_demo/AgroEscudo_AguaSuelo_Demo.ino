/* Agua y Suelo commercial demo. All six readings are SIMULATED.
 * ESP32 Arduino core 3.x, ArduinoJson 7. Dedicated IoT credentials required.
 * One durable pending sample; acquisition pauses during transport failures.
 */
#include <Arduino.h>
#include <ArduinoJson.h>
#include <HTTPClient.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <Preferences.h>
#include <time.h>
#include <mbedtls/md.h>
#include <mbedtls/sha256.h>
#include <mbedtls/version.h>
#include "secrets.h"
#include "demo_weather.h"
#include "trusted_root.h"

namespace {
constexpr uint32_t cadenceMs = 60000;
constexpr char firmware[] = "agua-suelo-demo-1.0.0";
Preferences storage;
DemoWeather weather;
Scenario scenario = Scenario::Auto;
String command, pending;
uint32_t bootId, sequenceNumber = 0, acquired = 0, lastAcquired = 0;
uint32_t lastWifi = 0, lastAttempt = 0, retryMs = 5000;
bool halted = false, configured = false, storeReady = false;
int lastHttp = 0;

String hex(const unsigned char* bytes, size_t length) {
  const char* digits = "0123456789abcdef";
  String result;
  result.reserve(length * 2);
  for (size_t i = 0; i < length; ++i) { result += digits[bytes[i] >> 4]; result += digits[bytes[i] & 15]; }
  return result;
}
String hash(const String& body) {
  unsigned char digest[32];
#if MBEDTLS_VERSION_MAJOR >= 3
  mbedtls_sha256(reinterpret_cast<const unsigned char*>(body.c_str()), body.length(), digest, 0);
#else
  mbedtls_sha256_ret(reinterpret_cast<const unsigned char*>(body.c_str()), body.length(), digest, 0);
#endif
  return hex(digest, 32);
}
String signature(const String& message) {
  unsigned char digest[32];
  mbedtls_md_hmac(mbedtls_md_info_from_type(MBEDTLS_MD_SHA256),
    reinterpret_cast<const unsigned char*>(AGRO_GATEWAY_SECRET), strlen(AGRO_GATEWAY_SECRET),
    reinterpret_cast<const unsigned char*>(message.c_str()), message.length(), digest);
  return hex(digest, 32);
}
String iso(time_t epoch) {
  struct tm utc;
  gmtime_r(&epoch, &utc);
  char text[25]; strftime(text, sizeof(text), "%Y-%m-%dT%H:%M:%SZ", &utc);
  return String(text);
}
String requestId() {
  char text[40];
  snprintf(text, sizeof(text), "%08lx%08lx%08lx%08lx", (unsigned long)esp_random(),
    (unsigned long)esp_random(), (unsigned long)esp_random(), (unsigned long)esp_random());
  return String(text);
}
void addMetric(JsonArray metrics, const char* channel, const char* code, float value, const char* unit) {
  JsonObject metric = metrics.add<JsonObject>();
  metric["channel_key"] = channel; metric["metric_code"] = code;
  metric["raw_value"] = value; metric["unit"] = unit; metric["quality"] = "VALID";
}
bool acquire() {
  const time_t epoch = time(nullptr);
  weather.sample(scenario, epoch, acquired);
  JsonDocument document;
  document["device_id"] = AGRO_DEVICE_ID; document["boot_id"] = bootId;
  document["sequence"] = sequenceNumber; document["sample_counter"] = acquired;
  document["timestamp_utc"] = static_cast<uint32_t>(epoch);
  document["time_quality"] = "NTP_SYNCED"; document["protocol_version"] = 4;
  document["capabilities_version"] = 1; document["firmware_version"] = firmware;
  document["sensor_profile"] = "rain_gauge"; document["sensor_status_flags"] = 0;
  document["rssi_dbm"] = WiFi.RSSI();
  JsonArray metrics = document["metrics"].to<JsonArray>();
  addMetric(metrics, "rain_1", "RAIN_DELTA_MM", weather.rain, "mm");
  addMetric(metrics, "ambient_temp_1", "AMBIENT_TEMPERATURE_C", weather.temperature, "degC");
  addMetric(metrics, "ambient_rh_1", "AMBIENT_RELATIVE_HUMIDITY_PCT", weather.humidity, "percent");
  addMetric(metrics, "wind_speed_1", "WIND_SPEED_KMH", weather.wind, "km/h");
  addMetric(metrics, "wind_direction_1", "WIND_DIRECTION_DEG", weather.direction, "degree");
  addMetric(metrics, "battery_1", "BATTERY_PERCENT", weather.battery, "percent");
  String candidate; serializeJson(document, candidate);
  if (storage.putString("pending", candidate) != candidate.length()) {
    Serial.println("ERROR NVS: muestra no enviada; revisar almacenamiento"); halted = true; return false;
  }
  pending = candidate; ++acquired; lastAcquired = millis();
  Serial.printf("SIMULADO | Dispositivo: %s\nTemperatura: %.2f C\nHumedad: %.2f %%\nLluvia delta: %.3f mm\nViento: %.2f km/h\nDireccion FROM: %.2f grados\nBateria: %.2f %%\n",
    AGRO_DEVICE_ID, weather.temperature, weather.humidity, weather.rain, weather.wind, weather.direction, weather.battery);
  return true;
}
void sendPending() {
  JsonDocument event;
  if (deserializeJson(event, pending) || event["device_id"].as<String>() != String(AGRO_DEVICE_ID)) {
    halted = true; Serial.println("ERROR: muestra NVS invalida o de otro dispositivo; no se transmite"); return;
  }
  const String identity = requestId();
  const String timestamp = String(static_cast<uint32_t>(time(nullptr)));
  JsonDocument batch;
  batch["gateway_id"] = AGRO_GATEWAY_ID; batch["firmware_version"] = firmware;
  batch["sent_at"] = iso(time(nullptr)); batch["batch_id"] = "demo-" + identity;
  batch["protocol_version"] = 4;
  batch["events"].to<JsonArray>().add(event.as<JsonObject>());
  String body; serializeJson(batch, body);
  const String nonce = "demo-" + identity;
  const String signedValue = signature(String(AGRO_GATEWAY_ID) + timestamp + nonce + hash(body));
  WiFiClientSecure tls; tls.setCACert(AGRO_TRUSTED_ROOT);
  tls.setHandshakeTimeout(30);
  HTTPClient http; http.setConnectTimeout(30000); http.setTimeout(55000);
  if (!http.begin(tls, String(AGRO_BASE_URL) + "/api/iot/v1/ingest/batch")) return;
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-Agro-Gateway-ID", AGRO_GATEWAY_ID);
  http.addHeader("X-Agro-Timestamp", timestamp);
  http.addHeader("X-Agro-Nonce", nonce); http.addHeader("X-Agro-Signature", signedValue);
  Serial.println("Enviando por HTTPS con certificado validado...");
  lastHttp = http.POST(body);
  const String response = lastHttp > 0 ? http.getString() : "";
  http.end(); Serial.printf("HTTP %d\n", lastHttp);
  if (lastHttp == 200) {
    JsonDocument result;
    if (!deserializeJson(result, response) && result["batch_id"].as<String>() == "demo-" + identity
        && result["results"].size() == 1) {
      JsonObject item = result["results"][0];
      const String status = item["canonical_status"].as<String>();
      if (item["device_id"].as<String>() == String(AGRO_DEVICE_ID)
          && item["boot_id"].as<uint32_t>() == event["boot_id"].as<uint32_t>()
          && item["sequence"].as<uint32_t>() == event["sequence"].as<uint32_t>()) {
        Serial.println(status);
        if (status == "ACCEPTED" || status == "DUPLICATE") {
          if (!storage.remove("pending")) { halted = true; Serial.println("ERROR NVS al confirmar; se conserva muestra"); return; }
          if (event["boot_id"].as<uint32_t>() == bootId) ++sequenceNumber;
          pending = ""; retryMs = 5000;
          // Keep regular cadence, but do not burst to catch up after a long outage.
          if (millis() - lastAcquired >= cadenceMs) lastAcquired = millis();
          Serial.println("Proxima lectura: 60 segundos (cadencia de adquisicion)"); return;
        }
        if (status == "REJECTED" || status == "QUARANTINED") halted = true;
      }
    }
  }
  if (lastHttp == 400 || lastHttp == 401 || lastHttp == 403 || lastHttp == 404 || lastHttp == 422) halted = true;
  retryMs = min(retryMs * 2, static_cast<uint32_t>(60000));
  Serial.println(halted ? "Muestra conservada. Corregir configuracion y usar retry." : "Muestra conservada. Reintento con nueva firma y misma identidad.");
}
void status() {
  Serial.printf("AGROESCUDO — AGUA Y SUELO DEMO\nDATOS SIMULADOS\nWiFi: %s\nNTP: %s\nAPI: HTTPS\nDispositivo: %s\nHTTP anterior: %d\nPendiente durable: %s\nBloqueado: %s\n",
    WiFi.status() == WL_CONNECTED ? "conectado" : "desconectado",
    time(nullptr) >= 1700000000 ? "sincronizado" : "esperando", AGRO_DEVICE_ID,
    lastHttp, pending.length() ? "si" : "no", halted ? "si" : "no");
}
void handleCommand(String value) {
  value.trim(); value.toLowerCase();
  if (value == "status") { status(); return; }
  if (value == "retry") { if (storeReady) { halted = false; lastAttempt = millis() - retryMs; } return; }
  if (value == "normal") scenario = Scenario::Normal;
  else if (value == "dry") scenario = Scenario::Dry;
  else if (value == "rain_light") scenario = Scenario::Light;
  else if (value == "rain_heavy") scenario = Scenario::Heavy;
  else if (value == "storm") scenario = Scenario::Storm;
  else if (value == "battery_low") scenario = Scenario::BatteryLow;
  else if (value == "auto") scenario = Scenario::Auto;
  else { Serial.println("Comandos: status normal dry rain_light rain_heavy storm battery_low auto retry"); return; }
  Serial.printf("Escenario: %s — SIMULADO; aplica a la proxima muestra nueva\n", value.c_str());
}
}
void setup() {
  Serial.begin(115200); delay(300);
  bootId = esp_random();
  storeReady = storage.begin("agro-demo", false);
  if (!storeReady) { halted = true; Serial.println("ERROR NVS; transmision bloqueada"); }
  if (storeReady) pending = storage.getString("pending", "");
  configured = !String(WIFI_SSID).startsWith("REPLACE_")
    && !String(WIFI_PASSWORD).startsWith("REPLACE_")
    && !String(AGRO_GATEWAY_SECRET).startsWith("REPLACE_")
    && !String(AGRO_GATEWAY_ID).startsWith("REPLACE_")
    && !String(AGRO_DEVICE_ID).startsWith("REPLACE_")
    && String(AGRO_BASE_URL) == "https://agroescudo-api.onrender.com";
  WiFi.mode(WIFI_STA); WiFi.setAutoReconnect(true);
  configTime(0, 0, "pool.ntp.org", "time.nist.gov");
  status();
  if (!configured) Serial.println("Completar secrets.h con credenciales DEMO aprovisionadas. No se transmite.");
}
void loop() {
  while (Serial.available()) {
    const char c = Serial.read();
    if (c == '\n' || c == '\r') { if (command.length()) handleCommand(command); command = ""; }
    else if (command.length() < 48) command += c;
    else command = "";
  }
  const uint32_t now = millis();
  if (!configured || !storeReady || halted) { delay(10); return; }
  if (WiFi.status() != WL_CONNECTED) {
    if (!lastWifi || now - lastWifi >= 10000) { lastWifi = now; WiFi.begin(WIFI_SSID, WIFI_PASSWORD); Serial.println("Reconectando WiFi..."); }
    delay(10); return;
  }
  if (time(nullptr) < 1700000000) { delay(10); return; }
  if (!pending.length() && (!acquired || now - lastAcquired >= cadenceMs)) acquire();
  if (!halted && pending.length() && (!lastAttempt || now - lastAttempt >= retryMs)) { sendPending(); lastAttempt = millis(); }
  delay(10);
}
