# AgroEscudo - Comunicacion Nodo LoRa, Gateway WiFi y Plataforma

Este documento explica como conectar un nodo ESP32 LoRa con un gateway ESP32 LoRa/WiFi y la API de AgroEscudo usando Arduino IDE.

El flujo recomendado para piloto es:

```text
Nodo ESP32 LoRa
  -> envia lectura por LoRa autenticada con HMAC
Gateway ESP32 LoRa/WiFi
  -> valida la lectura
  -> arma lote JSON
  -> firma el lote con HMAC
  -> envia HTTPS a FastAPI
Plataforma AgroEscudo
  -> guarda lectura
  -> evalua umbrales
  -> crea alertas
  -> muestra dashboard, app y PDF
```

## Archivos creados

```text
firmware/arduino_ide/agroescudo_node_lora/agroescudo_node_lora.ino
firmware/arduino_ide/agroescudo_gateway_wifi_lora/agroescudo_gateway_wifi_lora.ino
```

Abre cada carpeta desde Arduino IDE y carga el `.ino` correspondiente.

## Librerias Arduino IDE

Instala desde Library Manager:

- `LoRa` de Sandeep Mistry
- `ArduinoJson` de Benoit Blanchon

El core ESP32 ya incluye:

- `WiFi`
- `HTTPClient`
- `WiFiClientSecure`
- `mbedtls` para SHA256/HMAC

## Hardware sugerido

Nodo:

- ESP32 LoRa, por ejemplo LILYGO TTGO LoRa32/T3.
- Sensor de temperatura/humedad.
- JSN-SR04T para distancia de nivel en perfil SiloSensor.

Gateway:

- ESP32 LoRa con WiFi, por ejemplo T-Beam o TTGO LoRa32.
- Conexion WiFi con internet.

## Configuracion importante

### 1. Frecuencia LoRa

En Bolivia normalmente se trabaja cerca de 915 MHz, pero debes validar la normativa local y el modulo comprado.

En ambos sketches:

```cpp
static const long LORA_BAND = 915E6;
```

### 2. Pines LoRa

Los pines cambian segun placa. Valores comunes TTGO/T-Beam:

```cpp
static const int LORA_SCK = 5;
static const int LORA_MISO = 19;
static const int LORA_MOSI = 27;
static const int LORA_SS = 18;
static const int LORA_RST = 14;
static const int LORA_DIO0 = 26;
```

Si tu placa no inicia LoRa, revisa el pinout exacto.

### 2.1 JSN-SR04T

El sketch de nodo usa por defecto:

```cpp
static const int ULTRASONIC_TRIG_PIN = 32;
static const int ULTRASONIC_ECHO_PIN = 33;
```

Cableado:

```text
TRIG -> GPIO 32
ECHO -> divisor de tension -> GPIO 33
GND  -> GND comun
VCC  -> segun la version del JSN-SR04T
```

ADVERTENCIA: ECHO puede entregar 5 V. No lo conectes directamente al ESP32. El divisor o acondicionador a 3.3 V es obligatorio.

El nodo toma cinco muestras, descarta timeouts y envia la mediana. Si ninguna muestra es valida, el paquete no marca la metrica de nivel. El backend calcula el porcentaje despues de configurar distancia de silo vacio y lleno.

### 3. IDs de dispositivos

El seed de AgroEscudo deja estos nodos IoT:

```text
SILO-001    -> node_id 1001
SILO-002    -> node_id 1002
GALPON-001  -> node_id 1003
```

En el nodo:

```cpp
static const uint16_t NODE_ID = 1001;
```

### 4. Clave nodo -> gateway

El nodo y el gateway deben compartir una clave para validar paquetes LoRa.

En el nodo:

```cpp
static const char* NODE_SECRET = "cambia-esta-clave-node-1001";
```

En el gateway:

```cpp
static const char* NODE_SECRET_1001 = "cambia-esta-clave-node-1001";
```

Para piloto real no uses estas claves de ejemplo.

### 5. Clave gateway -> backend

El gateway firma el batch que envia a FastAPI.

En el gateway:

```cpp
static const char* GATEWAY_ID = "GW-CBBA-001";
static const char* GATEWAY_SECRET = "pon-aqui-el-mismo-secreto-del-backend";
```

Ese secreto debe coincidir con el backend. Para configurar el backend:

```powershell
setx AGRO_SEED_GATEWAY_SECRET "pon-aqui-el-mismo-secreto-del-backend"
```

Luego ejecutar seed en backend:

```powershell
cd backend
python -m app.seed
```

En Render debes configurar la variable `AGRO_SEED_GATEWAY_SECRET` y correr el seed/despliegue correspondiente.

