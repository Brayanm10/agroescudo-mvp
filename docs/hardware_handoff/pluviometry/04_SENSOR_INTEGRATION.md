# 04 - Integración de sensores

## Orden obligatorio recomendado

### Fase 1 - SHT31

- `ambient_temp_1` -> `AMBIENT_TEMPERATURE_C` -> `degC`;
- `ambient_rh_1` -> `AMBIENT_RELATIVE_HUMIDITY_PCT` -> `percent`.

Listo cuando ambas lecturas son estables, finitas, están dentro de rango y fueron comparadas con un instrumento de referencia.

### Fase 2 - Pluviómetro real

- `rain_1` -> `RAIN_DELTA_MM` -> `mm`.

Listo cuando produce deltas no negativos, repetibles y calibrados para varios volúmenes o niveles equivalentes de precipitación.

### Fase 3 - Anemómetro

- `wind_speed_1` -> `WIND_SPEED_KMH` -> `km/h`.

Listo cuando la respuesta, el cero, la escala y la comparación con referencia son coherentes.

### Fase 4 - Veleta

- `wind_direction_1` -> `WIND_DIRECTION_DEG` -> `degree`.

La convención es meteorológica: el ángulo indica **de dónde viene** el viento. Debe tratar correctamente el cruce 359 -> 0 -> 1 sin enviar 360.

### Fase 5 - Batería

- `battery_1` -> `BATTERY_PERCENT` -> `percent`.

Listo cuando la estimación se compara con multímetro y con una curva/criterio documentado para la química y electrónica elegidas.

## Regla de una fase a la vez

No integrar todos los sensores simultáneamente. Cada fase debe cerrar:

1. lectura local estable;
2. unidad canónica correcta;
3. calibración documentada;
4. JSON correcto;
5. `ACCEPTED`;
6. valor visible en gráfico;
7. prueba de reinicio y falla básica.

## Lluvia incremental

AgroEscudo espera el incremento desde la muestra anterior, no el acumulado permanente del sensor.

```text
acumulado físico anterior: 12.0 mm
acumulado físico nuevo:    12.4 mm
enviar RAIN_DELTA_MM:       0.4 mm
```

No enviar `12.4` como delta.

El diseño definitivo deberá definir, cuando se conozca el mecanismo real:

- comportamiento después de reinicio;
- overflow del contador;
- tara y factor de calibración;
- rebote/ruido de pulsos;
- resolución por vuelco o muestra;
- evaporación, si el principio de medición la hace relevante;
- persistencia del último acumulado necesario para calcular el delta.

No se fija aquí un algoritmo definitivo porque depende del sensor seleccionado.

## Entregable mínimo por fase

- esquema eléctrico y pinout;
- modelo y hoja técnica del sensor;
- versión de firmware;
- frecuencia de muestreo;
- fórmula de conversión;
- tabla de calibración;
- evidencia Serial y respuesta API;
- captura del gráfico;
- desviaciones conocidas y decisión de aceptación.
