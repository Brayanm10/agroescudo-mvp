AGROESCUDO SENTINEL V0.2 - EJEMPLO FUNCIONAL
============================================

Estado
------
Implementado contra POST /api/sentinel/poll y
POST /api/sentinel/jobs/{job_id}/result. FastAPI decide el trabajo; Sentinel
solo ejecuta SMS o llamada y reporta el resultado. No accede a PostgreSQL.

Hardware y conexiones
---------------------
Componente       Pin dispositivo       Pin ESP32
SIM800L           TX/RX                 16/17 en este firmware
OLED I2C          SDA/SCL               21/22

El pinout 26/27 usado por algunas TTGO T-Call NO se aplica automaticamente.
Revise el esquema de su revision exacta; ajuste SIM800_RX_PIN y SIM800_TX_PIN.
La alimentacion del SIM800 requiere picos cercanos a 2 A y masa comun.

Preparacion
-----------
1. Cree el equipo en Web > Sentinel. Copie el token mostrado una sola vez.
2. Copie secrets.example.h como secrets.h y configure Wi-Fi, API_BASE_URL,
   SENTINEL_DEVICE_UID y SENTINEL_TOKEN.
3. Instale ESP32 Arduino Core, ArduinoJson, Adafruit GFX y SSD1306.
4. Abra agroescudo_sentinel_example.ino y compile para su ESP32/TTGO.
5. En el panel, configure contactos E.164 con consentimiento y programe una
   prueba controlada.

Salida serial esperada
----------------------
[BOOT] AgroEscudo Sentinel
[WIFI] connected
[GSM] SIM ready / registered
[API] poll HTTP 200
[JOB] sms claimed
[SIM800] submitted
[API] result reported

Seguridad y limites
-------------------
Nunca publique secrets.h ni el token. El equipo aplica polling, cooldown,
deduplicacion y reintentos basicos. Un trabajo pendiente impide eliminar el
Sentinel o su contacto hasta finalizar o vencer, preservando la auditoria.
