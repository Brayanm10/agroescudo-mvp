#include "AgroEscudoProtocol.h"

#include <math.h>
#include "mbedtls/ccm.h"

namespace {

void buildNonce(const AgroFrameHeader& header, uint8_t nonce[12]) {
  memset(nonce, 0, 12);
  memcpy(&nonce[0], &header.device_id, sizeof(header.device_id));
  memcpy(&nonce[2], &header.boot_id, sizeof(header.boot_id));
  memcpy(&nonce[6], &header.sequence, sizeof(header.sequence));
}

void buildAad(const AgroFrameHeader& header, uint8_t aad[15]) {
  memcpy(&aad[0], &header.magic, 2);
  aad[2] = header.protocol_version;
  aad[3] = header.message_type;
  aad[4] = header.key_version;
  memcpy(&aad[5], &header.device_id, 2);
  memcpy(&aad[7], &header.boot_id, 4);
  memcpy(&aad[11], &header.sequence, 4);
}

bool metricRangeIsValid(const AgroMetricTlv& metric) {
  const float value = agroScaledValue(metric);
  if (!isfinite(value)) return false;
  switch (metric.metric_id) {
    case AGRO_METRIC_GRAIN_TEMPERATURE_C: return value >= -40 && value <= 100;
    case AGRO_METRIC_AMBIENT_TEMPERATURE_C: return value >= -40 && value <= 80;
    case AGRO_METRIC_AMBIENT_RELATIVE_HUMIDITY_PCT: return value >= 0 && value <= 100;
    case AGRO_METRIC_SOIL_MOISTURE_RAW: return value >= 0 && value <= 4095;
    case AGRO_METRIC_SOIL_MOISTURE_PCT:
    case AGRO_METRIC_LEVEL_PERCENT:
    case AGRO_METRIC_BATTERY_PERCENT: return value >= 0 && value <= 100;
    case AGRO_METRIC_LEVEL_DISTANCE_MM: return value >= 20 && value <= 20000;
    case AGRO_METRIC_BATTERY_VOLTAGE_MV: return value >= 0 && value <= 6000;
    default: return true;
  }
}

}  // namespace

size_t agroPayloadSize(uint8_t metricCount) {
  return sizeof(AgroTelemetryHeaderV4) + metricCount * sizeof(AgroMetricTlv);
}

float agroScaledValue(const AgroMetricTlv& metric) {
  switch (metric.scale_code) {
    case AGRO_SCALE_X10: return metric.value_scaled / 10.0f;
    case AGRO_SCALE_X100: return metric.value_scaled / 100.0f;
    case AGRO_SCALE_X1000: return metric.value_scaled / 1000.0f;
    default: return static_cast<float>(metric.value_scaled);
  }
}

const char* agroMetricCode(uint8_t metricId) {
  switch (metricId) {
    case AGRO_METRIC_GRAIN_TEMPERATURE_C: return "GRAIN_TEMPERATURE_C";
    case AGRO_METRIC_AMBIENT_TEMPERATURE_C: return "AMBIENT_TEMPERATURE_C";
    case AGRO_METRIC_AMBIENT_RELATIVE_HUMIDITY_PCT: return "AMBIENT_RELATIVE_HUMIDITY_PCT";
    case AGRO_METRIC_SOIL_MOISTURE_RAW: return "SOIL_MOISTURE_RAW";
    case AGRO_METRIC_SOIL_MOISTURE_PCT: return "SOIL_MOISTURE_PCT";
    case AGRO_METRIC_LEVEL_DISTANCE_MM: return "LEVEL_DISTANCE_MM";
    case AGRO_METRIC_LEVEL_PERCENT: return "LEVEL_PERCENT";
    case AGRO_METRIC_BATTERY_VOLTAGE_MV: return "BATTERY_VOLTAGE_MV";
    case AGRO_METRIC_BATTERY_PERCENT: return "BATTERY_PERCENT";
    case AGRO_METRIC_SIGNAL_RSSI_DBM: return "SIGNAL_RSSI_DBM";
    case AGRO_METRIC_SIGNAL_SNR_DB: return "SIGNAL_SNR_DB";
    case AGRO_METRIC_DEVICE_INTERNAL_TEMPERATURE_C: return "DEVICE_INTERNAL_TEMPERATURE_C";
    case AGRO_METRIC_GATEWAY_QUEUE_SIZE: return "GATEWAY_QUEUE_SIZE";
    case AGRO_METRIC_SENSOR_STATUS_FLAGS: return "SENSOR_STATUS_FLAGS";
    case AGRO_METRIC_TIME_QUALITY: return "TIME_QUALITY";
    default: return nullptr;
  }
}

const char* agroChannelKey(uint8_t channelId) {
  switch (channelId) {
    case AGRO_CHANNEL_GRAIN_TEMP_1: return "grain_temp_1";
    case AGRO_CHANNEL_AMBIENT_TEMP_1: return "ambient_temp_1";
    case AGRO_CHANNEL_AMBIENT_RH_1: return "ambient_rh_1";
    case AGRO_CHANNEL_SOIL_MOISTURE_1: return "soil_moisture_1";
    case AGRO_CHANNEL_LEVEL_ULTRASONIC_1: return "level_ultrasonic_1";
    case AGRO_CHANNEL_BATTERY_1: return "battery_1";
    case AGRO_CHANNEL_SOIL_TEMP_1: return "soil_temp_1";
    default: return nullptr;
  }
}

