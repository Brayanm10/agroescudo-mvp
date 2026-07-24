# Checklist Release Piloto

## Software

- [x] Backend tests aprobados.
- [x] Migraciones limpias.
- [x] Frontend build aprobado.
- [x] Flutter analyze aprobado.
- [x] Flutter tests aprobados.
- [x] APK release generado.
- [x] Roles probados por suite backend.
- [x] Aislamiento probado.
- [x] Credenciales demo ocultas en las interfaces de produccion.
- [x] Sin credenciales reales ni claves privadas versionadas.

## IoT

- [x] LoRa binario compilado.
- [x] AES-CCM compilado.
- [x] Persistencia nodo implementada.
- [x] Persistencia gateway implementada.
- [x] ACK despues de guardar implementado.
- [x] Deduplicacion persistente implementada.
- [x] HTTPS TLS implementado.
- [x] HMAC gateway implementado.
- [x] Idempotencia backend probada.
- [x] Lectura disponible en dashboard por API y build.

Los puntos marcados como implementados en firmware requieren validacion fisica antes de considerarse aprobados en campo.

## Operacion

- [x] Backup documentado.
- [x] Rollback documentado.
- [x] Checklist digital de instalacion implementado.
- [x] Checklist de recuperacion documentado.
- [x] Riesgos pendientes documentados.

## P1 Primeros Pilotos

- [x] Mantenimiento con estados, responsable, cierre y eventos.
- [x] QR aleatorio, rotatable y revocable.
- [x] Evidencia con RBAC, MIME permitido, tamano y metadatos.
- [x] Salud del sistema y gateways dentro del alcance autorizado.
- [x] Delivery de notificaciones con `SENT` separado de `DELIVERED`.
- [x] Reintentos auditados con backoff.
- [x] PDF ejecutivo y tecnico.
- [x] Comparacion de periodos y exportaciones CSV.
- [x] Registro manual de firmware, sin OTA.
- [ ] Camara, QR, LoRa y sensores validados en hardware real.
- [ ] Proveedores externos probados con credenciales de piloto.
- [ ] Despliegue revisado y aprobado manualmente.

