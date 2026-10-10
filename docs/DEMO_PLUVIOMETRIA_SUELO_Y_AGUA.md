# Demo pluviómetro — Suelo y Agua (contrato V4 existente)

**Estado:** guía de integración y simulador local, sin datos de producción modificados.

La pantalla de referencia es `/pluviometria?predio=8`. El ID 8 no prueba permisos ni identidad del pluviómetro. El administrador debe confirmar en Neon qué usuario, empresa, predio, parcela y dispositivo están vinculados.

**Hallazgo importante:** ya existe `POST /api/iot/v1/ingest/batch`, con `X-Agro-Gateway-ID`, `X-Agro-Timestamp`, `X-Agro-Nonce`, `X-Agro-Signature` (HMAC-SHA256 del body exacto). No usar el prototipo anterior `POST /api/pluviometry/ingest` ni `X-Device-Key`: no son rutas de esta versión. Reutilizar `RAIN_GAUGE_BASE`, `RAIN_DELTA_MM`, `AMBIENT_TEMPERATURE_C`, `AMBIENT_RELATIVE_HUMIDITY_PCT`, `BATTERY_PERCENT`. Ver `docs/hardware_handoff/pluviometry/02_TELEMETRY_CONTRACT.md` y `hardware/pluviometry/esp32_hil/esp32_hil.ino`.

## Ejecución local sin ESP32

```sh
python scripts/pluviometry_demo_client.py --count 5 --interval 1
```

Solo imprime paquetes JSON; **no envía ni conecta la cuenta**. Para transmitir luego de que un admin aprovisione un gateway DEMO y confirme un pluviómetro DEMO vinculado al predio correcto:

```sh
export AGRO_DEMO_GATEWAY_ID='GW-DEMO-SYA-01'
export AGRO_DEMO_GATEWAY_SECRET='SECRETO_GESTIONADO_FUERA_DE_GIT'
export AGRO_DEMO_DEVICE_ID='PLUVIO-DEMO-SYA-01'
python scripts/pluviometry_demo_client.py --count 15 --interval 60 --send --base-url https://agroescudo-api.onrender.com
```

La clave del cliente **nunca** se usa como clave IoT. Si el dispositivo del predio 8 es real, no reutilizarlo para simulación: crear una unidad DEMO separada. La API actual no etiqueta por sí misma estos eventos como simulados, así que restringir emisiones a un dispositivo/empresa de demo; no atribuirlas a lluvia real.

## ESP32

El firmware HIL actual genera datos sintéticos, pero está marcado explícitamente como **solo pruebas de banco** y envía HTTP sin TLS. No poner contraseñas productivas en `secrets.h` ni enviarlo directamente a Render por HTTP. Para un ESP32 que transmita por internet, ajustar ese firmware existente a `WiFiClientSecure` con CA verificada, identificador de gateway específico para la demo y conservación de la secuencia en reintentos. No utilizar `setInsecure()`.

## Vista web

El mapa real ya solicita `GET /api/pluviometry/sites` y `GET /api/pluviometry/sites/{site_id}/map` con JWT. El historial real consulta métricas canónicas por dispositivo. Una vez que el backend acepta una lectura V4 para un dispositivo correctamente aprovisionado, debe aparecer mediante el sistema de consultas existente. En respuestas HTTP 200, inspeccionar el estado **por evento**: solo `accepted` o `duplicate` significan éxito lógico.

## Criterios de aceptación (pendientes)

1. Verificar identidad/permisos del cliente y su asociación real con predio/parcela/dispositivo.
2. Crear gateway y dispositivo de integración aislados, secretos rotables y autorización para ingestión.
3. Test de ingestión con respuesta `accepted` y prueba de idempotencia `duplicate`.
4. Lectura en BD y snapshot/serie accesible únicamente al usuario autorizado; verificar `America/La_Paz`.
5. Marcar DEMO visiblemente en mapas, historial, CSV y PDF; mantener la separación respecto de lecturas reales.
6. Validar TLS, tests y build antes de desplegar. No activar cambios productivos por este documento.

**No se ha creado la cuenta, el gateway ni el dispositivo en la base de datos.** No se ha desplegado ni certificado un piloto en funcionamiento.
