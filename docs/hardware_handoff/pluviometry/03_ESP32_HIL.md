# 03 - Referencia ESP32 HIL

## Ubicación

```text
hardware/pluviometry/esp32_hil/
|-- esp32_hil.ino
+-- secrets.example.h
```

## Estado validado

La prueba HIL fue validada físicamente con esta cadena:

```text
ESP32 -> WiFi -> API -> HTTP 200 -> ACCEPTED -> dashboard
```

El sketch demuestra:

- conexión y reconexión WiFi;
- sincronización NTP en UTC;
- construcción del lote y seis métricas sintéticas;
- Device ID externo;
- `boot_id`, `sequence`, `sample_counter`, `batch_id` y nonce;
- SHA256 del cuerpo y HMAC-SHA256;
- envío al endpoint de ingesta;
- mensajes de diagnóstico sin imprimir secretos;
- prueba manual `wifi_off`, `wifi_on` y `status`.

## Lo que no demuestra

- precisión de sensores;
- firmware de producción;
- LoRa o gateway físico final;
- almacenamiento durable;
- store-and-forward;
- recuperación de muestras generadas sin red;
- Secure Boot o cifrado de secretos en hardware;
- consumo real, autonomía o protección ambiental.

Actualmente, al desactivar WiFi, el HIL no genera ni recupera muestras. Esta es una deuda conocida, no un comportamiento objetivo del firmware productivo.

## Uso correcto por el colaborador

1. Compilar primero el HIL sin cambiar nombres de métricas.
2. Usar únicamente credenciales de integración entregadas por un canal seguro.
3. Confirmar `HTTP 200` y `ACCEPTED`.
4. Sustituir valores sintéticos por una variable física a la vez.
5. Repetir pruebas de rango, reinicio y desconexión después de cada fase.

`secrets.example.h` es una plantilla. Debe copiarse localmente como `secrets.h`; el archivo real nunca se sube a Git ni se adjunta al paquete de handoff.
