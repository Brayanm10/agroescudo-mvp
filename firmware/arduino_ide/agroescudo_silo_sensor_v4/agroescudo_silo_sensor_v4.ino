#include <Adafruit_SHT31.h>
#include <AgroEscudoProtocol.h>
#include <DallasTemperature.h>
#include <LoRa.h>
#include <OneWire.h>
#include <Preferences.h>
#include <SPI.h>

#include "secrets.h"

// LILYGO LoRa32/T3 V1.6.1 + SX1276. Confirma la revision impresa en tu placa.
static constexpr int AGRO_LORA_SCK_PIN = 5;
static constexpr int AGRO_LORA_MISO_PIN = 19;
static constexpr int AGRO_LORA_MOSI_PIN = 27;
static constexpr int AGRO_LORA_SS_PIN = 18;
static constexpr int AGRO_LORA_RST_PIN = 23;
static constexpr int AGRO_LORA_DIO0_PIN = 26;
static constexpr long LORA_FREQUENCY_HZ = 915E6;
static constexpr uint8_t LORA_SYNC_WORD = 0x12;

static constexpr int DS18B20_GRAIN_PIN = 4;
static constexpr int SHT31_SDA_PIN = 21;
static constexpr int SHT31_SCL_PIN = 22;
static constexpr int ULTRASONIC_TRIG_PIN = 32;
static constexpr int ULTRASONIC_ECHO_PIN = 33;
static constexpr int BATTERY_ADC_PIN = 35;
static constexpr uint32_t SAMPLE_INTERVAL_MS = 300000;
static constexpr uint16_t FIRMWARE_VERSION = 0x0100;
static constexpr uint16_t STATUS_GRAIN_OK = 1 << 0;
static constexpr uint16_t STATUS_AMBIENT_OK = 1 << 1;
static constexpr uint16_t STATUS_LEVEL_OK = 1 << 2;
static constexpr uint16_t STATUS_BATTERY_OK = 1 << 3;

struct PendingFrame {
  uint16_t payload_length;
  uint8_t payload[AGRO_TLV_MAX_PAYLOAD];
};

Preferences preferences;
OneWire oneWire(DS18B20_GRAIN_PIN);
DallasTemperature grainSensor(&oneWire);
Adafruit_SHT31 ambientSensor;
uint32_t bootId = 0;
uint32_t sequenceNumber = 0;

static bool addMetric(
  AgroMetricTlv* metrics,
  uint8_t& count,
  uint8_t metricId,
  uint8_t channelId,
  int32_t value,
  uint8_t scale,
  uint8_t quality = AGRO_QUALITY_VALID) {
  if (count >= AGRO_TLV_MAX_METRICS) return false;
  metrics[count++] = {metricId, channelId, value, scale, quality};
  return true;
}

static bool readUltrasonicMedian(uint32_t& distanceMm) {
  uint32_t samples[5]{};
  uint8_t valid = 0;
  for (uint8_t attempt = 0; attempt < 5; attempt++) {
    digitalWrite(ULTRASONIC_TRIG_PIN, LOW);
    delayMicroseconds(3);
    digitalWrite(ULTRASONIC_TRIG_PIN, HIGH);
    delayMicroseconds(12);
    digitalWrite(ULTRASONIC_TRIG_PIN, LOW);
    const uint32_t durationUs = pulseIn(ULTRASONIC_ECHO_PIN, HIGH, 60000);
    const uint32_t measuredMm = static_cast<uint32_t>(durationUs * 0.343f / 2.0f);
    if (durationUs > 0 && measuredMm >= 200 && measuredMm <= 20000) {
      samples[valid++] = measuredMm;
    }
    delay(70);
  }
  if (valid == 0) return false;
  for (uint8_t left = 0; left < valid; left++) {
    for (uint8_t right = left + 1; right < valid; right++) {
      if (samples[right] < samples[left]) {
        const uint32_t swap = samples[left];
        samples[left] = samples[right];
        samples[right] = swap;
      }
    }
  }
  distanceMm = samples[valid / 2];
  return true;
}

