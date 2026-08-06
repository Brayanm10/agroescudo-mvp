# Manual de firmware AgroEscudo

## Gateway multinodo, SiloSensor y CampoSensor con Arduino IDE

Version: 1.0 / 2026-08-06
Estado de software: compilacion verificada
Estado fisico: NO VERIFICADO - requiere prueba de banco con las placas reales

## 1. Objetivo

Este manual explica como cargar, configurar y operar los tres programas que
conectan sensores fisicos con AgroEscudo:

```text
SiloSensor o CampoSensor
  -> paquete binario V4 TLV
  -> AES-128-CCM
  -> radio LoRa 915 MHz
  -> Gateway T-Beam
  -> persistencia LittleFS
  -> ACK al nodo
  -> HTTPS + HMAC-SHA256
  -> FastAPI /api/iot/v1/ingest/batch
  -> PostgreSQL
  -> grafica exacta del nodo y canal
```

El gateway no calcula porcentajes comerciales, no mezcla nodos y no usa
posiciones de arreglos para interpretar variables. Cada dato lleva
`metric_code` y `channel_key` explicitos.

## 2. Archivos que debes usar

```text
firmware/arduino_ide/
  libraries/AgroEscudoProtocol/
  agroescudo_gateway_multinodo_v4/
    agroescudo_gateway_multinodo_v4.ino
    secrets.example.h
  agroescudo_silo_sensor_v4/
    agroescudo_silo_sensor_v4.ino
    secrets.example.h
  agroescudo_campo_sensor_v4/
    agroescudo_campo_sensor_v4.ino
    secrets.example.h
```

El `.ino` recibido originalmente se conserva fuera del repositorio y no fue
sobrescrito. Su panel local y WiFiManager son utiles como referencia, pero su
protocolo textual `AGRO1`, TLS inseguro y tokens por nodo no deben ser el flujo
principal del piloto.

## 3. Mejoras respecto al gateway anterior

| Antes | Version V4 de piloto |
|---|---|
| Paquete de texto `AGRO1` | Binario TLV versionado |
| Campos interpretados por posicion | Metrica y canal identificados |
| Token API de cada nodo en gateway | Credencial HMAC unica del gateway |
| TLS inseguro habilitable | CA raiz obligatoria, sin `setInsecure()` |
| POST individual a `/api/readings` | Batch firmado a `/api/iot/v1/ingest/batch` |
| Confirmacion antes de trazabilidad durable | ACK solo despues de guardar en LittleFS |
| Busqueda de texto en respuesta HTTP | Parseo JSON de `canonical_status` |
| Rechazos descartables | Archivo dead-letter preservado |
| Clave comun implicita | Tabla explicita de claves por `node_id` |

## 4. Hardware objetivo

### Gateway

- LILYGO T-Beam V1.2 con AXP2101.
- Radio SX1276 de 915 MHz.
- Antena 915 MHz instalada antes de energizar y transmitir.

### Nodos

- LILYGO LoRa32/T3 V1.6.1 con SX1276.
- SiloSensor: DS18B20, SHT31, JSN-SR04T y medicion de bateria.
- CampoSensor: sensor analogico de humedad de suelo, SHT31 y bateria.

Confirma la revision impresa de cada placa. Las revisiones V1.0, V1.2 y V1.6
pueden usar otro pin RESET de LoRa. El codigo de piloto usa GPIO 23 para la
revision V1.6.1; si tu placa es V1.0 cambia `AGRO_LORA_RST_PIN` a GPIO 14.

## 5. Cableado SiloSensor

| Funcion | GPIO |
|---|---:|
| LoRa SCK / MISO / MOSI | 5 / 19 / 27 |
| LoRa NSS / RESET / DIO0 | 18 / 23 / 26 |
| DS18B20 DATA | 4 |
| SHT31 SDA / SCL | 21 / 22 |
| JSN-SR04T TRIG / ECHO | 32 / 33 |
| Bateria ADC | 35 |

Advertencias:

- DS18B20 necesita pull-up de 4.7 kOhm entre DATA y 3.3 V.
- El ECHO del JSN-SR04T puede entregar 5 V. Usa divisor o level shifter para
  que GPIO 33 nunca reciba mas de 3.3 V.
- Comparte GND entre placa y sensores.
- Instala el ultrasonico perpendicular al producto y lejos de paredes.
- La lectura representa altura estimada, no toneladas ni volumen exacto.

