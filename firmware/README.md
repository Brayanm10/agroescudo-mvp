# Firmware AgroEscudo

PlatformIO compila protocolo V3:

- `AGRO_SENSOR_PROFILE=1`: SiloSensor con JSN-SR04T.
- `AGRO_SENSOR_PROFILE=2`: CampoSensor con `soil_moisture_raw`.
- `AGRO_SOIL_MOISTURE_PIN=34`: ADC configurable.

El gateway conserva V1/V2/V3 y solo envia metricas presentes. La calibracion se realiza en FastAPI.

Este directorio contiene puntos de partida para el enlace:

```text
Nodo ESP32 LoRa -> Gateway LoRa/WiFi -> HTTPS batch -> FastAPI
```

## Carpetas

- `node_lora_t3`: ejemplo avanzado PlatformIO con paquete binario, AES-128-CCM, persistencia antes de transmitir y ACK.
- `gateway_tbeam`: ejemplo avanzado PlatformIO con recepcion LoRa, descifrado, deduplicacion, persistencia previa a ACK y HTTPS/HMAC.
- `shared`: protocolo binario y funciones de cifrado compartidas.
- `arduino_ide`: sketches `.ino` mas simples para cargar desde Arduino IDE y probar nodo -> gateway -> plataforma.

## Guia Arduino IDE

Lee primero:

```text
docs/ARDUINO_IDE_COMUNICACION_NODO_GATEWAY_PLATAFORMA.md
```

La telemetria por nodo, calibracion y nivel JSN-SR04T estan documentados en:

```text
docs/TELEMETRIA_POR_NODO_Y_NIVEL.md
```

## Compilacion PlatformIO

```powershell
cd firmware
pio run
```

Entornos compilados:

- `node_lora_t3`: protocolo V2 y mediana de cinco muestras del JSN-SR04T.
- `gateway_tbeam`: decodificacion V1/V2, cola LittleFS, NTP, TLS y batch HTTPS firmado.

El gateway conserva los registros restantes al confirmar el primero. Solo retira una lectura si el backend responde `accepted` o `duplicate`.

## Estado

NO VERIFICADO - requiere prueba fisica o credenciales externas:

- Pinout exacto de LILYGO T3 LoRa32/T-Beam.
- Inicializacion de energia AXP2101 si tu placa la requiere.
- Certificado CA real de produccion.
- Aprovisionamiento seguro de claves en NVS.
- Recuperacion de cola ante corrupcion durante compactacion.
- Pruebas de alcance, perdida de ACK, reinicio y operacion sin internet.
- Comportamiento real del JSN-SR04T con polvo, ecos y condensacion.

## Reglas de piloto

- No enviar JSON por LoRa en la version final de campo.
- No incluir cliente, empresa, telefono, correo ni ubicacion en radio.
- No usar `client.setInsecure()` en produccion.
- No borrar lecturas del gateway hasta que el backend responda `accepted` o `duplicate`.
- No pilotear con las claves de ejemplo incluidas en el codigo.
