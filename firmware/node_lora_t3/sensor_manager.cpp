#include "sensor_manager.h"

#include <algorithm>
#include <cmath>

#ifndef AGRO_DS18B20_PIN
#define AGRO_DS18B20_PIN 4
#endif
#ifndef AGRO_SOIL_MOISTURE_PIN
#define AGRO_SOIL_MOISTURE_PIN 32
#endif
#ifndef AGRO_ULTRASONIC_TRIG_PIN
#define AGRO_ULTRASONIC_TRIG_PIN 32
#endif
#ifndef AGRO_ULTRASONIC_ECHO_PIN
#define AGRO_ULTRASONIC_ECHO_PIN 33
#endif
#ifndef AGRO_BATTERY_ADC_PIN
#define AGRO_BATTERY_ADC_PIN 35
#endif
#ifndef AGRO_BATTERY_DIVIDER_RATIO_X1000
#define AGRO_BATTERY_DIVIDER_RATIO_X1000 2000
#endif

static constexpr uint16_t STATUS_GRAIN_OK = 1 << 0;
static constexpr uint16_t STATUS_AMBIENT_OK = 1 << 1;
static constexpr uint16_t STATUS_SOIL_OK = 1 << 2;
static constexpr uint16_t STATUS_LEVEL_OK = 1 << 3;
static constexpr uint16_t STATUS_BATTERY_OK = 1 << 4;

SensorManager::SensorManager()
  : oneWire_(AGRO_DS18B20_PIN),
    grainSensor_(&oneWire_),
    grainAvailable_(false),
    ambientAvailable_(false) {}

void SensorManager::begin() {
  analogReadResolution(12);
  pinMode(AGRO_BATTERY_ADC_PIN, INPUT);
  ambientAvailable_ = ambientSensor_.begin(0x44);
#if AGRO_SENSOR_PROFILE == AGRO_PROFILE_SILO
  grainSensor_.begin();
  grainSensor_.setWaitForConversion(true);
  grainAvailable_ = grainSensor_.getDeviceCount() > 0;
  pinMode(AGRO_ULTRASONIC_TRIG_PIN, OUTPUT);
  pinMode(AGRO_ULTRASONIC_ECHO_PIN, INPUT);
#else
  pinMode(AGRO_SOIL_MOISTURE_PIN, INPUT);
#endif
}

