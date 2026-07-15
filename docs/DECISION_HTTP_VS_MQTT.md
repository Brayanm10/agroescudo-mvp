# Decision HTTP vs MQTT

Decision para piloto: **HTTPS POST + JSON por lotes**.

## Razones

- Backend FastAPI ya existe.
- Facilita pruebas con curl y pytest.
- Evita operar broker adicional.
- Reduce superficie operativa.
- Permite idempotencia por lectura.
- Maneja conectividad intermitente con lotes.
- Permite respuestas individuales `accepted`/`duplicate`.

## MQTT Como Futuro

MQTT seria util cuando existan muchos gateways conectados permanentemente, telemetria frecuente o necesidad de comandos bidireccionales.

Requeriria:

- broker;
- ACL;
- certificados;
- gestion de sesiones;
- QoS;
- observabilidad;
- mantenimiento adicional.

## Aclaracion

HTTP o MQTT son transporte. JSON es formato de payload.

