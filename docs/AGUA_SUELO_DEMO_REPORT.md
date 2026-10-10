# Agua y Suelo — reporte de implementación A–T

Fecha: 9 de octubre de 2026, America/La_Paz.

**Resultado: software DEMO implementado y compilado; activación productiva pendiente de acceso administrativo/backend, respaldo y prueba con el ESP32.** No se declara cumplida todavía la demostración física extremo a extremo.

| Punto | Evidencia y estado |
|---|---|
| A. Cuenta y empresa | Sesión productiva verificada: `sueloyagua@gmail.com`, SUELO Y AGUA, rol cliente. El propietario corrigió el correo del pedido original. No se crearon usuarios ni empresas. ID interno de empresa pendiente de inspección administrativa. |
| B. Equipo existente | `Pluvi1`, ID web 20; visible en mapa. Sin conexión y sin lecturas en las vistas abiertas. No confirmado como exclusivamente DEMO; conservado. |
| C. Device ID físico DEMO | Propuesto `DEMO-AGUA-SUELO-P01`. Todavía no creado/aprovisionado en Neon. El script registra y devuelve identidad física y DB ID por separado. |
| D. Predio/parcela | Existentes verificados: `sueloyagua.com`, ID web 8; `Piloto1`. La implementación prepara una estación y parcela virtuales DEMO separadas, con coordenadas verificadas obligatorias. No se inventó ubicación del cliente. |
| E. PLUVIOMETRY | Visible y accesible para la cuenta confirmada. El script habilita exclusivamente su empresa si estuviera deshabilitada; no se modificó ningún permiso productivo en esta entrega. |
| F. Firmware | `hardware/pluviometry/esp32_agua_suelo_demo/AgroEscudo_AguaSuelo_Demo.ino`, con demo_weather.h, trusted_root.h y secrets.example.h. Compilación real ESP32 Dev Module, Arduino core 3.3.7, ArduinoJson 7.4.3. |
| G. GitHub | La publicación del commit/archivo se informa en el mensaje final con permalink verificado; no confundir con despliegue. |
| H. Arduino IDE | Procedimiento completo en README del sketch: carpeta coincidente, ESP32 Dev Module, ArduinoJson 7, secretos locales, puerto USB identificado, Verificar/Subir y Serial 115200. |
| I. HMAC | Proceso seguro implementado: gateway dedicado, secreto cifrado en DB, salida local ignorada con permisos restringidos, sin stdout. No se aprovisionó credencial productiva. |
| J. Métricas | Las seis métricas/canales/unidades oficiales. Temperatura/humedad/viento/batería con aproximación gradual; dirección circular FROM; lluvia como intensidad × intervalo, períodos secos y eventos. Calidad VALID indica validez del contrato, no presencia de sensor físico. |
| K. Escenarios | status, normal, dry, rain_light, rain_heavy, storm, battery_low, auto; retry para recuperar después de corregir un rechazo. |
| L. Respuesta API | Resultado real del servicio canónico en SQLite aislado: ACCEPTED y, con otro lote/nonce para la misma identidad, DUPLICATE. Ejemplo sanitizado debajo. No es respuesta productiva ni evidencia de envío físico. |
| M. Ingesta | Pruebas de software demuestran HMAC, esquema, persistencia de seis métricas, deduplicación y rechazo de equipo ajeno. Ingesta desde ESP32 a producción pendiente. |
| N. Historial | Proceso idempotente implementado, 1..7 días completos, hasta 10 080 muestras/minuto. Canonical ingestion, sin borrar datos, con inicio fijo y protección contra ventanas sintéticas solapadas. Prueba de un día: 1440 ACCEPTED; reejecución: 1440 DUPLICATE. No ejecutado en Neon. |
| O. Mapa/gráficas | Mapa satelital productivo de la cuenta verificado visualmente con marcador Pluvi1. Avisos DEMO en mapa/popup/histórico verificados por tests; build pasa. Refresco cada 30 s conserva cámara y actualiza popup. Datos/QA visual de la nueva demo y responsive con su historial siguen pendientes de activación. |
| P. Enlace DEMO | Aún no existe un ID DB DEMO productivo; no se inventa URL. El script devuelve la ruta real `/pluviometria/pluviometros/{id}` tras aprovisionamiento. El equipo 20 es el existente, no el nuevo DEMO. |
| Q. Tests/compilación | Backend completo: 221 passed. Suite DEMO final adicional: 10 passed. Frontend: 88 passed, lint y build. Firmware final: 1 072 324 bytes flash (81%), 48 920 bytes variables globales (14%). TLS de la API validado con las raíces incluidas. Warnings existentes de dependencias/teardown, sin fallos. |
| R. Git/despliegue | Cambios acotados en rama codex/agua-suelo-demo. Documentos preexistentes ADEPLEC y guía administrativa ajenos a este pedido preservados y excluidos del commit. Despliegue Render/Vercel productivo no ejecutado: falta acceso Render/backend y preflight productivo. |
| S. Integridad | Ninguna escritura productiva, cambio de contraseña, borrado ni seed general. Las demás empresas y equipos reales permanecieron intactos. Tests comprueban conservación del equipo original y aislamiento del gateway. |
| T. Pendientes manuales | Sesión/admin o ejecución segura en backend; confirmar company_id/admin/node_id y ubicación DEMO; respaldo recuperable verificado; despliegue revisado; aprovisionar credencial/historial; WiFi/carga/prueba ESP32; rotar contraseña expuesta mediante procedimiento seguro. |

