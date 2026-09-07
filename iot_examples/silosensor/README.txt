AGROESCUDO SILOSENSOR V4 - EJEMPLO FUNCIONAL
============================================

Estado
------
Implementado sobre el protocolo binario TLV V4 real del repositorio. El nodo
lee sensores, conserva secuencia en Preferences, cifra/autentica la trama y la
envia por LoRa. La validacion fisica en silo sigue siendo obligatoria.

Flujo
-----
DS18B20 + SHT31 + JSN-SR04T -> ESP32 LoRa -> 915 MHz -> Gateway AgroEscudo.
No envia JSON por radio y no se conecta directamente a PostgreSQL ni FastAPI.

Hardware y conexiones (LILYGO LoRa32/T3 V1.6.1)
------------------------------------------------
Componente       Pin dispositivo       Pin ESP32
SX1276            SCK/MISO/MOSI/NSS     5/19/27/18
SX1276            RESET/DIO0            23/26
DS18B20           DATA                  4 (usar pull-up 4.7 kOhm)
SHT31             SDA/SCL               21/22
JSN-SR04T         TRIG/ECHO              32/33
Bateria           salida divisor ADC    35

IMPORTANTE: ECHO del JSN-SR04T puede trabajar a 5 V. Use divisor resistivo o
adaptador de nivel para no aplicar mas de 3.3 V al ESP32.

Preparacion
-----------
1. Copie secrets.example.h como secrets.h en esta misma carpeta.
2. Cambie AGRO_DEVICE_ID, AGRO_KEY_VERSION y la clave AES. Deben coincidir con
   el nodo registrado en la configuracion privada del gateway.
3. Instale ESP32 Arduino Core, LoRa, OneWire, DallasTemperature y
   Adafruit_SHT31.
4. Instale firmware/arduino_ide/libraries/AgroEscudoProtocol en la carpeta
   libraries de Arduino.
5. Abra agroescudo_silosensor_example.ino, seleccione su placa ESP32 y compile.

Salida serial esperada
----------------------
[BOOT] AgroEscudo SiloSensor V4
[SENSOR] grain=27.40 C ambient=25.90 C humidity=63.20 %
[LEVEL] distance=184.2 cm valid
[LORA] frame sent seq=1523
[ACK] accepted

Seguridad
---------
Nunca publique secrets.h. Use una clave diferente por nodo. La frecuencia,
potencia y antena deben cumplir la normativa local. Los valores de pines se
deben contrastar con la revision impresa en la placa antes de energizar.
