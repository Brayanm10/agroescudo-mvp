# Firmware AgroEscudo

## Arduino IDE V4 para piloto

La entrega compilada para Arduino IDE esta en `firmware/arduino_ide/` e
incluye gateway multinodo, SiloSensor, CampoSensor y la biblioteca comun
`AgroEscudoProtocol`. Consulta
`docs/MANUAL_GATEWAY_SILO_CAMPO_ARDUINO_IDE.md` antes de cargar las placas.

PlatformIO compila protocolo V4 P1.5:

- `AGRO_SENSOR_PROFILE=1`: SiloSensor con JSN-SR04T.
- `AGRO_SENSOR_PROFILE=2`: CampoSensor con `soil_moisture_raw`.
- `AGRO_SOIL_MOISTURE_PIN=32`: ADC1 configurable para CampoSensor.

El gateway conserva V1/V2/V3 y agrega V4 TLV. Solo envia metricas presentes,
identificadas por `metric_id`, `channel_id`, `metric_code` y `channel_key`. La
calibracion y las metricas derivadas se calculan en FastAPI.

Este directorio contiene puntos de partida para el enlace:

```text
Nodo ESP32 LoRa -> Gateway LoRa/WiFi -> HTTPS batch -> FastAPI
```

## Carpetas

- `node_lora_t3`: ejemplo avanzado PlatformIO con paquete binario, AES-128-CCM, persistencia antes de transmitir y ACK.
- `gateway_tbeam`: ejemplo avanzado PlatformIO con recepcion LoRa, descifrado, deduplicacion, persistencia previa a ACK y HTTPS/HMAC.
- `shared`: protocolo binario y funciones de cifrado compartidas.
- `arduino_ide`: sketches legacy de laboratorio. No son el firmware P1.5 para
  piloto; el build verificado está en PlatformIO.

## Guia Arduino IDE

Lee primero:

```text
docs/ARDUINO_IDE_COMUNICACION_NODO_GATEWAY_PLATAFORMA.md
```

La telemetria por nodo, calibracion y nivel JSN-SR04T estan documentados en:

```text
docs/TELEMETRIA_POR_NODO_Y_NIVEL.md
docs/MANUAL_TECNICO_INTEGRACION_SENSORES_LORA_P1_5.md
```

## Compilacion PlatformIO

```powershell
cd firmware
C:\Users\braya\.platformio\penv\Scripts\platformio.exe run
```

Entornos compilados:

- `node_lora_t3`: SiloSensor V4 TLV con DS18B20, SHT31, JSN-SR04T y batería.
- `node_field_t3`: CampoSensor V4 TLV con suelo raw, SHT31 y batería.
- `gateway_tbeam`: decodificación V1/V2/V3/V4, colas LittleFS separadas,
  deduplicación, NTP, TLS y batch HTTPS firmado.

El gateway conserva los registros restantes al confirmar el primero. Solo retira
una lectura V4 si el backend responde `ACCEPTED` o `DUPLICATE`.

## Estado

NO VERIFICADO - requiere prueba fisica o credenciales externas:

- Cableado y comportamiento eléctrico en las placas físicas disponibles.
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
