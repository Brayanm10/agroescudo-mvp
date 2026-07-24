# Telemetria Por Nodo Y Nivel Ultrasonico

## Alcance

AgroEscudo relaciona cada lectura con un unico `device_id`. Las pantallas, alertas y reportes pueden filtrar por dispositivo para impedir que dos nodos instalados en el mismo silo produzcan una serie temporal combinada.

Perfiles canonicos:

- `silo_sensor`: temperatura de grano, temperatura ambiente, humedad ambiente, bateria y distancia de nivel.
- `field_sensor`: temperatura ambiente, humedad ambiente, humedad de suelo, temperatura de suelo y bateria.
- Dispositivos legacy `esp32_*`: se interpretan como `silo_sensor` hasta que un administrador los reclasifique.

Una metrica ausente se guarda como `null`. Nunca se sustituye por cero.

## Endpoints

```http
GET /api/storage-units/{storage_unit_id}/devices
GET /api/devices/{device_id}/readings?from=&to=&limit=100&order=desc
GET /api/devices/{device_id}/summary
GET /api/devices/{device_id}/alerts
PATCH /api/admin/devices/{device_id}/calibration
GET /api/reports/weekly?storage_unit_id=&device_id=
GET /api/reports/weekly/pdf?storage_unit_id=&device_id=
```

El `device_id` del reporte es opcional. Sin el filtro, el reporte conserva los totales del silo y agrega una seccion separada por nodo. No crea una unica serie temporal mezclada.

## Calibracion De Nivel

La calibracion pertenece al dispositivo fisico:

```json
{
  "empty_distance_cm": 480.0,
  "full_distance_cm": 40.0
}
```

Regla obligatoria:

```text
empty_distance_cm > full_distance_cm > 0
```

El backend calcula:

```text
nivel = ((distancia_vacio - distancia_actual) /
         (distancia_vacio - distancia_lleno)) * 100
```

El resultado se limita a `0..100`. Si no existe calibracion, se conserva la distancia y `level_percent` queda en `null`. La interfaz muestra `Calibracion pendiente`.

El porcentaje representa altura ocupada. No representa volumen ni toneladas exactas.

## JSN-SR04T

Configuracion inicial del firmware:

```text
TRIG -> GPIO 32
ECHO -> GPIO 33 mediante divisor de tension
VCC  -> alimentacion segun la version del sensor
GND  -> tierra comun con ESP32
```

El pin ECHO del JSN-SR04T puede entregar 5 V. No debe conectarse directamente al ESP32. Use un divisor resistivo o acondicionador que limite la entrada a 3.3 V.

El nodo toma cinco muestras, descarta timeouts y valores fuera de rango, ordena las muestras validas y transmite la mediana en milimetros. El gateway convierte a centimetros antes de enviar la lectura HTTPS.

## Privacidad Por Rol

- `client`: recibe variables operativas; `signal_quality` y `sensor_status` se devuelven como `null`.
- `technician`: recibe RSSI, SNR, estado de sensor y firmware para los nodos asignados.
- `admin`: recibe diagnostico y calibracion, y puede modificarla.

El backend aplica estas reglas. Ocultar componentes en web o Flutter no se considera control de acceso.

## Validacion Antes Del Piloto

Confirmado por software:

- migracion SQLite reversible;
- filtrado por dispositivo;
- ingestiones directas y batch V1/V2;
- calculo y clamp de nivel;
- RBAC de diagnostico;
- nodo y gateway compilados con PlatformIO.

NO VERIFICADO - requiere prueba fisica:

- pinout exacto de la revision de placa;
- estabilidad electrica del divisor ECHO;
- rango util dentro del silo;
- ecos por paredes, cono de grano, polvo y condensacion;
- alcance y perdida de paquetes LoRa;
- autonomia real y comportamiento del gateway sin internet.

