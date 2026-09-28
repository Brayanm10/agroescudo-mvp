# 05 - Plantilla de calibración

## Identificación de la sesión

| Campo | Valor |
|---|---|
| Dispositivo / Device ID | |
| Sensor y modelo | |
| Número de serie | |
| Variable / código métrico | |
| Unidad canónica | |
| Firmware | |
| Fecha y hora UTC | |
| Responsable | |
| Lugar / banco | |
| Temperatura y condiciones del ensayo | |
| Instrumento de referencia | |
| Certificado / fecha de calibración de referencia | |

## Registro de puntos

| Punto | Valor real | Valor sensor | Error absoluto | Error relativo (%) | Factor/offset aplicado | Repetición | Resultado |
|---:|---:|---:|---:|---:|---|---:|---|
| 1 | | | | | | 1 | |
| 2 | | | | | | 1 | |
| 3 | | | | | | 1 | |
| 4 | | | | | | 1 | |
| 5 | | | | | | 1 | |

Fórmulas de referencia:

```text
error absoluto = valor sensor - valor real
error relativo (%) = 100 * |error absoluto| / |valor real|
```

Cuando el valor real sea cero, informar error absoluto y no dividir por cero.

## Ensayo específico de lluvia

Realizar varios puntos, varias repeticiones y al menos una verificación de cero.

| Ensayo | Volumen/precipitación de referencia | Pulsos o lectura cruda | Delta calculado (mm) | Error | Repetible | Observación |
|---:|---:|---:|---:|---:|---|---|
| 1 | | | | | | |
| 2 | | | | | | |
| 3 | | | | | | |
| 4 | | | | | | |
| 5 | | | | | | |

Registrar también:

- superficie/colector utilizado para convertir volumen a milímetros;
- resolución mecánica o por pulso;
- tiempo de aplicación;
- pérdidas, salpicadura y drenaje;
- criterio de debounce/filtrado;
- comportamiento después de reinicio y overflow.

## Cierre de calibración

| Criterio | Resultado |
|---|---|
| Rango cubierto | |
| Número de repeticiones | |
| Error máximo observado | |
| Error medio | |
| Factor/offset aprobado | |
| Criterio de aceptación aplicado | |
| Aprobado / rechazado | |
| Firma responsable | |

La tolerancia final debe ser acordada con AgroEscudo según el sensor y el uso agronómico. Este documento no inventa una precisión que el fabricante o el ensayo no demuestren.
