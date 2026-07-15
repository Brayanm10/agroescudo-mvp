# API De Ingestion IoT

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
      "boot_id": 843221,
      "sequence": 2048,
      "sample_counter": 2048,
      "timestamp_utc": 1782949800,
      "time_quality": 2,
      "grain_temp_c_x100": 2540,
      "air_temp_c_x100": 2380,
      "rh_x100": 6320,
      "battery_mv": 3910,
      "sensor_status": 15,
      "firmware_version": 256,
      "rssi_dbm": -72,
      "snr_db_x10": 85
    }
  ]
}
```

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

