# Changelog

## 2026-09-01 - Actualizacion movil y urgencias Sentinel

- Alta de cuenta cliente simplificada en Flutter y web.
- Contacto de urgencia opcional durante el registro, alta de piloto o creacion de silo.
- SMS critico habilitado por defecto y llamada Sentinel solo con autorizacion explicita.
- Edicion del contacto por empresa o silo desde la app para admin y cliente.
- Portada cliente con continuidad operativa, prioridades y acceso rapido a urgencias.
- Flutter actualizado a `1.1.0+2` y mensajes de validacion mas claros.

## 2026-07-01 - Auditoria final piloto

- Agregado endpoint IoT batch `/api/iot/v1/ingest/batch`.
- Agregadas tablas IoT para gateways, credenciales, devices, readings, batches, events y health.
- Agregada verificacion HMAC-SHA256 y anti-replay por nonce.
- Agregada idempotencia por `iot_device_id + boot_id + sequence`.
- Agregados tests de ingestion IoT.
- Retiradas credenciales visibles del login Flutter.
- Agregado scaffold firmware nodo/gateway LoRa.
- Agregada documentacion de arquitectura, seguridad, despliegue, rollback, backup y decision HTTP vs MQTT.