## Endpoint usado

El gateway envia a:

```text
POST https://agroescudo-api.onrender.com/api/iot/v1/ingest/batch
```

Importante: este endpoint debe estar desplegado en el backend. Si Render todavia tiene una version anterior del backend, primero debes desplegar la version que incluye `backend/app/api/routes/iot.py` y la migracion IoT.

Headers:

```text
X-Agro-Gateway-ID: GW-CBBA-001
X-Agro-Timestamp: 2026-07-02T12:00:00Z
X-Agro-Nonce: valor-unico
X-Agro-Signature: firma_hmac_sha256
```

Payload:

```json
{
  "gateway_id": "GW-CBBA-001",
  "firmware_version": "arduino-gateway-1.0.0",
  "sent_at": "2026-07-02T12:00:00Z",
  "batch_id": "GW-CBBA-001-123456",
  "readings": [
    {
      "device_id": 1001,
      "protocol_version": 2,
      "sensor_profile": "silo_sensor",
      "metric_flags": 79,
      "boot_id": 12345,
      "sequence": 1,
      "sample_counter": 1,
      "timestamp_utc": 1782993600,
      "time_quality": 1,
      "grain_temp_c_x100": 3150,
      "air_temp_c_x100": 2820,
      "rh_x100": 7210,
      "level_distance_cm": 120.5,
      "battery_mv": 3910,
      "sensor_status": 0,
      "firmware_version": 100,
      "rssi_dbm": -67,
      "snr_db_x10": 75
    }
  ]
}
```

## Orden de prueba

1. Levanta backend o usa Render:

```text
https://agroescudo-api.onrender.com/health
```

2. Configura y ejecuta seed con el secreto del gateway.
3. Carga `agroescudo_gateway_wifi_lora.ino` al gateway.
4. Abre Serial Monitor a `115200`.
5. Verifica WiFi, NTP y LoRa.
6. Carga `agroescudo_node_lora.ino` al nodo.
7. Abre Serial Monitor del nodo.
8. Espera envio LoRa.
9. El gateway debe mostrar HTTP 200.
10. En AgroEscudo revisa lecturas, alertas, silo y reporte.

## Respuesta esperada del backend

Ejemplo correcto:

```json
{
  "batch_id": "GW-CBBA-001-123456",
  "results": [
    {
      "device_id": 1001,
      "boot_id": 12345,
      "sequence": 1,
      "status": "accepted",
      "detail": null
    }
  ]
}
```

Si repites la misma lectura:

```text
duplicate
```

Eso es correcto: evita duplicados.

## Seguridad

- No mandes password ni usuario por LoRa.
- No pongas `device_token` en la app movil ni frontend.
- El nodo solo manda mediciones tecnicas.
- El gateway firma contra backend con HMAC.
- Para piloto real, cambia todas las claves de ejemplo.
- El gateway Arduino viene con `USE_INSECURE_TLS_FOR_DEMO = false`.
- Pega el certificado CA real en `ROOT_CA`. Solo usa `true` durante una prueba local controlada, nunca en piloto.

## Limitaciones de esta version Arduino IDE

Esta version esta hecha para que puedas entender, cargar y probar el flujo completo.

Pendiente para campo real avanzado:

- Cifrado LoRa AES-CCM completo.
- Cola durable en gateway si no hay internet.
- Persistencia robusta ante cortes de energia.
- Provisionamiento seguro de claves.
- Prueba fisica de alcance, antenas y consumo.

Para el piloto comercial inicial, este flujo sirve para demostrar la comunicacion completa con datos reales y alertas reales si se configuran claves y sensores correctamente.

La compilacion del codigo no sustituye la prueba fisica. La distancia real, ecos del techo y paredes, polvo, condensacion, alcance LoRa y consumo permanecen `NO VERIFICADO` hasta completar una prueba de banco y una prueba dentro del silo.

## Resumen de que editar antes de subir

Nodo:

```cpp
NODE_ID
NODE_SECRET
LORA_BAND
LORA_SCK / LORA_MISO / LORA_MOSI / LORA_SS / LORA_RST / LORA_DIO0
ULTRASONIC_TRIG_PIN / ULTRASONIC_ECHO_PIN
```

Gateway:

```cpp
WIFI_SSID
WIFI_PASSWORD
GATEWAY_SECRET
NODE_SECRET_1001 / NODE_SECRET_1002 / NODE_SECRET_1003
LORA_BAND
LORA_SCK / LORA_MISO / LORA_MOSI / LORA_SS / LORA_RST / LORA_DIO0
USE_INSECURE_TLS_FOR_DEMO
ROOT_CA
```