## 6. Cableado CampoSensor

| Funcion | GPIO |
|---|---:|
| LoRa SCK / MISO / MOSI | 5 / 19 / 27 |
| LoRa NSS / RESET / DIO0 | 18 / 23 / 26 |
| Humedad de suelo ADC | 32 |
| SHT31 SDA / SCL | 21 / 22 |
| Bateria ADC | 35 |

El nodo envia `SOIL_MOISTURE_RAW` entre 0 y 4095. AgroEscudo aplica la
calibracion activa en backend; el ESP32 no inventa un porcentaje. La
temperatura de suelo queda pendiente de registrar como metrica canonica
independiente y no se etiqueta como temperatura interna del nodo.

## 7. Instalacion de Arduino IDE

1. Instala Arduino IDE 2.x.
2. En preferencias agrega el indice oficial de placas ESP32 de Espressif.
3. Instala una version estable de `esp32 by Espressif Systems`.
4. Desde Library Manager instala:
   - LoRa de Sandeep Mistry 0.8.x.
   - ArduinoJson 7.x.
   - Adafruit SHT31 2.2.x.
   - OneWire 2.3.x y DallasTemperature 3.11.x para SiloSensor.
   - WiFiManager 2.0.17 o superior para gateway.
   - XPowersLib 0.3.x para T-Beam AXP2101.
5. Copia `firmware/arduino_ide/libraries/AgroEscudoProtocol` a
   `Documentos/Arduino/libraries/AgroEscudoProtocol`.
6. Reinicia Arduino IDE.

## 8. Configurar secretos de los nodos

En cada carpeta de nodo:

1. Duplica `secrets.example.h`.
2. Renombra la copia como `secrets.h`.
3. Asigna un `AGRO_NODE_ID` unico.
4. Genera una clave AES de 16 bytes.
5. Registra el mismo ID y clave en la tabla `AGRO_NODE_KEYS` del gateway.

Ejemplo conceptual:

```cpp
static constexpr uint16_t AGRO_NODE_ID = 1001;
static constexpr uint8_t AGRO_NODE_KEY_VERSION = 1;
static constexpr uint8_t AGRO_NODE_AES_KEY[16] = { /* 16 bytes privados */ };
```

No uses las claves de ejemplo en una instalacion compartida.

## 9. Configurar el gateway

Copia `secrets.example.h` como `secrets.h` y configura:

- `AGRO_API_URL`: URL HTTPS del endpoint batch.
- `AGRO_GATEWAY_ID`: ID registrado en backend.
- `AGRO_GATEWAY_HMAC_SECRET`: secreto provisionado para ese gateway.
- `AGRO_ROOT_CA_PEM`: CA raiz vigente de la cadena TLS.
- `AGRO_NODE_KEYS`: IDs, version y clave AES de nodos autorizados.

El secreto HMAC debe coincidir con la credencial cifrada del gateway en el
backend. No es el JWT, la password de admin ni el `device_token` legacy.

## 10. Compilar y cargar

### SiloSensor y CampoSensor

1. Abre el `.ino` correspondiente.
2. Selecciona la placa LILYGO/TTGO LoRa32 compatible o ESP32 Dev Module.
3. Selecciona el puerto COM.
4. Compila.
5. Carga.
6. Abre monitor serie a 115200 baud.

### Gateway

1. Abre `agroescudo_gateway_multinodo_v4.ino`.
2. Selecciona TTGO T-Beam.
3. Selecciona `Partition Scheme: Huge APP (3MB No OTA/1MB SPIFFS)`.
4. Selecciona el puerto COM.
5. Compila y carga.
6. En primer inicio conecta el celular al AP `AgroEscudo-Gateway` y configura
   el WiFi.
7. Revisa el monitor serie a 115200 baud.

La particion Huge APP es obligatoria para esta composicion: TLS, WiFiManager,
LittleFS, ArduinoJson y XPowers ocupan aproximadamente 1.33 MB.

## 11. Flujo de confirmacion y reintento

1. El nodo conserva el frame pendiente en Preferences.
2. Transmite hasta tres veces.
3. El gateway valida nodo, version, longitud, AES-CCM, metrica, canal y rango.
4. Persiste el evento en LittleFS.
5. Solo entonces envia ACK.
6. Si no hay internet, el evento permanece en cola.
7. Al recuperar internet, firma y envia el evento.
8. `ACCEPTED` o `DUPLICATE`: retira el evento de la cola.
9. `REJECTED` o `QUARANTINED`: mueve el evento a dead-letter para auditoria.
10. Error temporal: conserva el evento para reintentar.

