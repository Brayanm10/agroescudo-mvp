# 01. Arquitectura general AgroEscudo

Estado del documento: BORRADOR CONTROLADO  
Fecha de auditoria: 2026-07-02  
Fuente principal: inspeccion del repositorio local `C:\Users\braya\Documents\AgroEscudo`

## Resumen ejecutivo

AgroEscudo es una plataforma B2B agri-tech para monitoreo postcosecha, gestion de riesgo operativo y trazabilidad en silos, galpones y centros de acopio. La arquitectura confirmada combina:

- Backend FastAPI como API central y fuente de verdad.
- Base de datos SQL con SQLite para desarrollo local y PostgreSQL para produccion.
- Frontend web Next.js para administracion, operacion, reportes y demo comercial.
- App Flutter Android para consulta operativa en campo.
- Firmware ESP32/LoRa en estructura separada para nodo y gateway.
- Reportes PDF corporativos generados desde backend.
- Notificaciones WhatsApp, Telegram, push y dry-run en modo controlado.

La plataforma ya no debe tratarse como una demo aislada. El repositorio contiene componentes de piloto comercial, pero algunas capacidades dependen de credenciales, despliegue cloud o pruebas fisicas y deben quedar marcadas como no verificadas cuando corresponda.

## Clasificacion global de evidencia

| Area | Estado | Evidencia |
|---|---|---|
| Backend FastAPI | CONFIRMADO EN CODIGO | `backend/app/main.py` registra routers principales y health checks. |
| Base SQL local | CONFIRMADO EN CODIGO | `DATABASE_URL` soporta SQLite por defecto. |
| PostgreSQL productivo | CONFIGURADO PERO NO VERIFICADO EN ESTA FASE | `psycopg` y URL SQLAlchemy estan soportados. Requiere entorno productivo activo. |
| Frontend Next.js | CONFIRMADO EN CODIGO | `frontend/` contiene app, API client, componentes y reportes. |
| App Flutter Android | CONFIRMADO EN CODIGO | `mobile/` contiene app con `API_BASE_URL`, secure storage y pantallas operativas. |
| Landing | CONFIRMADO EN CODIGO | `landing/` existe con Next.js. No se ejecuto build en esta fase documental. |
| IoT batch HMAC | CONFIRMADO EN CODIGO | `/api/iot/v1/ingest/batch` y servicios HMAC existen. |
| Ingestion sensor legacy | CONFIRMADO EN CODIGO | `POST /api/readings` se conserva para dispositivos con token. |
| Firmware LoRa | CONFIGURADO PERO NO VERIFICADO | Hay estructura `firmware/`, pero no se probo hardware ni compilacion fisica. |
| WhatsApp/Telegram reales | CONFIGURADO PERO NO VERIFICADO | Hay variables y flujo dry-run; envio real requiere tokens externos. |
| IA real | CONFIGURADO COMO OPCIONAL | El asistente puede funcionar con reglas; LLM depende de `OPENAI_API_KEY` y flag. |

## Vista de arquitectura

```mermaid
flowchart LR
    subgraph Campo["Campo / Planta"]
        Node["Nodo ESP32 LoRa\nTemperatura, humedad, bateria"]
        Gateway["Gateway ESP32/T-Beam\nLoRa + WiFi/4G"]
    end

    subgraph Cloud["Plataforma AgroEscudo"]
        API["Backend FastAPI\nJWT, RBAC, IoT, alertas"]
        DB[("SQL Database\nSQLite dev / PostgreSQL prod")]
        PDF["ReportLab PDF\nReporte tecnico semanal"]
        Notify["Notificaciones\nDry-run / WhatsApp / Telegram / Push"]
    end

    subgraph Apps["Experiencias de usuario"]
        Web["Dashboard web Next.js\nAdmin, tecnico, cliente"]
        Mobile["App Android Flutter\nOperacion movil"]
        Landing["Landing publica\nComercial"]
    end

    Node -->|"Paquete LoRa"| Gateway
    Gateway -->|"HTTPS batch + HMAC"| API
    API --> DB
    API --> PDF
    API --> Notify
    Web -->|"REST + JWT"| API
    Mobile -->|"REST + JWT"| API
    Landing -.->|"Enlaces comerciales"| Web
```

## Flujo operativo principal

```mermaid
sequenceDiagram
    participant Sensor as Sensor / Gateway
    participant API as FastAPI
    participant DB as Base SQL
    participant Alert as Motor de alertas
    participant User as Usuario web/mobile
    participant PDF as Reporte PDF

    Sensor->>API: POST /api/readings o /api/iot/v1/ingest/batch
    API->>API: Valida token o firma HMAC
    API->>DB: Guarda lectura valida
    API->>Alert: Evalua umbrales
    Alert->>DB: Crea alerta si corresponde
    User->>API: Consulta dashboard, alertas y lecturas
    User->>API: Registra bitacora o mantenimiento
    User->>PDF: Solicita reporte semanal
    PDF->>DB: Lee metricas, alertas y bitacora
    PDF-->>User: Archivo PDF corporativo
```

## Flujo de autenticacion y roles

