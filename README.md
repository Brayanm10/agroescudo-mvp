# AgroEscudo

AgroEscudo es una plataforma agri-tech B2B para monitoreo de riesgo operativo y postcosecha en silos, galpones, centros de acopio, molinos y agroindustrias.

El repositorio incluye:

- Backend FastAPI con JWT, SQLAlchemy, Alembic, ingestion IoT, alertas, bitacora, umbrales y reporte semanal.
- Base de datos SQLite para desarrollo local sin Docker.
- PostgreSQL como opcion para Docker/produccion.
- Frontend Next.js con dashboard industrial para operar el MVP con datos reales del backend.
- App Flutter Android para pilotos de campo con roles, cache local de solo lectura y descarga de PDF.
- Flujo de pilotos comerciales con alta guiada, asignacion de responsables y checklist de instalacion.

## Stack

- Backend: Python 3.12+, FastAPI
- Base de datos local: SQLite
- Base de datos Docker/produccion: PostgreSQL 16
- ORM: SQLAlchemy 2.0
- Migraciones: Alembic
- Auth: JWT simple
- Frontend: Next.js, React, TypeScript, Tailwind CSS, Recharts
- PDF compartido: FastAPI + `reportlab`
- Mobile: Flutter Android
- Tests: pytest

## Variables De Entorno

Backend (`backend/.env`, copiar desde `backend/.env.example`):

| Variable | Uso | Valor local recomendado |
| --- | --- | --- |
| `DATABASE_URL` | Conexion SQLAlchemy. SQLite permite correr sin Docker; PostgreSQL queda disponible para despliegue. | `sqlite:///./agroescudo_dev.db` |
| `JWT_SECRET` | Firma de tokens JWT. Cambiar antes de compartir o desplegar la app. | `change-me-in-production` solo para desarrollo |
| `API_URL` | URL publica de referencia para operadores y scripts externos. | `http://127.0.0.1:8010` |
| `ENVIRONMENT` | `local` y `demo` habilitan la simulacion comercial admin; `production` la bloquea. | `local` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Duracion de sesion JWT. | `480` |
| `WHATSAPP_ENABLED` / `WHATSAPP_ACCESS_TOKEN` / `WHATSAPP_PHONE_NUMBER_ID` | Activa envio por WhatsApp Cloud API. | `false` hasta tener credenciales Meta |
| `TELEGRAM_ENABLED` / `TELEGRAM_BOT_TOKEN` | Activa envio por bot de Telegram. | `false` hasta crear bot |
| `NOTIFICATIONS_DRY_RUN` | Registra entregas WhatsApp/Telegram sin enviar mensajes reales. | `true` |
| `FCM_ENABLED` / `FIREBASE_PROJECT_ID` / `FIREBASE_SERVICE_ACCOUNT_FILE` | Activa push notification para Android. | `false` hasta configurar Firebase |
| `AI_ENABLED` / `OPENAI_API_KEY` / `OPENAI_MODEL` | Activa recomendaciones IA; sin API key usa reglas internas. | `false` |

El backend sigue aceptando `SECRET_KEY` como alias historico de `JWT_SECRET`, pero las nuevas configuraciones deben usar `JWT_SECRET`.

Frontend (`frontend/.env.local`, copiar desde `frontend/.env.example`):

| Variable | Uso | Valor local recomendado |
| --- | --- | --- |
| `NEXT_PUBLIC_API_URL` | URL del backend consumida desde el navegador. | `http://127.0.0.1:8010` |
| `NEXT_PUBLIC_SHOW_DEMO_CREDENTIALS` | Muestra el bloque de credenciales demo en login. En Vercel publico debe ser `false`. | `true` local |

## Modo Local Sin Docker

Backend en Windows:

```powershell
cd backend
py -3.13 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
alembic upgrade head
python -m app.seed
python -m uvicorn app.main:app --host 127.0.0.1 --port 8010
```

Despues de instalar dependencias una vez, tambien puedes usar los atajos PowerShell:

```powershell
cd backend
powershell -ExecutionPolicy Bypass -File scripts\seed.ps1
powershell -ExecutionPolicy Bypass -File scripts\dev.ps1
```

La API queda disponible en:

- `http://127.0.0.1:8010`
- `http://127.0.0.1:8010/docs`
- `http://127.0.0.1:8010/api/health/db`

El `.env.example` del backend usa SQLite por defecto:

```env
DATABASE_URL=sqlite:///./agroescudo_dev.db
```

## Frontend Local

En otra terminal:

```powershell
cd frontend
copy .env.example .env.local
```

Edita `frontend/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://127.0.0.1:8010
```

Luego:

```powershell
npm install
npm run dev
```

El frontend queda disponible en:

- `http://localhost:3000`

Login demo:

- Admin: `admin@agroescudo.local` / `admin123`
- Tecnico: `tecnico@agroescudo.local` / `tecnico123`
- Cliente silo demo: `cliente@silo-demo.local` / `cliente123`

En Vercel publico configura `NEXT_PUBLIC_SHOW_DEMO_CREDENTIALS=false` para no mostrar estas credenciales en pantalla.

Build frontend:

```powershell
npm run build
```

El script usa `next build --webpack` para evitar fallos de permisos de Turbopack en Windows.

## Identidad Visual Frontend

El frontend usa los assets oficiales en `frontend/public/brand/`:

- `logo-horizontal.png`
- `logo-horizontal-transparent.png`
- `logo-vertical-campo.png`
- `shield-transparent.png`
- `shield-white.png`

La UI fue ajustada hacia un lenguaje B2B industrial/agtech:

- Sidebar verde profundo con marca integrada.
- Login premium con composicion de confianza operacional.
- Dashboard ejecutivo con KPIs, estado general y alertas recientes.
- Detalle de silo/galpon con metricas prioritarias, graficas y bitacora.
- Tablas, badges, formularios, empty states y errores con estilos consistentes.
- Modulo visual `Consulta tu sensor` con recomendaciones operativas basadas en lecturas y alertas existentes.
- Accesos de mantenimiento, ayuda y educacion tecnica sin requerir backend nuevo.

## Reportes PDF

FastAPI genera un unico reporte PDF corporativo con `reportlab`. La web y la app Android descargan el mismo archivo desde:

```text
GET /api/reports/weekly/pdf?storage_unit_id=
```

El componente web `frontend/components/reports/ReportDownloadButton.tsx` consume ese endpoint. La plantilla React PDF previa permanece temporalmente como referencia visual mientras se valida paridad en piloto; ya no interviene en la descarga principal.

Uso en la app:

- Pantalla `Reportes`: boton `Descargar reporte PDF`.
- Vista de silo/galpon: accion secundaria para descargar el PDF semanal de la unidad seleccionada.

El PDF incluye:

- Portada corporativa AgroEscudo.
- Resumen ejecutivo.
- Consulta del sensor / asistente operativo basado en reglas del MVP.
- Metricas principales.
- Estado del piloto, checklist de instalacion y mantenimientos registrados.
- Graficas simples de temperatura y humedad con lecturas disponibles.
- Alertas del periodo con recomendaciones operativas.
- Bitacora de acciones.
- Conclusiones y recomendaciones.

Assets del PDF:

- Coloca logos oficiales en `frontend/public/brand/`.
- El PDF usa `logo-horizontal-transparent.png`, `shield-transparent.png` y `shield-white.png` si estan disponibles.

Limitaciones actuales:

- La plantilla PDF es comun para web y Android; los ajustes visuales se realizan en `backend/app/services/pdf_reports.py`.
- Si un valor no existe en la API, el reporte muestra `Dato no disponible` o `No registrado durante el periodo`.
- El asistente actual no llama a un modelo externo: usa reglas operativas simples del MVP para mantener bajo riesgo tecnico.

## App Flutter Android

La primera app de piloto vive en `mobile/`. Consume FastAPI como unica fuente de verdad: no replica usuarios, lecturas ni alertas en Firebase. Firebase queda reservado para una fase posterior de notificaciones push con FCM.

Incluye:

- Login JWT para `admin`, `technician` y `client`.
- Resumen operativo adaptado al rol.
- Silos, galpones, lecturas y curvas historicas.
- Alertas con reconocimiento para tecnico/admin y resolucion para admin.
- Bitacora, mantenimiento y checklist de instalacion para tecnico/admin.
- Descarga y apertura del PDF semanal.
- Cache local de solo lectura para consultar el ultimo estado sin internet.
- Bloqueo de escrituras cuando no existe conectividad.

