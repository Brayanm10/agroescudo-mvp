# Arquitectura Del Sistema

```mermaid
flowchart LR
  Node["Nodo ESP32/T3"] --> Radio["LoRa P2P binario"]
  Radio --> Gateway["Gateway ESP32/T-Beam"]
  Gateway --> Queue["Cola durable local"]
  Queue --> HTTPS["HTTPS batch + HMAC"]
  HTTPS --> API["FastAPI Render"]
  API --> DB["PostgreSQL Neon"]
  API --> Alerts["Motor de alertas"]
  API --> Reports["Reportes PDF"]
  API --> Web["Dashboard Next.js"]
  API --> Mobile["App Flutter"]
```

## Servicios

- Backend: FastAPI, SQLAlchemy 2, Alembic, JWT, ReportLab.
- Base local: SQLite para desarrollo.
- Base produccion: PostgreSQL compatible con Neon.
- Web: Next.js, React, TypeScript, Tailwind, Recharts.
- Movil: Flutter Android con `API_BASE_URL`.
- IoT: LoRa P2P nodo/gateway, HTTPS por lotes hacia FastAPI.

## Fuente De Verdad

FastAPI + SQL son la fuente de verdad. Firebase no almacena datos operativos. MQTT queda como alternativa futura, no como transporte principal del piloto.

