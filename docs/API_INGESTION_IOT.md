# API De Ingestion IoT

> P1.5 conserva V1/V2/V3 y agrega eventos V4 explícitos. La API nunca
> determina una variable por la posición que ocupa en un array.

## Compatibilidad

- V1: telemetria original de silo.
- V2: perfiles SiloSensor/CampoSensor y nivel ultrasonico.
- V3: agrega `soil_moisture_raw` para calibracion versionada.

```json
{
  "protocol_version": 3,
  "sensor_profile": "field_sensor",
  "metric_flags": 142,
  "soil_moisture_raw": 2050
}
```

El ADC predeterminado es `0..4095`. No se permite enviar simultaneamente `soil_moisture_raw` y `soil_moisture_percent`; las metricas ausentes se omiten.

## Evento V4 explícito

```json
{
  "gateway_id": "GW-CBBA-001",
  "batch_id": "uuid-unico",
  "sent_at": "2026-07-24T12:00:00Z",
  "protocol_version": 4,
  "events": [
    {
      "device_id": "SILO-001",
      "boot_id": 1281,
      "sequence": 445,
      "sample_counter": 445,
      "sampled_at": "2026-07-24T11:55:00Z",
      "time_quality": "SYNCED",
      "firmware_version": "1.5.0",
      "capabilities_version": 2,
      "sensor_status_flags": 0,
      "metrics": [
        {
          "channel_key": "grain_temp_1",
          "metric_code": "GRAIN_TEMPERATURE_C",
          "raw_value": 25.4,
          "unit": "degC",
          "quality": "VALID"
        }
      ]
    }
  ]
}
```

Resultados canónicos por evento:

- `ACCEPTED`: persistido en la proyección legacy y estructura normalizada.
- `DUPLICATE`: ya existía; el gateway puede retirarlo de la cola.
- `REJECTED`: inválido, no autorizado o dispositivo desconocido.
- `QUARANTINED`: canal, métrica o unidad no coincide con capacidades.
- `TEMPORARY_ERROR`: conservar en cola y reintentar.

## Consultas dinámicas

```text
GET /api/devices/{device_id}/dashboard-schema
GET /api/devices/{device_id}/channels
GET /api/devices/{device_id}/metrics/{metric_code}/readings
    ?channel_key=grain_temp_1
    &from=2026-07-23T00:00:00Z
    &to=2026-07-24T00:00:00Z
    &resolution=15m
    &limit=1000
    &order=asc
```

La consulta valida empresa, dispositivo exacto, canal y métrica. Mientras la
conciliación productiva no esté aprobada, el servicio usa fallback legacy
explícito y responde `reconciliation_approved=false`.

Endpoint:

```http
POST /api/iot/v1/ingest/batch
```

Headers:

```http
X-Agro-Gateway-ID: GW-CBBA-001
X-Agro-Timestamp: 2026-07-01T20:30:00Z
X-Agro-Nonce: uuid-o-contador-unico
X-Agro-Signature: hex_hmac_sha256
Content-Type: application/json
```

Firma:

```text
HMAC_SHA256(
  gateway_secret,
  gateway_id + timestamp + nonce + SHA256(body)
)
```

Payload:

```json
{
  "gateway_id": "GW-CBBA-001",
  "firmware_version": "1.0.0",
  "sent_at": "2026-07-01T20:30:00Z",
  "batch_id": "uuid",
  "readings": [
    {
      "device_id": 1001,
      "protocol_version": 2,
      "sensor_profile": "silo_sensor",
      "metric_flags": 79,
      "boot_id": 843221,
      "sequence": 2048,
      "sample_counter": 2048,
      "timestamp_utc": 1782949800,
      "time_quality": 2,
      "grain_temp_c_x100": 2540,
      "air_temp_c_x100": 2380,
      "rh_x100": 6320,
      "level_distance_cm": 120.5,
      "battery_mv": 3910,
      "sensor_status": 15,
      "firmware_version": 256,
      "rssi_dbm": -72,
      "snr_db_x10": 85
    }
  ]
}
```

Los campos V2 son opcionales para conservar compatibilidad con V1. Metricas ausentes se omiten o se envian como `null`; no deben enviarse como cero ficticio.

Para un `field_sensor` se admiten `soil_moisture_x100` y `soil_temp_c_x100`. No se admite nivel o temperatura de grano. Para un `silo_sensor` no se admiten metricas de suelo.

La plataforma calcula `level_percent` con `empty_distance_cm` y `full_distance_cm` configurados para ese dispositivo. El gateway solo transmite la distancia observada.

Respuesta:

```json
{
  "batch_id": "uuid",
  "results": [
    {
      "device_id": 1001,
      "boot_id": 843221,
      "sequence": 2048,
      "status": "accepted"
    }
  ]
}
```

Estados permitidos:

- `accepted`
- `duplicate`
- `rejected_invalid`
- `rejected_unknown_device`
- `rejected_unauthorized`
- `temporary_error`

