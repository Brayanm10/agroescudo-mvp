# AgroEscudo - Inventario Real Del Repositorio

Fecha de inventario: 2026-07-02  
Repositorio local: `C:\Users\braya\Documents\AgroEscudo`  
Estado documental: **CONFIRMADO POR INSPECCION LOCAL**  

> Este inventario no incluye secretos reales. Las credenciales, tokens, claves HMAC, claves AES, URL privadas de base de datos y passwords deben registrarse solo en gestores seguros. En documentos se usan placeholders como `<JWT_SECRET>`, `<DATABASE_URL>`, `<GATEWAY_HMAC_SECRET>`, `<NODE_AES_KEY>` y `<WIFI_PASSWORD>`.

## 1. Estado Git

| Elemento | Valor | Estado |
| --- | --- | --- |
| Rama actual | `audit/final-pilot-readiness` | CONFIRMADO EN COMANDO |
| Commit HEAD | `b722e62 Prepare AgroEscudo pilot release` | CONFIRMADO EN COMANDO |
| Ultimos commits visibles | `b722e62`, `d30867a`, `2df9667` | CONFIRMADO EN COMANDO |
| Worktree | Hay cambios modificados y archivos nuevos sin commit | CONFIRMADO EN COMANDO |
| Riesgo | El estado no esta congelado para release | P1 |
| Accion | Antes de release candidate, revisar diff, ejecutar pruebas y crear commit firmado o trazable | PENDIENTE |

Comandos ejecutados:

```powershell
git branch --show-current
git status --short
git log -5 --oneline
git diff --stat
```

## 2. Estructura Principal

| Area | Componente | Ruta | Estado | Evidencia | Riesgo | Accion |
| --- | --- | --- | --- | --- | --- | --- |
| Backend | FastAPI, SQLAlchemy, Alembic, ReportLab | `backend/` | CONFIRMADO EN CODIGO Y PRUEBA | `backend/app/main.py`, `backend/requirements.txt`, pytest pasa | Warnings de dependencias; despliegue real requiere variables seguras | Mantener tests por cambio |
| Frontend web | Next.js, React, TypeScript, Tailwind, Recharts | `frontend/` | CONFIRMADO EN CODIGO Y PRUEBA | `frontend/package.json`, lint/build pasan | Worktree no congelado | Smoke manual por rol |
| App movil | Flutter Android | `mobile/` | CONFIRMADO EN CODIGO Y PRUEBA | `mobile/pubspec.yaml`, `flutter analyze`, `flutter test` pasan | APK release y prueba en telefono no verificados en esta fase | Generar APK y probar en Android real |
| Landing | Next.js comercial | `landing/` | CONFIRMADO EN CODIGO | `landing/package.json` | Build no ejecutado en esta pasada | Ejecutar build antes de publicar cambios |
| Firmware | PlatformIO y Arduino IDE | `firmware/` | CONFIGURADO PERO NO VERIFICADO | `firmware/platformio.ini`, `.ino`, `main.cpp` | No hay prueba fisica de nodo/gateway | Probar en banco con hardware |
| Documentacion | Docs operativos existentes | `docs/` | CONFIRMADO EN CODIGO | archivos `docs/*.md` | Algunos docs son parciales y anteriores al documento maestro | Consolidar en `docs/source/` |
| Dist | Artefactos locales | `dist/` | CONFIRMADO EN FS | carpeta existente | APK/PDF no deben versionarse | Mantener ignorado en Git |

## 3. Backend

### Stack Confirmado

| Item | Evidencia | Estado |
| --- | --- | --- |
| FastAPI | `backend/requirements.txt`, `backend/app/main.py` | CONFIRMADO EN CODIGO |
| SQLAlchemy 2 | `backend/requirements.txt`, `backend/app/models.py` | CONFIRMADO EN CODIGO |
| Alembic | `backend/alembic/` | CONFIRMADO EN CODIGO |
| PostgreSQL driver | `psycopg[binary]==3.2.13` | CONFIRMADO EN CODIGO |
| SQLite local | `DATABASE_URL` default en config | CONFIRMADO EN CODIGO |
| JWT | `backend/app/core/security.py`, `backend/app/api/routes/auth.py` | CONFIRMADO EN CODIGO |
| PDF backend | `reportlab`, `backend/app/services/pdf_reports.py` | CONFIRMADO EN CODIGO |
| IoT batch | `backend/app/api/routes/iot.py`, `backend/app/services/iot_ingestion.py` | CONFIRMADO EN CODIGO Y PRUEBA |

### Routers Confirmados

El backend registra routers en `backend/app/main.py`:

- `auth`
- `admin`
- `companies`
- `sites`
- `storage_units`
- `devices`
- `iot`
- `readings`
- `alerts`
- `operational_logs`
- `reports`
- `pilots`
- `users`
- `demo`
- `notifications`
- `ai`
- `insights`

Health checks confirmados:

- `GET /health`
- `GET /api/health/db`

### Modelos Confirmados

Modelos presentes en `backend/app/models.py`:

