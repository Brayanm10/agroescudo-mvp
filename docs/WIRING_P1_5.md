# Cableado P1.5 - SiloSensor, CampoSensor y gateway

Estado: **CONFIGURADO Y COMPILADO; NO VERIFICADO EN HARDWARE REAL**.

## Radio LoRa común

| Señal SX1276 | GPIO ESP32 |
|---|---:|
| SCK | 5 |
| MISO | 19 |
| MOSI | 27 |
| NSS / CS | 18 |
| RESET | 23 |
| DIO0 | 26 |
| Frecuencia | 915 MHz |

## SiloSensor LILYGO T3 LoRa32 V1.6.1

| Elemento | Conexión |
|---|---|
| DS18B20 DATA | GPIO 4 con pull-up 4.7 kOhm a 3.3 V |
| SHT31 SDA | GPIO 21 |
| SHT31 SCL | GPIO 22 |
| JSN-SR04T TRIG | GPIO 32 |
| JSN-SR04T ECHO | GPIO 33 mediante divisor o level shifter |
| Medición de batería | GPIO 35 según divisor confirmado de la placa |

**Advertencia crítica:** ECHO del ultrasónico puede entregar 5 V. Nunca debe
conectarse directamente al ESP32. Usar, por ejemplo, 10 kOhm desde ECHO al nodo
de señal y 20 kOhm desde ese nodo a GND, verificando con multímetro que la salida
sea segura para 3.3 V.

El sensor ultrasónico debe instalarse perpendicular a la superficie, lejos de
paredes, travesaños y zonas de condensación. AgroEscudo transmite distancia en
milímetros; el porcentaje se calcula únicamente en backend con geometría válida.

## CampoSensor LILYGO T3

| Elemento | Conexión |
|---|---|
| Sensor de suelo analógico | ADC1 GPIO 32 |
| SHT31 SDA | GPIO 21 |
| SHT31 SCL | GPIO 22 |
| Medición de batería | GPIO 35 según divisor confirmado |

CampoSensor y SiloSensor son builds separados. GPIO 32 se usa para suelo en el
perfil campo y para TRIG ultrasónico en el perfil silo; no se habilitan ambas
funciones en el mismo firmware.

## Alimentación

- ESP32 y señales digitales: 3.3 V.
- Confirmar tensión admitida por cada módulo antes de energizar.
- Unir GND entre sensores y nodo.
- Separar cableado de potencia y radio de cables de medición.
- Usar caja con protección contra polvo y humedad sin bloquear el transductor.
- No asumir autonomía hasta medir consumo de sueño, transmisión y sensores.

## Verificación previa

1. Medir tensiones sin conectar el ESP32.
2. Confirmar continuidad y tierra común.
3. Verificar ausencia de 5 V en GPIO.
4. Arrancar por USB con monitor serie.
5. Probar cada sensor individualmente.
6. Probar paquete completo.
7. Recién después conectar antena, montar y probar alcance.
