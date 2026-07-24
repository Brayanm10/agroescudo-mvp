#include <Arduino.h>
#include <LoRa.h>
#include <Preferences.h>

#include "../shared/agro_crypto.h"

static constexpr uint16_t DEVICE_ID = 1001;
static constexpr uint8_t KEY_VERSION = 1;
static constexpr uint16_t FIRMWARE_VERSION = 0x0100;
#ifndef AGRO_ULTRASONIC_TRIG_PIN
#define AGRO_ULTRASONIC_TRIG_PIN 32
#endif
#ifndef AGRO_ULTRASONIC_ECHO_PIN
#define AGRO_ULTRASONIC_ECHO_PIN 33
#endif
static constexpr uint8_t NODE_KEY[16] = {
  0x00, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77,
  0x88, 0x99, 0xaa, 0xbb, 0xcc, 0xdd, 0xee, 0xff
};

Preferences prefs;
uint32_t bootId = 0;
uint32_t sequence = 0;

static uint16_t readBatteryMv() {
  return 3910;
}

static bool readUltrasonicDistanceMm(uint32_t& distanceMm) {
  uint32_t samples[5]{};
  uint8_t valid = 0;
  for (uint8_t attempt = 0; attempt < 5; attempt++) {
    digitalWrite(AGRO_ULTRASONIC_TRIG_PIN, LOW);
    delayMicroseconds(3);
    digitalWrite(AGRO_ULTRASONIC_TRIG_PIN, HIGH);
    delayMicroseconds(12);
    digitalWrite(AGRO_ULTRASONIC_TRIG_PIN, LOW);
    const uint32_t durationUs = pulseIn(AGRO_ULTRASONIC_ECHO_PIN, HIGH, 60000);
    const uint32_t measuredMm = static_cast<uint32_t>((durationUs * 0.343f) / 2.0f);
    if (durationUs > 0 && measuredMm >= 200 && measuredMm <= 20000) samples[valid++] = measuredMm;
    delay(70);
  }
  if (!valid) return false;
  for (uint8_t i = 0; i < valid; i++) {
    for (uint8_t j = i + 1; j < valid; j++) {
      if (samples[j] < samples[i]) {
        const uint32_t current = samples[i];
        samples[i] = samples[j];
        samples[j] = current;
      }
    }
  }
  distanceMm = samples[valid / 2];
  return true;
}

static AgroReadingPayloadV3 readSensors() {
  AgroReadingPayloadV3 payload{};
  payload.sample_counter = sequence;
  payload.timestamp_utc = 0;
  payload.time_quality = 0;
  payload.sensor_profile = AGRO_SENSOR_PROFILE;
  payload.metric_flags = AGRO_HAS_AIR_TEMP | AGRO_HAS_AIR_HUMIDITY | AGRO_HAS_BATTERY;
  payload.air_temp_c_x100 = 2380;
  payload.rh_x100 = 6320;
  payload.battery_mv = readBatteryMv();
  if (payload.sensor_profile == AGRO_PROFILE_FIELD) {
    payload.soil_moisture_raw = analogRead(AGRO_SOIL_MOISTURE_PIN);
    payload.metric_flags |= AGRO_HAS_SOIL_MOISTURE_RAW;
    payload.sensor_status |= AGRO_HAS_SOIL_MOISTURE_RAW;
  } else {
    payload.grain_temp_c_x100 = 2540;
    payload.metric_flags |= AGRO_HAS_GRAIN_TEMP;
    uint32_t distanceMm = 0;
    if (readUltrasonicDistanceMm(distanceMm)) {
      payload.level_distance_mm = distanceMm;
      payload.metric_flags |= AGRO_HAS_LEVEL_DISTANCE;
      payload.sensor_status |= AGRO_HAS_LEVEL_DISTANCE;
    }
  }
  payload.sensor_status |= 0x000F;
  payload.firmware_version = FIRMWARE_VERSION;
  return payload;
}

static bool waitForAck(uint32_t expectedSequence) {
  const uint32_t deadline = millis() + 3000;
  while (millis() < deadline) {
    int packetSize = LoRa.parsePacket();
    if (packetSize != sizeof(AgroFrameHeader) + sizeof(AgroAckPayload)) {
      delay(20);
      continue;
    }
    AgroFrameHeader header{};
    AgroAckPayload ack{};
    LoRa.readBytes(reinterpret_cast<uint8_t*>(&header), sizeof(header));
    LoRa.readBytes(reinterpret_cast<uint8_t*>(&ack), sizeof(ack));
    if (header.magic == AGRO_MAGIC &&
        header.message_type == AGRO_MSG_ACK &&
        ack.device_id == DEVICE_ID &&
        ack.boot_id == bootId &&
        ack.sequence == expectedSequence &&
        ack.accepted == 1) {
      return true;
    }
  }
  return false;
}

static bool sendReading(const AgroReadingPayloadV3& payload) {
  AgroFrameHeader header{};
  header.magic = AGRO_MAGIC;
  header.protocol_version = AGRO_PROTOCOL_VERSION;
  header.message_type = AGRO_MSG_READING;
  header.key_version = KEY_VERSION;
  header.device_id = DEVICE_ID;
  header.boot_id = bootId;
  header.sequence = sequence;
  header.payload_len = sizeof(AgroReadingPayloadV3);

  uint8_t encrypted[sizeof(AgroReadingPayloadV3)]{};
  uint8_t tag[AGRO_CCM_TAG_LEN]{};
  if (!agroEncryptPayload(header, NODE_KEY, reinterpret_cast<const uint8_t*>(&payload), sizeof(payload), encrypted, tag)) {
    return false;
  }

  LoRa.beginPacket();
  LoRa.write(reinterpret_cast<uint8_t*>(&header), sizeof(header));
  LoRa.write(encrypted, sizeof(encrypted));
  LoRa.write(tag, sizeof(tag));
  LoRa.endPacket();
  return waitForAck(sequence);
}

void setup() {
  Serial.begin(115200);
  prefs.begin("agro-node", false);
  bootId = prefs.getUInt("boot", 0) + 1;
  sequence = prefs.getUInt("seq", 0);
  prefs.putUInt("boot", bootId);
  pinMode(AGRO_ULTRASONIC_TRIG_PIN, OUTPUT);
  pinMode(AGRO_ULTRASONIC_ECHO_PIN, INPUT);

  if (!LoRa.begin(AGRO_LORA_FREQUENCY)) {
    Serial.println("LoRa init failed");
    while (true) delay(1000);
  }
}

void loop() {
  AgroReadingPayloadV3 payload = readSensors();
  if (!agroValidReadingRanges(payload)) {
    delay(60000);
    return;
  }

  prefs.putBytes("pending", &payload, sizeof(payload));
  for (uint8_t attempt = 0; attempt < 3; attempt++) {
    if (sendReading(payload)) {
      sequence++;
      prefs.putUInt("seq", sequence);
      prefs.remove("pending");
      break;
    }
    delay(1000 * (attempt + 1));
  }
  delay(300000);
}
