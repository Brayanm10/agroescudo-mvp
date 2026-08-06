# Reglas de mapeo legacy P1.5

Version de reglas: `p1.5-v1`

## Principios

- El mapeo es aditivo.
- `raw_value`, `device_id` y timestamps originales no se modifican.
- Una variable ambigua no se reasigna.
- Las tablas `sensor_readings` e `iot_readings` permanecen disponibles.
- Un rollback elimina solo filas P1.5 del lote indicado.
- El frontend usa fallback legacy hasta aprobacion humana de conciliacion.

## Tabla explicita

| legacy_field | device_type | sensor_type | channel_key | metric_code | canonical_unit | regla |
|---|---|---|---|---|---|---|
| grain_temperature / grain_temp_c_x100 | SiloSensor | DS18B20 | grain_temp_1 | GRAIN_TEMPERATURE_C | degC | segura con dispositivo y canal conocidos |
| ambient_temperature / air_temp_c_x100 | ambos | SHT31 | ambient_temp_1 | AMBIENT_TEMPERATURE_C | degC | segura |
| ambient_humidity / rh_x100 | ambos | SHT31 | ambient_rh_1 | AMBIENT_RELATIVE_HUMIDITY_PCT | percent | segura |
| soil_moisture_raw | CampoSensor | analog soil | soil_moisture_1 | SOIL_MOISTURE_RAW | ADC_RAW | segura |
| soil_moisture_percent / soil_moisture_x100 | CampoSensor | derivada legacy | soil_moisture_1 | SOIL_MOISTURE_PCT | percent | conserva calidad legacy |
| level_distance_cm / level_distance_mm | SiloSensor | JSN-SR04T | level_ultrasonic_1 | LEVEL_DISTANCE_MM | mm | convierte cm a mm sin alterar fuente |
| level_percent / level_percent_x100 | SiloSensor | derivada legacy | level_ultrasonic_1 | LEVEL_PERCENT | percent | no recalcular |
| battery_voltage / battery_mv | ambos | battery ADC | battery_1 | BATTERY_VOLTAGE_MV | mV | convierte V a mV sin alterar fuente |
| signal_quality / rssi_dbm | diagnostico | radio gateway | radio_link_1 | SIGNAL_RSSI_DBM | dBm | solo tecnico/admin |
| snr_db_x10 | diagnostico | radio gateway | radio_link_1 | SIGNAL_SNR_DB | dB | escala x10 |
| sensor_status | ambos | nodo | status_1 | SENSOR_STATUS_FLAGS | flags | tecnica |
| time_quality | ambos | reloj nodo | time_1 | TIME_QUALITY | code | tecnica |
| soil_temperature_c / soil_temp_c_x100 | no confirmado | no confirmado | - | - | - | REQUIRES_MAPPING |

## Clasificacion

- `SAFE_TO_MIGRATE`: dispositivo, metrica, unidad, timestamp y canal inequivocos.
- `REQUIRES_MAPPING`: existe informacion parcial y se exige decision humana.
- `QUARANTINED`: dispositivo, canal o variable ambiguos.
- `INVALID`: estructura corrupta o valor fisicamente imposible.
- `DUPLICATE`: se conserva la fuente, pero se excluye de calculos normalizados.
