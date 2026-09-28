# AgroEscudo - Handoff técnico de hardware de Pluviometría

## Estado oficial

**PLUVIOMETRÍA SOFTWARE MVP**

**STATUS: SOFTWARE READY FOR HARDWARE INTEGRATION**

Este paquete define qué debe construir, verificar y entregar el equipo de hardware para que un pluviómetro sea compatible con AgroEscudo. No entrega secretos productivos y no exige conocimiento interno del backend.

## Qué está terminado en software

- alta administrativa de predios, parcelas y pluviómetros;
- ubicación cartográfica y visualización satelital/híbrida;
- plantilla `RAIN_GAUGE_BASE` con seis canales canónicos;
- endpoint de ingesta por lotes `POST /api/iot/v1/ingest/batch`;
- autenticación HMAC-SHA256 por gateway;
- idempotencia por dispositivo, arranque y secuencia;
- normalización a `TelemetryEvent` y `MetricReading`;
- estados `ACCEPTED`, `DUPLICATE`, `QUARANTINED`, `REJECTED` y `TEMPORARY_ERROR`;
- dashboard, mapa, gráfico e histórico;
- ejemplo HIL validado con ESP32 real, WiFi, API y dashboard.

## Qué queda del lado de hardware

- seleccionar e integrar sensores físicos;
- convertir señales crudas a las unidades canónicas;
- producir lluvia incremental, no acumulado histórico;
- calibrar y documentar cada variable;
- versionar firmware y mantener identidad/contadores;
- validar reinicios, pérdida de red y recuperación;
- diseñar posteriormente buffer durable y store-and-forward;
- entregar evidencia de prueba end-to-end.

## Documentos del paquete

1. [Arquitectura](01_ARCHITECTURE.md)
2. [Contrato de telemetría](02_TELEMETRY_CONTRACT.md)
3. [Referencia ESP32 HIL](03_ESP32_HIL.md)
4. [Integración de sensores](04_SENSOR_INTEGRATION.md)
5. [Plantilla de calibración](05_CALIBRATION.md)
6. [Plan de pruebas](06_TEST_PLAN.md)
7. [Seguridad y aprovisionamiento](07_SECURITY.md)
8. [Checklist de campo](08_FIELD_CHECKLIST.md)

Material complementario:

- `docs/AgroEscudo_Guia_Instalacion_Pluviometro.pdf`;
- `hardware/pluviometry/esp32_hil/esp32_hil.ino`;
- `hardware/pluviometry/esp32_hil/secrets.example.h`.

## Regla de alcance

El HIL actual es una referencia de integración. No es firmware productivo, no implementa sensores físicos, LoRa, buffer offline, persistencia de muestras ni recuperación store-and-forward.

Ante una discrepancia, prevalecen los códigos, unidades y rangos documentados en `02_TELEMETRY_CONTRACT.md`. Cualquier cambio debe coordinarse con AgroEscudo antes de modificar firmware o electrónica.
