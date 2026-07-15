# Credenciales externas de AgroEscudo

## Regla de despliegue

Los secretos se cargan en Render, Vercel, Firebase Console o el equipo local. Nunca se pegan en Git, en variables `NEXT_PUBLIC_*`, en Flutter ni en el firmware distribuido.

## Backend Render

Variables base obligatorias:

```env
ENVIRONMENT=production
DATABASE_URL=postgresql+psycopg://...
JWT_SECRET=<secreto-aleatorio-de-64-caracteres-o-mas>
API_URL=https://agroescudo-api.onrender.com
PUBLIC_APP_URL=https://agroescudobo.vercel.app
CORS_ORIGINS=https://agroescudobo.vercel.app
```

### Gemini

Crear una key restringida en Google AI Studio y cargarla solo en Render:

```env
AI_ENABLED=true
AGRO_ASSISTANT_LLM_ENABLED=true
AI_PROVIDER=gemini
GEMINI_API_KEY=<key>
GEMINI_MODEL=gemini-2.5-flash
```

Sin key, el asistente sigue funcionando con reglas verificables.

### Telegram

Crear el bot con `@BotFather`, abrir el bot desde cada cuenta destinataria y enviar `/start`. Guardar el token en Render y el `chat_id` en el perfil de cada usuario.

```env
NOTIFICATIONS_DRY_RUN=false
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=<token>
```

### WhatsApp Cloud API

Desde Meta for Developers se requieren el access token, Phone Number ID y una plantilla aprobada para alertas iniciadas por la empresa.

```env
NOTIFICATIONS_DRY_RUN=false
WHATSAPP_ENABLED=true
WHATSAPP_ACCESS_TOKEN=<token>
WHATSAPP_PHONE_NUMBER_ID=<id>
WHATSAPP_API_VERSION=v20.0
WHATSAPP_TEMPLATE_ALERT_NAME=agroescudo_alerta_operativa
```

### Correo Resend

Validar un dominio remitente en Resend antes de producción.

```env
EMAIL_ENABLED=true
EMAIL_PROVIDER=resend
EMAIL_FROM=AgroEscudo <notificaciones@dominio-validado.com>
EMAIL_REPLY_TO=soporte@dominio-validado.com
EMAIL_API_KEY=<re_...>
```

### Firebase Cloud Messaging

Crear la app Android `com.agroescudo.mobile`, descargar `google-services.json` para la app y un service account para el backend. En Render es preferible cargar el JSON completo o base64 en un secreto.

```env
FCM_ENABLED=true
FIREBASE_PROJECT_ID=<project-id>
FIREBASE_SERVICE_ACCOUNT_JSON=<json-o-base64>
```

### Archivos S3/R2

```env
STORAGE_PROVIDER=s3
S3_ENDPOINT_URL=https://<account>.r2.cloudflarestorage.com
S3_BUCKET=agroescudo
S3_ACCESS_KEY_ID=<id>
S3_SECRET_ACCESS_KEY=<secret>
S3_PUBLIC_BASE_URL=https://archivos.dominio.com
```

## Frontend Vercel

Estas variables son públicas por diseño; no contienen secretos:

```env
NEXT_PUBLIC_API_URL=https://agroescudo-api.onrender.com
NEXT_PUBLIC_SHOW_DEMO_CREDENTIALS=false
NEXT_PUBLIC_PUBLIC_LANDING_URL=https://agroescudo.vercel.app
NEXT_PUBLIC_SUPPORT_EMAIL=soporte@agroescudo.com
```

## Validación

```powershell
py -3.13 scripts/check_env.py --environment production --env-file backend/.env
```

El script solo informa si una clave existe; no imprime su valor.
