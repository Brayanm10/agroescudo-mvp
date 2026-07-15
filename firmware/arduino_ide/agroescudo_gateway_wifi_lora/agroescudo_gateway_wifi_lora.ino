/*
  AgroEscudo - Gateway ESP32 LoRa/WiFi para Arduino IDE

  Recibe paquetes LoRa del nodo, valida HMAC y envia un batch HTTPS
  firmado a FastAPI:

  POST /api/iot/v1/ingest/batch

  Librerias:
  - LoRa by Sandeep Mistry
  - ArduinoJson by Benoit Blanchon

  Ajusta WiFi, pines, frecuencia, GATEWAY_SECRET y NODE_SECRET antes de subir.
*/

#include <Arduino.h>
#include <SPI.h>
#include <LoRa.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include <ArduinoJson.h>
#include <time.h>
#include "mbedtls/md.h"

// ===== WIFI =====
static const char* WIFI_SSID = "TU_WIFI";
static const char* WIFI_PASSWORD = "TU_PASSWORD_WIFI";

// ===== API AGROESCUDO =====
static const char* API_URL = "https://agroescudo-api.onrender.com/api/iot/v1/ingest/batch";
static const char* GATEWAY_ID = "GW-CBBA-001";
static const char* GATEWAY_SECRET = "pon-aqui-el-mismo-secreto-del-backend";
static const char* GATEWAY_FIRMWARE = "arduino-gateway-1.0.0";

// Para que puedas probar rapido en laboratorio queda en true.
// Para piloto real cambia a false y pega el certificado CA real en ROOT_CA.
static const bool USE_INSECURE_TLS_FOR_DEMO = true;

static const char* ROOT_CA = R"EOF(
-----BEGIN CERTIFICATE-----
PEGA_AQUI_EL_CERTIFICADO_CA_REAL_DEL_BACKEND
-----END CERTIFICATE-----
)EOF";

// ===== LORA =====
static const long LORA_BAND = 915E6;
static const int LORA_SCK = 5;
static const int LORA_MISO = 19;
static const int LORA_MOSI = 27;
static const int LORA_SS = 18;
static const int LORA_RST = 14;
static const int LORA_DIO0 = 26;

// ===== CLAVES POR NODO =====
static const char* NODE_SECRET_1001 = "cambia-esta-clave-node-1001";
static const char* NODE_SECRET_1002 = "cambia-esta-clave-node-1002";
static const char* NODE_SECRET_1003 = "cambia-esta-clave-node-1003";

struct Reading {
  uint16_t deviceId;
  uint32_t bootId;
  uint32_t sequence;
  uint32_t timestampUtc;
  int grainTempX100;
  int airTempX100;
  int rhX100;
  int batteryMv;
  int sensorStatus;
  int firmwareVersion;
  int rssiDbm;
  int snrDbX10;
};

String sha256Hex(const String& message) {
  byte hash[32];
  mbedtls_md_context_t ctx;
  const mbedtls_md_info_t* info = mbedtls_md_info_from_type(MBEDTLS_MD_SHA256);
  mbedtls_md_init(&ctx);
  mbedtls_md_setup(&ctx, info, 0);
  mbedtls_md_starts(&ctx);
  mbedtls_md_update(&ctx, (const unsigned char*)message.c_str(), message.length());
  mbedtls_md_finish(&ctx, hash);
  mbedtls_md_free(&ctx);

  char hex[65];
  for (int i = 0; i < 32; i++) {
    sprintf(hex + (i * 2), "%02x", hash[i]);
  }
  hex[64] = '\0';
  return String(hex);
}

String hmacSha256Hex(const String& message, const char* secret) {
  byte hmacResult[32];
  const mbedtls_md_info_t* mdInfo = mbedtls_md_info_from_type(MBEDTLS_MD_SHA256);
  mbedtls_md_context_t ctx;
  mbedtls_md_init(&ctx);
  mbedtls_md_setup(&ctx, mdInfo, 1);
  mbedtls_md_hmac_starts(&ctx, (const unsigned char*)secret, strlen(secret));
  mbedtls_md_hmac_update(&ctx, (const unsigned char*)message.c_str(), message.length());
  mbedtls_md_hmac_finish(&ctx, hmacResult);
  mbedtls_md_free(&ctx);

  char hex[65];
  for (int i = 0; i < 32; i++) {
    sprintf(hex + (i * 2), "%02x", hmacResult[i]);
  }
  hex[64] = '\0';
  return String(hex);
}