- `Company`
- `User`
- `Site`
- `StorageUnit`
- `Device`
- `IotGateway`
- `IotGatewayCredential`
- `IotDevice`
- `IotIngestionBatch`
- `IotReading`
- `IotIngestionEvent`
- `IotGatewayHealth`
- `SensorReading`
- `Alert`
- `OperationalLog`
- `NotificationPreference`
- `PushDeviceToken`
- `NotificationEvent`
- `NotificationDelivery`
- `ThresholdConfig`

## 4. Frontend Web

| Item | Ruta | Estado | Evidencia |
| --- | --- | --- | --- |
| App principal | `frontend/app/page.tsx` | CONFIRMADO EN CODIGO | contiene login, dashboard, roles, soporte, reportes |
| API client | `frontend/lib/api.ts` | CONFIRMADO EN CODIGO | usa `NEXT_PUBLIC_API_URL` y fallback local solo en dev |
| Tipos | `frontend/lib/types.ts` | CONFIRMADO EN CODIGO | incluye modelos de app, insights, roles |
| Layout | `frontend/components/AppLayout.tsx` | CONFIRMADO EN CODIGO | header, sidebar, cuenta |
| Sidebar | `frontend/components/Sidebar.tsx` | CONFIRMADO EN CODIGO | navegacion por rol |
| Chat ayuda | `frontend/components/SupportChatbot.tsx` | CONFIRMADO EN CODIGO | asistente por reglas y datos visibles |
| Graficas | `frontend/components/ReadingChart.tsx` | CONFIRMADO EN CODIGO | Recharts, metricas, umbral |
| PDF React legacy | `frontend/components/reports/` | CONFIRMADO EN CODIGO | existe componente PDF frontend |

Variables:

- `NEXT_PUBLIC_API_URL`: publica, solo URL de backend.
- No deben colocarse tokens, passwords ni secretos en variables `NEXT_PUBLIC_*`.

Pruebas ejecutadas recientemente:

```powershell
cd frontend
npm.cmd run lint
npm.cmd run build
```

Resultado: **CONFIRMADO POR PRUEBA, ambos pasaron**.

## 5. App Flutter

| Item | Ruta | Estado | Evidencia |
| --- | --- | --- | --- |
| API client | `mobile/lib/core/api_client.dart` | CONFIRMADO EN CODIGO | usa `API_BASE_URL`, bloquea release sin URL valida |
| Estado/sesion | `mobile/lib/core/app_store.dart` | CONFIRMADO EN CODIGO | usa store, cache y API |
| Pantallas | `mobile/lib/ui/screens.dart` | CONFIRMADO EN CODIGO | login, dashboard, units, alerts, logs, reports |
| Assets marca | `mobile/assets/brand/` | CONFIRMADO EN FS | logo integrado |

Pruebas ejecutadas recientemente:

```powershell
cd mobile
flutter analyze
flutter test
```

Resultado: **CONFIRMADO POR PRUEBA, ambos pasaron**.

No verificado en esta fase:

- `flutter build apk --release --dart-define=API_BASE_URL=https://agroescudo-api.onrender.com`
- instalacion en telefono real
- firma con keystore productivo

## 6. Landing Comercial

| Item | Ruta | Estado | Evidencia | Riesgo | Accion |
| --- | --- | --- | --- | --- | --- |
| Next.js landing | `landing/` | CONFIRMADO EN CODIGO | `landing/package.json` | Build no ejecutado en esta pasada | Ejecutar `npm run build` antes de publicar |
| Assets | `landing/public/` | CONFIRMADO EN FS | carpeta presente | enlaces/contacto no auditados aqui | Auditar en documento `07_LANDING.md` |

## 7. Firmware E IoT

| Item | Ruta | Estado | Evidencia | Riesgo | Accion |
| --- | --- | --- | --- | --- | --- |
| PlatformIO | `firmware/platformio.ini` | CONFIGURADO PERO NO VERIFICADO | archivo presente | no compilado en esta pasada | Compilar con toolchain disponible |
| Nodo LoRa | `firmware/node_lora_t3/main.cpp` | CONFIGURADO PERO NO VERIFICADO | archivo presente | no probado con hardware | Prueba de banco |
| Gateway T-Beam | `firmware/gateway_tbeam/main.cpp` | CONFIGURADO PERO NO VERIFICADO | archivo presente | no probado con hardware ni red real | Prueba de banco |
| Arduino IDE nodo | `firmware/arduino_ide/agroescudo_node_lora/` | CONFIGURADO PERO NO VERIFICADO | `.ino` presente | no compilado en Arduino IDE | Validar librerias |
| Arduino IDE gateway | `firmware/arduino_ide/agroescudo_gateway_wifi_lora/` | CONFIGURADO PERO NO VERIFICADO | `.ino` presente | no compilado en Arduino IDE | Validar librerias |
| Protocolo compartido | `firmware/shared/` | CONFIGURADO PERO NO VERIFICADO | headers/cpp presentes | seguridad fisica no validada | Revisar claves y pruebas |

Backend IoT confirmado:

