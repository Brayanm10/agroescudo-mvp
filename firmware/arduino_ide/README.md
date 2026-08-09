# AgroEscudo para Arduino IDE

Firmware de piloto para la cadena:

```text
SiloSensor / CampoSensor -> LoRa cifrado -> Gateway -> HTTPS firmado -> AgroEscudo API
```

## Versiones para piloto

- `agroescudo_silo_sensor_v4/agroescudo_silo_sensor_v4.ino`
- `agroescudo_campo_sensor_v4/agroescudo_campo_sensor_v4.ino`
- `agroescudo_gateway_multinodo_v4/agroescudo_gateway_multinodo_v4.ino`
- `libraries/AgroEscudoProtocol/`
- `agroescudo_sentinel_v02/agroescudo_sentinel_v02.ino` para el relay GSM externo.

Los sketches antiguos `agroescudo_node_lora` y
`agroescudo_gateway_wifi_lora` se conservan solo como referencia legacy. No
son la version recomendada para un piloto.

## Preparacion rapida

1. Copia `libraries/AgroEscudoProtocol` dentro de la carpeta `libraries` de tu
   sketchbook de Arduino.
2. Instala las librerias indicadas en el manual tecnico.
3. Copia `secrets.example.h` como `secrets.h` dentro de cada sketch.
4. Configura un `node_id` unico y la misma clave AES en nodo y gateway.
5. Configura `gateway_id`, secreto HMAC y CA TLS en el gateway.
6. Selecciona la placa correcta y 915 MHz.
7. Para el gateway elige la particion `Huge APP (3MB No OTA/1MB SPIFFS)`.
8. Compila, carga y abre el monitor serie a 115200 baud.

Lee [MANUAL_GATEWAY_SILO_CAMPO_ARDUINO_IDE.md](../../docs/MANUAL_GATEWAY_SILO_CAMPO_ARDUINO_IDE.md)
antes de conectar sensores o alimentar las placas.

## Seguridad

`secrets.h` esta ignorado por Git. No publiques WiFi, HMAC, claves AES ni
certificados privados. El ejemplo contiene valores de muestra y no debe usarse
sin reemplazarlos.
