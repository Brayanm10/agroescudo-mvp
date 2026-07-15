# AgroEscudo Control Center V1.0 - Implementation Plan

## Estado

P0 en progreso sobre la arquitectura existente: FastAPI + SQLAlchemy/Alembic, Next.js, Flutter Android y firmware/documentacion IoT. La prioridad es piloto comercial B2B sin blockchain, marketplace, scoring ni Firebase como base de datos.

## Entregado en esta iteracion

- Auditoria inicial en `LAUNCH_AUDIT.md`.
- Migracion `202607030001_control_center_p0.py`.
- Campos P0 en usuarios, empresas y sitios.
- Tablas P0 para signup, invitaciones, verificacion, password reset, sesiones, auditoria, leads, servicio, archivos, mantenimiento, educacion, asistente y rate limit events.
- Auth publica segura con preview local cuando `EMAIL_ENABLED=false`.
- Sesiones JWT con `jti`, logout y logout-all.
- Control Center backend con formula versionada.
- Centro de Servicio backend minimo.
- Academia backend minima.
- AgroAsistente P0 basado en reglas.
- Dashboard web consume `/api/control-center/summary`.
- Panel funcional de acceso publico en login: crear cuenta, invitacion, forgot/reset, verificacion y demo request.
- Sala de Control fullscreen disponible en `/control-room`.
- Tests backend P0 agregados.

## P0 restante recomendado

- Pulir UX web de signup, invitacion y recuperacion en pantallas dedicadas si se requiere mas refinamiento comercial.
- Agregar rotacion por sitio y QR a Sala de Control si el piloto lo necesita.
- Completar mobile P0 para signup, invitacion, casos, fotos/firma y cola offline.
- Conectar Resend/S3 reales cuando existan credenciales.
- Smoke manual Render/Vercel/Android real.

## P1/P2

- FCM real, WhatsApp/Telegram reales, Sentry y storage S3 validado.
- LLM opcional bajo feature flag.
- Analitica avanzada y automatizaciones operativas.
