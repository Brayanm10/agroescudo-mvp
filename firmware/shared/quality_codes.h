#pragma once

#include <Arduino.h>

enum AgroQualityCode : uint8_t {
  AGRO_QUALITY_VALID = 1,
  AGRO_QUALITY_SUSPECT = 2,
  AGRO_QUALITY_SENSOR_FAULT = 3,
  AGRO_QUALITY_OUT_OF_RANGE = 4,
};

inline const char* agroQualityCode(uint8_t quality) {
  switch (quality) {
    case AGRO_QUALITY_VALID: return "VALID";
    case AGRO_QUALITY_SUSPECT: return "SUSPECT";
    case AGRO_QUALITY_SENSOR_FAULT: return "SENSOR_FAULT";
    case AGRO_QUALITY_OUT_OF_RANGE: return "OUT_OF_RANGE";
    default: return "SENSOR_FAULT";
  }
}