Preparacion:

```powershell
cd mobile
flutter pub get
flutter doctor
```

Emulador Android:

```powershell
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8010
```

Telefono Android fisico conectado por USB:

1. Levanta FastAPI accesible en la red local:

```powershell
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8010
```

2. Reemplaza `192.168.1.50` por la IPv4 LAN del PC:

```powershell
cd mobile
flutter run --dart-define=API_BASE_URL=http://192.168.1.50:8010
```

APK release para piloto:

```powershell
cd mobile
flutter build apk --release --dart-define=API_BASE_URL=https://api.agroescudo.com
```

El archivo se genera en `mobile/build/app/outputs/flutter-apk/app-release.apk`. Antes de distribuir una APK productiva configura firma Android propia; la primera APK local de piloto usa la firma de depuracion del scaffold Flutter.

## Modo Docker con PostgreSQL

Docker es opcional. Para usarlo, crea primero una configuracion local a partir del ejemplo:

```powershell
copy .env.example .env
docker compose up --build
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.seed
```

La API queda disponible en:

- `http://localhost:8000`
- `http://localhost:8000/docs`
- `http://localhost:8000/api/health/db`

`docker-compose.yml` incluye health checks para PostgreSQL y FastAPI. El contenedor carga `.env`, no `.env.example`, para evitar usar secretos de ejemplo como configuracion real.

Para usar PostgreSQL fuera de Docker, configura:

```env
DATABASE_URL=postgresql+psycopg://agroescudo:agroescudo@localhost:5432/agroescudo
```

## Seed

El seed crea:

- Empresa cliente: `Acopio Valle Bajo S.R.L.`
- Usuario admin: `admin@agroescudo.local` / `admin123`
- Usuario tecnico: `tecnico@agroescudo.local` / `tecnico123`
- Usuario cliente: `cliente@silo-demo.local` / `cliente123`
- Sitio: `Centro de Acopio Norte`, Quillacollo, Cochabamba
- Unidades: `Silo Maiz Seco 01`, `Galpon Sorgo 02` y `Almacen Balanceado 03`
- Dispositivos: `SILO-001`, `GALPON-001` y `SILO-002`
- Token principal del dispositivo `SILO-001`: `secret-token`
- Umbrales demo de temperatura, humedad y bateria
- Lecturas historicas de siete dias para graficas reales
- Alertas normales, preventivas, criticas y tecnicas
- Bitacora profesional con instalacion, mantenimiento, inspecciones y acciones correctivas

El seed es idempotente: si la demo ya existe, actualiza estructura, usuarios y evidencia esperada sin duplicar registros.

Desde la seccion `Pilotos`, el admin puede usar `Borrar datos operativos` para limpiar lecturas, alertas y bitacora de una unidad sin eliminar el cliente, el sitio ni el dispositivo. Esto permite reiniciar una presentacion y volver a cargar la evidencia con `python -m app.seed`.

## Modo Presentacion Comercial

El rol `admin` dispone de la seccion `Modo presentacion`, accesible desde el dashboard y el sidebar. Esta vista organiza una demostracion B2B de 5 a 7 minutos:

1. Sitio monitoreado.
2. Silo con nodo IoT asignado.
3. Ultima lectura recibida.
4. Alerta critica automatica.
5. Registro de accion correctiva.
6. Descarga del reporte PDF.

La accion `Simular lectura critica` usa `POST /api/demo/simulate-critical-reading`. El endpoint reutiliza el motor real de ingestion y alertas, pero solo esta disponible para `admin` cuando `ENVIRONMENT` es `local` o `demo`. Tecnicos y clientes no ven el acceso y reciben `403` si intentan invocarlo directamente.

Para una presentacion, entra como admin y abre `Modo presentacion` desde el sidebar. El boton `Simular lectura critica` agrega una lectura fuera de rango al nodo `SILO-001`, actualiza alertas y deja evidencia visible para el PDF.

Prueba directa por API en PowerShell:

```powershell
$login = Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8010/api/auth/login" `
  -ContentType "application/json" `
  -Body '{"email":"admin@agroescudo.local","password":"admin123"}'

Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8010/api/demo/simulate-critical-reading" `
  -Headers @{ Authorization = "Bearer $($login.access_token)" }
```

## Roles Demo

- `admin`: ve toda la demo, prepara pilotos completos, asigna responsables, reconoce y resuelve alertas, registra bitacora y edita umbrales.
- `technician`: ve operacion demo, dispositivos, lecturas y alertas; puede registrar checklist de instalacion, mantenimiento y acciones correctivas.
- `client`: ve su empresa/sitio/silo demo en modo lectura, consulta estado del piloto, alertas, bitacora y descarga reportes PDF.

`POST /api/readings` sigue siendo publico para dispositivos IoT y usa `device_token`, no JWT.

## Usuarios, Notificaciones e IA Operativa

El admin dispone de secciones para cierre comercial de piloto:

- `Usuarios`: crear usuarios, activar/desactivar cuentas, resetear password y asignar storage units a tecnicos/clientes.
- `Notificaciones`: registrar pruebas dry-run de WhatsApp/Telegram y revisar entregas auditables.

El acceso efectivo se limita por storage unit:

- `admin`: acceso total.
- `technician`: solo unidades asignadas en `assigned_technician_id`.
- `client`: solo unidades asignadas en `assigned_client_id`.

AgroEscudo ya incluye infraestructura backend para notificaciones multicanal:

- `GET /api/notifications/preferences`
- `PUT /api/notifications/preferences/{channel}` con `channel`: `whatsapp`, `telegram` o `push`
- `POST /api/notifications/push-tokens`
- `GET /api/notifications/events`
- `POST /api/notifications/test/{channel}`
- `GET /api/ai/alerts/{id}/recommendation`

Cuando una lectura crea una alerta nueva, el backend busca preferencias activas y registra eventos de notificacion. Para WhatsApp/Telegram tambien registra `notification_deliveries`, pensados para auditoria comercial. Con `NOTIFICATIONS_DRY_RUN=true`, el sistema deja evidencia sin enviar mensajes reales; es el modo recomendado para pilotos y demo.

Para activar WhatsApp necesitas:

- Meta Business verificado o configuracion Cloud API.
- `WHATSAPP_ACCESS_TOKEN`
- `WHATSAPP_PHONE_NUMBER_ID`
- telefono destino en formato internacional, por ejemplo `5917XXXXXXX`.
- Plantillas aprobadas si deseas iniciar conversaciones fuera de la ventana permitida.

Para activar Telegram necesitas:

- Crear bot con BotFather.
- `TELEGRAM_BOT_TOKEN`.
- Obtener el `chat_id` del usuario o grupo.

Para activar push Android necesitas:

- Proyecto Firebase.
- `google-services.json` para la app Flutter.
- Service account JSON en backend.
- `FIREBASE_PROJECT_ID` y `FIREBASE_SERVICE_ACCOUNT_FILE`.

Para activar IA real necesitas:

- `OPENAI_API_KEY`.
- `AI_ENABLED=true`.
- Modelo en `OPENAI_MODEL`. Sin esta configuracion, el endpoint usa recomendaciones por reglas internas.

## Probar Los Tres Roles

1. Limpia la sesion desde el boton de cerrar sesion o borra `localStorage` del navegador.
2. Ingresa como admin y verifica `Dashboard`, `Modo presentacion`, `Pilotos`, `Umbrales` y descarga PDF.
3. Cierra sesion e ingresa como tecnico. Verifica lecturas, alertas, bitacora y mantenimiento. No debe aparecer `Modo presentacion`.
4. Cierra sesion e ingresa como cliente. Verifica estado del silo, alertas, bitacora y reporte PDF. No debe aparecer configuracion tecnica ni simulacion.

La descarga PDF esta disponible desde `Reportes`, desde el detalle de storage unit y desde el recorrido admin `Modo presentacion`.

## Flujo De Piloto Comercial

La seccion `Pilotos` esta disponible para el rol admin. El formulario guiado crea o reutiliza:

- Cliente / empresa.
- Sitio operativo.
- Silo, galpon o ambiente monitoreado.
- Dispositivo IoT y token de ingestion.
- Usuario cliente.
- Tecnico responsable.
- Umbrales iniciales.

La bitacora incluye categorias `installation`, `maintenance`, `corrective_action`, `inspection` y `general`.

El tecnico puede registrar un checklist de instalacion con:

- Ubicacion fisica.
- Instalacion correcta del sensor.
- Conectividad verificada.
- Lectura inicial registrada.
- Bateria verificada.
- Observaciones tecnicas.

El estado del piloto se calcula con la evidencia disponible: instalacion, lecturas, alertas activas y reportes generados.

## Probar Login por API

```bash
curl -X POST http://127.0.0.1:8010/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@agroescudo.local","password":"admin123"}'
```

Usa el `access_token` devuelto como bearer token:

```bash
curl http://127.0.0.1:8010/api/me \
  -H "Authorization: Bearer ACCESS_TOKEN"
