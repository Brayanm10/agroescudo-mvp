# Reporte de conciliacion P1.5

Estado: **PENDIENTE DE APROBACION HUMANA**

## Ejecucion local

La base SQLite local respaldada antes de P1.5 contenia:

- dispositivos: 4;
- `sensor_readings`: 0;
- `iot_readings`: 0;
- eventos IoT: 0;
- duplicados: 0.

La suma local cumple:

`total_original = safe_to_migrate + requires_mapping + quarantined + invalid + duplicate = 0`

No se elimino ningun registro. La migracion Alembic fue aditiva y el seed
preservo la informacion operativa existente.

Evidencia:

- Backup: `var/backups/agroescudo_dev_pre_p1_5_20260724_002329.db`
- Tamaño: `1409024` bytes.
- SHA-256: `0E55A86BDFD378A4C0374C2CA2AEF5CE89AB7FEFE0D687B0C3B3347B409BA03B`
- Auditoría JSON: `var/audit/p1_5_pre_migration_20260724_002329.json`
- Dry run: `p1-5-local-dry-run-20260724`
- Resultado: 0 originales, 0 clasificados, conciliación exacta.

## Roundtrip de migración

Se copió la base local a
`tmp/p1_5/migration-roundtrip-20260724.db`. Sobre esa copia se ejecutó:

```text
alembic downgrade 202607230002
alembic upgrade head
```

Resultado: `202607240002 (head)`. El SHA-256 de la base fuente antes y después
fue idéntico:

`CDD5ED83AA55E18E4E25E08A291FF9F907797DD247CF627FD2A152A23DBFCA04`

## Produccion

**NO VERIFICADO - requiere credenciales PostgreSQL/Neon y backup.**

Antes de aplicar:

1. Ejecutar `scripts/backup_postgres_p1_5.ps1`.
2. Restaurar el dump en una base temporal.
3. Ejecutar `alembic upgrade head` sobre la copia.
4. Ejecutar `python scripts/audit_legacy_telemetry.py`.
5. Ejecutar `python scripts/migrate_legacy_telemetry.py` sin `--apply`.
6. Revisar todas las filas `REQUIRES_MAPPING`, `QUARANTINED` e `INVALID`.
7. Ejecutar con `--apply` solo tras aprobar el mapeo.
8. Comparar conteos, fechas, minimos, maximos y promedios para todos los
   dispositivos si son menos de 20.

## Cuarentena local

No existen lecturas locales en cuarentena. En produccion, consultar:

```sql
SELECT *
FROM legacy_mapping_results
WHERE classification IN ('QUARANTINED', 'REQUIRES_MAPPING', 'INVALID')
ORDER BY legacy_table, legacy_row_id, legacy_field;
```

La lista exportable se inicializó en `docs/P1_5_QUARANTINE.csv`. Solo debe
completarse a partir de `legacy_mapping_results`; no se agregan decisiones
inferidas.

## Evidencia de cero eliminaciones

- Ninguna migracion P1.5 ejecuta `DELETE` sobre tablas legacy.
- El script de migracion solo inserta en tablas P1.5.
- El rollback filtra por `migration_batch_id` y elimina exclusivamente
  `metric_readings`, `telemetry_events` y resultados del lote.
- Las lecturas de sensores retirados permanecen consultables.
