# 02 - Contrato de telemetría

## Contrato canónico inmutable para `RAIN_GAUGE_BASE`

| Canal | Código de métrica | Unidad exacta | Semántica y rango aceptado |
|---|---|---|---|
| `rain_1` | `RAIN_DELTA_MM` | `mm` | Lluvia incremental desde la lectura anterior. `x >= 0`. |
| `ambient_temp_1` | `AMBIENT_TEMPERATURE_C` | `degC` | Temperatura ambiente. `-40 <= x <= 80`. |
| `ambient_rh_1` | `AMBIENT_RELATIVE_HUMIDITY_PCT` | `percent` | Humedad relativa. `0 <= x <= 100`. |
| `wind_speed_1` | `WIND_SPEED_KMH` | `km/h` | Velocidad del viento. `x >= 0`. |
| `wind_direction_1` | `WIND_DIRECTION_DEG` | `degree` | Dirección meteorológica: indica de dónde viene el viento. `0 <= x < 360`. |
| `battery_1` | `BATTERY_PERCENT` | `percent` | Porcentaje de batería. `0 <= x <= 100`. |

Los nombres, mayúsculas, canales y unidades son parte del contrato. No usar `%`, `C`, `m/s`, `degrees`, aliases ni códigos inventados.

Todos los valores deben ser numéricos finitos: no se admiten `NaN`, infinito ni texto numérico.

## Forma conceptual de una métrica

```json
{
  "channel_key": "rain_1",
  "metric_code": "RAIN_DELTA_MM",
  "raw_value": 0.4,
  "unit": "mm",
  "quality": "VALID"
}
```

## Estados y validaciones reales

### HTTP 422 - lote no procesable

Ocurre antes de procesar lecturas cuando el JSON o el modelo del lote no cumple el esquema. Ejemplos:

- JSON inválido;
- falta timestamp y falta `sampled_at`;
- una métrica no es finita;
- lluvia o velocidad negativas;
- humedad o batería fuera de 0..100;
- dirección fuera de `0 <= x < 360`;
- lote sin lecturas o con `readings` y `events` simultáneamente.

El lote debe corregirse; HTTP 422 no significa que la lectura fue aceptada.

### HTTP 200 con `QUARANTINED`

La autenticación y estructura del lote son válidas, pero una lectura explícita no coincide con la configuración registrada. Ejemplos:

- canal inexistente o deshabilitado;
- métrica no canónica;
- métrica asignada al canal equivocado;
- unidad distinta de la canónica;
- métrica incompatible con el perfil `RAIN_GAUGE`;
- pareja canal/métrica repetida.

Una lectura en cuarentena no crea `TelemetryEvent`, `MetricReading` ni lectura operacional.

### HTTP 200 con `ACCEPTED`

La lectura fue autenticada, validada, persistida y normalizada. Se crean el evento y sus métricas; el dispositivo puede pasar de `awaiting_first_reading` a `operational`.

### Otros resultados por lectura

- `DUPLICATE`: ya existe el mismo dispositivo + `boot_id` + `sequence`; no se crea otra lectura.
- `REJECTED`: dispositivo desconocido/inactivo, perfil incorrecto, rangos legacy inválidos u otra incompatibilidad de autorización/lectura.
- `TEMPORARY_ERROR`: el emisor debe conservar y reintentar posteriormente.

## Identidad del dispositivo

- **Device ID físico:** identificador aprobado usado por el firmware, por ejemplo `PLUV-001`. Corresponde al identificador externo registrado.
- **Database ID interno:** clave numérica de la base de datos. No debe cablearse en firmware ni asumirse estable entre entornos.

## Tiempo

- `timestamp_utc` es Unix epoch en UTC.
- El ESP32 debe sincronizar mediante NTP antes de transmitir.
- `sent_at` y el encabezado temporal también representan UTC.
- No restar manualmente cuatro horas.
- AgroEscudo presenta la hora local usando `Site.timezone`; para Bolivia: `America/La_Paz`.

Si se utiliza `sampled_at` para un `rain_gauge`, debe incluir zona horaria explícita.

## Identidad de evento e idempotencia

| Campo | Propósito |
|---|---|
| `boot_id` | Identifica un ciclo de arranque. Debe cambiar al reiniciar. |
| `sequence` | Secuencia monotónica dentro del arranque. Puede comenzar en 0 con un nuevo `boot_id`. |
| `sample_counter` | Contador de muestras adquiridas; permite diagnosticar pérdidas o saltos. |
| `batch_id` | Identidad única del lote HTTP. No reutilizar. |
| `nonce` | Identidad anti-replay del request firmado. No reutilizar con el mismo gateway. |

```text
nuevo reinicio -> nuevo boot_id -> sequence puede volver a 0
mismo Device ID + boot_id + sequence -> DUPLICATE
```

Un reintento de la misma muestra debe conservar `boot_id` y `sequence`, pero el diseño de transporte debe respetar las reglas de `batch_id` y nonce del gateway.
