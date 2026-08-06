# DATA MAPPING AUDIT - P1.5

Generado: 2026-07-24T05:16:47.351353+00:00
Motor: `sqlite`
Dispositivos: 4

## Tablas legacy

| Tabla | Filas | Fecha minima | Fecha maxima | Duplicados | SHA-256 logico |
|---|---:|---|---|---:|---|
| sensor_readings | 0 | - | - | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| iot_readings | 0 | - | - | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |

## Proteccion

- Esta auditoria es solo lectura.
- No elimina, actualiza ni recalcula filas legacy.
- Los nulos se registran por campo en el JSON de evidencia.
- La migracion productiva requiere `pg_dump` verificado y ejecucion previa en copia.
