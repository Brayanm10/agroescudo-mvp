# Arquitectura IoT

Objetivo del piloto:

```text
Nodo LoRa -> Gateway -> almacenamiento durable -> HTTPS batch -> FastAPI -> PostgreSQL -> dashboard/app
```

## Reglas

- LoRa usa paquete binario, no JSON.
- Gateway solo emite ACK despues de persistir.
- Gateway borra datos solo cuando backend responde `accepted` o `duplicate`.
- Gateway firma cada batch con HMAC-SHA256.
- Backend rechaza replay por nonce y lecturas duplicadas por `device_id + boot_id + sequence`.

## Flujo ACK

```mermaid
sequenceDiagram
  participant N as Nodo
  participant G as Gateway
  N->>G: Paquete binario AES-CCM
  G->>G: Validar magic/version/tamano
  G->>G: Autenticar y descifrar
  G->>G: Deduplicar
  G->>G: Persistir durablemente
  G-->>N: ACK
```

## Flujo Cloud

```mermaid
flowchart TD
  Pending["Lecturas pendientes"] --> Batch["Construir batch JSON"]
  Batch --> Sign["Firmar HMAC"]
  Sign --> Post["HTTPS POST"]
  Post --> Result["Resultado por lectura"]
  Result --> Delete["Eliminar accepted/duplicate"]
  Result --> Keep["Conservar errores temporales"]
```

## No Verificado

- Pinout real T3/T-Beam.
- Energia AXP2101.
- Alcance LoRa.
- Reinicio durante compactacion de cola.
- Certificado CA real instalado en firmware.