const char* agroCanonicalUnit(uint8_t metricId) {
  switch (metricId) {
    case AGRO_METRIC_GRAIN_TEMPERATURE_C:
    case AGRO_METRIC_AMBIENT_TEMPERATURE_C:
    case AGRO_METRIC_DEVICE_INTERNAL_TEMPERATURE_C: return "degC";
    case AGRO_METRIC_AMBIENT_RELATIVE_HUMIDITY_PCT:
    case AGRO_METRIC_SOIL_MOISTURE_PCT:
    case AGRO_METRIC_LEVEL_PERCENT:
    case AGRO_METRIC_BATTERY_PERCENT: return "percent";
    case AGRO_METRIC_SOIL_MOISTURE_RAW: return "ADC_RAW";
    case AGRO_METRIC_LEVEL_DISTANCE_MM: return "mm";
    case AGRO_METRIC_BATTERY_VOLTAGE_MV: return "mV";
    case AGRO_METRIC_SIGNAL_RSSI_DBM: return "dBm";
    case AGRO_METRIC_SIGNAL_SNR_DB: return "dB";
    case AGRO_METRIC_GATEWAY_QUEUE_SIZE: return "count";
    case AGRO_METRIC_SENSOR_STATUS_FLAGS: return "flags";
    case AGRO_METRIC_TIME_QUALITY: return "code";
    default: return nullptr;
  }
}

const char* agroQualityCode(uint8_t quality) {
  switch (quality) {
    case AGRO_QUALITY_VALID: return "VALID";
    case AGRO_QUALITY_SUSPECT: return "SUSPECT";
    case AGRO_QUALITY_SENSOR_FAULT: return "SENSOR_FAULT";
    case AGRO_QUALITY_OUT_OF_RANGE: return "OUT_OF_RANGE";
    default: return nullptr;
  }
}

bool agroValidatePayload(const uint8_t* payload, size_t payloadLength, uint16_t expectedDeviceId) {
  if (payload == nullptr || payloadLength < sizeof(AgroTelemetryHeaderV4)) return false;
  const auto* header = reinterpret_cast<const AgroTelemetryHeaderV4*>(payload);
  if (header->device_id != expectedDeviceId ||
      header->metric_count == 0 ||
      header->metric_count > AGRO_TLV_MAX_METRICS ||
      agroPayloadSize(header->metric_count) != payloadLength) {
    return false;
  }
  const auto* metrics = reinterpret_cast<const AgroMetricTlv*>(payload + sizeof(AgroTelemetryHeaderV4));
  for (uint8_t index = 0; index < header->metric_count; index++) {
    if (agroMetricCode(metrics[index].metric_id) == nullptr ||
        agroChannelKey(metrics[index].channel_id) == nullptr ||
        agroQualityCode(metrics[index].quality_code) == nullptr ||
        !metricRangeIsValid(metrics[index])) {
      return false;
    }
    for (uint8_t previous = 0; previous < index; previous++) {
      if (metrics[index].metric_id == metrics[previous].metric_id &&
          metrics[index].channel_id == metrics[previous].channel_id) {
        return false;
      }
    }
  }
  return true;
}

bool agroEncryptPayload(
  const AgroFrameHeader& header,
  const uint8_t key[16],
  const uint8_t* plain,
  size_t plainLength,
  uint8_t* encrypted,
  uint8_t tag[AGRO_CCM_TAG_LEN]) {
  uint8_t nonce[12];
  uint8_t aad[15];
  buildNonce(header, nonce);
  buildAad(header, aad);
  mbedtls_ccm_context context;
  mbedtls_ccm_init(&context);
  int result = mbedtls_ccm_setkey(&context, MBEDTLS_CIPHER_ID_AES, key, 128);
  if (result == 0) {
    result = mbedtls_ccm_encrypt_and_tag(
      &context, plainLength, nonce, sizeof(nonce), aad, sizeof(aad),
      plain, encrypted, tag, AGRO_CCM_TAG_LEN);
  }
  mbedtls_ccm_free(&context);
  return result == 0;
}

bool agroDecryptPayload(
  const AgroFrameHeader& header,
  const uint8_t key[16],
  const uint8_t* encrypted,
  size_t encryptedLength,
  const uint8_t tag[AGRO_CCM_TAG_LEN],
  uint8_t* plain) {
  uint8_t nonce[12];
  uint8_t aad[15];
  buildNonce(header, nonce);
  buildAad(header, aad);
  mbedtls_ccm_context context;
  mbedtls_ccm_init(&context);
  int result = mbedtls_ccm_setkey(&context, MBEDTLS_CIPHER_ID_AES, key, 128);
  if (result == 0) {
    result = mbedtls_ccm_auth_decrypt(
      &context, encryptedLength, nonce, sizeof(nonce), aad, sizeof(aad),
      encrypted, plain, tag, AGRO_CCM_TAG_LEN);
  }
  mbedtls_ccm_free(&context);
  return result == 0;
}
