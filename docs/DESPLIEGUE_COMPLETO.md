# Despliegue Completo

## Backend Render

- Root directory: `backend`
- Dockerfile: `backend/Dockerfile`
- Start: `sh scripts/start.sh`
- Variables minimas:
  - `ENVIRONMENT=production`
  - `DATABASE_URL=postgresql+psycopg://...`
  - `JWT_SECRET=<secreto-largo>`
  - `CORS_ORIGINS=https://agroescudobo.vercel.app`
  - `NOTIFICATIONS_DRY_RUN=true`
- Health:
  - `/health`
  - `/api/health/db`

## Neon PostgreSQL

- Usar conexion con SSL.
- Ejecutar migraciones desde Render start o consola controlada.
- Hacer backup antes de migraciones destructivas.
- Rotar password si se comparte con terceros.

## Frontend Vercel

- Root directory: `frontend`
- Framework: Next.js
- Build: `npm run build`
- Variable:
  - `NEXT_PUBLIC_API_URL=https://agroescudo-api.onrender.com`
- Smoke:
  - login admin interno;
  - listar silos;
  - generar lectura controlada;
  - ver alerta;
  - descargar PDF.

## Flutter Android

```powershell
cd mobile
flutter clean
flutter pub get
flutter analyze
flutter test
flutter build apk --release --dart-define=API_BASE_URL=https://agroescudo-api.onrender.com
```

No versionar APK ni keystore.

## Firmware

- Instalar PlatformIO.
- Configurar claves y Wi-Fi fuera del repositorio.
- Compilar:

```powershell
cd firmware
platformio run
```

NO VERIFICADO - requiere placas T3/T-Beam conectadas.

