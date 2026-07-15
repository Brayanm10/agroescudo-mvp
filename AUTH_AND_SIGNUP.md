# Auth And Signup - AgroEscudo Control Center V1.0

## Endpoints Nuevos

- `POST /api/auth/signup/company`
- `POST /api/auth/demo-request`
- `POST /api/auth/invites/preview`
- `POST /api/auth/invites/accept`
- `POST /api/auth/email/verify`
- `POST /api/auth/password/forgot`
- `POST /api/auth/password/reset`
- `POST /api/auth/logout`
- `POST /api/auth/logout-all`

## Estados

Usuario:

- `EMAIL_PENDING`
- `PENDING_APPROVAL`
- `ACTIVE`
- `INACTIVE`
- `SUSPENDED`
- `INVITED`
- `INVITE_EXPIRED`

Empresa:

- `PENDING_REVIEW`
- `APPROVED`
- `REJECTED`
- `NEEDS_INFO`

## Modo Local

Con `EMAIL_ENABLED=false`, signup y forgot password devuelven tokens preview para pruebas. En produccion, los flujos que requieren email deben usar Resend con credenciales reales.
