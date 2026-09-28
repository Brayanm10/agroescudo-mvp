# 01 - Arquitectura de integración

## Cadena funcional requerida

```text
Sensores físicos
      -> ESP32
      -> comunicación
      -> ingesta AgroEscudo
      -> TelemetryEvent
      -> MetricReading
      -> dashboard Pluviometría
```

El hardware es responsable de medir, convertir, identificar y transmitir. AgroEscudo autentica el lote, valida el contrato, deduplica, normaliza y presenta los datos.

## HIL actual validado

```text
ESP32 -> WiFi -> HTTPS/HTTP de banco -> API AgroEscudo -> base de datos -> dashboard
```

El HIL confirma que el ESP32 puede:

- sincronizar tiempo mediante NTP;
- construir JSON compatible;
- calcular SHA256 del cuerpo y HMAC-SHA256;
- enviar los seis canales;
- recibir HTTP 200 con `ACCEPTED`;
- hacer visible la lectura en el dashboard.

No presenta sensores reales y genera valores sintéticos. No debe copiarse sin revisión como firmware definitivo.

## Arquitectura futura posible

```text
Nodo de sensores -> radio/LoRa -> gateway -> HTTPS -> nube AgroEscudo
```

Esta evolución puede separar la adquisición del transporte a Internet. No está implementada en este cierre y no cambia el contrato de métricas que recibe AgroEscudo.

## Fronteras de responsabilidad

| Componente | Responsabilidad |
|---|---|
| Sensor | Producir una señal física repetible y documentada. |
| ESP32 | Adquirir, filtrar, convertir, fechar, identificar y empaquetar. |
| Comunicación | Transportar sin alterar identidad, tiempo ni unidades. |
| Ingesta | Autenticar, validar, deduplicar y clasificar. |
| `TelemetryEvent` | Representar una muestra aceptada con identidad y tiempo. |
| `MetricReading` | Guardar cada métrica canónica asociada a su canal. |
| Dashboard | Mostrar mapa, estado, valores e histórico. |

## Criterio de cierre

Una lectura por Serial no demuestra integración. La cadena se considera validada únicamente cuando el evento real completa:

```text
sensor -> ESP32 -> JSON -> HMAC -> HTTP 200 -> ACCEPTED -> DB -> mapa -> gráfico
```
