#include <Arduino.h>
#include <ArduinoJson.h>
#include <HTTPClient.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

#ifdef AGRO_SENTINEL_COMPILE_TEST
#include "secrets.example.h"
#else
#include "secrets.h"
#endif

static constexpr char FIRMWARE_VERSION[] = "0.2.0";
static constexpr int OLED_WIDTH = 128;
static constexpr int OLED_HEIGHT = 64;
static constexpr int OLED_ADDRESS = 0x3C;
static constexpr int I2C_SDA_PIN = 21;
static constexpr int I2C_SCL_PIN = 22;
static constexpr int SIM800_RX_PIN = 16;  // ESP32 RX <- SIM800 TX
static constexpr int SIM800_TX_PIN = 17;  // ESP32 TX -> SIM800 RX (adaptar nivel si corresponde)
static constexpr uint32_t SIM800_BAUD = 9600;
static constexpr uint32_t WIFI_RETRY_MS = 15000;
static constexpr uint32_t HTTP_TIMEOUT_MS = 25000;

Adafruit_SSD1306 display(OLED_WIDTH, OLED_HEIGHT, &Wire, -1);
HardwareSerial sim800(2);

uint32_t nextPollAt = 0;
uint32_t lastWifiAttemptAt = 0;
uint32_t pollIntervalMs = 60000;
bool apiOnline = false;
bool dbOnline = false;
bool gsmRegistered = false;
bool simReady = false;
int pendingJobs = 0;
String lastJobStatus = "none";

String readModem(uint32_t timeoutMs) {
  String response;
  const uint32_t started = millis();
  while (millis() - started < timeoutMs) {
    while (sim800.available()) response += static_cast<char>(sim800.read());
    delay(10);
  }
  return response;
}

bool modemCommand(const String& command, const char* expected, uint32_t timeoutMs = 2000) {
  while (sim800.available()) sim800.read();
  sim800.println(command);
  const String response = readModem(timeoutMs);
  return response.indexOf(expected) >= 0;
}

void refreshModemStatus() {
  simReady = modemCommand("AT+CPIN?", "READY");
  gsmRegistered = modemCommand("AT+CREG?", ",1") || modemCommand("AT+CREG?", ",5");
}

String maskedPhone(const String& phone) {
  if (phone.length() < 7) return "***";
  return phone.substring(0, 4) + "******" + phone.substring(phone.length() - 3);
}

bool sendSms(const String& phone, const String& message, String& code) {
  if (!simReady) { code = "SIM_NOT_READY"; return false; }
  if (!gsmRegistered) { code = "GSM_NOT_REGISTERED"; return false; }
  if (!modemCommand("AT+CMGF=1", "OK")) { code = "SIM800_CMGF_FAILED"; return false; }
  while (sim800.available()) sim800.read();
  sim800.print("AT+CMGS=\"");
  sim800.print(phone);
  sim800.println("\"");
  const String prompt = readModem(3000);
  if (prompt.indexOf('>') < 0) { code = "SIM800_CMGS_PROMPT_FAILED"; return false; }
  sim800.print(message);
  sim800.write(26);
  const String response = readModem(15000);
  if (response.indexOf("+CMGS:") >= 0 && response.indexOf("OK") >= 0) {
    code = "SIM800_CMGS_OK";
    return true;
  }
  code = "SIM800_CMGS_FAILED";
  return false;
}

bool attemptCall(const String& phone, int ringSeconds, String& code) {
  if (!simReady) { code = "SIM_NOT_READY"; return false; }
  if (!gsmRegistered) { code = "GSM_NOT_REGISTERED"; return false; }
  if (!modemCommand("ATD" + phone + ";", "OK", 5000)) {
    code = "SIM800_CALL_FAILED";
    return false;
  }
  delay(static_cast<uint32_t>(constrain(ringSeconds, 5, 60)) * 1000UL);
  modemCommand("ATH", "OK", 3000);
  code = "SIM800_CALL_STARTED";
  return true;
}

void drawStatus() {
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.println("AGROESCUDO SENTINEL");
  display.println("--------------------");
  display.printf("WiFi %s %d dBm\n", WiFi.status() == WL_CONNECTED ? "OK " : "OFF", WiFi.RSSI());
  display.printf("API  %s  DB %s\n", apiOnline ? "OK" : "OFF", dbOnline ? "OK" : "OFF");
  display.printf("GSM  %s SIM %s\n", gsmRegistered ? "REG" : "OFF", simReady ? "OK" : "OFF");
  display.printf("Jobs %d\n", pendingJobs);
  display.print("Last ");
  display.println(lastJobStatus.substring(0, 15));
  display.display();
}

