# Auditoria Final AgroEscudo

Fecha: 2026-07-01  
Rama: `audit/final-pilot-readiness`  
Commit base inspeccionado: `b722e62 Prepare AgroEscudo pilot release`

## Veredicto

**LISTO PARA DEMO CONTROLADA**

No se declara listo para piloto comercial completo porque la cadena fisica Nodo LoRa -> Gateway T-Beam -> nube no fue probada con hardware real. El backend, web y movil pueden operar una demo/piloto controlado con datos reales de API, pero IoT fisico queda como **NO VERIFICADO - requiere prueba fisica o credenciales externas**.

## Estado Por Componente

| Componente | Estado | Evidencia | Riesgos | Accion |
| --- | --- | --- | --- | --- |
| Backend FastAPI | Verificado localmente y health publico | pytest completo y `https://agroescudo-api.onrender.com/health` 200 | Rate limiting formal pendiente | Mantener tests por cambio |
| PostgreSQL/Alembic | Verificado por migraciones locales | `alembic upgrade head` | Neon real no verificado desde esta maquina | Validar en Render/Neon |
| Dashboard Next.js | Verificado por build y URL publica | `npm.cmd run build` y `https://agroescudobo.vercel.app` 200 | Flujo admin completo requiere smoke manual con sesion | Ejecutar checklist web |
| Flutter Android | Parcial | API por `API_BASE_URL`; credenciales visibles retiradas | Build APK depende SDK local | Ejecutar checklist movil |
| Landing | Build y URL publica verificados | `npm run build` y `https://agroescudo.vercel.app` 200 | Enlaces sociales externos sin prueba funcional profunda | Smoke manual |
| Firmware LoRa | No verificado fisicamente | Scaffold `firmware/` creado | Pinout, energia AXP2101, alcance y cola durable requieren banco | Prueba de laboratorio |
| IoT batch API | Verificado localmente | Tests HMAC/replay/idempotencia | Credenciales gateway piloto deben provisionarse | Rotacion y monitoreo |

## Problemas Criticos Encontrados

### P0 - bloquea piloto comercial

- No habia firmware versionado ni pruebas fisicas de Nodo LoRa/Gateway.
- No existia endpoint batch gateway -> backend con HMAC e idempotencia.

### P1 - alto

- Flutter mostraba credenciales/autollenado de demo en login.
- Documentacion no contenia procedimientos completos de backup, rollback, seguridad IoT y recuperacion.

### P2 - medio

- No hay rate limit persistente para login ni ingestion IoT.
- Verificacion de servicios Render/Vercel/Neon depende de credenciales externas.
- El seed local conserva contrasenas iniciales internas para poder iniciar el piloto en desarrollo. No aparecen en UI ni docs de entrega, pero deben rotarse antes de compartir cualquier ambiente.

### P3 - bajo

- Algunos nombres internos de rutas siguen usando `demo` para la presentacion comercial controlada.

## Cambios Realizados

- Se agrego ingestion IoT batch con HMAC, anti-replay, idempotencia y resultados por lectura.
- Se agregaron tablas IoT y migracion Alembic.
- Se agregaron tests de ingestion IoT.
- Se removieron credenciales visibles del login Flutter.
- Se creo scaffold firmware para nodo T3 y gateway T-Beam.
- Se crearon documentos operativos y de auditoria.

## Pruebas No Ejecutadas

- Prueba fisica LoRa: **NO VERIFICADO - requiere hardware**.
- Envio real WhatsApp/Telegram/FCM: **NO VERIFICADO - requiere credenciales externas**.
- Smoke real Render/Vercel/Neon: **NO VERIFICADO - requiere acceso/red y entorno desplegado**.
- Firma release Android con keystore productivo: **NO VERIFICADO - requiere keystore**.
