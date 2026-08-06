# Registro canónico de métricas P1.5

Versión inmutable: `1`

Este registro es la única referencia para firmware, gateway, API, base de datos,
web y Flutter. Una métrica se identifica por `numeric_id` y `metric_code`; el
orden de llegada nunca define su significado.

| ID | metric_code | Unidad | Origen | Producto | Cliente | Derivada |
|---:|---|---|---|---|---|---|
| 1 | GRAIN_TEMPERATURE_C | degC | DS18B20 | SiloSensor | Sí | No |
| 2 | AMBIENT_TEMPERATURE_C | degC | SHT31 | Ambos | Sí | No |
| 3 | AMBIENT_RELATIVE_HUMIDITY_PCT | percent | SHT31 | Ambos | Sí | No |
| 4 | SOIL_MOISTURE_RAW | ADC_RAW | ADC1 | CampoSensor | No | No |
| 5 | SOIL_MOISTURE_PCT | percent | Backend | CampoSensor | Sí | Sí |
| 6 | LEVEL_DISTANCE_MM | mm | JSN-SR04T | SiloSensor | Sí | No |
| 7 | LEVEL_PERCENT | percent | Backend | SiloSensor | Sí | Sí |
| 8 | BATTERY_VOLTAGE_MV | mV | ADC batería | Ambos | Sí | No |
| 9 | BATTERY_PERCENT | percent | Backend | Ambos | Sí | Sí |
| 10 | SIGNAL_RSSI_DBM | dBm | Gateway | Diagnóstico | No | No |
| 11 | SIGNAL_SNR_DB | dB | Gateway | Diagnóstico | No | No |
| 12 | DEVICE_INTERNAL_TEMPERATURE_C | degC | Sensor físico opcional | Todos | No | No |
| 13 | GATEWAY_QUEUE_SIZE | count | Gateway | Gateway | No | No |
| 14 | SENSOR_STATUS_FLAGS | flags | Nodo | Ambos | No | No |
| 15 | TIME_QUALITY | code | Nodo/gateway | Todos | No | No |

## Reglas inmutables

- Un `numeric_id` usado no se reasigna.
- `metric_code` no se edita en un canal con historial.
- Las unidades se validan contra `canonical_unit`.
- Temperatura de suelo legacy no se convierte en temperatura interna del nodo.
- `SOIL_MOISTURE_PCT`, `LEVEL_PERCENT` y `BATTERY_PERCENT` no se aceptan como
  lecturas físicas nuevas: se derivan en backend cuando existe calibración.
- Los valores raw se conservan aunque una calibración produzca otro valor.

## Canales estables

| channel_key | Sensor | Métricas permitidas |
|---|---|---|
| grain_temp_1 | DS18B20 | GRAIN_TEMPERATURE_C |
| ambient_temp_1 | SHT31 | AMBIENT_TEMPERATURE_C |
| ambient_rh_1 | SHT31 | AMBIENT_RELATIVE_HUMIDITY_PCT |
| soil_moisture_1 | Sensor ADC | SOIL_MOISTURE_RAW, SOIL_MOISTURE_PCT |
| level_ultrasonic_1 | JSN-SR04T | LEVEL_DISTANCE_MM, LEVEL_PERCENT |
| battery_1 | ADC batería | BATTERY_VOLTAGE_MV, BATTERY_PERCENT |

Los canales retirados conservan `channel_key`, fecha, usuario, motivo y todo su
historial. Nunca se reutiliza un `channel_key` retirado para otro sensor físico.
