# Estado de servicios externos

| Servicio | Código | Credencial | Prueba real |
|---|---|---|---|
| Render + PostgreSQL | Integrado | Requiere variables de producción | Verificar health tras deploy |
| Vercel | Integrado | Requiere sesión de propietario | Pendiente de nuevo deploy |
| Gemini | Integrado con fallback por reglas | `GEMINI_API_KEY` | Pendiente |
| Telegram | Integrado | Bot token + chat ID | Pendiente |
| WhatsApp Cloud API | Integrado | Meta token + Phone Number ID | Pendiente |
| Resend | Integrado con envío HTTP real | API key + dominio | Pendiente |
| Firebase FCM backend | Integrado | Project ID + service account | Pendiente |
| Firebase FCM Android | Requiere configuración FlutterFire | `google-services.json` | Pendiente |
| S3 compatible | Integrado con subida real | Endpoint, bucket y keys | Pendiente |
| Sentry | Configuración reservada | DSN | Pendiente |

`Pendiente` significa que el código está preparado, pero no puede declararse operativo sin credenciales y una prueba contra la cuenta externa.
