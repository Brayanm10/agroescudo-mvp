# P1 Operacion De Primeros Pilotos

Fecha de cierre tecnico: 23 de julio de 2026.

## Veredicto

P1 cerrado para operacion controlada de primeros pilotos, pendiente de validacion continua en campo, revision previa al despliegue y definicion del alcance P2.

No se declara listo para produccion. No se realizo push, merge ni despliegue.

## Estado P0

Antes de modificar codigo se revisaron:

- `docs/AUDITORIA_FINAL.md`
- `docs/REPORTE_DE_TESTS.md`
- `docs/TELEMETRIA_POR_NODO_Y_NIVEL.md`
- `docs/CALIBRACION_VERSIONADA_Y_PRODUCTOS.md`

La matriz P0 se repitio completa:

- Backend: migraciones, seed y 97 pruebas aprobadas.
- Frontend: lint, 8 pruebas Vitest y build aprobados.
- Landing: build aprobado.
- Flutter: analyze, test y APK release aprobados.
- Firmware: nodo y gateway compilados con PlatformIO.

No se encontro una regresion P0 antes de iniciar P1.

## Arquitectura P1

P1 conserva FastAPI, SQLAlchemy, Alembic, PostgreSQL/SQLite, Next.js, Flutter y el protocolo IoT existente. Las funciones nuevas se agregan como modulos compatibles:

- mantenimiento y eventos inmutables;
- checklist digital de instalacion;
- QR publico aleatorio con control de acceso posterior al login;
- evidencia en storage local o S3 compatible;
- salud del sistema, gateways y metricas del piloto;
- entregas de notificacion auditables;
- PDF ejecutivo y tecnico;
- comparacion de periodos;
- exportaciones CSV;
- versiones de firmware y registro manual de actualizacion.

La administracion avanzada permanece en la web. Flutter prioriza la ejecucion tecnica de campo.

## Migracion

Revision Alembic P1:

`202607230002_p1_pilot_operations.py`

Agrega:

- campos operativos, cadencia y QR a `devices`;
- alcance y salud a `iot_gateways`;
- relacion gateway en `iot_devices`;
- auditoria de entregas en `notification_deliveries`;
- metadatos de evidencia en `stored_files`;
- `maintenance_records`;
- `maintenance_events`;
- `installation_checklists`;
- `firmware_releases`;
- `firmware_update_records`.

El downgrade a `202607230001` y posterior upgrade a `head` fueron ejecutados correctamente en SQLite local.

## Seguridad Y RBAC

- Admin gestiona programacion, gateways, metricas, QR y firmware.
- Tecnico solo opera mantenimiento, instalaciones y evidencia asignados.
- Cliente recibe resumen autorizado y no modifica controles tecnicos.
- El QR no contiene `device_token`, API key ni identificadores secuenciales como credencial.
- Un escaneo anonimo solo identifica el producto y exige login.
- Evidencias se filtran por unidad y empresa; las sensibles no se entregan al cliente.
- Los CSV, PDF, comparaciones y firmware validan alcance en backend.
- No se encontraron claves privadas, API keys reales ni APK versionados.
- Las credenciales demo siguen en seed/tests por decision de producto, no en interfaces productivas.

## Endpoints P1

### Mantenimiento

- `GET /api/maintenance`
- `POST /api/maintenance`
- `GET /api/maintenance/{id}`
- `PATCH /api/maintenance/{id}`
- `POST /api/maintenance/{id}/start`
- `POST /api/maintenance/{id}/complete`
- `POST /api/maintenance/{id}/cancel`
- `GET /api/maintenance/{id}/events`
- `GET /api/maintenance/device/{device_id}/summary`

### Instalacion Y QR

- `GET /api/installations`
- `POST /api/installations`
- `PATCH /api/installations/{id}`
- `POST /api/installations/{id}/validate`
- `POST /api/devices/{id}/qr`
- `POST /api/devices/{id}/qr/rotate`
- `POST /api/devices/{id}/qr/revoke`
- `GET /api/devices/scan/{public_token}`

### Evidencia

- `GET /api/evidence`
- `POST /api/evidence`
- `GET /api/evidence/{id}`
- `GET /api/evidence/{id}/download`
- `DELETE /api/evidence/{id}`

### Operacion