const char* nodeSecretFor(uint16_t nodeId) {
  if (nodeId == 1001) return NODE_SECRET_1001;
  if (nodeId == 1002) return NODE_SECRET_1002;
  if (nodeId == 1003) return NODE_SECRET_1003;
  return nullptr;
}

String isoTimestampUtc() {
  time_t now = time(nullptr);
  struct tm timeinfo;
  gmtime_r(&now, &timeinfo);
  char buffer[25];
  strftime(buffer, sizeof(buffer), "%Y-%m-%dT%H:%M:%SZ", &timeinfo);
  return String(buffer);
}

uint32_t unixNow() {
  time_t now = time(nullptr);
  return (uint32_t)now;
}

bool parsePacket(const String& packet, Reading& out) {
  int positions[12];
  int found = 0;
  for (int i = 0; i < packet.length() && found < 12; i++) {
    if (packet.charAt(i) == '|') {
      positions[found++] = i;
    }
  }

  if (found != 11) {
    Serial.println("Paquete rechazado: formato invalido.");
    return false;
  }

  String prefix = packet.substring(0, positions[0]);
  if (prefix != "AGRO1") {
    Serial.println("Paquete rechazado: prefijo invalido.");
    return false;
  }

  String signedBody = packet.substring(0, positions[10]);
  String receivedHmac = packet.substring(positions[10] + 1);

  uint16_t nodeId = packet.substring(positions[0] + 1, positions[1]).toInt();
  const char* secret = nodeSecretFor(nodeId);
  if (secret == nullptr) {
    Serial.println("Paquete rechazado: nodo no autorizado.");
    return false;
  }

  String expectedHmac = hmacSha256Hex(signedBody, secret);
  if (!expectedHmac.equalsIgnoreCase(receivedHmac)) {
    Serial.println("Paquete rechazado: HMAC LoRa invalido.");
    return false;
  }

  out.deviceId = nodeId;
  out.bootId = packet.substring(positions[1] + 1, positions[2]).toInt();
  out.sequence = packet.substring(positions[2] + 1, positions[3]).toInt();
  out.timestampUtc = packet.substring(positions[3] + 1, positions[4]).toInt();
  out.grainTempX100 = packet.substring(positions[4] + 1, positions[5]).toInt();
  out.airTempX100 = packet.substring(positions[5] + 1, positions[6]).toInt();
  out.rhX100 = packet.substring(positions[6] + 1, positions[7]).toInt();
  out.batteryMv = packet.substring(positions[7] + 1, positions[8]).toInt();
  out.sensorStatus = packet.substring(positions[8] + 1, positions[9]).toInt();
  out.firmwareVersion = packet.substring(positions[9] + 1, positions[10]).toInt();
  out.rssiDbm = LoRa.packetRssi();
  out.snrDbX10 = (int)(LoRa.packetSnr() * 10);

  if (out.timestampUtc == 0) {
    out.timestampUtc = unixNow();
  }

  return true;
}

String buildJsonBatch(const Reading& reading, const String& timestampIso, const String& batchId) {
  StaticJsonDocument<1024> doc;
  doc["gateway_id"] = GATEWAY_ID;
  doc["firmware_version"] = GATEWAY_FIRMWARE;
  doc["sent_at"] = timestampIso;
  doc["batch_id"] = batchId;

  JsonArray readings = doc.createNestedArray("readings");
  JsonObject r = readings.createNestedObject();
  r["device_id"] = reading.deviceId;
  r["boot_id"] = reading.bootId;
  r["sequence"] = reading.sequence;
  r["sample_counter"] = reading.sequence;
  r["timestamp_utc"] = reading.timestampUtc;
  r["time_quality"] = 1;
  r["grain_temp_c_x100"] = reading.grainTempX100;
  r["air_temp_c_x100"] = reading.airTempX100;
  r["rh_x100"] = reading.rhX100;
  r["battery_mv"] = reading.batteryMv;
  r["sensor_status"] = reading.sensorStatus;
  r["firmware_version"] = reading.firmwareVersion;
  r["rssi_dbm"] = reading.rssiDbm;
  r["snr_db_x10"] = reading.snrDbX10;

  String body;
  serializeJson(doc, body);
  return body;
}

