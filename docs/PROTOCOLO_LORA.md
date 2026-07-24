# Protocolo LoRa AgroEscudo V1/V2/V3

V3 conserva encabezado, cifrado, ACK, reintentos e idempotencia y agrega `soil_moisture_raw` en `uint16_t`. El gateway detecta version y longitud antes de descifrar y mantiene V1/V2.

Arduino IDE incluye un formato HMAC `AGRO3` de puesta en marcha. PlatformIO mantiene el paquete binario cifrado recomendado. La validacion fisica de ADC y JSN-SR04T esta **NO VERIFICADO**.

No se envia JSON por radio. El paquete se compone de:

- `AgroFrameHeader`
- payload cifrado AES-128-CCM
- tag de autenticacion

El gateway detecta `protocol_version` y `payload_len` antes de descifrar. V1 permanece soportado para nodos instalados; V2 agrega perfiles y presencia explicita de metricas.

Cabecera comun:

```text
message_type
key_version
device_id
boot_id
sequence
payload_len
```

Payload V1:

```text
sample_counter
timestamp_utc
time_quality
grain_temp_c_x100
air_temp_c_x100
rh_x100
battery_mv
sensor_status
firmware_version
```

Payload V2:

```text
sample_counter
timestamp_utc
time_quality
sensor_profile
metric_flags
grain_temp_c_x100
air_temp_c_x100
rh_x100
soil_moisture_x100
soil_temp_c_x100
level_distance_mm
battery_mv
sensor_status
firmware_version
```

Perfiles:

- `1`: SiloSensor.
- `2`: CampoSensor.

`metric_flags` indica que valores estan presentes. Un campo sin flag no se interpreta ni se convierte en cero.

## Escalado

- `25.40 C` se transmite como `2540`.
- `63.20 % HR` se transmite como `6320`.
- `3910 mV` se transmite como `3910`.
- `120.5 cm` de distancia se transmite como `1205 mm`.

## Seguridad

- AES-128-CCM mediante mbedTLS.
- Nonce: `device_id + boot_id + sequence`.
- AAD visible: version, tipo, key_version, device_id, boot_id, sequence.
- Datos cifrados: timestamp, temperaturas, humedad, bateria, estado y firmware.
- V2 tambien cifra perfil, mascara de metricas, suelo y distancia ultrasonica.

## ACK Y Compatibilidad

- El gateway responde ACK solo despues de persistir la lectura o reconocer un duplicado.
- El ACK conserva la version del paquete recibido.
- La identidad idempotente es `device_id + boot_id + sequence`.
- El gateway elimina de su cola solo resultados `accepted` o `duplicate`.
- Una cola creada con una estructura de firmware incompatible se conserva como `/queue-incompatible.bak` para diagnostico; no se interpreta con el formato nuevo.

## Sensor Ultrasonico

- El nodo toma cinco muestras y transmite la mediana valida.
- Timeout o ausencia de eco: no activa `AGRO_HAS_LEVEL_DISTANCE`.
- El backend, no el firmware, calcula el porcentaje con la calibracion del dispositivo.
- Distancia valida de software: mayor a 0 y hasta 20 m; el rango util real debe validarse en el silo.

## Privacidad

No incluir por LoRa:

- nombre de cliente;
- empresa;
- telefono;
- correo;
- direccion;
- coordenadas exactas;
- credenciales;
- nombres de trabajadores.

