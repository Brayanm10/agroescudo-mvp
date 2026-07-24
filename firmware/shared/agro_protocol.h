#pragma once

#include <Arduino.h>

static constexpr uint16_t AGRO_MAGIC = 0xA650;
static constexpr uint8_t AGRO_MSG_READING = 0x01;
static constexpr uint8_t AGRO_MSG_ACK = 0x02;
static constexpr size_t AGRO_CCM_TAG_LEN = 8;
static constexpr uint8_t AGRO_PROTOCOL_V1 = 1;
static constexpr uint8_t AGRO_PROTOCOL_V2 = 2;
static constexpr uint8_t AGRO_PROTOCOL_V3 = 3;
static constexpr uint8_t AGRO_PROFILE_SILO = 1;
static constexpr uint8_t AGRO_PROFILE_FIELD = 2;

enum AgroMetricFlag : uint16_t {
  AGRO_HAS_GRAIN_TEMP = 1 << 0,
  AGRO_HAS_AIR_TEMP = 1 << 1,
  AGRO_HAS_AIR_HUMIDITY = 1 << 2,
  AGRO_HAS_BATTERY = 1 << 3,
  AGRO_HAS_SOIL_MOISTURE = 1 << 4,
  AGRO_HAS_SOIL_TEMP = 1 << 5,
  AGRO_HAS_LEVEL_DISTANCE = 1 << 6,
  AGRO_HAS_SOIL_MOISTURE_RAW = 1 << 7,
};

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

struct __attribute__((packed)) AgroReadingPayloadV1 {
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

struct __attribute__((packed)) AgroReadingPayloadV2 {
  uint32_t sample_counter;
  uint32_t timestamp_utc;
  uint8_t time_quality;
  uint8_t sensor_profile;
  uint16_t metric_flags;
  int16_t grain_temp_c_x100;
  int16_t air_temp_c_x100;
  uint16_t rh_x100;
  uint16_t soil_moisture_x100;
  int16_t soil_temp_c_x100;
  uint32_t level_distance_mm;
  uint16_t battery_mv;
  uint16_t sensor_status;
  uint16_t firmware_version;
};

struct __attribute__((packed)) AgroReadingPayloadV3 {
  uint32_t sample_counter;
  uint32_t timestamp_utc;
  uint8_t time_quality;
  uint8_t sensor_profile;
  uint16_t metric_flags;
  int16_t grain_temp_c_x100;
  int16_t air_temp_c_x100;
  uint16_t rh_x100;
  uint16_t soil_moisture_raw;
  int16_t soil_temp_c_x100;
  uint32_t level_distance_mm;
  uint16_t battery_mv;
  uint16_t sensor_status;
  uint16_t firmware_version;
};

using AgroReadingPayload = AgroReadingPayloadV1;

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

inline bool agroValidReadingRanges(const AgroReadingPayloadV2& payload) {
  if (payload.sensor_profile != AGRO_PROFILE_SILO && payload.sensor_profile != AGRO_PROFILE_FIELD) return false;
  if ((payload.metric_flags & AGRO_HAS_GRAIN_TEMP) && (payload.grain_temp_c_x100 < -4000 || payload.grain_temp_c_x100 > 10000)) return false;
  if ((payload.metric_flags & AGRO_HAS_AIR_TEMP) && (payload.air_temp_c_x100 < -4000 || payload.air_temp_c_x100 > 8000)) return false;
  if ((payload.metric_flags & AGRO_HAS_AIR_HUMIDITY) && payload.rh_x100 > 10000) return false;
  if ((payload.metric_flags & AGRO_HAS_SOIL_MOISTURE) && payload.soil_moisture_x100 > 10000) return false;
  if ((payload.metric_flags & AGRO_HAS_SOIL_TEMP) && (payload.soil_temp_c_x100 < -4000 || payload.soil_temp_c_x100 > 8000)) return false;
  if ((payload.metric_flags & AGRO_HAS_LEVEL_DISTANCE) && (payload.level_distance_mm == 0 || payload.level_distance_mm > 20000)) return false;
  if ((payload.metric_flags & AGRO_HAS_BATTERY) && payload.battery_mv > 6000) return false;
  if (payload.sensor_profile == AGRO_PROFILE_FIELD && (payload.metric_flags & (AGRO_HAS_GRAIN_TEMP | AGRO_HAS_LEVEL_DISTANCE))) return false;
  if (payload.sensor_profile == AGRO_PROFILE_SILO && (payload.metric_flags & (AGRO_HAS_SOIL_MOISTURE | AGRO_HAS_SOIL_TEMP))) return false;
  return payload.metric_flags != 0;
}

inline bool agroValidReadingRanges(const AgroReadingPayloadV3& payload) {
  if (payload.sensor_profile != AGRO_PROFILE_SILO && payload.sensor_profile != AGRO_PROFILE_FIELD) return false;
  if ((payload.metric_flags & AGRO_HAS_GRAIN_TEMP) && (payload.grain_temp_c_x100 < -4000 || payload.grain_temp_c_x100 > 10000)) return false;
  if ((payload.metric_flags & AGRO_HAS_AIR_TEMP) && (payload.air_temp_c_x100 < -4000 || payload.air_temp_c_x100 > 8000)) return false;
  if ((payload.metric_flags & AGRO_HAS_AIR_HUMIDITY) && payload.rh_x100 > 10000) return false;
  if ((payload.metric_flags & AGRO_HAS_SOIL_MOISTURE_RAW) && payload.soil_moisture_raw > 4095) return false;
  if ((payload.metric_flags & AGRO_HAS_SOIL_TEMP) && (payload.soil_temp_c_x100 < -4000 || payload.soil_temp_c_x100 > 8000)) return false;
  if ((payload.metric_flags & AGRO_HAS_LEVEL_DISTANCE) && (payload.level_distance_mm == 0 || payload.level_distance_mm > 20000)) return false;
  if ((payload.metric_flags & AGRO_HAS_BATTERY) && payload.battery_mv > 6000) return false;
  if (payload.sensor_profile == AGRO_PROFILE_FIELD && (payload.metric_flags & (AGRO_HAS_GRAIN_TEMP | AGRO_HAS_LEVEL_DISTANCE))) return false;
  if (payload.sensor_profile == AGRO_PROFILE_SILO && (payload.metric_flags & (AGRO_HAS_SOIL_MOISTURE_RAW | AGRO_HAS_SOIL_TEMP))) return false;
  return payload.metric_flags != 0;
}

inline void agroBuildNonce(const AgroFrameHeader& header, uint8_t nonce[12]) {
  memset(nonce, 0, 12);
  memcpy(&nonce[0], &header.device_id, sizeof(header.device_id));
  memcpy(&nonce[2], &header.boot_id, sizeof(header.boot_id));
  memcpy(&nonce[6], &header.sequence, sizeof(header.sequence));
}
