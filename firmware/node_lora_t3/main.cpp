#include <Arduino.h>
#include <LoRa.h>
#include <Preferences.h>

#include "../shared/agro_crypto.h"
#include "../shared/protocol_tlv.h"
#include "sensor_manager.h"

static constexpr uint16_t DEVICE_ID = 1001;
static constexpr uint8_t KEY_VERSION = 1;
static constexpr uint16_t FIRMWARE_VERSION = 0x0101;
static constexpr uint32_t SAMPLE_INTERVAL_MS = 300000;
static constexpr uint8_t NODE_KEY[16] = {
  0x00, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77,
  0x88, 0x99, 0xaa, 0xbb, 0xcc, 0xdd, 0xee, 0xff
};

struct PendingPacketV4 {
  uint16_t payloadLength;
  uint8_t payload[AGRO_TLV_MAX_PAYLOAD];
};

Preferences prefs;
SensorManager sensors;
uint32_t bootId = 0;
uint32_t sequence = 0;

static bool waitForAck(uint32_t expectedSequence) {
  const uint32_t deadline = millis() + 3000;
  while (millis() < deadline) {
    const int packetSize = LoRa.parsePacket();
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

static bool sendPacket(const PendingPacketV4& packet) {
  if (packet.payloadLength < sizeof(AgroTelemetryHeaderV4) ||
      packet.payloadLength > AGRO_TLV_MAX_PAYLOAD) {
    return false;
  }
  AgroFrameHeader header{};
  header.magic = AGRO_MAGIC;
  header.protocol_version = AGRO_PROTOCOL_V4;
  header.message_type = AGRO_MSG_READING;
  header.key_version = KEY_VERSION;
  header.device_id = DEVICE_ID;
  header.boot_id = bootId;
  header.sequence = sequence;
  header.payload_len = packet.payloadLength;

  uint8_t encrypted[AGRO_TLV_MAX_PAYLOAD]{};
  uint8_t tag[AGRO_CCM_TAG_LEN]{};
  if (!agroEncryptPayload(
        header,
        NODE_KEY,
        packet.payload,
        packet.payloadLength,
        encrypted,
        tag)) {
    return false;
  }
  LoRa.beginPacket();
  LoRa.write(reinterpret_cast<uint8_t*>(&header), sizeof(header));
  LoRa.write(encrypted, packet.payloadLength);
  LoRa.write(tag, sizeof(tag));
  LoRa.endPacket();
  return waitForAck(sequence);
}

static PendingPacketV4 buildPacket() {
  PendingPacketV4 packet{};
  auto* header = reinterpret_cast<AgroTelemetryHeaderV4*>(packet.payload);
  auto* metrics = reinterpret_cast<AgroMetricTlv*>(
    packet.payload + sizeof(AgroTelemetryHeaderV4));
  uint16_t statusFlags = 0;
  const uint8_t metricCount = sensors.readAll(metrics, AGRO_TLV_MAX_METRICS, statusFlags);
  header->device_id = DEVICE_ID;
  header->sample_counter = sequence;
  header->timestamp_utc = 0;
  header->time_quality = 0;
  header->firmware_version = FIRMWARE_VERSION;
  header->capabilities_version = AGRO_CAPABILITIES_VERSION;
  header->metric_count = metricCount;
  header->sensor_status_flags = statusFlags;
  packet.payloadLength = agroTlvPayloadSize(metricCount);
  return packet;
}

static bool deliverWithRetry(const PendingPacketV4& packet) {
  for (uint8_t attempt = 0; attempt < 3; attempt++) {
    if (sendPacket(packet)) return true;
    delay(1000 * (attempt + 1));
  }
  return false;
}

void setup() {
  Serial.begin(115200);
  prefs.begin("agro-node", false);
  bootId = prefs.getUInt("boot", 0) + 1;
  sequence = prefs.getUInt("seq", 0);
  prefs.putUInt("boot", bootId);
  sensors.begin();
  if (!LoRa.begin(AGRO_LORA_FREQUENCY)) {
    Serial.println("LoRa init failed");
    while (true) delay(1000);
  }

  PendingPacketV4 recovered{};
  if (prefs.getBytesLength("pending-v4") == sizeof(recovered) &&
      prefs.getBytes("pending-v4", &recovered, sizeof(recovered)) == sizeof(recovered) &&
      deliverWithRetry(recovered)) {
    sequence++;
    prefs.putUInt("seq", sequence);
    prefs.remove("pending-v4");
  }
}

void loop() {
  const PendingPacketV4 packet = buildPacket();
  const auto* header = reinterpret_cast<const AgroTelemetryHeaderV4*>(packet.payload);
  if (header->metric_count == 0 ||
      !agroValidateTlvPayload(packet.payload, packet.payloadLength, DEVICE_ID)) {
    delay(SAMPLE_INTERVAL_MS);
    return;
  }

  // Persist before radio transmission. A reboot retries the exact same packet.
  prefs.putBytes("pending-v4", &packet, sizeof(packet));
  if (deliverWithRetry(packet)) {
    sequence++;
    prefs.putUInt("seq", sequence);
    prefs.remove("pending-v4");
  }
  delay(SAMPLE_INTERVAL_MS);
}
