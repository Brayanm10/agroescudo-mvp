#pragma once
#include <math.h>

// Synthetic weather only. Rain is an interval delta, direction is FROM.
enum class Scenario { Normal, Dry, Light, Heavy, Storm, BatteryLow, Auto };
struct DemoWeather {
  float temperature = 24, humidity = 65, wind = 8, direction = 225, battery = 95;
  float rain = 0;
  static float approach(float current, float target, float step) {
    const float delta = target - current;
    return current + (delta > step ? step : delta < -step ? -step : delta);
  }
  void sample(Scenario selected, unsigned long utc, unsigned long index, float intervalSeconds = 60) {
    Scenario scenario = selected;
    if (scenario == Scenario::Auto) {
      // Twenty-minute transitions: dry -> normal -> light -> heavy -> light -> normal.
      const Scenario cycle[] = {Scenario::Dry, Scenario::Normal, Scenario::Light,
                                Scenario::Heavy, Scenario::Light, Scenario::Normal};
      scenario = cycle[(index / 20) % 6];
    }
    const float wave = sinf(index * 0.12f);
    // UTC-4 solar cycle affects weather, never transmitted timestamps.
    const float diurnal = sinf(((utc % 86400) / 86400.0f - 0.42f) * 6.2831853f);
    float targetTemp = 24 + 2 * diurnal, targetHumidity = 65 - 5 * diurnal;
    float targetWind = 8, rainRate = 0, targetDirection = 225;
    switch (scenario) {
      case Scenario::Dry: targetTemp = 29 + 2 * diurnal; targetHumidity = 38; targetWind = 14; break;
      case Scenario::Light: targetTemp = 22; targetHumidity = 82; targetWind = 12; rainRate = 3; break;
      case Scenario::Heavy: targetTemp = 20; targetHumidity = 92; targetWind = 24; rainRate = 18; break;
      case Scenario::Storm: targetTemp = 18; targetHumidity = 96; targetWind = 42; rainRate = 40; targetDirection = 350; break;
      default: break;
    }
    temperature = approach(temperature, targetTemp + 0.3f * wave, 0.4f);
    humidity = approach(humidity, targetHumidity + wave, 2.0f);
    wind = approach(wind, targetWind + 1.5f * wave, 3.0f);
    float delta = fmodf(targetDirection + 8 * wave - direction + 540, 360) - 180;
    direction = fmodf(direction + (delta > 5 ? 5 : delta < -5 ? -5 : delta) + 360, 360);
    battery = approach(battery, scenario == Scenario::BatteryLow ? 8.0f : 95.0f, scenario == Scenario::BatteryLow ? 0.8f : 0.2f);
    rain = rainRate * (1 + 0.15f * wave) * intervalSeconds / 3600.0f;
  }
};
