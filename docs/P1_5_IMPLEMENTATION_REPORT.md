# Informe de implementación P1.5

## Veredicto

La cadena de software SensorManager -> LoRa V4 -> gateway durable -> FastAPI ->
SQL normalizado -> schema dinámico -> gráfica está implementada y pasa pruebas.
P0 y P1 continúan estables.

La fase queda **lista para prueba física controlada**, no para despliegue
productivo automático. Hardware, alcance y base PostgreSQL productiva permanecen
`NO VERIFICADO`.

## Arquitectura implementada

- Registro canónico v1 con 15 IDs estables.
- Plantillas SiloSensor base, SiloSensor con nivel y CampoSensor.
- Canales estables, auditables y retirables sin borrar datos.
- V4 TLV con identificación explícita de métrica y canal.
- Compatibilidad gateway V1/V2/V3.
- SensorManager con fallos parciales.
- Cola LittleFS V4 separada, deduplicación y ACK posterior a persistencia.
- Batch HTTPS HMAC con estados canónicos.
- Tablas normalizadas y dual write.
- Consulta exacta por dispositivo/canal/métrica/rango.
- Schema de dashboard generado por capacidades.
- Gestión admin/técnico y visibilidad cliente.
- Alertas trazadas a canal y definición de métrica.
- Migración histórica aditiva con dry run y rollback.

## Archivos principales

Backend:

- `app/domain/metric_registry.py`
- `app/domain/device_templates.py`
- `app/services/device_capabilities.py`
- `app/services/normalized_telemetry.py`
- `app/services/telemetry_queries.py`
- `app/api/routes/telemetry.py`
- migraciones `202607240001` y `202607240002`

Firmware:

- `shared/metric_registry.h`
- `shared/quality_codes.h`
- `shared/protocol_tlv.h`
- `node_lora_t3/sensor_manager.*`
- `node_lora_t3/main.cpp`
- `gateway_tbeam/main.cpp`

Web y móvil:

- `frontend/components/telemetry/*`
- `frontend/lib/api.ts`
- `frontend/lib/types.ts`
- `mobile/lib/core/app_store.dart`
- `mobile/lib/ui/screens.dart`

Migración y documentación:

- `backend/scripts/backup_postgres_p1_5.ps1`
- `backend/scripts/audit_legacy_telemetry.py`
- `backend/scripts/migrate_legacy_telemetry.py`
- `backend/scripts/rollback_legacy_telemetry.py`
- `docs/DATA_MAPPING_AUDIT.md`
- `docs/LEGACY_MAPPING_RULES.md`
- `docs/MIGRATION_RECONCILIATION_REPORT.md`
- `docs/P1_5_QUARANTINE.csv`

## Protección histórica

- No se eliminó ninguna tabla o fila legacy.
- No se modifican `device_id`, timestamps o raw.
- Temperatura de suelo ambigua queda `REQUIRES_MAPPING`.
- Duplicados conservan fuente y se excluyen de la copia normalizada.
- El frontend aún recibe fallback legacy mientras
  `reconciliation_approved=false`.
- El rollback elimina únicamente filas P1.5 del batch elegido.

## Riesgos y pendientes

1. Ejecutar `pg_dump` productivo y restaurar en una base temporal.
2. Correr auditoría y dry run en esa copia.
3. Resolver manualmente cuarentena y `REQUIRES_MAPPING`.
4. Comparar conteos, fechas y estadísticos por dispositivo.
5. Validar DS18B20, SHT31, ADC y JSN-SR04T en banco.
6. Validar radio, ACK, reinicio, cola offline y TLS.
7. Medir autonomía y presupuesto de flash del gateway.
8. Aprovisionar claves reales fuera del código.

## Confirmaciones

- P2 no fue iniciado.
- No se hizo push.
- No se hizo merge.
- No se hizo despliegue.
- No se modificó producción.
