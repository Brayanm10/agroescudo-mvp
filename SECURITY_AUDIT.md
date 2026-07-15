# Security Audit - AgroEscudo Control Center V1.0

## Confirmado

- JWT sigue usando `JWT_SECRET`; en demo/produccion no se permite valor default.
- Los nuevos tokens de sesion incluyen `jti` y se registran en `user_sessions`.
- `logout` y `logout-all` revocan sesiones.
- Passwords se almacenan con bcrypt/passlib.
- Tokens de verificacion, invitacion y reset se guardan hasheados.
- Auditoria evita registrar claves con nombres `password`, `token`, `secret`, `api_key`, `authorization` o `jwt`.
- RBAC existente por storage unit se mantiene para cliente/tecnico.
- `POST /api/readings` no requiere JWT y conserva `device_token`.

## Riesgos

- Email/S3/FCM/WhatsApp/Telegram reales requieren credenciales externas.
- En SQLite los datetimes vuelven sin timezone; se normalizo en auth/deps.
- Hay ciclo FK `companies.approved_by_id -> users` y `users.company_id -> companies`; funcional, pero genera warning en test teardown SQLite.

## Requiere Credencial

- `EMAIL_API_KEY`, `EMAIL_FROM`.
- `S3_ENDPOINT_URL`, `S3_BUCKET`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`.
- `SENTRY_DSN`, FCM, WhatsApp y Telegram si se habilitan.
