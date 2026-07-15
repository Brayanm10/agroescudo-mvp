# Rollback

## Backend

1. Identificar ultimo deploy estable en Render.
2. Restaurar variables si fueron modificadas.
3. Si hubo migracion, restaurar backup Neon antes de volver codigo atras.
4. Ejecutar smoke:
   - `/health`
   - `/api/health/db`
   - login interno
   - listar storage units

## Frontend

1. Usar rollback de deployment en Vercel.
2. Confirmar `NEXT_PUBLIC_API_URL`.
3. Probar login y dashboard.

## Mobile

1. Reinstalar APK anterior.
2. Confirmar `API_BASE_URL`.
3. Limpiar cache si hubo cambio de contrato.

## Firmware

1. Conservar binario anterior.
2. Flashear por USB.
3. Verificar radio y ACK.