static uint16_t readBatteryMv() {
  // Ajusta el factor si tu placa usa otro divisor. Nunca excedas 3.3 V en el ADC.
  const uint32_t pinMv = analogReadMilliVolts(BATTERY_ADC_PIN);
  return static_cast<uint16_t>(min<uint32_t>(6000, pinMv * 2));
}

static PendingFrame buildFrame() {
  PendingFrame frame{};
  auto* header = reinterpret_cast<AgroTelemetryHeaderV4*>(frame.payload);
  auto* metrics = reinterpret_cast<AgroMetricTlv*>(frame.payload + sizeof(AgroTelemetryHeaderV4));
  uint8_t count = 0;
  uint16_t status = 0;

  grainSensor.requestTemperatures();
  const float grainC = grainSensor.getTempCByIndex(0);
  if (grainC != DEVICE_DISCONNECTED_C && grainC >= -40 && grainC <= 100) {
    addMetric(metrics, count, AGRO_METRIC_GRAIN_TEMPERATURE_C,
              AGRO_CHANNEL_GRAIN_TEMP_1, lroundf(grainC * 100), AGRO_SCALE_X100);
    status |= STATUS_GRAIN_OK;
  }

  const float airC = ambientSensor.readTemperature();
  const float humidity = ambientSensor.readHumidity();
  if (isfinite(airC) && airC >= -40 && airC <= 80) {
    addMetric(metrics, count, AGRO_METRIC_AMBIENT_TEMPERATURE_C,
              AGRO_CHANNEL_AMBIENT_TEMP_1, lroundf(airC * 100), AGRO_SCALE_X100);
  }
  if (isfinite(humidity) && humidity >= 0 && humidity <= 100) {
    addMetric(metrics, count, AGRO_METRIC_AMBIENT_RELATIVE_HUMIDITY_PCT,
              AGRO_CHANNEL_AMBIENT_RH_1, lroundf(humidity * 100), AGRO_SCALE_X100);
  }
  if (isfinite(airC) && isfinite(humidity)) status |= STATUS_AMBIENT_OK;

  uint32_t distanceMm = 0;
  if (readUltrasonicMedian(distanceMm)) {
    addMetric(metrics, count, AGRO_METRIC_LEVEL_DISTANCE_MM,
              AGRO_CHANNEL_LEVEL_ULTRASONIC_1, distanceMm, AGRO_SCALE_INTEGER);
    status |= STATUS_LEVEL_OK;
  }

  const uint16_t batteryMv = readBatteryMv();
  if (batteryMv <= 6000) {
    addMetric(metrics, count, AGRO_METRIC_BATTERY_VOLTAGE_MV,
              AGRO_CHANNEL_BATTERY_1, batteryMv, AGRO_SCALE_INTEGER);
    status |= STATUS_BATTERY_OK;
  }

  header->device_id = AGRO_NODE_ID;
  header->sample_counter = sequenceNumber;
  header->timestamp_utc = 0;  // El gateway asigna UTC si el nodo no tiene reloj confiable.
  header->time_quality = 0;
  header->firmware_version = FIRMWARE_VERSION;
  header->capabilities_version = AGRO_CAPABILITIES_VERSION;
  header->metric_count = count;
  header->sensor_status_flags = status;
  frame.payload_length = agroPayloadSize(count);
  return frame;
}

static bool waitForAck(uint32_t expectedSequence) {
  const uint32_t started = millis();
  while (millis() - started < 3500) {
    const int packetSize = LoRa.parsePacket();
    if (packetSize != static_cast<int>(sizeof(AgroFrameHeader) + sizeof(AgroAckPayload))) {
      delay(15);
      continue;
    }
    AgroFrameHeader header{};
    AgroAckPayload ack{};
    LoRa.readBytes(reinterpret_cast<uint8_t*>(&header), sizeof(header));
    LoRa.readBytes(reinterpret_cast<uint8_t*>(&ack), sizeof(ack));
    if (header.magic == AGRO_MAGIC && header.message_type == AGRO_MSG_ACK &&
        ack.device_id == AGRO_NODE_ID && ack.boot_id == bootId &&
        ack.sequence == expectedSequence && ack.accepted == 1) {
      return true;
    }
  }
  return false;
}