La idempotencia final usa `device_id + boot_id + sequence`.

## 12. Mostrar u ocultar nivel y otras graficas

No borres lecturas para ocultar una grafica.

1. Inicia sesion como admin o tecnico autorizado.
2. Abre `Silos/Galpones` y entra al detalle.
3. Selecciona `Nodo monitoreado`.
4. Baja a `Sensores y graficas`.
5. En la fila `Nivel estimado`, usa el icono de ojo:
   - ojo visible: la grafica aparece;
   - ojo tachado: la grafica se oculta.
6. El boton de energia de la columna Alertas habilita o pausa alertas del
   canal sin eliminar datos.

Para retirar fisicamente el JSN-SR04T:

1. Oculta la grafica y desactiva alertas.
2. Apaga el nodo.
3. Desconecta el sensor respetando el procedimiento electrico.
4. Carga una version de SiloSensor sin esa metrica o deja que los timeouts la
   omitan; nunca envies cero para representar ausencia.
5. Conserva el canal historico para trazabilidad.

Para instalarlo de nuevo, agrega o habilita el canal
`level_ultrasonic_1`, configura la misma metrica en firmware y calibra distancia
de silo vacio y lleno desde la web.

## 13. Como verificar que los datos entraron

En el monitor serie del nodo debe aparecer:

```text
Lectura confirmada por gateway.
```

En gateway:

```text
Nodo 1001, secuencia 25 persistida.
Evento confirmado por AgroEscudo API.
```

En la web:

1. Selecciona exactamente el nodo.
2. Verifica ultima lectura.
3. Verifica que cada grafica corresponda a su canal.
4. Cambia a otro nodo y confirma que las series se reemplazan, no se suman.

## 14. Diagnostico

### No aparece el AP WiFi

- Borra credenciales WiFi del ESP32 o usa el reset de WiFiManager.
- Confirma alimentacion y monitor serie.

### Nodo informa `Sin ACK`

- Nodo y gateway deben usar 915 MHz, SF7, BW125, CR4/5, sync 0x12.
- Confirma `node_id`, version de clave y AES iguales.
- Instala antenas antes de transmitir.
- Revisa que el gateway pueda escribir LittleFS.

### Gateway muestra HTTP 401

- `AGRO_GATEWAY_ID` o HMAC no coincide con backend.
- Hora NTP fuera de ventana.
- Credencial revocada o gateway inactivo.

### TLS falla

- CA raiz incorrecta o vencida.
- Hora del gateway no sincronizada.
- No uses `setInsecure()` para ocultar el problema.

### API devuelve `QUARANTINED`

- Canal no registrado o deshabilitado.
- `metric_code`, unidad o perfil incompatible.
- Revisa dead-letter antes de corregir y reenviar.

## 15. Checklist de banco

- [ ] Revision exacta de placas confirmada.
- [ ] Antenas 915 MHz conectadas.
- [ ] ECHO reducido a 3.3 V.
- [ ] Fuente estable y GND comun.
- [ ] IDs unicos registrados.
- [ ] Claves AES coinciden.
- [ ] Gateway HMAC provisionado.
- [ ] CA TLS vigente instalada.
- [ ] Tres compilaciones exitosas.
- [ ] ACK probado a 1 m, 10 m y distancia objetivo.
- [ ] Prueba sin WiFi: evento queda en cola.
- [ ] Prueba con reconexion: evento llega una vez.
- [ ] Cambio de nodo no mezcla graficas.
- [ ] Datos invalidos no aparecen como cero.

## 16. Limitaciones verificadas

- El software compila para ESP32, TTGO LoRa32 y T-Beam.
- No se cargo aun en el hardware fisico de este entorno.
- No se valido alcance de radio, polvo, condensacion, autonomia ni montaje.
- La CA TLS debe verificarse con el dominio productivo al provisionar.
- El CampoSensor transmite humedad raw; requiere calibracion de dos puntos en
  campo antes de interpretar porcentaje.
- El nivel ultrasonico requiere calibracion por dispositivo y no equivale por
  si solo a masa o toneladas.
