# API Endpoints - AgroEscudo Control Center V1.0

## Health

- `GET /health`
- `GET /api/health/db`

## Auth

- `POST /api/auth/login`
- `GET /api/me`
- `PATCH /api/me`
- `POST /api/auth/change-password`
- `POST /api/auth/signup/company`
- `POST /api/auth/demo-request`
- `POST /api/auth/invites/preview`
- `POST /api/auth/invites/accept`
- `POST /api/auth/email/verify`
- `POST /api/auth/password/forgot`
- `POST /api/auth/password/reset`
- `POST /api/auth/logout`
- `POST /api/auth/logout-all`

## Operacion

- Companies, sites, storage units, devices, readings, alerts, operational logs, pilots, reports.
- `GET /api/control-center/summary`
- `GET/POST /api/service-cases`
- `GET/PATCH /api/service-cases/{id}`
- `POST /api/service-cases/{id}/events`
- `POST /api/service-cases/{id}/maintenance-reports`
- `POST /api/service-cases/{id}/photos`
- `POST /api/service-cases/{id}/signature`
- `POST /api/agro-assistant/messages`
- `GET /api/education/articles`
- `GET /api/education/articles/{slug}`
- `POST /api/education/articles/{id}/complete`

## IoT

- `POST /api/readings`
- `POST /api/iot/v1/ingest/batch`