void ensureWifi() {
  if (WiFi.status() == WL_CONNECTED) return;
  if (millis() - lastWifiAttemptAt < WIFI_RETRY_MS) return;
  lastWifiAttemptAt = millis();
  WiFi.disconnect();
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
}

bool postJson(const String& path, const String& body, String& responseBody, int& httpCode) {
  if (WiFi.status() != WL_CONNECTED) { httpCode = 0; return false; }
  WiFiClientSecure tls;
  tls.setCACert(AGRO_ROOT_CA);
  HTTPClient http;
  http.setTimeout(HTTP_TIMEOUT_MS);
  if (!http.begin(tls, String(API_BASE_URL) + path)) { httpCode = 0; return false; }
  http.addHeader("Content-Type", "application/json");
  http.addHeader("Authorization", String("Bearer ") + SENTINEL_TOKEN);
  httpCode = http.POST(body);
  responseBody = httpCode > 0 ? http.getString() : "";
  http.end();
  return httpCode >= 200 && httpCode < 300;
}

void reportJobResult(const String& jobId, const String& status, const String& code, const String& message) {
  JsonDocument result;
  result["status"] = status;
  result["result_code"] = code;
  if (message.length()) result["message"] = message;
  String body;
  serializeJson(result, body);
  String response;
  int httpCode = 0;
  if (postJson("/api/sentinel/jobs/" + jobId + "/result", body, response, httpCode)) {
    lastJobStatus = status;
  } else {
    lastJobStatus = "result_error";
  }
}

void executeJob(JsonObjectConst job) {
  const String id = job["id"] | "";
  const String type = job["type"] | "";
  const String phone = job["phone"] | "";
  const String message = job["message"] | "";
  const int ringSeconds = job["ring_seconds"] | 25;
  if (!id.length() || !phone.length()) return;

  Serial.printf("Sentinel job %s -> %s\n", type.c_str(), maskedPhone(phone).c_str());
  String code;
  bool ok = false;
  if (type == "sms") {
    ok = sendSms(phone, message, code);
    reportJobResult(id, ok ? "submitted" : "failed", code, ok ? "" : "El modem no acepto el SMS.");
  } else if (type == "call") {
    ok = attemptCall(phone, ringSeconds, code);
    reportJobResult(id, ok ? "attempted" : "failed", code, ok ? "" : "El modem no pudo iniciar la llamada.");
  } else {
    reportJobResult(id, "failed", "UNSUPPORTED_JOB_TYPE", "Tipo de trabajo no soportado por firmware.");
  }
}

void pollCloud() {
  refreshModemStatus();
  JsonDocument payload;
  payload["device_uid"] = SENTINEL_DEVICE_UID;
  payload["firmware_version"] = FIRMWARE_VERSION;
  payload["uptime_seconds"] = millis() / 1000UL;
  payload["wifi_rssi"] = WiFi.status() == WL_CONNECTED ? WiFi.RSSI() : -127;
  payload["gsm_registered"] = gsmRegistered;
  payload["sim_ready"] = simReady;
  String body;
  serializeJson(payload, body);

  String responseBody;
  int httpCode = 0;
  if (!postJson("/api/sentinel/poll", body, responseBody, httpCode)) {
    apiOnline = false;
    dbOnline = false;
    nextPollAt = millis() + 30000UL;
    drawStatus();
    return;
  }

  JsonDocument response;
  if (deserializeJson(response, responseBody)) {
    apiOnline = false;
    nextPollAt = millis() + 30000UL;
    return;
  }
  apiOnline = String(response["server"] | "") == "online";
  dbOnline = String(response["database"] | "") == "online";
  pendingJobs = response["pending_jobs"] | 0;
  lastJobStatus = String(response["last_job_status"] | lastJobStatus);
  const int pollSeconds = constrain(response["poll_after_seconds"] | 60, 30, 600);
  pollIntervalMs = static_cast<uint32_t>(pollSeconds) * 1000UL;
  nextPollAt = millis() + pollIntervalMs;
  drawStatus();
  if (!response["job"].isNull()) executeJob(response["job"].as<JsonObjectConst>());
}

void setup() {
  Serial.begin(115200);
  sim800.begin(SIM800_BAUD, SERIAL_8N1, SIM800_RX_PIN, SIM800_TX_PIN);
  Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN);
  display.begin(SSD1306_SWITCHCAPVCC, OLED_ADDRESS);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  modemCommand("AT", "OK", 3000);
  modemCommand("ATE0", "OK", 2000);
  drawStatus();
  nextPollAt = 1000;
}

void loop() {
  ensureWifi();
  if (static_cast<int32_t>(millis() - nextPollAt) >= 0) pollCloud();
  delay(100);
}