```

## Probar POST /api/readings

Este endpoint es para dispositivos IoT y no requiere JWT; valida `device_id` y `device_token`.

```bash
curl -X POST http://127.0.0.1:8010/api/readings \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "SILO-001",
    "device_token": "secret-token",
    "grain_temperature": 31.5,
    "ambient_temperature": 28.2,
    "ambient_humidity": 72.1,
    "battery_voltage": 3.91,
    "signal_quality": -67,
    "timestamp": "2026-05-26T20:00:00Z"
  }'
```

Si la lectura supera umbrales, la API crea alertas automaticamente y evita duplicar alertas activas identicas.

## Endpoints del Dashboard

- `POST /api/auth/login`
- `GET /api/me`
- `GET|POST /api/companies`
- `GET /api/companies/{id}`
- `GET|POST /api/sites`
- `GET /api/sites/{id}`
- `GET|POST /api/storage-units`
- `GET /api/storage-units/{id}`
- `GET /api/storage-units/{id}/readings`
- `GET /api/storage-units/{id}/operational-logs`
- `GET|POST /api/devices`
- `GET /api/devices/{id}`
- `GET|PUT /api/devices/{id}/thresholds`
- `GET /api/readings?device_id=&limit=&from=&to=`
- `POST /api/demo/simulate-critical-reading` (`admin`, solo entorno `local` o `demo`)
- `GET /api/alerts`
- `GET /api/alerts/active`
- `PATCH /api/alerts/{id}/acknowledge`
- `PATCH /api/alerts/{id}/resolve`
- `GET|POST /api/operational-logs`
- `POST /api/operational-logs/installations`
- `GET|POST /api/pilots`
- `GET /api/pilots/{storage_unit_id}`
- `PATCH /api/pilots/{storage_unit_id}/assignments`
- `DELETE /api/pilots/{storage_unit_id}/operational-data`
- `GET|POST /api/users`
- `GET /api/reports/weekly?storage_unit_id=`
- `GET /api/reports/weekly/pdf?storage_unit_id=`
- `GET|PUT /api/notifications/preferences`
- `POST /api/notifications/push-tokens`
- `GET /api/notifications/events`
- `POST /api/notifications/test/{channel}`
- `GET /api/ai/alerts/{id}/recommendation`
- `GET /api/health/db`

## Tests

Local:

```powershell
cd backend
python -m pytest -p no:cacheprovider
```

Atajo Windows:

```powershell
cd backend
powershell -ExecutionPolicy Bypass -File scripts\test.ps1
```

Con Docker:

```bash
docker compose exec backend python -m pytest
```

## Scripts Utiles

Backend Windows:

| Script | Comando | Uso |
| --- | --- | --- |
| Seed | `powershell -ExecutionPolicy Bypass -File scripts\seed.ps1` | Aplica migraciones y carga datos demo idempotentes. |
| Dev | `powershell -ExecutionPolicy Bypass -File scripts\dev.ps1` | Levanta FastAPI en `127.0.0.1:8010` con reload. |
| Test | `powershell -ExecutionPolicy Bypass -File scripts\test.ps1` | Ejecuta pytest sin cache. |

Frontend:

| Script | Comando | Uso |
| --- | --- | --- |
| Dev | `npm run dev` | Levanta Next.js localmente. |
| Build | `npm run build` | Verifica el build productivo con webpack. |