static bool transmit(const PendingFrame& frame) {
  AgroFrameHeader radioHeader{};
  radioHeader.magic = AGRO_MAGIC;
  radioHeader.protocol_version = AGRO_PROTOCOL_V4;
  radioHeader.message_type = AGRO_MSG_READING;
  radioHeader.key_version = AGRO_NODE_KEY_VERSION;
  radioHeader.device_id = AGRO_NODE_ID;
  radioHeader.boot_id = bootId;
  radioHeader.sequence = sequenceNumber;
  radioHeader.payload_len = frame.payload_length;
  uint8_t encrypted[AGRO_TLV_MAX_PAYLOAD]{};
  uint8_t tag[AGRO_CCM_TAG_LEN]{};
  if (!agroEncryptPayload(radioHeader, AGRO_NODE_AES_KEY, frame.payload,
                          frame.payload_length, encrypted, tag)) {
    return false;
  }
  for (uint8_t attempt = 0; attempt < 3; attempt++) {
    LoRa.beginPacket();
    LoRa.write(reinterpret_cast<uint8_t*>(&radioHeader), sizeof(radioHeader));
    LoRa.write(encrypted, frame.payload_length);
    LoRa.write(tag, sizeof(tag));
    LoRa.endPacket();
    if (waitForAck(sequenceNumber)) return true;
    delay(1000U * (attempt + 1));
  }
  return false;
}

static void configureLoRa() {
  SPI.begin(AGRO_LORA_SCK_PIN, AGRO_LORA_MISO_PIN, AGRO_LORA_MOSI_PIN, AGRO_LORA_SS_PIN);
  LoRa.setPins(AGRO_LORA_SS_PIN, AGRO_LORA_RST_PIN, AGRO_LORA_DIO0_PIN);
  if (!LoRa.begin(LORA_FREQUENCY_HZ)) {
    Serial.println("ERROR: SX1276 no encontrado. Revisa placa, antena y pines.");
    while (true) delay(1000);
  }
  LoRa.setSignalBandwidth(125E3);
  LoRa.setSpreadingFactor(7);
  LoRa.setCodingRate4(5);
  LoRa.setPreambleLength(8);
  LoRa.setSyncWord(LORA_SYNC_WORD);
  LoRa.disableCrc();  // AES-CCM autentica el frame y conserva compatibilidad con V4 existente.
}

void setup() {
  Serial.begin(115200);
  analogReadResolution(12);
  pinMode(ULTRASONIC_TRIG_PIN, OUTPUT);
  pinMode(ULTRASONIC_ECHO_PIN, INPUT);
  pinMode(BATTERY_ADC_PIN, INPUT);
  Wire.begin(SHT31_SDA_PIN, SHT31_SCL_PIN);
  grainSensor.begin();
  ambientSensor.begin(0x44);
  preferences.begin("agro-silo", false);
  bootId = preferences.getUInt("boot", 0) + 1;
  sequenceNumber = preferences.getUInt("sequence", 0);
  preferences.putUInt("boot", bootId);
  configureLoRa();

  PendingFrame recovered{};
  if (preferences.getBytesLength("pending") == sizeof(recovered) &&
      preferences.getBytes("pending", &recovered, sizeof(recovered)) == sizeof(recovered) &&
      transmit(recovered)) {
    sequenceNumber++;
    preferences.putUInt("sequence", sequenceNumber);
    preferences.remove("pending");
  }
}

void loop() {
  const PendingFrame frame = buildFrame();
  if (!agroValidatePayload(frame.payload, frame.payload_length, AGRO_NODE_ID)) {
    Serial.println("Lectura sin metricas validas; no se transmite.");
    delay(SAMPLE_INTERVAL_MS);
    return;
  }
  preferences.putBytes("pending", &frame, sizeof(frame));
  if (transmit(frame)) {
    sequenceNumber++;
    preferences.putUInt("sequence", sequenceNumber);
    preferences.remove("pending");
    Serial.println("Lectura confirmada por gateway.");
  } else {
    Serial.println("Sin ACK; lectura conservada para reintento.");
  }
  delay(SAMPLE_INTERVAL_MS);
}
