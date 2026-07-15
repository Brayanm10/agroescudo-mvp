# 03. Backend FastAPI

Estado del documento: BORRADOR CONTROLADO  
Fecha de auditoria: 2026-07-02  
Fuente principal: inspeccion de `backend/`

## Stack detectado

| Componente | Estado | Evidencia |
|---|---|---|
| FastAPI | CONFIRMADO EN CODIGO | `backend/app/main.py` |
| SQLAlchemy 2.x | CONFIRMADO EN CODIGO | `backend/app/models.py`, `backend/app/db/session.py` |
| Alembic | CONFIRMADO EN CODIGO | `backend/alembic/versions/` |
| SQLite local | CONFIRMADO EN CODIGO | `DATABASE_URL=sqlite:///./agroescudo_dev.db` en ejemplos. |
| PostgreSQL | CONFIGURADO PERO NO VERIFICADO EN ESTA FASE | Driver `psycopg` y URLs `postgresql+psycopg`. |
| JWT | CONFIRMADO EN CODIGO | Auth y deps. |
| ReportLab PDF | CONFIRMADO EN CODIGO | Servicio de reporte PDF. |
| Notificaciones | CONFIRMADO EN CODIGO | Preferencias, eventos y deliveries. |
| IoT HMAC batch | CONFIRMADO EN CODIGO | Router `iot.py` y servicio `iot_ingestion.py`. |

## Configuracion

Archivo principal: `backend/app/core/config.py`

Variables relevantes:

| Variable | Uso | Estado |
|---|---|---|
| `DATABASE_URL` | Conexion SQL. | CONFIRMADO EN CODIGO |
| `JWT_SECRET` / `SECRET_KEY` | Firma JWT. | CONFIRMADO EN CODIGO |
| `CORS_ORIGINS` | Origenes permitidos para frontend. | CONFIRMADO EN CODIGO |
| `ENVIRONMENT` | Validaciones de produccion/demo. | CONFIRMADO EN CODIGO |
| `NOTIFICATIONS_DRY_RUN` | Evita envios reales por defecto. | CONFIRMADO EN CODIGO |
| `WHATSAPP_*` | Integracion WhatsApp Cloud API. | CONFIGURADO PERO NO VERIFICADO |
| `TELEGRAM_*` | Integracion Telegram Bot API. | CONFIGURADO PERO NO VERIFICADO |
| `FCM_*` | Push futuro/configurado. | CONFIGURADO PERO NO VERIFICADO |
| `OPENAI_API_KEY` | LLM opcional del asistente. | CONFIGURADO PERO NO VERIFICADO |

Regla productiva confirmada: en entorno demo/produccion el backend no debe usar SQLite, secretos por defecto ni CORS abierto.

## Routers registrados

Archivo: `backend/app/main.py`

| Router | Prefijo | Proposito |
|---|---|---|
| `auth` | `/api` | Login, usuario actual y password. |
| `admin` | `/api/admin` | Administracion B2B. |
| `companies` | `/api/companies` | Empresas. |
| `sites` | `/api/sites` | Sitios. |
| `storage_units` | `/api/storage-units` | Silos, galpones y almacenes. |
| `devices` | `/api/devices` | Sensores/dispositivos. |
| `iot` | `/api/iot/v1` | Ingestion batch gateway. |
| `readings` | `/api/readings` | Ingestion legacy y consulta de lecturas. |
| `alerts` | `/api/alerts` | Alertas y estados. |
| `operational_logs` | `/api/operational-logs` | Bitacora, acciones e instalaciones. |
| `reports` | `/api/reports` | Reporte semanal JSON/PDF. |
| `pilots` | `/api/pilots` | Flujo de piloto y datos operativos. |
| `users` | `/api/users` | Compatibilidad admin de usuarios. |
| `demo` | `/api/demo` | Simulacion controlada admin/demo. |
| `notifications` | `/api/notifications` | Preferencias, eventos y pruebas. |
| `ai` | `/api/ai` | Recomendaciones asistidas. |
| `insights` | `/api/insights` | Resumenes operativos. |

## Health checks

| Metodo | Ruta | Estado |
|---|---|---|
| GET | `/health` | CONFIRMADO EN CODIGO |
| GET | `/api/health/db` | CONFIRMADO EN CODIGO |

## Catalogo de endpoints principales