- `GET /api/admin/system-health`
- `GET /api/admin/gateways`
- `PATCH /api/admin/gateways/{id}`
- `POST /api/admin/gateways/{id}/assign-devices`
- `GET /api/admin/pilot-metrics`
- `GET /api/devices/{id}/compare`

### Notificaciones

- `GET /api/notifications/deliveries`
- `POST /api/notifications/{id}/retry`
- `POST /api/notifications/{id}/provider-status`

`SENT` indica aceptacion del proveedor. `DELIVERED` requiere confirmacion separada. Los reintentos usan 3, 6 y 12 segundos, con limite configurable.

### Reportes, Exportaciones Y Firmware

- `GET /api/reports/executive`
- `GET /api/reports/technical`
- `GET /api/exports/readings.csv`
- `GET /api/exports/alerts.csv`
- `GET /api/exports/incidents.csv`
- `GET /api/exports/maintenance.csv`
- `GET /api/firmware/releases`
- `POST /api/firmware/releases`
- `PATCH /api/firmware/releases/{id}`
- `GET /api/firmware/devices/status`
- `POST /api/firmware/devices/{id}/update-record`
- `POST /api/devices/{id}/firmware-update-record`

El firmware es manual y auditado. No existe OTA en P1.

## Frontend Web

Componentes P1:

- `components/p1/PilotOperationsViews.tsx`
- mantenimiento y cierre tecnico;
- checklist y QR;
- galeria/carga de evidencia;
- salud y gateways;
- metricas del piloto;
- comparacion de periodos;
- firmware;
- PDF/CSV;
- auditoria y reintento de notificaciones.

La navegacion se filtra por rol. El cliente no recibe vistas tecnicas.

## Flutter

Se agrego `ui/pilot_operations_screen.dart`:

- mantenimientos asignados;
- iniciar y completar intervencion;
- checklist digital;
- escaneo QR con `mobile_scanner`;
- foto de camara o galeria con compresion;
- carga multipart protegida;
- bloqueo de mutaciones sin internet.

El JWT permanece en `flutter_secure_storage`. No se guarda password ni token de sensor.

## Pruebas Finales

| Superficie | Resultado |
| --- | --- |
| Alembic downgrade/upgrade | Aprobado |
| Seed local | Aprobado, datos operativos limpios |
| Pytest | 118 passed, 265 warnings |
| Frontend ESLint | Aprobado |
| Frontend Vitest | 8 passed |
| Frontend build | Aprobado |
| Landing build | Aprobado |
| Flutter analyze | Sin observaciones |
| Flutter test | 3 passed |
| APK release | Aprobado, 68.31 MB |
| APK SHA-256 | `AFDD1DC08FB5E901DC00703C0352E2E929480F6431ACC2AB84E0240A1C357445` |
| Firmware nodo | SUCCESS, RAM 6.8%, flash 25.2% |
| Firmware gateway | SUCCESS, RAM 3.8%, flash 87.7% |

El controlador de browser local no pudo inicializarse durante la inspeccion visual automatizada. Backend y frontend locales respondieron, y lint/tests/build aprobaron. Esta limitacion no sustituye el QA visual manual.

## Riesgos Y Pendientes

- Validar camara, QR y subida de fotos en un Android fisico.
- Validar JSN-SR04T, LoRa, ACK, ruido, polvo y alcance en hardware real.
- Probar storage S3 compatible con credenciales del piloto.
- Probar WhatsApp, Telegram, FCM y email con cuentas reales; por defecto siguen en dry-run o desactivados.
- Revisar las 5 vulnerabilidades npm altas del frontend y 3 de landing sin usar `audit fix --force`.
- El gateway usa 87.7% de flash y debe vigilarse antes de ampliar firmware.
- Validar PostgreSQL/Neon y despliegues en un entorno de staging antes de produccion.
- Realizar QA visual manual desktop/mobile y pruebas E2E con los tres roles.

## Fuera De P1

- OTA de firmware.
- Automatizacion de mantenimiento predictivo.
- SLA y escalamiento avanzado.
- Colas offline de mutaciones moviles.
- Analitica comparativa multiempresa avanzada.
- Integraciones ERP, seguros, pagos, blockchain o marketplace.
- IA agronomica no validada.

Estos puntos requieren definicion separada de P2.
