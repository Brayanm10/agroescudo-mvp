# Seguridad Y Privacidad

## Implementado

- JWT para usuarios.
- Hash de passwords con passlib/bcrypt.
- RBAC por rol y storage unit asignada.
- CORS por ambiente.
- `JWT_SECRET` requerido no default en `demo` y `production`.
- Gateway HMAC-SHA256 para batch IoT.
- Anti-replay por nonce de gateway.
- Secretos gateway cifrados en base usando clave derivada de `JWT_SECRET`.
- No se guardan device tokens completos en respuestas publicas.

## Pendiente

- Rate limiting persistente para login e ingestion.
- Rotacion operativa de credenciales gateway desde UI admin.
- Auditoria centralizada de logs.
- Pruebas de penetracion.
- Politica formal de retencion de datos.
- Rotar contrasenas iniciales creadas por `app.seed` antes de entregar cualquier ambiente a terceros.

## Datos Capturados

- Lecturas ambientales y de grano.
- Estado tecnico del nodo.
- Alertas y bitacora operacional.
- Datos administrativos de empresa, sitio, silo y usuarios asignados.

## Acceso

- Admin: acceso global.
- Tecnico: unidades asignadas.
- Cliente: unidades asignadas propias.

## Revocacion

- Usuario: desactivar cuenta.
- Sensor: desactivar dispositivo.
- Gateway: desactivar gateway o credencial.
- Notificaciones: desactivar preferencia/canal.