uint8_t SensorManager::readAll(
  AgroMetricTlv* metrics,
  uint8_t capacity,
  uint16_t& statusFlags) {
  uint8_t count = 0;
  statusFlags = 0;

#if AGRO_SENSOR_PROFILE == AGRO_PROFILE_SILO
  if (grainAvailable_) {
    grainSensor_.requestTemperatures();
    const float grain = grainSensor_.getTempCByIndex(0);
    if (grain != DEVICE_DISCONNECTED_C && grain > -40 && grain < 100) {
      const uint8_t quality = fabsf(grain - 85.0f) < 0.01f ? AGRO_QUALITY_SUSPECT : AGRO_QUALITY_VALID;
      append(metrics, capacity, count, AGRO_METRIC_GRAIN_TEMPERATURE_C,
             AGRO_CHANNEL_GRAIN_TEMP_1, lroundf(grain * 100), AGRO_SCALE_X100, quality);
      statusFlags |= STATUS_GRAIN_OK;
    }
  }
#else
  const uint16_t soil = readSoilRaw();
  append(metrics, capacity, count, AGRO_METRIC_SOIL_MOISTURE_RAW,
         AGRO_CHANNEL_SOIL_MOISTURE_1, soil, AGRO_SCALE_INTEGER, AGRO_QUALITY_VALID);
  statusFlags |= STATUS_SOIL_OK;
#endif

  if (ambientAvailable_) {
    const float temperature = ambientSensor_.readTemperature();
    const float humidity = ambientSensor_.readHumidity();
    if (isfinite(temperature) && temperature >= -40 && temperature <= 80) {
      append(metrics, capacity, count, AGRO_METRIC_AMBIENT_TEMPERATURE_C,
             AGRO_CHANNEL_AMBIENT_TEMP_1, lroundf(temperature * 100), AGRO_SCALE_X100,
             AGRO_QUALITY_VALID);
    }
    if (isfinite(humidity) && humidity >= 0 && humidity <= 100) {
      append(metrics, capacity, count, AGRO_METRIC_AMBIENT_RELATIVE_HUMIDITY_PCT,
             AGRO_CHANNEL_AMBIENT_RH_1, lroundf(humidity * 100), AGRO_SCALE_X100,
             AGRO_QUALITY_VALID);
    }
    if (isfinite(temperature) && isfinite(humidity)) statusFlags |= STATUS_AMBIENT_OK;
  }

#if AGRO_SENSOR_PROFILE == AGRO_PROFILE_SILO && AGRO_ENABLE_ULTRASONIC
  uint32_t distanceMm = 0;
  if (readUltrasonic(distanceMm)) {
    append(metrics, capacity, count, AGRO_METRIC_LEVEL_DISTANCE_MM,
           AGRO_CHANNEL_LEVEL_ULTRASONIC_1, distanceMm, AGRO_SCALE_INTEGER,
           AGRO_QUALITY_VALID);
    statusFlags |= STATUS_LEVEL_OK;
  }
#endif

  const uint16_t batteryMv = readBatteryMv();
  if (batteryMv <= 6000) {
    append(metrics, capacity, count, AGRO_METRIC_BATTERY_VOLTAGE_MV,
           AGRO_CHANNEL_BATTERY_1, batteryMv, AGRO_SCALE_INTEGER, AGRO_QUALITY_VALID);
    statusFlags |= STATUS_BATTERY_OK;
  }
  return count;
}

bool SensorManager::append(
  AgroMetricTlv* metrics,
  uint8_t capacity,
  uint8_t& count,
  uint8_t metricId,
  uint8_t channelId,
  int32_t value,
  uint8_t scale,
  uint8_t quality) {
  if (count >= capacity) return false;
  metrics[count++] = {metricId, channelId, value, scale, quality};
  return true;
}

bool SensorManager::readUltrasonic(uint32_t& distanceMm) {
  uint32_t samples[5]{};
  uint8_t valid = 0;
  for (uint8_t attempt = 0; attempt < 5; attempt++) {
    digitalWrite(AGRO_ULTRASONIC_TRIG_PIN, LOW);
    delayMicroseconds(3);
    digitalWrite(AGRO_ULTRASONIC_TRIG_PIN, HIGH);
    delayMicroseconds(12);
    digitalWrite(AGRO_ULTRASONIC_TRIG_PIN, LOW);
    const uint32_t durationUs = pulseIn(AGRO_ULTRASONIC_ECHO_PIN, HIGH, 60000);
    const uint32_t measured = static_cast<uint32_t>((durationUs * 0.343f) / 2.0f);
    if (durationUs > 0 && measured >= 200 && measured <= 20000) samples[valid++] = measured;
    delay(70);
  }
  if (!valid) return false;
  std::sort(samples, samples + valid);
  distanceMm = samples[valid / 2];
  return true;
}

uint16_t SensorManager::readBatteryMv() {
  const uint32_t adcMv = analogReadMilliVolts(AGRO_BATTERY_ADC_PIN);
  return static_cast<uint16_t>(
    min<uint32_t>(6000, adcMv * AGRO_BATTERY_DIVIDER_RATIO_X1000 / 1000));
}

uint16_t SensorManager::readSoilRaw() {
  uint16_t samples[5]{};
  for (uint8_t index = 0; index < 5; index++) {
    samples[index] = analogRead(AGRO_SOIL_MOISTURE_PIN);
    delay(20);
  }
  std::sort(samples, samples + 5);
  return samples[2];
}
