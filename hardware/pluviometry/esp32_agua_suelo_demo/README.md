# Agua y Suelo — ESP32 DEMO

Cuenta confirmada por el propietario: **sueloyagua@gmail.com**, empresa visible **SUELO Y AGUA**. El correo `aguaysuelo@gmail.com` del pedido inicial fue corregido por el propietario.

Todos los valores son meteorología **SIMULADA**, sin sensores conectados. El equipo comercial existente `Pluvi1` (ID web 20) debe conservarse; no está confirmado como exclusivamente DEMO.

## Cargar en Arduino IDE

1. Instalar Arduino IDE y el paquete oficial **esp32 by Espressif Systems**. Se usa core 3.x; la compilación de este paquete se realiza con 3.3.7.
2. En el gestor de librerías instalar **ArduinoJson 7** (toolchain disponible: 7.4.3). WiFi, HTTPClient, WiFiClientSecure, Preferences y mbedTLS vienen con el core.
3. Crear una carpeta llamada exactamente `AgroEscudo_AguaSuelo_Demo` fuera del repositorio o dentro de `tmp/`. Copiar allí el `.ino`, `demo_weather.h` y `trusted_root.h`. Arduino exige que el nombre del sketch coincida con la carpeta.
4. Copiar `secrets.example.h` como `secrets.h` dentro de esa carpeta. Introducir WiFi local. Copiar Gateway ID, secreto HMAC dedicado y Device ID físico desde el aprovisionamiento descrito en la guía. No usar el correo ni contraseña del cliente.
5. Seleccionar **Herramientas → Placa → esp32 → ESP32 Dev Module** (`esp32:esp32:esp32`). Seleccionar el puerto USB del ESP32. Hay varios COM en esta estación; identificarlos desconectando/reconectando la placa, sin adivinar.
6. Pulsar **Verificar**, luego **Subir**. Si el equipo lo requiere, mantener BOOT durante el inicio de carga.
7. Abrir Monitor Serial a **115200**, con nueva línea. Ejecutar `status`.
8. Confirmar WiFi conectado, NTP sincronizado y API HTTPS. Al enviar deben aparecer `HTTP 200` y `ACCEPTED` o `DUPLICATE`.
9. Abrir la URL del equipo **DEMO** devuelta por el aprovisionamiento. Verificar el aviso **MODO DEMOSTRACIÓN — DATOS SIMULADOS**, hora local boliviana y actualización de valores/histórico.

El firmware bloquea transmisión mientras existan placeholders. `trusted_root.h` contiene certificados públicos, no secretos. La raíz TLS fue obtenida del [repositorio oficial de Google Trust Services](https://pki.goog/repository/) y debe revisarse si cambia el emisor de la API. No desactivar la verificación.

## Escenarios por Serial

| Comando | Comportamiento |
|---|---|
| `status` | WiFi, reloj, último HTTP, muestra pendiente y bloqueo; sin secretos. |
| `normal` | Ciclo térmico suave, humedad moderada, viento suave, lluvia cero. |
| `dry` | Temperatura mayor, humedad menor y viento moderado; lluvia cero. |
| `rain_light` | 3 mm/h expresados como deltas por minuto; humedad aumenta progresivamente. |
| `rain_heavy` | 18 mm/h, descenso térmico gradual y viento mayor. |
| `storm` | 40 mm/h y viento fuerte; datos sintéticos, sin notificaciones de riesgo a clientes. |
| `battery_low` | Batería desciende 0.8 puntos por muestra hasta 8%; valores ambientales normales. |
| `auto` | Ciclo seco → normal → ligera → intensa → ligera → normal, 20 muestras por tramo. |
| `retry` | Reintenta la muestra conservada después de corregir configuración/rechazo. |

Los cambios afectan la próxima **muestra nueva**, nunca alteran una pendiente. Temperatura, humedad, viento, batería y dirección tienen límites de cambio por muestra. La dirección es meteorológica FROM y usa el camino angular más corto.

## Entrega, lluvia y cortes

- Cadencia objetivo: **60 segundos**, intervalo registrado: **1 minuto**.
- Lluvia = intensidad × 60/3600; cada muestra contiene solamente su delta. En normal/dry/battery_low el delta es cero.
- Se guarda una muestra pendiente en NVS **antes** del envío. Se conserva su timestamp, métricas, boot, sequence y sample_counter durante los reintentos y reinicios.
- Cada request recibe un batch_id y nonce nuevos, hora actual y HMAC sobre el cuerpo exacto transmitido.
- Solo se libera la muestra y avanza la secuencia con respuesta del mismo lote y muestra clasificada `ACCEPTED` o `DUPLICATE`.
- Timeouts, 5xx, 429 y respuestas temporales usan reintento de hasta 60 segundos. 401/403/404/422, rechazo o cuarentena bloquean y conservan la muestra para revisión.
- Reconexión WiFi automática cada 10 segundos. No se imprimen claves, contraseña WiFi ni firmas.
- **Buffer de una muestra:** la adquisición se pausa durante una falla y los intervalos no medidos quedan como huecos. No se rellena lluvia ficticia ni se promete una cola ilimitada. La identidad guardada sobrevive a reinicio; un nuevo arranque usa otro boot_id para muestras nuevas.
- Estados existentes: online hasta 2 minutos de edad, delayed después de 2 y offline después de 6; el histórico sintético no simula presencia del ESP32.

## Verificación física pendiente

Con credenciales ya aprovisionadas: enviar normal, lluvia ligera, reiniciar mientras hay una muestra pendiente, cortar/restablecer WiFi, probar falla de API y comprobar duplicados sin doble lluvia. No cortar otros servicios productivos. Las pruebas automatizadas/compilación no sustituyen esta prueba con la placa.

Ver la [guía operativa del piloto](../../../docs/AGUA_SUELO_DEMO_GUIDE.md).
