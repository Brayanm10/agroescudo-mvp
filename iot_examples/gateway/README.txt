AGROESCUDO GATEWAY MULTINODO V4 - EJEMPLO FUNCIONAL
===================================================

Estado
------
Implementado con el endpoint real POST /api/iot/v1/ingest/batch. Recibe tramas
LoRa V4, valida y descifra cada nodo, deduplica, persiste una cola LittleFS y
envia lotes HTTPS firmados con HMAC-SHA256. Solo elimina accepted/duplicate.

Flujo
-----
SiloSensor/CampoSensor -> LoRa 915 MHz -> T-Beam Gateway -> Wi-Fi -> HTTPS ->
FastAPI -> PostgreSQL. El gateway nunca accede directamente a la base de datos.

Hardware y conexiones (LILYGO T-Beam V1.2 AXP2101 + SX1276)
------------------------------------------------------------
Componente       Pin dispositivo       Pin ESP32
SX1276            SCK/MISO/MOSI/NSS     5/19/27/18
SX1276            RESET/DIO0            23/26
AXP2101           SDA/SCL               21/22

Preparacion
-----------
1. Registre el gateway en Web > Gateways. Copie el secreto mostrado una vez.
2. Copie secrets.example.h como secrets.h.
3. Configure AGRO_GATEWAY_ID, AGRO_GATEWAY_HMAC_SECRET, CA raiz PEM y las claves
   AES de cada nodo. No use setInsecure() en piloto.
4. Instale ESP32 Arduino Core, LoRa, ArduinoJson, WiFiManager y XPowersLib.
5. Instale firmware/arduino_ide/libraries/AgroEscudoProtocol.
6. Abra agroescudo_gateway_example.ino y compile para su T-Beam.

Salida serial esperada
----------------------
[BOOT] AgroEscudo Gateway V4
[WIFI] connected
[LORA] node=1001 seq=1523 RSSI=-78
[QUEUE] event persisted
[API] batch HTTP 200 accepted=1
[QUEUE] accepted record removed

Operacion y recuperacion
------------------------
- Sin internet: las tramas quedan en LittleFS y se reintentan posteriormente.
- Backend temporalmente caido: no se borra el evento.
- Duplicado: backend responde duplicate y la cola puede retirarlo con seguridad.
- Firma invalida/401: revise ID, secreto HMAC, hora del equipo y CA TLS.

Seguridad
---------
Nunca publique secrets.h, Wi-Fi, secreto HMAC, claves AES o certificados
privados. El reloj debe sincronizarse para la ventana anti-replay. Valide antena
y fuente antes de una prueba de alcance.
