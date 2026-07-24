# Calibracion versionada y productos AgroEscudo

## Alcance

AgroEscudo distingue dos perfiles operativos:

- **SiloSensor**: almacenamiento postcosecha, temperatura de grano, ambiente, humedad, nivel ultrasonico y bateria.
- **CampoSensor**: parcela/campo, humedad de suelo raw y calibrada, temperatura ambiente, humedad ambiente, temperatura de suelo y bateria.

`StorageUnit.operation_type` define `storage` o `field`. Un `field_sensor` solo puede asignarse a `field`; un `silo_sensor` y los dispositivos legacy solo pueden asignarse a `storage`.

## Trazabilidad

Las lecturas originales no se sobrescriben. Cada metrica nueva guarda valor raw, valor calibrado, valor final compatible, unidad, calidad y version aplicada. Las lecturas anteriores permanecen como `legacy_unversioned`; una version nueva solo afecta lecturas recibidas despues de activarla.

Metodos:

- `OFFSET`: `raw + offset`.
- `LINEAR_TWO_POINT`: recta entre dos puntos, incluida pendiente negativa.
- `LEVEL_GEOMETRY`: distancia vacio/lleno o altura/zona muerta.

El clamp `0..100` se aplica solo a porcentajes.

## Permisos

- **Admin**: crea, previsualiza, activa y desactiva calibraciones autorizadas.
- **Tecnico**: calibra solo nodos asignados.
- **Cliente**: consulta estado, fecha, version y responsable; no recibe coeficientes, ADC raw, RSSI ni diagnostico.

Cada cambio genera auditoria. Crear una version tambien registra mantenimiento en bitacora.

## API

```text
GET  /api/devices?device_type=silo_sensor|field_sensor
GET  /api/devices/{id}/readings?from=&to=&limit=&order=&variable=
GET  /api/devices/{id}/calibrations
GET  /api/devices/{id}/calibrations/active
POST /api/devices/{id}/calibrations/preview
POST /api/devices/{id}/calibrations
POST /api/devices/{id}/calibrations/{calibration_id}/activate
POST /api/devices/{id}/calibrations/{calibration_id}/deactivate
GET  /api/storage-units/{id}/product-summary
```

La calibracion legacy `PATCH /api/admin/devices/{id}/calibration` continua disponible y crea una version `LEVEL_GEOMETRY`.

## CampoSensor V3

V3 transmite `soil_moisture_raw` (`0..4095` por defecto). FastAPI aplica la calibracion activa y conserva el ADC raw. El porcentaje existente sigue admitido como legacy, pero no debe enviarse junto con raw.

## Evidencia

- Migracion SQLite `upgrade -> downgrade -> upgrade`: verificada.
- Backend: 97 tests aprobados.
- Frontend: Vitest, ESLint y build Next.js verificados.
- Flutter: analyze y tests verificados.
- PlatformIO: nodo y gateway V3 compilados.
- PostgreSQL real y sensores fisicos: **NO VERIFICADO**.
