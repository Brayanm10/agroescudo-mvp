# 17. Faltantes para final

Estado del documento: BORRADOR CONTROLADO  
Fecha de auditoria: 2026-07-02

## Faltantes para piloto comercial real

### Hardware e IoT

| Faltante | Prioridad | Estado |
|---|---|---|
| Definir placa exacta de nodo y gateway | P0 | PENDIENTE |
| Confirmar pinout real | P0 | PENDIENTE |
| Compilar firmware en toolchain final | P0 | NO VERIFICADO |
| Probar LoRa en banco | P0 | NO VERIFICADO |
| Probar gateway con internet intermitente | P0 | NO VERIFICADO |
| Medir autonomia de bateria | P1 | PENDIENTE |
| Procedimiento de instalacion fisica | P1 | PENDIENTE |

### Cloud y datos

| Faltante | Prioridad | Estado |
|---|---|---|
| Confirmar Render/Neon/Vercel activos | P0 | NO VERIFICADO EN ESTA FASE |
| Ejecutar migraciones contra staging PostgreSQL | P0 | NO VERIFICADO |
| Ejecutar backup/restore | P0 | NO VERIFICADO |
| Rotar secrets demo | P0 | PENDIENTE |
| Configurar CORS final | P0 | PENDIENTE |
| Plan activo para evitar sleep | P1 | PENDIENTE |

### Producto

| Faltante | Prioridad | Estado |
|---|---|---|
| Smoke de flujo admin completo | P0 | PENDIENTE |
| Smoke tecnico completo | P0 | PENDIENTE |
| Smoke cliente completo | P0 | PENDIENTE |
| Validar PDF con datos reales | P0 | PENDIENTE |
| Reemplazar seeds demo en entorno productivo | P0 | PENDIENTE |
| Guia de soporte para cliente | P1 | BORRADOR |

### Seguridad

| Faltante | Prioridad | Estado |
|---|---|---|
| Escaneo final de secretos | P0 | PENDIENTE |
| Politica de privacidad minima | P1 | PENDIENTE |
| Consentimiento WhatsApp | P1 | PENDIENTE |
| Auditoria de usuarios admin | P2 | PROPUESTO |

## Lo que no debe agregarse antes del piloto

- Blockchain.
- Marketplace.
- Scoring financiero.
- Integraciones bancarias.
- App movil iOS si no hay demanda inmediata.
- IA generativa sin control operativo.
- Automatizacion de seguros.

## Decisiones cerradas

| Decision | Estado |
|---|---|
| FastAPI como API central | CONFIRMADO |
| SQL como fuente de verdad | CONFIRMADO |
| Firebase solo futuro para push | CONFIRMADO |
| Web para administracion avanzada | CONFIRMADO |
| Flutter para operacion movil | CONFIRMADO |
| HTTPS batch gateway como transporte cloud | CONFIRMADO |
| MQTT como alternativa futura | PROPUESTO |

## Ruta recomendada de cierre

1. Completar documentacion fuente.
2. Generar PDF maestro.
3. Ejecutar pruebas completas.
4. Resolver P0.
5. Crear paquete demo comercial.
6. Ejecutar piloto controlado con un sitio.
7. Medir resultados 60-90 dias.

