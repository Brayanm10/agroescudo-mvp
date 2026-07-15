# Protocolo LoRa AgroEscudo

No se envia JSON por radio. El paquete se compone de:

- `AgroFrameHeader`
- payload cifrado AES-128-CCM
- tag de autenticacion

Campos minimos:

```text
protocol_version
message_type
key_version
device_id
boot_id
sequence
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

## Escalado

- `25.40 C` se transmite como `2540`.
- `63.20 % HR` se transmite como `6320`.
- `3910 mV` se transmite como `3910`.

## Seguridad

- AES-128-CCM mediante mbedTLS.
- Nonce: `device_id + boot_id + sequence`.
- AAD visible: version, tipo, key_version, device_id, boot_id, sequence.
- Datos cifrados: timestamp, temperaturas, humedad, bateria, estado y firmware.

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

