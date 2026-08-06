#pragma once

#include <Arduino.h>

#include "agro_protocol.h"
#include "metric_registry.h"
#include "quality_codes.h"

static constexpr uint8_t AGRO_TLV_MAX_METRICS = 12;
static constexpr uint16_t AGRO_CAPABILITIES_VERSION = 1;

enum AgroScaleCode : uint8_t {
  AGRO_SCALE_INTEGER = 0,
  AGRO_SCALE_X10 = 1,
  AGRO_SCALE_X100 = 2,
  AGRO_SCALE_X1000 = 3,
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

static constexpr size_t AGRO_TLV_MAX_PAYLOAD =
  sizeof(AgroTelemetryHeaderV4) + AGRO_TLV_MAX_METRICS * sizeof(AgroMetricTlv);

inline size_t agroTlvPayloadSize(uint8_t metricCount) {
  return sizeof(AgroTelemetryHeaderV4) + metricCount * sizeof(AgroMetricTlv);
}

inline float agroScaledValue(const AgroMetricTlv& metric) {
  switch (metric.scale_code) {
    case AGRO_SCALE_X10: return metric.value_scaled / 10.0f;
    case AGRO_SCALE_X100: return metric.value_scaled / 100.0f;
    case AGRO_SCALE_X1000: return metric.value_scaled / 1000.0f;
    default: return static_cast<float>(metric.value_scaled);
  }
}

inline bool agroValidMetricTlv(const AgroMetricTlv& metric) {
  if (metric.metric_id < AGRO_METRIC_GRAIN_TEMPERATURE_C ||
      metric.metric_id > AGRO_METRIC_TIME_QUALITY ||
      agroMetricCode(metric.metric_id) == nullptr ||
      agroChannelKey(metric.channel_id) == nullptr) {
    return false;
  }
  if (metric.quality_code < AGRO_QUALITY_VALID ||
      metric.quality_code > AGRO_QUALITY_OUT_OF_RANGE) {
    return false;
  }
  const float value = agroScaledValue(metric);
  switch (metric.metric_id) {
    case AGRO_METRIC_GRAIN_TEMPERATURE_C: return value >= -40 && value <= 100;
    case AGRO_METRIC_AMBIENT_TEMPERATURE_C: return value >= -40 && value <= 80;
    case AGRO_METRIC_AMBIENT_RELATIVE_HUMIDITY_PCT: return value >= 0 && value <= 100;
    case AGRO_METRIC_SOIL_MOISTURE_RAW: return value >= 0 && value <= 4095;
    case AGRO_METRIC_LEVEL_DISTANCE_MM: return value >= 20 && value <= 20000;
    case AGRO_METRIC_BATTERY_VOLTAGE_MV: return value >= 0 && value <= 6000;
    default: return true;
  }
}

inline bool agroValidateTlvPayload(
  const uint8_t* payload,
  size_t payloadLength,
  uint32_t expectedDeviceId) {
  if (payloadLength < sizeof(AgroTelemetryHeaderV4)) return false;
  const auto* header = reinterpret_cast<const AgroTelemetryHeaderV4*>(payload);
  if (header->device_id != expectedDeviceId ||
      header->metric_count == 0 ||
      header->metric_count > AGRO_TLV_MAX_METRICS ||
      agroTlvPayloadSize(header->metric_count) != payloadLength) {
    return false;
  }
  const auto* metrics = reinterpret_cast<const AgroMetricTlv*>(
    payload + sizeof(AgroTelemetryHeaderV4));
  for (uint8_t index = 0; index < header->metric_count; index++) {
    if (!agroValidMetricTlv(metrics[index])) return false;
    for (uint8_t previous = 0; previous < index; previous++) {
      if (metrics[index].metric_id == metrics[previous].metric_id &&
          metrics[index].channel_id == metrics[previous].channel_id) {
        return false;
      }
    }
  }
  return true;
}
