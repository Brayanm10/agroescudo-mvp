#pragma once

#include <Arduino.h>

static constexpr uint16_t AGRO_MAGIC = 0xA650;
static constexpr uint8_t AGRO_MSG_READING = 0x01;
static constexpr uint8_t AGRO_MSG_ACK = 0x02;
static constexpr size_t AGRO_CCM_TAG_LEN = 8;

struct __attribute__((packed)) AgroFrameHeader {
  uint16_t magic;
  uint8_t protocol_version;
  uint8_t message_type;
  uint8_t key_version;
  uint16_t device_id;
  uint32_t boot_id;
  uint32_t sequence;
  uint16_t payload_len;
};

struct __attribute__((packed)) AgroReadingPayload {
  uint32_t sample_counter;
  uint32_t timestamp_utc;
  uint8_t time_quality;
  int16_t grain_temp_c_x100;
  int16_t air_temp_c_x100;
  uint16_t rh_x100;
  uint16_t battery_mv;
  uint16_t sensor_status;
  uint16_t firmware_version;
};

struct __attribute__((packed)) AgroAckPayload {
  uint16_t device_id;
  uint32_t boot_id;
  uint32_t sequence;
  uint8_t accepted;
};

inline bool agroValidReadingRanges(const AgroReadingPayload& payload) {
  return payload.grain_temp_c_x100 >= -4000 &&
         payload.grain_temp_c_x100 <= 10000 &&
         payload.air_temp_c_x100 >= -4000 &&
         payload.air_temp_c_x100 <= 8000 &&
         payload.rh_x100 <= 10000 &&
         payload.battery_mv <= 6000;
}

inline void agroBuildNonce(const AgroFrameHeader& header, uint8_t nonce[12]) {
  memset(nonce, 0, 12);
  memcpy(&nonce[0], &header.device_id, sizeof(header.device_id));
  memcpy(&nonce[2], &header.boot_id, sizeof(header.boot_id));
  memcpy(&nonce[6], &header.sequence, sizeof(header.sequence));
}
