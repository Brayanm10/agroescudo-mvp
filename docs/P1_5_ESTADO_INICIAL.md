# AgroEscudo P1.5 - Estado inicial

Fecha de auditoria: 2026-07-24
Rama de trabajo: `feature/p1-5-sensor-data-pipeline`
Commit base: `21c4cf6 Complete P1 pilot operations`

## Objetivo

Registrar el estado verificable previo a la integracion sensor -> LoRa -> gateway
-> API -> base de datos -> grafica, sin modificar datos productivos ni reemplazar
contratos existentes.

## Resultado P0/P1

- Backend FastAPI, migraciones y seed: verificados.
- Suite backend: 118 pruebas aprobadas.
- Frontend Next.js: lint, 8 pruebas Vitest y build aprobados.
- Flutter: analyze, 3 pruebas y APK release aprobados.
- Landing: build aprobado.
- Firmware nodo y gateway: compilacion aprobada con el ejecutable de PlatformIO
  de su entorno Python 3.11.
- El comando global `pio` usa Python 3.13 y falla por incompatibilidad local de
  `littlefs-python`; no es un error del firmware.

## Respaldo previo

La base SQLite local se respaldo antes de cualquier migracion:

`var/backups/agroescudo_dev_pre_p1_5_20260724_002329.db`

Auditoria de respaldo:

`var/audit/p1_5_pre_migration_20260724_002329.json`

- Integridad SQLite: `ok`.
- Dispositivos: 4.
- Lecturas locales: 0.
- Eventos IoT locales: 0.
- Grupos duplicados: 0.
- SHA-256 origen:
  `4fa48165cb3d7d8711bf4405205d55cedb1199cff73b3b5258e171099e0ad039`.

El hash binario del archivo restaurado puede diferir por la disposicion interna
de paginas de SQLite. La validacion se realiza por integridad, esquema,
conteos y contenido logico.

## Produccion

**NO VERIFICADO - requiere credenciales externas.**

No se dispone en esta ejecucion de credenciales PostgreSQL/Neon para generar un
`pg_dump`. No se ejecutara ninguna migracion ni escritura en produccion. P1.5
incluira un script reproducible de backup y exigira respaldo verificado antes
de cualquier despliegue.

## Arquitectura encontrada

### Firmware

- Protocolo binario V1/V2/V3 con AES-CCM.
- Idempotencia por `device_id + boot_id + sequence`.
- Nodo LILYGO T3 con perfiles silo/campo y campos de presencia.
- Gateway T-Beam con cola durable LittleFS, ACK posterior a persistencia y
  subida HTTPS firmada con HMAC.
- La identidad de metricas V1/V2/V3 depende todavia de campos de estructura.

### Backend

- `POST /api/iot/v1/ingest/batch` valida HMAC, ventana temporal, nonce,
  gateway, dispositivo, rangos e idempotencia.
- `sensor_readings` e `iot_readings` son tablas anchas legacy.
- `sensor_metric_values` conserva raw, calibrado, version y calidad, pero aun
  no usa un registro canonico inmutable ni linaje de migracion.
- `device_channels` existe, pero requiere capacidades operativas, estado,
  visibilidad, metrica canonica y ultima lectura valida.

### Web y Flutter

- Ambos filtran por dispositivo y separan perfiles silo/campo.
- Las graficas siguen declarando variables mediante propiedades legacy.
- No existe todavia `dashboard-schema` dinamico compartido.

## Riesgos que P1.5 debe cerrar

1. Evitar mapeos posicionales o nombres ambiguos entre firmware y nube.
2. Validar canal, metrica, unidad y capacidad antes de persistir.
3. Conservar tablas legacy y realizar doble escritura hasta aprobar
   conciliacion.
4. Identificar lecturas historicas ambiguas sin reasignarlas automaticamente.
5. Generar graficas solo para canales instalados y habilitados.
6. Mantener aislamiento por empresa, unidad, dispositivo, canal y metrica.
7. No calcular nivel o humedad de suelo sin geometria/calibracion valida.

## Decisiones de implementacion

- Registro canonico P1.5 version 1 con IDs numericos inmutables 1..15.
- Protocolo TLV nuevo V4; V1/V2/V3 permanecen decodificables.
- Tablas normalizadas nuevas y doble escritura compatible.
- Ingestion explicita por `channel_key` y `metric_code`; no se crean canales
  desde telemetria no confiable.
- Migracion historica en modo `dry-run` por defecto, por lotes y con rollback
  limitado exclusivamente a filas nuevas del lote.
- La interfaz no dependera exclusivamente de la estructura nueva hasta que
  `MIGRATION_RECONCILIATION_REPORT.md` sea aprobado humanamente.
