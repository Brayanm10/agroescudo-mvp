#pragma once

#include <Arduino.h>

static constexpr uint16_t AGRO_MAGIC = 0xA650;
static constexpr uint8_t AGRO_PROTOCOL_V4 = 4;
static constexpr uint8_t AGRO_MSG_READING = 0x01;
static constexpr uint8_t AGRO_MSG_ACK = 0x02;
static constexpr size_t AGRO_CCM_TAG_LEN = 8;
static constexpr uint8_t AGRO_TLV_MAX_METRICS = 12;
static constexpr uint16_t AGRO_CAPABILITIES_VERSION = 1;

enum AgroMetricId : uint8_t {
  AGRO_METRIC_GRAIN_TEMPERATURE_C = 1,
  AGRO_METRIC_AMBIENT_TEMPERATURE_C = 2,
  AGRO_METRIC_AMBIENT_RELATIVE_HUMIDITY_PCT = 3,
  AGRO_METRIC_SOIL_MOISTURE_RAW = 4,
  AGRO_METRIC_SOIL_MOISTURE_PCT = 5,
  AGRO_METRIC_LEVEL_DISTANCE_MM = 6,
  AGRO_METRIC_LEVEL_PERCENT = 7,
  AGRO_METRIC_BATTERY_VOLTAGE_MV = 8,
  AGRO_METRIC_BATTERY_PERCENT = 9,
  AGRO_METRIC_SIGNAL_RSSI_DBM = 10,
  AGRO_METRIC_SIGNAL_SNR_DB = 11,
  AGRO_METRIC_DEVICE_INTERNAL_TEMPERATURE_C = 12,
  AGRO_METRIC_GATEWAY_QUEUE_SIZE = 13,
  AGRO_METRIC_SENSOR_STATUS_FLAGS = 14,
  AGRO_METRIC_TIME_QUALITY = 15,
};

enum AgroChannelId : uint8_t {
  AGRO_CHANNEL_GRAIN_TEMP_1 = 1,
  AGRO_CHANNEL_AMBIENT_TEMP_1 = 2,
  AGRO_CHANNEL_AMBIENT_RH_1 = 3,
  AGRO_CHANNEL_SOIL_MOISTURE_1 = 4,
  AGRO_CHANNEL_LEVEL_ULTRASONIC_1 = 5,
  AGRO_CHANNEL_BATTERY_1 = 6,
  AGRO_CHANNEL_SOIL_TEMP_1 = 7,
};

enum AgroScaleCode : uint8_t {
  AGRO_SCALE_INTEGER = 0,
  AGRO_SCALE_X10 = 1,
  AGRO_SCALE_X100 = 2,
  AGRO_SCALE_X1000 = 3,
};

enum AgroQualityCode : uint8_t {
  AGRO_QUALITY_VALID = 1,
  AGRO_QUALITY_SUSPECT = 2,
  AGRO_QUALITY_SENSOR_FAULT = 3,
  AGRO_QUALITY_OUT_OF_RANGE = 4,
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

struct __attribute__((packed)) AgroTelemetryHeaderV4 {
  uint32_t device_id;
  uint32_t sample_counter;
  uint32_t timestamp_utc;
  uint8_t time_quality;
  uint16_t firmware_version;
  uint16_t capabilities_version;
  uint8_t metric_count;
  uint16_t sensor_status_flags;
};

struct __attribute__((packed)) AgroMetricTlv {
  uint8_t metric_id;
  uint8_t channel_id;
  int32_t value_scaled;
  uint8_t scale_code;
  uint8_t quality_code;
};

struct __attribute__((packed)) AgroAckPayload {
  uint16_t device_id;
  uint32_t boot_id;
  uint32_t sequence;
  uint8_t accepted;
};

static constexpr size_t AGRO_TLV_MAX_PAYLOAD =
  sizeof(AgroTelemetryHeaderV4) + AGRO_TLV_MAX_METRICS * sizeof(AgroMetricTlv);

size_t agroPayloadSize(uint8_t metricCount);
float agroScaledValue(const AgroMetricTlv& metric);
const char* agroMetricCode(uint8_t metricId);
const char* agroChannelKey(uint8_t channelId);
const char* agroCanonicalUnit(uint8_t metricId);
const char* agroQualityCode(uint8_t quality);
bool agroValidatePayload(const uint8_t* payload, size_t payloadLength, uint16_t expectedDeviceId);
bool agroEncryptPayload(
  const AgroFrameHeader& header,
  const uint8_t key[16],
  const uint8_t* plain,
  size_t plainLength,
  uint8_t* encrypted,
  uint8_t tag[AGRO_CCM_TAG_LEN]);
bool agroDecryptPayload(
  const AgroFrameHeader& header,
  const uint8_t key[16],
  const uint8_t* encrypted,
  size_t encryptedLength,
  const uint8_t tag[AGRO_CCM_TAG_LEN],
  uint8_t* plain);
