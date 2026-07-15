# Environment Variables - AgroEscudo

## Backend

| Variable | Uso | Default local |
|---|---|---|
| `DATABASE_URL` | Conexion SQL | `sqlite:///./agroescudo_dev.db` |
| `JWT_SECRET` | Firma JWT | `change-me-in-production` solo local |
| `CORS_ORIGINS` | Origenes web permitidos | localhost |
| `EMAIL_ENABLED` | Activa email real | `false` |
| `EMAIL_PROVIDER` | Proveedor email | `resend` |
| `EMAIL_FROM` | Remitente | `REQUIERE CREDENCIAL` |
| `EMAIL_API_KEY` | API key Resend | `REQUIERE CREDENCIAL` |
| `PUBLIC_APP_URL` | URL dashboard | `http://localhost:3000` |
| `STORAGE_PROVIDER` | `local` o `s3` | `local` |
| `S3_*` | Storage compatible S3 | `REQUIERE CREDENCIAL` |
| `DEVICE_OFFLINE_AFTER_MINUTES` | Corte offline Control Center | `120` |
| `NOTIFICATIONS_DRY_RUN` | WhatsApp/Telegram simulado | `true` |
| `SENTRY_ENABLED` | Observabilidad | `false` |

## Frontend

| Variable | Uso |
|---|---|
| `NEXT_PUBLIC_API_URL` | API publica Render o backend local |
| `NEXT_PUBLIC_SHOW_DEMO_CREDENTIALS` | Mostrar credenciales demo solo local |
| `NEXT_PUBLIC_SUPPORT_EMAIL` | Contacto soporte |

## Mobile

| Variable | Uso |
|---|---|
| `API_BASE_URL` | URL publica de FastAPI para build APK |
