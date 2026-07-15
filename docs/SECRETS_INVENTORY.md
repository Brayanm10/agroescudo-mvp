# Inventario de secretos

| Servicio | Secreto | Ubicación correcta | Estado inicial |
|---|---|---|---|
| Base de datos | `DATABASE_URL` | Render | Requerido |
| JWT | `JWT_SECRET` | Render | Requerido |
| Gemini | `GEMINI_API_KEY` | Render | Opcional |
| Telegram | `TELEGRAM_BOT_TOKEN` | Render | Opcional |
| WhatsApp | `WHATSAPP_ACCESS_TOKEN` | Render | Opcional |
| Resend | `EMAIL_API_KEY` | Render | Opcional |
| Firebase | `FIREBASE_SERVICE_ACCOUNT_JSON` | Render | Opcional |
| Firebase Android | `google-services.json` | Equipo/build seguro | Opcional, no versionar |
| S3/R2 | `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY` | Render | Opcional |
| Sentry | `SENTRY_DSN` | Render | Opcional |
| Gateway IoT | secreto HMAC | Aprovisionamiento del gateway | Requerido por gateway |

Si una credencial real se comparte en un chat, captura o commit, debe rotarse antes del piloto.
