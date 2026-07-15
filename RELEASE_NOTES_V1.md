# Release Notes - AgroEscudo Control Center V1.0 P0

## Nuevo

- Control Center con Indice Operativo de Proteccion.
- Auth publica: signup empresa, solicitud demo, invitaciones, verificacion email, forgot/reset password, logout y logout-all.
- Sesiones JWT revocables.
- Centro de Servicio: casos, eventos, reportes de mantenimiento, fotos y firma.
- Academia AgroEscudo: articulos y progreso.
- AgroAsistente P0 deterministico basado en reglas.
- Auditoria de eventos operativos y de seguridad.
- Configuracion base para Resend, S3 compatible, soporte y observabilidad.
- Login web con crear cuenta, invitacion, recuperacion, verificacion y solicitud demo.
- Sala de Control fullscreen en `/control-room`.

## Compatibilidad

- Login existente se mantiene.
- `/api/readings` se mantiene compatible con sensores.
- `/api/iot/v1/ingest/batch` no se modifica.
- PDF semanal actual no se rompe.

## Limitaciones P0

- Email real, S3 real, FCM, WhatsApp y Telegram requieren credenciales.
- IA real no esta habilitada por defecto.
- Mobile P0 extendido queda pendiente de hardening completo.
