#include <Arduino.h>
#include <LoRa.h>
#include <Preferences.h>

#include "../shared/agro_crypto.h"

static constexpr uint16_t DEVICE_ID = 1001;
static constexpr uint8_t KEY_VERSION = 1;
static constexpr uint16_t FIRMWARE_VERSION = 0x0100;
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

static AgroReadingPayload readSensors() {
  AgroReadingPayload payload{};
  payload.sample_counter = sequence;
  payload.timestamp_utc = 0;
  payload.time_quality = 0;
  payload.grain_temp_c_x100 = 2540;
  payload.air_temp_c_x100 = 2380;
  payload.rh_x100 = 6320;
  payload.battery_mv = readBatteryMv();
  payload.sensor_status = 0x000F;
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

static bool sendReading(const AgroReadingPayload& payload) {
  AgroFrameHeader header{};
  header.magic = AGRO_MAGIC;
  header.protocol_version = AGRO_PROTOCOL_VERSION;
  header.message_type = AGRO_MSG_READING;
  header.key_version = KEY_VERSION;
  header.device_id = DEVICE_ID;
  header.boot_id = bootId;
  header.sequence = sequence;
  header.payload_len = sizeof(AgroReadingPayload);

  uint8_t encrypted[sizeof(AgroReadingPayload)]{};
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

  if (!LoRa.begin(AGRO_LORA_FREQUENCY)) {
    Serial.println("LoRa init failed");
    while (true) delay(1000);
  }
}

void loop() {
  AgroReadingPayload payload = readSensors();
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
