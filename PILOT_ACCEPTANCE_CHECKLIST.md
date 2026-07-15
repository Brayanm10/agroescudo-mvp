# Pilot Acceptance Checklist - AgroEscudo

## Prevuelo

- [ ] `alembic upgrade head`.
- [ ] `python -m app.seed`.
- [ ] Backend `/api/health/db` responde `ok`.
- [ ] Frontend usa `NEXT_PUBLIC_API_URL` publica.
- [ ] APK usa `API_BASE_URL` publica.
- [ ] Copiar `dist/AgroEscudo-MVP-release.apk` a Android.

## Flujo Admin

- [ ] Login admin.
- [ ] Ver Control Center.
- [ ] Abrir `/control-room` con sesion admin activa.
- [ ] Crear/editar empresa, silo y sensor si aplica.
- [ ] Asignar tecnico y cliente.
- [ ] Simular o recibir lectura real.
- [ ] Ver alerta.
- [ ] Descargar PDF.

## Flujo Tecnico

- [ ] Login tecnico.
- [ ] Ver silos asignados.
- [ ] Reconocer alerta.
- [ ] Crear caso de servicio.
- [ ] Registrar mantenimiento.
- [ ] Registrar bitacora.

## Flujo Cliente

- [ ] Login cliente.
- [ ] Ver su operacion.
- [ ] Ver alertas y bitacora.
- [ ] Descargar PDF.
- [ ] No acceder a datos ajenos.

## Flujo Publico Web

- [ ] Solicitar demo.
- [ ] Crear cuenta empresa.
- [ ] Verificar correo con token local o email real.
- [ ] Recuperar password.
- [ ] Aceptar invitacion.

## Externos

- [ ] Resend configurado o marcado `REQUIERE CREDENCIAL`.
- [ ] S3 configurado o marcado `REQUIERE CREDENCIAL`.
- [ ] WhatsApp/Telegram en dry-run o configurados.
