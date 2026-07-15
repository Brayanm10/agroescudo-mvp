# 02. Estructura del repositorio

Estado del documento: BORRADOR CONTROLADO  
Fecha de auditoria: 2026-07-02  
Fuente principal: inspeccion del repositorio local

## Estructura superior confirmada

| Ruta | Estado | Proposito |
|---|---|---|
| `backend/` | CONFIRMADO EN CODIGO | API FastAPI, modelos, migraciones, servicios, tests y PDF. |
| `frontend/` | CONFIRMADO EN CODIGO | Dashboard web Next.js, Tailwind, Recharts y componentes B2B. |
| `mobile/` | CONFIRMADO EN CODIGO | App Flutter Android conectada por `API_BASE_URL`. |
| `landing/` | CONFIRMADO EN CODIGO | Landing comercial separada. |
| `firmware/` | CONFIRMADO EN CODIGO | Codigo ESP32/LoRa nodo, gateway y Arduino IDE. |
| `docs/` | CONFIRMADO EN CODIGO | Documentacion tecnica y comercial del piloto. |
| `dist/` | CONFIRMADO EN CODIGO | Artefactos locales generados. No debe versionar APKs ni secretos. |
| `.env.example` | CONFIRMADO EN CODIGO | Variables ejemplo sin secretos reales. |
| `.gitignore` | CONFIRMADO EN CODIGO | Exclusiones de builds, envs y artefactos. |
| `docker-compose.yml` | CONFIRMADO EN CODIGO | Despliegue local con servicios de soporte. |

## Backend

Ruta base: `backend/`

| Archivo o carpeta | Proposito |
|---|---|
| `backend/app/main.py` | Crea la app FastAPI, CORS, routers y health checks. |
| `backend/app/core/config.py` | Configuracion por variables de entorno. |
| `backend/app/db/session.py` | Engine SQLAlchemy y sesiones. |
| `backend/app/models.py` | Modelos principales de dominio. |
| `backend/app/schemas.py` | Contratos de entrada/salida API. |
| `backend/app/api/deps.py` | JWT, usuario actual, roles y filtros RBAC. |
| `backend/app/api/routes/` | Routers REST por modulo. |
| `backend/app/services/` | Logica de negocio: alertas, PDF, IoT, notificaciones, insights. |
| `backend/alembic/versions/` | Migraciones de base de datos. |
| `backend/tests/` | Tests pytest. |
| `backend/scripts/start.sh` | Arranque productivo del contenedor. |

### Migraciones confirmadas

| Archivo | Estado |
|---|---|
| `202605260001_initial_schema.py` | CONFIRMADO EN CODIGO |
| `202605260002_dashboard_api_schema.py` | CONFIRMADO EN CODIGO |
| `202605270001_user_roles.py` | CONFIRMADO EN CODIGO |
| `202605310001_pilot_operations.py` | CONFIRMADO EN CODIGO |
| `202606070001_notifications_ai.py` | CONFIRMADO EN CODIGO |
| `202606180001_notification_deliveries.py` | CONFIRMADO EN CODIGO |
| `202606180002_b2b_admin_flow.py` | CONFIRMADO EN CODIGO |
| `202607010001_iot_batch_ingestion.py` | CONFIRMADO EN CODIGO |
| `202607020001_account_profile_insights.py` | CONFIRMADO EN CODIGO |

## Frontend web

Ruta base: `frontend/`

| Archivo o carpeta | Proposito |
|---|---|
| `frontend/app/page.tsx` | Pantalla principal y flujos por rol. |
| `frontend/lib/api.ts` | Cliente API, URL base y diagnostico de errores. |
| `frontend/lib/types.ts` | Tipos TypeScript compartidos. |
| `frontend/components/AppLayout.tsx` | Layout principal del dashboard. |
| `frontend/components/Sidebar.tsx` | Navegacion por rol. |
| `frontend/components/SupportChatbot.tsx` | Chatbot de ayuda basado en reglas de la app. |
| `frontend/components/ReadingChart.tsx` | Graficas de lecturas. |
| `frontend/components/reports/` | Componentes de reporte PDF frontend o compatibilidad visual. |
| `frontend/.env.example` | API local de desarrollo. |
| `frontend/.env.production.example` | API publica esperada para despliegue. |

