# Protocolo LoRa AgroEscudo P1.5

## Compatibilidad

- V1: lectura fija original.
- V2: perfiles silo/campo y presencia por máscara.
- V3: humedad de suelo raw.
- V4: TLV canónico por `metric_id` y `channel_id`.

El gateway mantiene decodificación V1, V2 y V3. Las nuevas instalaciones deben
usar V4. No se reinterpretan paquetes históricos.

## Frame V4

El envelope `AgroFrameHeader` contiene:

| Campo | Tipo |
|---|---|
| magic | uint16 |
| protocol_version | uint8 |
| message_type | uint8 |
| key_version | uint8 |
| device_id | uint16 |
| boot_id | uint32 |
| sequence | uint32 |
| payload_len | uint16 |

El payload autenticado contiene `device_id`, `sample_counter`, `timestamp_utc`,
`time_quality`, `firmware_version`, `capabilities_version`, `metric_count` y
`sensor_status_flags`.

Cada TLV contiene `metric_id:uint8`, `channel_id:uint8`,
`value_scaled:int32`, `scale_code:uint8` y `quality_code:uint8`.

Ejemplo: `metric_id=1`, `channel_id=1`, `value_scaled=2540`,
`scale_code=2` significa `GRAIN_TEMPERATURE_C = 25.40 degC`.

## Seguridad e idempotencia

- El payload se cifra y autentica con AES-CCM.
- El nonce deriva de `device_id + boot_id + sequence`.
- El gateway rechaza tamaño, versión, métrica, canal, calidad y rango inválidos.
- La clave de idempotencia es `device_id + boot_id + sequence`.
- El nodo persiste antes de transmitir.
- El gateway persiste antes de ACK.
- Un duplicado recibe ACK otra vez, pero no crea otra lectura.
- El gateway elimina de cola solo respuestas `ACCEPTED` o `DUPLICATE`.

## Pérdida parcial

Una falla del DS18B20 no cancela SHT31 o batería. El nodo incluye únicamente
métricas válidas y reporta el fallo en `sensor_status_flags`. Nunca usa cero para
representar una métrica ausente.

## HTTP del gateway

`POST /api/iot/v1/ingest/batch`

Headers obligatorios:

- `X-Agro-Gateway-ID`
- `X-Agro-Timestamp`
- `X-Agro-Nonce`
- `X-Agro-Signature`

La firma es HMAC-SHA256 de
`gateway_id + timestamp + nonce + sha256(body)`.

El body usa `events[].metrics[]` con `channel_key`, `metric_code`, `raw_value`,
`unit` y `quality`. La API no crea canales desde telemetría.