## Evidencia canónica real en entorno aislado

Respuesta obtenida del servicio `ingest_gateway_batch` usando un gateway dedicado creado en una base SQLite de pruebas y una firma HMAC válida. No se utilizó cuenta ni contraseña productiva. No se etiqueta como prueba física ni HTTP productivo.

```json
{"batch_id":"demo-37651f4099df78e7a5e7dd618e22e57c","results":[{"device_id":"DEMO-AGUA-SUELO-P01","boot_id":811,"sequence":0,"status":"accepted","detail":null,"canonical_status":"ACCEPTED"}]}
```

Reintento de la misma muestra con nuevo lote y nonce:

```json
{"batch_id":"demo-18b282688ec94b87212d167ded4247a6","results":[{"device_id":"DEMO-AGUA-SUELO-P01","boot_id":811,"sequence":0,"status":"duplicate","detail":"Reading already stored","canonical_status":"DUPLICATE"}]}
```

## Bloqueo productivo concreto

La sesión abierta es de **cliente**. El formulario local operativo de integraciones existe, pero no contiene DATABASE_URL, RENDER_API_KEY ni RENDER_SERVICE_ID operativos. No se usó la contraseña expuesta para elevar acceso. No se comprobó la revisión Alembic real ni un respaldo recuperable reciente de producción; no se realizaron escrituras.

La nueva verificación de gateway debe desplegarse después de revisar los vínculos productivos: cada IotDevice debe estar asignado al gateway que firma. No se reasignan equipos automáticamente.

## Enlaces de entrega

- [Plataforma productiva](https://agroescudobo.vercel.app).
- [Mapa existente verificado](https://agroescudobo.vercel.app/pluviometria?predio=8).
- [Pluvi1 existente verificado](https://agroescudobo.vercel.app/pluviometria/pluviometros/20?variable=RAIN_DELTA_MM&period=24h).
- [Firmware](../hardware/pluviometry/esp32_agua_suelo_demo/AgroEscudo_AguaSuelo_Demo.ino).
- [Guía de carga](../hardware/pluviometry/esp32_agua_suelo_demo/README.md).
- [Guía operativa](AGUA_SUELO_DEMO_GUIDE.md).

## Límites de la demostración

Se conserva una sola muestra durable y se pausa adquisición durante fallas. Los huecos son explícitos; no se fabrica lluvia de los minutos perdidos. Cold starts/timeouts se contemplan con backoff y firmas nuevas; reconexión/corte de energía deben validarse físicamente antes de presentar esta cadena como probada.

La clasificación DEMO pertenece a la configuración del equipo. Datos antiguos no hacen que aparezca online. Las mediciones de este modelo dedicado no generan alertas/notificaciones productivas. El dashboard reutiliza rutas, unidades, agregaciones y RBAC existentes.