## Mobile Flutter

Ruta base: `mobile/`

| Archivo o carpeta | Proposito |
|---|---|
| `mobile/lib/core/api_client.dart` | Cliente HTTP, `API_BASE_URL`, timeouts y errores. |
| `mobile/lib/core/app_store.dart` | Estado de sesion, cache y datos operativos. |
| `mobile/lib/ui/screens.dart` | Pantallas principales Android. |
| `mobile/pubspec.yaml` | Dependencias Flutter. |
| `mobile/android/` | Proyecto Android nativo generado por Flutter. |

## Firmware

Ruta base: `firmware/`

| Archivo o carpeta | Proposito |
|---|---|
| `firmware/platformio.ini` | Configuracion PlatformIO. |
| `firmware/README.md` | Guia firmware. |
| `firmware/node_lora_t3/` | Nodo LoRa para medicion. |
| `firmware/gateway_tbeam/` | Gateway LoRa + WiFi/4G. |
| `firmware/shared/` | Protocolo y funciones comunes. |
| `firmware/arduino_ide/` | Sketches para Arduino IDE. |

Estado: CONFIGURADO PERO NO VERIFICADO con hardware en esta fase.

## Donde modificar cada cosa

| Necesidad | Archivo recomendado | Precaucion |
|---|---|---|
| Nueva ruta backend | `backend/app/api/routes/*.py` y `backend/app/main.py` | Proteger con deps/RBAC si no es ingestion IoT. |
| Nuevo campo SQL | `backend/app/models.py` + Alembic | No modificar datos productivos sin migracion. |
| Nuevo schema API | `backend/app/schemas.py` | Mantener compatibilidad con web/mobile. |
| Regla de alerta | `backend/app/services/alerts.py` | No duplicar alertas activas. |
| Reporte PDF | `backend/app/services/pdf_report.py` | Validar layout y no incluir secretos. |
| URL API web | `frontend/.env*` y `frontend/lib/api.ts` | En produccion no usar localhost. |
| URL API Flutter | `--dart-define=API_BASE_URL=...` y `mobile/lib/core/api_client.dart` | Release debe usar HTTPS publico. |
| Sidebar web | `frontend/components/Sidebar.tsx` | Mantener visibilidad por rol. |
| Pantalla principal web | `frontend/app/page.tsx` | Archivo amplio; cambios pequenos y testeados. |
| Chatbot ayuda | `frontend/components/SupportChatbot.tsx` | No prometer IA real si no esta habilitada. |
| LoRa protocolo | `firmware/shared/` | Requiere pruebas fisicas. |
| Arduino IDE | `firmware/arduino_ide/` | Validar librerias del hardware real. |

## Archivos sensibles o de cuidado

No versionar ni incluir en documentos finales:

- `.env`
- tokens reales
- claves JWT reales
- API keys
- keystores Android
- APKs
- bases SQLite reales con datos sensibles
- dumps PostgreSQL
- certificados privados

## Comandos de verificacion por componente

Backend:

```powershell
cd backend
py -3.13 -m alembic upgrade head
py -3.13 -m app.seed
py -3.13 -m pytest -p no:cacheprovider
```

Frontend:

```powershell
cd frontend
npm install
npm run build
```

Flutter:

```powershell
cd mobile
flutter clean
flutter pub get
flutter analyze
flutter test
flutter build apk --release --dart-define=API_BASE_URL=https://agroescudo-api.onrender.com
```

Firmware:

```powershell
cd firmware
pio run
```

Estado firmware: PENDIENTE / NO VERIFICADO si no existe toolchain o hardware durante la prueba.

## Regla de documentacion

Todo documento maestro debe indicar si una afirmacion esta:

- CONFIRMADO EN CODIGO
- CONFIRMADO POR PRUEBA
- CONFIGURADO PERO NO VERIFICADO
- PROPUESTO
- PENDIENTE
- NO VERIFICADO

