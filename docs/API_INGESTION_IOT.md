# API De Ingestion IoT

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

