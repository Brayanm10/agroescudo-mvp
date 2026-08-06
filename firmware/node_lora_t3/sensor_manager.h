#pragma once

#include <Adafruit_SHT31.h>
#include <DallasTemperature.h>
#include <OneWire.h>

#include "../shared/protocol_tlv.h"

class SensorManager {
 public:
  SensorManager();
  void begin();
  uint8_t readAll(AgroMetricTlv* metrics, uint8_t capacity, uint16_t& statusFlags);

 private:
  bool append(
    AgroMetricTlv* metrics,
    uint8_t capacity,
    uint8_t& count,
    uint8_t metricId,
    uint8_t channelId,
    int32_t value,
    uint8_t scale,
    uint8_t quality);
  bool readUltrasonic(uint32_t& distanceMm);
  uint16_t readBatteryMv();
  uint16_t readSoilRaw();

  OneWire oneWire_;
  DallasTemperature grainSensor_;
  Adafruit_SHT31 ambientSensor_;
  bool grainAvailable_;
  bool ambientAvailable_;
};
