# Changelog

## 2026-07-01 - Auditoria final piloto

- Agregado endpoint IoT batch `/api/iot/v1/ingest/batch`.
- Agregadas tablas IoT para gateways, credenciales, devices, readings, batches, events y health.
- Agregada verificacion HMAC-SHA256 y anti-replay por nonce.
- Agregada idempotencia por `iot_device_id + boot_id + sequence`.
- Agregados tests de ingestion IoT.
- Retiradas credenciales visibles del login Flutter.
- Agregado scaffold firmware nodo/gateway LoRa.
- Agregada documentacion de arquitectura, seguridad, despliegue, rollback, backup y decision HTTP vs MQTT.