- Endpoint: `POST /api/iot/v1/ingest/batch`
- Headers esperados: `X-Agro-Gateway-ID`, `X-Agro-Timestamp`, `X-Agro-Nonce`, `X-Agro-Signature`
- HMAC-SHA256: CONFIRMADO EN CODIGO
- Anti-replay por nonce: CONFIRMADO EN CODIGO
- Idempotencia por lectura: CONFIRMADO EN CODIGO Y PRUEBA

## 8. Variables, Secretos Y Configuracion

| Variable | Uso | Ubicacion | Estado | Nota segura |
| --- | --- | --- | --- | --- |
| `DATABASE_URL` | conexion SQLAlchemy | backend env | CONFIRMADO EN CODIGO | usar `<DATABASE_URL>` en docs |
| `JWT_SECRET` | firma JWT y base para cifrado | backend env | CONFIRMADO EN CODIGO | usar `<JWT_SECRET>`, rotar antes de produccion |
| `CORS_ORIGINS` | origenes permitidos | backend env | CONFIRMADO EN CODIGO | explicito en production |
| `ENVIRONMENT` | local/demo/production | backend env | CONFIRMADO EN CODIGO | production bloquea comodines CORS |
| `NOTIFICATIONS_DRY_RUN` | simulacion notificaciones | backend env | CONFIRMADO EN CODIGO | recomendado `true` hasta credenciales reales |
| `WHATSAPP_*` | WhatsApp Cloud API | backend env | CONFIGURADO PERO NO VERIFICADO | no incluir tokens |
| `TELEGRAM_BOT_TOKEN` | Telegram | backend env | CONFIGURADO PERO NO VERIFICADO | no incluir token |
| `OPENAI_API_KEY` | IA opcional | backend env | CONFIGURADO PERO NO VERIFICADO | no requerido para asistente por reglas |
| `NEXT_PUBLIC_API_URL` | URL backend web | frontend env | CONFIRMADO EN CODIGO | publica, no secreto |
| `API_BASE_URL` | URL backend mobile | dart define | CONFIRMADO EN CODIGO | publica, no secreto |
| `GATEWAY_HMAC_SECRET` | firma gateway | backend/gateway | PROPUESTO/CONFIGURABLE | usar gestor seguro |
| `NODE_AES_KEY` | cifrado nodo LoRa | firmware/provisioning | PROPUESTO/CONFIGURABLE | no documentar valor real |

## 9. Pruebas Confirmadas En Esta Sesion

| Comando | Resultado | Estado |
| --- | --- | --- |
| `py -3.13 -m pytest -p no:cacheprovider` en `backend` | `72 passed, 63 warnings` | CONFIRMADO POR PRUEBA |
| `npm.cmd run lint` en `frontend` | sin errores | CONFIRMADO POR PRUEBA |
| `npm.cmd run build` en `frontend` | build completo | CONFIRMADO POR PRUEBA |
| `flutter analyze` en `mobile` | No issues found | CONFIRMADO POR PRUEBA |
| `flutter test` en `mobile` | All tests passed | CONFIRMADO POR PRUEBA |

No ejecutado en esta fase:

- landing build
- APK release
- PlatformIO firmware build
- prueba fisica LoRa
- smoke remoto Render/Vercel/Neon
- envio real WhatsApp/Telegram/FCM

## 10. Funciones Incompletas, Riesgos Y Contradicciones

| Area | Hallazgo | Estado | Riesgo | Accion |
| --- | --- | --- | --- | --- |
| Release | Worktree con cambios no confirmados | CONFIRMADO EN COMANDO | P1 | Congelar release en commit despues de validacion |
| Hardware | Nodo/gateway no probados fisicamente | NO VERIFICADO | P0 para piloto pagado | Prueba de banco obligatoria |
| Firmware | Compilacion no verificada en esta fase | NO VERIFICADO | P1 | Ejecutar PlatformIO/Arduino IDE |
| Notificaciones | WhatsApp/Telegram reales dependen de credenciales externas | CONFIGURADO PERO NO VERIFICADO | P1 | Mantener dry-run hasta validar |
| Mobile release | APK release no generado en esta fase | NO VERIFICADO | P1 | Generar y probar en Android |
| Documentacion | READMEs mezclan instrucciones locales, demo y piloto | CONFIRMADO EN INSPECCION | P2 | Consolidar en documento maestro y separar ambiente local/comercial |
| Secretos iniciales | Seed local contiene credenciales iniciales y tokens de prueba | CONFIRMADO EN CODIGO | P1 si se divulga | No incluir valores en documento maestro; rotar en entorno real |
| Seguridad | Rate limiting formal no confirmado | PENDIENTE | P2/P1 segun exposicion | Evaluar limite para login e ingestion |

## 11. Veredicto Actual

Clasificacion honesta: **LISTO PARA DEMO COMERCIAL CONTROLADA**.

No se declara listo para piloto pagado porque faltan evidencias externas:

- prueba fisica LoRa nodo/gateway;
- APK release en dispositivo real;
- smoke remoto completo;
- backup/restore probado contra base productiva o staging;
- notificaciones reales si se prometen al cliente;
- revision final de secretos y rotacion.

