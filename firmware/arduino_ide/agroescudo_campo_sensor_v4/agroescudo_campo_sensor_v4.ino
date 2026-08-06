#include <Adafruit_SHT31.h>
#include <AgroEscudoProtocol.h>
#include <LoRa.h>
#include <Preferences.h>
#include <SPI.h>

#include "secrets.h"

static constexpr int AGRO_LORA_SCK_PIN = 5;
static constexpr int AGRO_LORA_MISO_PIN = 19;
static constexpr int AGRO_LORA_MOSI_PIN = 27;
static constexpr int AGRO_LORA_SS_PIN = 18;
static constexpr int AGRO_LORA_RST_PIN = 23;
static constexpr int AGRO_LORA_DIO0_PIN = 26;
static constexpr long LORA_FREQUENCY_HZ = 915E6;
static constexpr uint8_t LORA_SYNC_WORD = 0x12;
static constexpr int SOIL_MOISTURE_ADC_PIN = 32;
static constexpr int SHT31_SDA_PIN = 21;
static constexpr int SHT31_SCL_PIN = 22;
static constexpr int BATTERY_ADC_PIN = 35;
static constexpr uint32_t SAMPLE_INTERVAL_MS = 300000;
static constexpr uint16_t FIRMWARE_VERSION = 0x0100;
static constexpr uint16_t STATUS_SOIL_MOISTURE_OK = 1 << 0;
static constexpr uint16_t STATUS_AMBIENT_OK = 1 << 1;
static constexpr uint16_t STATUS_BATTERY_OK = 1 << 2;

struct PendingFrame {
  uint16_t payload_length;
  uint8_t payload[AGRO_TLV_MAX_PAYLOAD];
};

Preferences preferences;
Adafruit_SHT31 ambientSensor;
uint32_t bootId = 0;
uint32_t sequenceNumber = 0;

static bool addMetric(AgroMetricTlv* metrics, uint8_t& count, uint8_t metricId,
                      uint8_t channelId, int32_t value, uint8_t scale,
                      uint8_t quality = AGRO_QUALITY_VALID) {
  if (count >= AGRO_TLV_MAX_METRICS) return false;
  metrics[count++] = {metricId, channelId, value, scale, quality};
  return true;
}

static uint16_t medianAdc(int pin) {
  uint16_t samples[7]{};
  for (uint8_t index = 0; index < 7; index++) {
    samples[index] = analogRead(pin);
    delay(20);
  }
  for (uint8_t left = 0; left < 7; left++) {
    for (uint8_t right = left + 1; right < 7; right++) {
      if (samples[right] < samples[left]) {
        const uint16_t swap = samples[left];
        samples[left] = samples[right];
        samples[right] = swap;
      }
    }
  }
  return samples[3];
}

static uint16_t readBatteryMv() {
  return static_cast<uint16_t>(min<uint32_t>(6000, analogReadMilliVolts(BATTERY_ADC_PIN) * 2));
}

static PendingFrame buildFrame() {
  PendingFrame frame{};
  auto* header = reinterpret_cast<AgroTelemetryHeaderV4*>(frame.payload);
  auto* metrics = reinterpret_cast<AgroMetricTlv*>(frame.payload + sizeof(AgroTelemetryHeaderV4));
  uint8_t count = 0;
  uint16_t status = 0;

  const uint16_t soilRaw = medianAdc(SOIL_MOISTURE_ADC_PIN);
  if (soilRaw <= 4095) {
    addMetric(metrics, count, AGRO_METRIC_SOIL_MOISTURE_RAW,
              AGRO_CHANNEL_SOIL_MOISTURE_1, soilRaw, AGRO_SCALE_INTEGER);
    status |= STATUS_SOIL_MOISTURE_OK;
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

  const uint16_t batteryMv = readBatteryMv();
  if (batteryMv <= 6000) {
    addMetric(metrics, count, AGRO_METRIC_BATTERY_VOLTAGE_MV,
              AGRO_CHANNEL_BATTERY_1, batteryMv, AGRO_SCALE_INTEGER);
    status |= STATUS_BATTERY_OK;
  }

  header->device_id = AGRO_NODE_ID;
  header->sample_counter = sequenceNumber;
  header->timestamp_utc = 0;
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
        ack.sequence == expectedSequence && ack.accepted == 1) return true;
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
                          frame.payload_length, encrypted, tag)) return false;
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
  LoRa.disableCrc();
}

void setup() {
  Serial.begin(115200);
  analogReadResolution(12);
  pinMode(SOIL_MOISTURE_ADC_PIN, INPUT);
  pinMode(BATTERY_ADC_PIN, INPUT);
  Wire.begin(SHT31_SDA_PIN, SHT31_SCL_PIN);
  ambientSensor.begin(0x44);
  preferences.begin("agro-field", false);
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
