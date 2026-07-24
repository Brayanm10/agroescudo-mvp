/*
  AgroEscudo - Nodo ESP32 LoRa para Arduino IDE

  Envia una lectura tecnica por LoRa al gateway.
  El paquete NO usa JSON por radio. Usa texto compacto con HMAC:

  AGRO3|node_id|boot_id|sequence|timestamp|profile|flags|grain_x100|air_x100|rh_x100|soil_raw|level_mm|battery_mv|status|fw|hmac

  Librerias:
  - LoRa by Sandeep Mistry

  Ajusta pines, frecuencia y NODE_SECRET antes de subir.
*/

#include <Arduino.h>
#include <SPI.h>
#include <LoRa.h>
#include "mbedtls/md.h"

// ===== CONFIGURACION DE PLACA / LORA =====
static const long LORA_BAND = 915E6;
static const int LORA_SCK = 5;
static const int LORA_MISO = 19;
static const int LORA_MOSI = 27;
static const int LORA_SS = 18;
static const int LORA_RST = 14;
static const int LORA_DIO0 = 26;
static const int ULTRASONIC_TRIG = 32;
static const int ULTRASONIC_ECHO = 33; // Usar divisor de tension hacia 3.3 V.
static const int SOIL_MOISTURE_PIN = 34;
static const int SENSOR_PROFILE = 1; // 1=SiloSensor, 2=CampoSensor.

// ===== IDENTIDAD DEL NODO =====
// Seed backend:
// SILO-001 -> 1001
// SILO-002 -> 1002
// GALPON-001 -> 1003
static const uint16_t NODE_ID = 1001;
static const uint16_t FIRMWARE_VERSION = 100;
static const char* NODE_SECRET = "cambia-esta-clave-node-1001";

// ===== TIEMPOS =====
static const unsigned long SEND_INTERVAL_MS = 60000;
static unsigned long lastSendMs = 0;
static uint32_t sequenceNumber = 1;
static uint32_t sampleCounter = 1;
static uint32_t bootId = 0;

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

int readBatteryMv() {
  // Para primera prueba usamos un valor estable.
  // Si tienes divisor resistivo, reemplaza por analogRead calibrado.
  return 3910;
}

int readGrainTempX100() {
  // Simulacion profesional para primera prueba.
  // Reemplaza con DS18B20, SHT31, DHT22 u otro sensor real.
  float base = 29.0 + (millis() % 12000) / 12000.0 * 4.0;
  return (int)(base * 100);
}

int readAirTempX100() {
  float base = 26.0 + (millis() % 10000) / 10000.0 * 3.0;
  return (int)(base * 100);
}

int readHumidityX100() {
  float base = 65.0 + (millis() % 15000) / 15000.0 * 10.0;
  return (int)(base * 100);
}

long readLevelDistanceMm() {
  long values[5];
  int valid = 0;
  for (int attempt = 0; attempt < 5; attempt++) {
    digitalWrite(ULTRASONIC_TRIG, LOW);
    delayMicroseconds(3);
    digitalWrite(ULTRASONIC_TRIG, HIGH);
    delayMicroseconds(12);
    digitalWrite(ULTRASONIC_TRIG, LOW);
    unsigned long duration = pulseIn(ULTRASONIC_ECHO, HIGH, 60000);
    long mm = (long)((duration * 0.343f) / 2.0f);
    if (duration > 0 && mm >= 200 && mm <= 20000) values[valid++] = mm;
    delay(70);
  }
  if (!valid) return -1;
  for (int i = 0; i < valid; i++) for (int j = i + 1; j < valid; j++) if (values[j] < values[i]) {
    long temp = values[i]; values[i] = values[j]; values[j] = temp;
  }
  return values[valid / 2];
}

String buildPacket() {
  // Nodo sin RTC confiable: manda 0. El gateway usara su hora NTP.
  uint32_t timestampUtc = 0;
  int grainX100 = readGrainTempX100();
  int airX100 = readAirTempX100();
  int rhX100 = readHumidityX100();
  int batteryMv = readBatteryMv();
  int sensorStatus = 0;
  long levelDistanceMm = SENSOR_PROFILE == 1 ? readLevelDistanceMm() : -1;
  int soilMoistureRaw = SENSOR_PROFILE == 2 ? analogRead(SOIL_MOISTURE_PIN) : 0;
  int metricFlags = 2 | 4 | 8; // ambiente, humedad y bateria
  if (SENSOR_PROFILE == 1) metricFlags |= 1; // temperatura de grano
  if (SENSOR_PROFILE == 2) metricFlags |= 128; // ADC raw de humedad de suelo
  if (levelDistanceMm > 0) { metricFlags |= 64; sensorStatus |= 64; }

  String body = "AGRO3|";
  body += String(NODE_ID) + "|";
  body += String(bootId) + "|";
  body += String(sequenceNumber) + "|";
  body += String(timestampUtc) + "|";
  body += String(SENSOR_PROFILE) + "|";
  body += String(metricFlags) + "|";
  body += String(grainX100) + "|";
  body += String(airX100) + "|";
  body += String(rhX100) + "|";
  body += String(soilMoistureRaw) + "|";
  body += String(levelDistanceMm > 0 ? levelDistanceMm : 0) + "|";
  body += String(batteryMv) + "|";
  body += String(sensorStatus) + "|";
  body += String(FIRMWARE_VERSION);

  String signature = hmacSha256Hex(body, NODE_SECRET);
  return body + "|" + signature;
}

void sendReading() {
  String packet = buildPacket();
  Serial.println("Enviando paquete LoRa:");
  Serial.println(packet);

  LoRa.beginPacket();
  LoRa.print(packet);
  LoRa.endPacket();

  sequenceNumber++;
  sampleCounter++;
}

void setup() {
  Serial.begin(115200);
  delay(1200);
  pinMode(ULTRASONIC_TRIG, OUTPUT);
  pinMode(ULTRASONIC_ECHO, INPUT);
  if (SENSOR_PROFILE == 2) pinMode(SOIL_MOISTURE_PIN, INPUT);

  bootId = (uint32_t)esp_random();
  Serial.println("AgroEscudo Nodo LoRa iniciando...");
  Serial.print("NODE_ID: ");
  Serial.println(NODE_ID);
  Serial.print("BOOT_ID: ");
  Serial.println(bootId);

  SPI.begin(LORA_SCK, LORA_MISO, LORA_MOSI, LORA_SS);
  LoRa.setPins(LORA_SS, LORA_RST, LORA_DIO0);

  if (!LoRa.begin(LORA_BAND)) {
    Serial.println("ERROR: No se pudo iniciar LoRa. Revisa pines/frecuencia.");
    while (true) {
      delay(1000);
    }
  }

  LoRa.setTxPower(17);
  LoRa.setSpreadingFactor(7);
  LoRa.setSignalBandwidth(125E3);
  LoRa.setCodingRate4(5);

  Serial.println("LoRa listo.");
  sendReading();
  lastSendMs = millis();
}

void loop() {
  if (millis() - lastSendMs >= SEND_INTERVAL_MS) {
    sendReading();
    lastSendMs = millis();
  }
}
