# AgroEscudo Premium V2.1 — informe de release y despliegue

Fecha de ejecución: 2026-10-05 (America/La_Paz)

## Hecho por Codex

- Inspección Git completa, `fetch origin` y confirmación del commit base `47106b2`.
- Migración local con una sola cabeza `202610050001`; ciclo `upgrade → downgrade → upgrade` correcto.
- Estado mínimo de commissioning añadido a la unidad/piloto (`PENDING_INSTALLATION` o `ACTIVE`).
- Herramienta transaccional `backend/scripts/purge_preproduction_data.py`, con selección explícita por nombre exacto, dry-run, confirmación fuerte, backup obligatorio, auditoría y protección del administrador.
- Dry-run local sobre `Acopio Valle Bajo S.R.L.`, `AgroEscudo Demo` y `uno`; ejecución validada sobre una copia temporal. La base local real no fue purgada.
- Bootstrap idempotente `backend/scripts/bootstrap_pilot.py`, sin datos inventados y con secretos aleatorios mostrados solo al crearse.
- Runbook y checklist imprimible ADEPLEC.
- Backend: 211 pruebas aprobadas.
- Frontend: 86 pruebas aprobadas; ESLint y build aprobados.
- Mobile: analyze sin incidencias; 4 pruebas aprobadas.
- Firmware: SiloSensor, gateway y Sentinel compilados correctamente.
- Producción actual (antes de este release): frontend, `/health`, `/api/health/db` y Swagger respondieron HTTP 200; DB reportó PostgreSQL.

## No ejecutado / acción manual necesaria

Resultado actual: **NO-GO**. No existe en este equipo `DATABASE_URL` productiva ni acceso confirmado a Neon/Render/Vercel; por tanto no fue posible crear/verificar backup productivo, migrar producción, purgarla, crear ADEPLEC ni validar logins/IoT reales. El frontend local usa `http://localhost:8010`; la variable de Vercel debe comprobarse en el panel.

Datos reales pendientes, que deben proporcionarse juntos: razón social exacta; responsable, email y teléfono; sitio y dirección; capacidad; técnico y email; `device_id`, `gateway_id` y `node_id` físicos.

Orden obligatorio:

1. Crear snapshot verificable en Neon y conservar su referencia.
2. Configurar `DATABASE_URL` productiva solo en la sesión segura del operador.
3. Ejecutar `python scripts/backup_postgres_portable.py --label pre-adeplec` y verificar ZIP/SHA256 fuera de Git.
4. Ejecutar `python -m alembic upgrade head` y confirmar `python -m alembic current` = `202610050001`.
5. Ejecutar primero el purge con `--dry-run`; revisar nombres/conteos. Solo después usar `--execute --backup-confirmed <referencia> --confirm "PURGE PREPRODUCTION COMPANIES"`.
6. Ejecutar el bootstrap con todos los datos reales y `--execute`; guardar secretos en el gestor seguro.
7. Desplegar backend desde el SHA final; luego frontend desde el mismo `main`. En Vercel confirmar `NEXT_PUBLIC_API_URL=https://agroescudo-api.onrender.com` y `NEXT_PUBLIC_SHOW_DEMO_CREDENTIALS=false`.
8. Ejecutar logins ADMIN/CLIENTE/TÉCNICO, RBAC, telemetría, duplicado, dispositivo inactivo, reconexión y alerta siguiendo el runbook.

## GO / NO-GO

Pasan localmente: build/tests, migración reversible, herramientas, protección del administrador en copia, runbook/checklist, health público actual.

Pendientes críticos: backup productivo; migración/deploy del nuevo SHA; purga productiva; datos y bootstrap ADEPLEC; credenciales; RBAC real; primera telemetría; dashboard; commissioning; resiliencia; activación. Hasta completarlos: **NO-GO PARA ADEPLEC**.