bool postReading(const Reading& reading) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("No hay WiFi. No se envia batch.");
    return false;
  }

  String timestampIso = isoTimestampUtc();
  String nonce = String(GATEWAY_ID) + "-" + String(millis()) + "-" + String((uint32_t)esp_random());
  String batchId = String(GATEWAY_ID) + "-" + String(millis());
  String body = buildJsonBatch(reading, timestampIso, batchId);
  String bodyHash = sha256Hex(body);
  String signingMessage = String(GATEWAY_ID) + timestampIso + nonce + bodyHash;
  String signature = hmacSha256Hex(signingMessage, GATEWAY_SECRET);

  WiFiClientSecure client;
  if (USE_INSECURE_TLS_FOR_DEMO) {
    client.setInsecure();
  } else {
    client.setCACert(ROOT_CA);
  }

  HTTPClient http;
  http.setTimeout(30000);
  if (!http.begin(client, API_URL)) {
    Serial.println("HTTP begin fallo.");
    return false;
  }

  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-Agro-Gateway-ID", GATEWAY_ID);
  http.addHeader("X-Agro-Timestamp", timestampIso);
  http.addHeader("X-Agro-Nonce", nonce);
  http.addHeader("X-Agro-Signature", signature);

  Serial.println("Enviando batch a AgroEscudo...");
  Serial.println(body);

  int code = http.POST(body);
  String response = http.getString();
  http.end();

  Serial.print("HTTP ");
  Serial.println(code);
  Serial.println(response);

  return code >= 200 && code < 300;
}

void connectWifi() {
  Serial.print("Conectando WiFi ");
  Serial.println(WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 30000) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("WiFi conectado. IP: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("No se pudo conectar WiFi.");
  }
}

void syncTime() {
  configTime(0, 0, "pool.ntp.org", "time.google.com");
  Serial.print("Sincronizando hora NTP");
  unsigned long start = millis();
  while (unixNow() < 1700000000 && millis() - start < 20000) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  Serial.print("Hora UTC: ");
  Serial.println(isoTimestampUtc());
}

void setupLoRa() {
  SPI.begin(LORA_SCK, LORA_MISO, LORA_MOSI, LORA_SS);
  LoRa.setPins(LORA_SS, LORA_RST, LORA_DIO0);

  if (!LoRa.begin(LORA_BAND)) {
    Serial.println("ERROR: No se pudo iniciar LoRa. Revisa pines/frecuencia.");
    while (true) {
      delay(1000);
    }
  }

  LoRa.setSpreadingFactor(7);
  LoRa.setSignalBandwidth(125E3);
  LoRa.setCodingRate4(5);
  Serial.println("LoRa gateway listo.");
}

void setup() {
  Serial.begin(115200);
  delay(1200);

  Serial.println("AgroEscudo Gateway LoRa/WiFi iniciando...");
  connectWifi();
  syncTime();
  setupLoRa();
}

void loop() {
  int packetSize = LoRa.parsePacket();
  if (!packetSize) {
    delay(20);
    return;
  }

  String packet = "";
  while (LoRa.available()) {
    packet += (char)LoRa.read();
  }

  Serial.println("Paquete LoRa recibido:");
  Serial.println(packet);

  Reading reading;
  if (!parsePacket(packet, reading)) {
    return;
  }

  Serial.println("Lectura valida. Enviando a plataforma...");
  bool ok = postReading(reading);
  if (ok) {
    Serial.println("Lectura entregada a AgroEscudo.");
  } else {
    Serial.println("No se pudo entregar. En version avanzada debe quedar en cola local.");
  }
}
