# Operacion Y Recuperacion

## Operacion Diaria

- Revisar `/api/health/db`.
- Revisar alertas activas.
- Confirmar ultimas lecturas por storage unit.
- Revisar bitacora y mantenimiento.
- Descargar reporte semanal.

## Recuperacion

- Backend caido: revisar logs Render, health y variables.
- Base no conecta: validar `DATABASE_URL`, SSL y estado Neon.
- Frontend sin datos: validar `NEXT_PUBLIC_API_URL` y CORS.
- App sin API: abrir `/health`, esperar cold start de Render y reintentar.
- Gateway sin internet: conservar cola local; no borrar lecturas.

## Incidentes IoT

- Paquete duplicado: backend responde `duplicate`; gateway puede borrar.
- Firma invalida: revisar secreto gateway y reloj.
- Replay: nonce repetido; generar batch nuevo.
- Device desconocido: registrar `iot_device` y mapearlo a `devices`.