| Metodo | Ruta | Acceso | Estado |
|---|---|---|---|
| POST | `/api/auth/login` | Publico | CONFIRMADO EN CODIGO |
| GET | `/api/me` | JWT | CONFIRMADO EN CODIGO |
| PATCH | `/api/me` | JWT | CONFIRMADO EN CODIGO |
| POST | `/api/auth/change-password` | JWT | CONFIRMADO EN CODIGO |
| GET | `/api/companies` | JWT filtrado | CONFIRMADO EN CODIGO |
| POST | `/api/companies` | Admin | CONFIRMADO EN CODIGO |
| GET | `/api/sites` | JWT filtrado | CONFIRMADO EN CODIGO |
| POST | `/api/sites` | Admin | CONFIRMADO EN CODIGO |
| GET | `/api/storage-units` | JWT filtrado | CONFIRMADO EN CODIGO |
| POST | `/api/storage-units` | Admin | CONFIRMADO EN CODIGO |
| GET | `/api/storage-units/{id}/readings` | JWT filtrado | CONFIRMADO EN CODIGO |
| GET | `/api/storage-units/{id}/operational-logs` | JWT filtrado | CONFIRMADO EN CODIGO |
| GET | `/api/devices` | JWT filtrado | CONFIRMADO EN CODIGO |
| POST | `/api/devices` | Admin | CONFIRMADO EN CODIGO |
| GET | `/api/devices/{id}/thresholds` | JWT filtrado | CONFIRMADO EN CODIGO |
| PUT | `/api/devices/{id}/thresholds` | Admin | CONFIRMADO EN CODIGO |
| POST | `/api/readings` | Sensor token | CONFIRMADO EN CODIGO |
| GET | `/api/readings` | JWT filtrado | CONFIRMADO EN CODIGO |
| POST | `/api/iot/v1/ingest/batch` | Gateway HMAC | CONFIRMADO EN CODIGO |
| GET | `/api/alerts` | JWT filtrado | CONFIRMADO EN CODIGO |
| GET | `/api/alerts/active` | JWT filtrado | CONFIRMADO EN CODIGO |
| PATCH | `/api/alerts/{id}/acknowledge` | Admin/tecnico segun acceso | CONFIRMADO EN CODIGO |
| PATCH | `/api/alerts/{id}/resolve` | Admin/tecnico segun acceso | CONFIRMADO EN CODIGO |
| POST | `/api/operational-logs` | Admin/tecnico segun acceso | CONFIRMADO EN CODIGO |
| POST | `/api/operational-logs/installations` | Admin/tecnico segun acceso | CONFIRMADO EN CODIGO |
| GET | `/api/reports/weekly` | JWT filtrado | CONFIRMADO EN CODIGO |
| GET | `/api/reports/weekly/pdf` | JWT filtrado | CONFIRMADO EN CODIGO |
| GET | `/api/admin/users` | Admin | CONFIRMADO EN CODIGO |
| POST | `/api/admin/users` | Admin | CONFIRMADO EN CODIGO |
| PATCH | `/api/admin/users/{id}` | Admin | CONFIRMADO EN CODIGO |
| POST | `/api/admin/users/{id}/reset-password` | Admin | CONFIRMADO EN CODIGO |
| POST | `/api/admin/users/{id}/assign-storage-units` | Admin | CONFIRMADO EN CODIGO |
| GET | `/api/admin/notifications/deliveries` | Admin | CONFIRMADO EN CODIGO |
| POST | `/api/admin/notifications/test/{channel}` | Admin | CONFIRMADO EN CODIGO |

## Seguridad y RBAC

Archivo principal: `backend/app/api/deps.py`

Modelo confirmado:

- `admin`: acceso total.
- `technician`: acceso operativo a storage units asignadas.
- `client`: acceso a storage units asignadas o de su empresa segun reglas existentes.
- Ingestion IoT no usa JWT; usa token del dispositivo o firma HMAC del gateway.

Puntos de control:

- `get_current_user`
- `require_role`
- `assigned_storage_unit_ids`
- `require_storage_unit_access`
- `require_device_access`
- `require_alert_access`
- helpers de filtrado por empresa, sitio, unidad, dispositivo y alerta.

## Motor IoT y alertas

### Ingestion legacy

Ruta: `POST /api/readings`  
Estado: CONFIRMADO EN CODIGO

Uso:

- Sensores existentes envian `device_id` y `device_token`.
- El backend valida dispositivo y token.
- La lectura se persiste.
- Se actualiza `last_seen_at` cuando corresponde.
- Se evalua el motor de alertas.

### Ingestion batch gateway

Ruta: `POST /api/iot/v1/ingest/batch`  
Estado: CONFIRMADO EN CODIGO

Headers:

- `X-Agro-Gateway-ID`
- `X-Agro-Timestamp`
- `X-Agro-Nonce`
- `X-Agro-Signature`

Comportamientos confirmados:

- HMAC-SHA256.
- Ventana temporal para firma.
- Nonce para anti-replay.
- Registro de batch y eventos.
- Idempotencia por lectura.
- Estados por lectura: `accepted`, `duplicate`, `rejected_invalid`, `rejected_unknown_device`, `rejected_unauthorized`, `temporary_error`.

## Errores

Estado: CONFIRMADO EN CODIGO.

El backend tiene handlers para errores SQLAlchemy y health DB con mensajes controlados. Las pantallas web/mobile deben traducir errores a mensajes humanos y no mostrar stack traces, tokens ni SQL crudo.

## Comandos backend

```powershell
cd backend
py -3.13 -m alembic upgrade head
py -3.13 -m app.seed
py -3.13 -m pytest -p no:cacheprovider
```

## Riesgos backend abiertos

| Riesgo | Estado | Accion |
|---|---|---|
| Envio WhatsApp/Telegram real no validado | NO VERIFICADO | Probar con credenciales reales y consentimiento. |
| Firmware/gateway real no probado | NO VERIFICADO | Ejecutar prueba fisica end-to-end. |
| Datos productivos dependen de Neon/Render | CONFIGURADO PERO NO VERIFICADO EN ESTA FASE | Ejecutar smoke test cloud antes de demo. |
| CORS productivo depende de env | PENDIENTE | Confirmar origen Vercel exacto en Render. |

