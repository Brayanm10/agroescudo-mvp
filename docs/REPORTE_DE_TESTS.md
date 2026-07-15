# Reporte De Tests

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
61 passed, 52 warnings
```

Notas:

- Las 7 pruebas nuevas de IoT batch pasaron.
- Warnings conocidos: `python-jose` usa `datetime.utcnow()` internamente.
- Seed local deja en cero: `sensor_readings`, `alerts`, `operational_logs`, `notification_deliveries`, `notification_events`, `iot_readings`, `iot_ingestion_batches`, `iot_ingestion_events`, `iot_gateway_health`.

## Frontend

Comandos:

```powershell
cd frontend
npm.cmd install
npm.cmd run lint
npm.cmd run build
```

Resultado:

```text
npm install: up to date; 3 vulnerabilidades moderadas reportadas por npm audit.
npm run lint: exitoso.
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
APK release: build/app/outputs/flutter-apk/app-release.apk (51.4MB)
SHA-256: 9F2FAE364C0ACF45E46B951E79A1CCDE45FA141CE1DC5EC25EB06636E4D9569F
```

## Firmware

Comando:

```powershell
cd firmware
platformio --version
```

Resultado:

```text
platformio: no reconocido como comando
```

Estado: **NO VERIFICADO - requiere PlatformIO y hardware fisico.**

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
