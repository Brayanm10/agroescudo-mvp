# Reporte De Tests

## Cierre P1 - 23 De Julio De 2026

La regresion final P1 se ejecuto despues de validar P0 y completar las fases 1 a 8.

- Alembic: downgrade `202607230002 -> 202607230001` y upgrade a `head`, aprobado.
- Seed: aprobado; conserva maestros y deja datos operativos limpios.
- Backend: `118 passed`, `265 warnings`, 157.05 s en la ultima regresion.
- Frontend: ESLint aprobado, Vitest `8 passed`, build Next.js aprobado.
- Landing: build Next.js aprobado.
- Flutter: analyze sin observaciones, tests `3 passed`, APK release aprobado.
- APK: 68.31 MB, SHA-256 `AFDD1DC08FB5E901DC00703C0352E2E929480F6431ACC2AB84E0240A1C357445`.
- Firmware nodo: SUCCESS, RAM 6.8%, flash 25.2%.
- Firmware gateway: SUCCESS, RAM 3.8%, flash 87.7%.

Advertencias conocidas:

- ReportLab y python-jose emiten deprecaciones para Python futuro.
- SQLite emite advertencia al ordenar el teardown por el ciclo `companies/users`.
- npm audit informa 5 vulnerabilidades altas en frontend y 3 en landing; no se aplico `audit fix` automatico.
- Flutter `clean` aviso inicialmente que un archivo estaba en uso; la secuencia continuo y el APK final se genero correctamente.
- Camara, QR, sensores y LoRa reales quedan `NO VERIFICADO` hasta prueba fisica.

Este documento se actualiza al cierre de cada auditoria.

## Backend

Comandos:

```powershell
cd backend
py -3.13 -m alembic upgrade head
py -3.13 -m app.seed
py -3.13 -m pytest -p no:cacheprovider
```

Resultado:

```text
97 passed, 194 warnings
```

Notas:

- Las pruebas de IoT batch V1/V2/V3, telemetria por nodo, calibracion versionada y RBAC pasaron.
- Warnings conocidos: `python-jose` usa `datetime.utcnow()` internamente.
- Seed local deja en cero: `sensor_readings`, `alerts`, `operational_logs`, `notification_deliveries`, `notification_events`, `iot_readings`, `iot_ingestion_batches`, `iot_ingestion_events`, `iot_gateway_health`.

## Frontend

Comandos:

```powershell
cd frontend
npm.cmd install
npm.cmd run lint
npm.cmd run test
npm.cmd run build
```

Resultado:

```text
npm install: 5 vulnerabilidades reportadas por npm audit (1 moderada, 4 altas); requieren revision separada, sin aplicar actualizaciones mayores automaticas.
npm run lint: exitoso.
npm run test: 8 pruebas aprobadas.
npm run build: exitoso.
```

Nota:

- No se ejecuto `npm audit fix --force`.

## Landing

Comandos:

```powershell
cd landing
npm.cmd install
npm.cmd run build
```

Resultado:

```text
npm install: up to date; 2 vulnerabilidades moderadas reportadas por npm audit.
npm run build: exitoso.
```

## Flutter

Comandos:

```powershell
cd mobile
flutter pub get
flutter analyze
flutter test
flutter build apk --release --dart-define=API_BASE_URL=https://agroescudo-api.onrender.com
```

Resultado:

```text
Flutter 3.38.9 / Dart 3.10.8
flutter analyze: No issues found.
flutter test: All tests passed.
APK release: build/app/outputs/flutter-apk/app-release.apk (51.9MB)
SHA-256: 2D1FFE8E7A230B630D7A20055E9BBEC29645A61ED3A2D5CD8361BF31768BA687
```

## Firmware

Comando:

```powershell
cd firmware
pio run
```

Resultado:

```text
node_lora_t3: SUCCESS, RAM 6.8%, Flash 25.2%.
gateway_tbeam: SUCCESS, RAM 3.8%, Flash 87.7%.
```

Estado: compilacion confirmada. Operacion fisica del JSN-SR04T, radio LoRa, ACK, cola sin internet y TLS en el hardware: **NO VERIFICADO - requiere prueba fisica.**

## Migracion De Telemetria

En una base SQLite temporal se ejecuto:

```text
upgrade head -> downgrade 202607220001 -> upgrade head
```

Resultado: exitoso.

## URLs Publicas

Comandos:

```powershell
Invoke-WebRequest https://agroescudo-api.onrender.com/health
Invoke-WebRequest https://agroescudobo.vercel.app
Invoke-WebRequest https://agroescudo.vercel.app
```

Resultado:

```text
Backend Render /health: 200 {"status":"ok"}
Dashboard Vercel: 200
Landing Vercel: 200
```

## Cierre De Calibracion Versionada - 2026-07-23

Validacion ejecutada sobre `feature/device-types-calibration-charts`:

```text
Backend pytest: 97 passed, 194 warnings.
Alembic SQLite: head aplicado sin errores.
Frontend Vitest: 8 passed.
Frontend ESLint: exitoso.
Frontend Next.js build: exitoso.
Flutter analyze: sin observaciones.
Flutter test: exitoso.
Firmware PlatformIO: nodo y gateway compilados.
Busqueda de secretos: sin patrones de claves privadas o tokens versionados.
```

Despliegue web:

```text
Vercel production: READY
URL publica: https://agroescudobo.vercel.app
HTTP dashboard: 200
API Render health/db: ok, PostgreSQL
Login admin remoto: exitoso
```

Limitacion productiva detectada:

```text
GET /api/devices/{id}/calibrations: 404 en Render
GET /api/storage-units/{id}/product-summary: 404 en Render
```

La web nueva esta publicada, pero Render aun ejecuta el backend anterior. Para habilitar
calibracion versionada en produccion se debe desplegar esta misma revision del backend;
`backend/scripts/start.sh` aplicara `alembic upgrade head` antes de iniciar Uvicorn.
La migracion PostgreSQL real y la validacion fisica de ADC/JSN-SR04T permanecen
**NO VERIFICADAS** hasta ese despliegue y las pruebas con hardware.
