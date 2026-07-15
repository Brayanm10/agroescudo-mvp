# Test Report - AgroEscudo Control Center V1.0

## Backend

Comando ejecutado:

```powershell
cd backend
py -3.13 -m pytest -p no:cacheprovider
```

Resultado:

- `78 passed`
- Warnings conocidos: ReportLab deprecations, datetime de python-jose y ciclo FK SQLite en teardown.

## Migracion Y Seed

Comando ejecutado:

```powershell
cd backend
py -3.13 -m alembic upgrade head
py -3.13 -m app.seed
```

Resultado:

- Migracion `202607030001` aplicada.
- Seed completo con empresa piloto, 3 storage units, 3 devices, usuarios y thresholds.

## Frontend

Comando ejecutado:

```powershell
cd frontend
npm.cmd run build
```

Resultado:

- Build Next.js completado correctamente.
- Rutas generadas: `/`, `/_not-found`, `/control-room`.

## No Verificado En Esta Iteracion

- Smoke manual en Android real.
- Smoke Render/Vercel con credenciales externas.
- Envio real Resend/S3/FCM/WhatsApp/Telegram.

## Mobile

Comando ejecutado:

```powershell
cd mobile
flutter analyze
```

Resultado:

- `No issues found!`

## Ultima Verificacion Ejecutada

- Backend: `78 passed`.
- Frontend: `npm.cmd run build` OK.
- Mobile: `flutter analyze` OK.
- APK release: `dist/AgroEscudo-MVP-release.apk`.
- APK size: `51.38 MB`.
- APK SHA-256: `9F2FAE364C0ACF45E46B951E79A1CCDE45FA141CE1DC5EC25EB06636E4D9569F`.

## APK Release

Comando ejecutado:

```powershell
cd mobile
flutter build apk --release --dart-define=API_BASE_URL=https://agroescudo-api.onrender.com
```

Resultado:

- `Built build\app\outputs\flutter-apk\app-release.apk (51.4MB)`.
