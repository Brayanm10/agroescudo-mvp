# AgroEscudo Premium V2.1: cierre CRUD reactivo e IoT

Fecha de verificación: 7 de septiembre de 2026

Rama de trabajo: `codex/premium-v2-1-reactive-crud`

Commit inicial: `22a6f9e272f597a37dabdeb3c13a277d7f3cbd53`

## A. Causa exacta del problema

Las mutaciones sí llegaban a FastAPI y se guardaban, pero varios controladores del frontend invocaban `onChanged()` sin esperar su finalización. Además, la carga global no tenía control de generaciones: una solicitud antigua podía terminar después de la revalidación posterior al `PATCH`, `POST` o `DELETE` y sobrescribir el estado reciente con una respuesta anterior.

La solución implementada no usa `window.location.reload()`:

1. Toda mutación espera `await onChanged()` antes de mostrar el resultado final.
2. `LatestRequest` asigna una generación a cada recarga y descarta respuestas obsoletas.
3. El cierre de sesión invalida solicitudes pendientes.
4. Los controles quedan deshabilitados mientras la mutación está en curso.
5. Los formularios de edición solo se cierran cuando el backend confirma éxito; ante error conservan el contenido.
6. Umbrales revalidan el estado global para actualizar semáforos, tarjetas y resúmenes.

## B. Seguridad de eliminación

La migración `202609060001` agrega `deleted_at` a empresas, usuarios, unidades, dispositivos, gateways, contactos Sentinel y equipos Sentinel. La eliminación administrativa es un retiro lógico auditable:

- conserva lecturas, alertas, bitácora y evidencia histórica;
- excluye entidades retiradas de inventarios y consultas operativas;
- desactiva credenciales y canales asociados;
- evita referencias huérfanas;
- bloquea eliminar la cuenta administrativa autenticada;
- bloquea eliminar el último administrador activo;
- bloquea eliminar unidades con sensores todavía vinculados;
- bloquea retirar contactos o Sentinel con trabajos pendientes o reclamados;
- registra eventos de auditoría donde corresponde.

`Desactivar` conserva la entidad y permite reactivarla. `Eliminar` la retira de la operación mediante `deleted_at` y no equivale a borrar telemetría.

El botón separado `Borrar datos` del modo piloto conserva infraestructura y sigue siendo una acción destructiva explícita de datos demo. No fue conectado al flujo normal de eliminación.

## C. Endpoints creados

- `DELETE /api/admin/companies/{company_id}`
- `DELETE /api/admin/storage-units/{storage_unit_id}`
- `DELETE /api/admin/devices/{device_id}`
- `DELETE /api/admin/users/{user_id}`
- `POST /api/admin/gateways`
- `DELETE /api/admin/gateways/{gateway_id}`
- `PATCH /api/admin/sentinel/devices/{device_id}`
- `DELETE /api/admin/sentinel/devices/{device_id}`
- `DELETE /api/alert-contacts/{contact_id}`
- `PATCH /api/pilots/{storage_unit_id}`
- `DELETE /api/pilots/{storage_unit_id}`

## D. Endpoints modificados sin ruptura

- Los listados admin omiten registros con `deleted_at`.
- Login y `/api/me` rechazan usuarios retirados.
- Acceso por empresa, sitio, unidad y dispositivo excluye entidades retiradas.
- Ingestión individual y batch rechazan sensores, unidades o empresas retiradas.
- Reportes JSON/PDF, monitoreo, insights, Control Center y pilotos no mezclan retirados con activos.
- `PATCH /api/admin/gateways/{id}` permite nombre, estado operativo y activación según RBAC.
- Las respuestas de entidades administrables incluyen `deleted_at` de forma aditiva.
- `PilotOut` incluye `is_active`.

No se eliminó ni renombró ningún endpoint existente. `POST /api/readings`, la ingestión HMAC batch y el PDF mantienen compatibilidad.

## E. Matriz CRUD realmente disponible

| Entidad | Crear | Editar | Activar | Desactivar | Eliminar | Reactivo |
| --- | --- | --- | --- | --- | --- | --- |
| Empresas | Sí | Sí | Sí | Sí | Sí | Sí |
| Usuarios | Sí | Sí | Sí | Sí | Sí, con protecciones | Sí |
| Pilotos/unidades | Sí | Sí | Sí | Sí | Sí, con dependencias | Sí |
| SiloSensor | Sí | Sí | Sí | Sí | Sí, conserva histórico | Sí |
| CampoSensor | Sí | Sí | Sí | Sí | Sí, conserva histórico | Sí |
| Gateway | Sí | Sí | Sí | Sí | Sí | Sí |
| Sentinel | Sí | Sí | Sí | Sí | Sí | Sí |
| Contactos Sentinel | Sí | Sí | Sí | Sí | Sí | Sí |
| Umbrales | Sí | Sí | No aplica | No aplica | No destructivo | Sí |
| Asignaciones técnico/cliente | Sí | Sí | No aplica | No aplica | Sí, desasignar | Sí |