```mermaid
flowchart TD
    Login["POST /api/auth/login"] --> Token["JWT bearer token"]
    Token --> Me["GET /api/me"]
    Me --> Role{"Rol"}
    Role --> Admin["admin\nAcceso total operativo y administrativo"]
    Role --> Tech["technician\nSilos asignados, alertas, bitacora, mantenimiento"]
    Role --> Client["client\nSolo sus silos, evidencias y reportes"]

    Admin --> AdminRoutes["/api/admin/*"]
    Tech --> ScopedRoutes["Rutas operativas filtradas por storage unit"]
    Client --> ClientRoutes["Lectura, reportes y evidencia de su unidad"]
```

Estado: CONFIRMADO EN CODIGO.  
Archivos relacionados:

- `backend/app/api/routes/auth.py`
- `backend/app/api/deps.py`
- `backend/app/models.py`
- `frontend/app/page.tsx`
- `mobile/lib/core/app_store.dart`

## Flujo IoT HMAC batch

```mermaid
sequenceDiagram
    participant GW as Gateway
    participant API as /api/iot/v1/ingest/batch
    participant DB as SQL
    participant Alert as Alert service

    GW->>GW: Construye JSON batch
    GW->>GW: Calcula body_hash
    GW->>GW: Firma HMAC-SHA256 con credencial activa
    GW->>API: Headers X-Agro-* + body
    API->>API: Valida timestamp, nonce, gateway y firma
    API->>DB: Registra batch y eventos
    loop Por lectura
        API->>API: Valida rango, dispositivo y duplicado
        API->>DB: Guarda lectura aceptada
        API->>Alert: Evalua umbral
    end
    API-->>GW: accepted / duplicate / rejected_* / temporary_error
```

Estado: CONFIRMADO EN CODIGO para backend.  
Estado: CONFIGURADO PERO NO VERIFICADO para firmware/gateway fisico.

## Flujo de notificaciones

```mermaid
flowchart LR
    Alert["Alerta creada"] --> Pref["Preferencias del usuario"]
    Pref --> Delivery["notification_deliveries"]
    Delivery --> DryRun{"NOTIFICATIONS_DRY_RUN"}
    DryRun -->|"true"| Sim["Registro simulado\ndry_run"]
    DryRun -->|"false"| Real{"Canal configurado"}
    Real -->|"WhatsApp"| WA["Meta WhatsApp Cloud API"]
    Real -->|"Telegram"| TG["Telegram Bot API"]
    Real -->|"Push"| FCM["FCM futuro/configurado"]
```

Estado: CONFIRMADO EN CODIGO para tabla y dry-run.  
Estado: NO VERIFICADO para envio real, porque requiere credenciales externas.

## Flujo de reporte PDF

```mermaid
flowchart TD
    UI["Web o Flutter"] --> API["GET /api/reports/weekly/pdf?storage_unit_id="]
    API --> RBAC["Valida JWT y acceso al silo"]
    RBAC --> Query["Consulta empresa, sitio, silo, lecturas, alertas y bitacora"]
    Query --> Render["ReportLab genera PDF"]
    Render --> Download["Archivo descargable"]
```

Estado: CONFIRMADO EN CODIGO.  
La verificacion visual final del PDF debe registrarse en `docs/REPORTE_DE_TESTS.md` cuando se ejecute el paquete completo de pruebas.

## Despliegue previsto

```mermaid
flowchart LR
    Dev["Local dev\nSQLite + localhost"] --> Render["Render\nFastAPI"]
    Render --> Neon[("Neon PostgreSQL")]
    Vercel["Vercel\nDashboard web"] --> Render
    APK["APK Flutter\nAPI_BASE_URL publico"] --> Render
    Sensor["Gateway IoT"] --> Render
```

Estado: CONFIGURADO PERO NO VERIFICADO EN ESTA FASE.  
Las URLs publicas deben verificarse antes de incluirlas como vigentes en un PDF final.

## Principios de arquitectura

- FastAPI es la unica fuente de verdad operativa.
- Firebase no almacena datos principales.
- SQLite es solo desarrollo local; PostgreSQL es la opcion productiva.
- `POST /api/readings` se mantiene compatible con sensores existentes.
- El batch IoT con HMAC es el camino mas robusto para gateway.
- La administracion avanzada se mantiene en web.
- Flutter es principalmente consulta, evidencia, acciones operativas y PDF.
- WhatsApp/Telegram deben permanecer en dry-run hasta configurar tokens reales y validar consentimiento.
- Las pruebas fisicas LoRa y gateway deben documentarse como no verificadas hasta ejecutarse con hardware.

## Riesgos arquitectonicos abiertos

| Riesgo | Estado | Mitigacion |
|---|---|---|
| Hardware LoRa no probado fisicamente | NO VERIFICADO | Ejecutar pruebas con nodo y gateway reales antes del piloto. |
| Credenciales externas no configuradas | PENDIENTE | Configurar Render/Vercel/Neon/WhatsApp/Telegram sin versionar secretos. |
| Render Free puede dormir | RIESGO | Usar plan activo para demo comercial o health warm-up controlado. |
| Envio real de WhatsApp requiere plantillas aprobadas | PENDIENTE | Mantener dry-run hasta validacion con Meta. |
| Calidad de datos IoT depende de calibracion | PENDIENTE | Procedimiento de instalacion y validacion de sensores. |

