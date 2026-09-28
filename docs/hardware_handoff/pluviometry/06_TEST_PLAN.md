# 06 - Plan de pruebas y aceptación

## Criterios por variable

| Variable | Criterios mínimos de aceptación |
|---|---|
| Temperatura | Sin `NaN`; estable; `-40..80 degC`; comparación y error frente a referencia documentados. |
| Humedad | Sin `NaN`; estable; `0..100 percent`; comparación frente a referencia y recuperación después de condensación/perturbación evaluadas. |
| Lluvia | Delta consistente y no negativo; cero sin lluvia; varios puntos calibrados; reinicio y overflow documentados. |
| Velocidad | No negativa; cero coherente; respuesta y escala comparadas con referencia. |
| Dirección | Convención "de dónde viene"; `0 <= x < 360`; cruce 359/0 correcto; orientación física documentada. |
| Batería | `0..100 percent`; coherencia con multímetro y curva/criterio de estimación. |

## Matriz de pruebas

| ID | Prueba | Evidencia esperada | Resultado |
|---|---|---|---|
| T01 | Encendido y Device ID | Identidad correcta en Serial y JSON. | |
| T02 | Sincronización NTP | `timestamp_utc` UTC válido; no ajuste manual -4 h. | |
| T03 | Seis métricas | Canales, códigos y unidades exactos. | |
| T04 | Límite inferior/superior | Aceptación dentro del rango. | |
| T05 | Fuera de rango | HTTP 422 o clasificación esperada; nunca `ACCEPTED`. | |
| T06 | Canal/unidad incorrectos | HTTP 200 con `QUARANTINED`; sin evento normalizado. | |
| T07 | Duplicado | Mismo Device ID + boot + sequence produce `DUPLICATE`. | |
| T08 | Reinicio | Nuevo `boot_id`; sequence puede volver a 0. | |
| T09 | HMAC incorrecto | HTTP 401; no persistencia. | |
| T10 | Lote válido | HTTP 200 + `ACCEPTED`. | |
| T11 | Dashboard | Valor visible en mapa/gráfico con hora local correcta. | |
| T12 | Sin red | Falla observada y pérdida cuantificada; no declarar store-and-forward. | |
| T13 | Recuperación de red | Reconexión sin duplicar eventos. | |
| T14 | Estabilidad | Ejecución prolongada sin caída ni degradación relevante. | |

## Checklist end-to-end obligatorio

```text
[ ] sensor real produce señal
[ ] ESP32 convierte a unidad canónica
[ ] JSON contiene identidad, UTC y métricas exactas
[ ] cuerpo hasheado con SHA256
[ ] request firmado con HMAC-SHA256
[ ] HTTP 200
[ ] resultado ACCEPTED
[ ] TelemetryEvent creado
[ ] MetricReading creadas
[ ] pluviómetro visible en mapa
[ ] variable visible en gráfico
[ ] calibración y evidencia archivadas
```

Un sensor no está terminado si solo se ve correctamente por Serial.

## Pruebas offline y deuda conocida

El HIL actual no implementa store-and-forward. El firmware productivo deberá diseñar posteriormente:

- detección de pérdida de red;
- buffer con capacidad y política definidas;
- reintentos con backoff;
- persistencia ante corte de energía;
- conservación de identidad de muestra;
- deduplicación;
- recuperación después de reinicio;
- borrado solo después de confirmación segura (`ACCEPTED` o `DUPLICATE`, según la arquitectura final).

En este handoff se prueba y documenta la deuda; no se implementa.

## Paquete de evidencia esperado

- informe de cada prueba con fecha UTC;
- logs Serial sanitizados;
- JSON sanitizado sin firma/secretos reutilizables;
- respuesta de la API;
- captura del dashboard;
- tabla de calibración;
- versión del firmware y hash/commit;
- lista de fallas conocidas.