Los responsables del piloto se editan en la misma tarjeta. La asociación física de sensores se administra en Sensores para conservar una sola fuente de verdad. No se inventaron fechas de piloto porque el modelo actual no tiene fechas contractuales de inicio y fin.

## F. Ejemplos IoT

### SiloSensor

Ruta: `iot_examples/silosensor/agroescudo_silosensor_example.ino`

Incluye DS18B20, SHT31, JSN-SR04T, batería, paquete LoRa binario TLV versionado, cifrado, contador persistente y ausencia de métricas representada sin ceros inventados.

### Gateway

Ruta: `iot_examples/gateway/agroescudo_gateway_example.ino`

Recibe LoRa, valida/descifra, deduplica, guarda una cola durable en LittleFS y publica lotes por HTTPS con HMAC. Solo elimina elementos confirmados como `accepted` o `duplicate`.

### Sentinel

Ruta: `iot_examples/sentinel/agroescudo_sentinel_example.ino`

Consulta trabajos autorizados en `/api/sentinel/poll` y reporta resultados en `/api/sentinel/jobs/{id}/result`. El token queda en `secrets.h`, no en el repositorio.

Cada carpeta incluye `README.txt` y `secrets.example.h` con hardware, conexiones, configuración, compilación, monitor serie y advertencias de seguridad.

Compilación verificada:

```powershell
& "$env:USERPROFILE\.platformio\penv\Scripts\platformio.exe" run `
  -e arduino_silo_sensor_v4 `
  -e arduino_gateway_multinodo_v4 `
  -e arduino_sentinel_v02
```

Resultado: tres entornos compilados correctamente. La prueba eléctrica, alcance LoRa, SIM y sensores físicos sigue requiriendo hardware real.

## G. Migración

Aplicación local/producción:

```powershell
cd backend
py -3.13 -m alembic upgrade head
```

Rollback técnico de esta revisión:

```powershell
py -3.13 -m alembic downgrade 202608090001
```

Antes de un rollback productivo debe existir backup verificado. El ciclo `upgrade -> downgrade -> upgrade` se probó sobre una base SQLite temporal y finalizó correctamente.

## H. Pruebas y builds

- Backend completo: `156 passed` tras la verificación final.
- CRUD/borrado enfocado: `6 passed`.
- Frontend Vitest: `20 passed`.
- Frontend ESLint: OK.
- Next.js build productivo: OK.
- Flutter analyze: OK.
- Flutter tests: `4 passed`.
- Firmware PlatformIO: SiloSensor, Gateway y Sentinel: OK.
- APK: no generado porque `mobile/` no tuvo cambios.
- Versión Android: se conserva `1.3.0+5`.

Los avisos deprecados de ReportLab/JWT y el warning de orden de borrado de tablas de test no produjeron fallos. Deben tratarse como mantenimiento técnico posterior, no como bloqueo de esta entrega.

## I. Archivos de implementación

Backend:

- `backend/alembic/versions/202609060001_soft_delete_administrable_entities.py`
- `backend/app/models.py`
- `backend/app/schemas.py`
- `backend/app/services/soft_delete.py`
- rutas y servicios de autenticación, administración, pilotos, Sentinel, ingestión, reportes y consultas operativas que aplican el filtro de retirados.
- `backend/tests/test_reactive_crud_soft_delete.py`

Frontend:

- `frontend/app/page.tsx`
- `frontend/lib/api.ts`
- `frontend/lib/types.ts`
- `frontend/lib/latest-request.ts`
- `frontend/lib/latest-request.test.ts`
- vistas de perfil, preferencias, canales, gateways y Sentinel que esperan la revalidación.

IoT:

- `iot_examples/gateway/`
- `iot_examples/silosensor/`
- `iot_examples/sentinel/`

## J. Estado Git y release

Esta revisión se desarrolló en `codex/premium-v2-1-reactive-crud`. No incluye `.env`, APK, bases temporales, backups, keystores ni secretos. El commit final se registra después de ejecutar el chequeo de diff y la búsqueda de credenciales.

No se hizo push ni despliegue automático como parte de esta tarea. Las migraciones deben ejecutarse antes de desplegar el backend que usa `deleted_at`.
