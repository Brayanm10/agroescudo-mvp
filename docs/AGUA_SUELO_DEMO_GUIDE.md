# Piloto Agua y Suelo — preparación y activación

Fecha: 9 de octubre de 2026. Cuenta confirmada: **sueloyagua@gmail.com**. Empresa visible: **SUELO Y AGUA**, rol visible: cliente.

## Estado comprobado y frontera productiva

La sesión existente accede a [AgroEscudo](https://agroescudobo.vercel.app) y al [equipo Pluvi1, ID web 20](https://agroescudobo.vercel.app/pluviometria/pluviometros/20?variable=RAIN_DELTA_MM&period=24h), en predio `sueloyagua.com` (ID web 8), parcela `Piloto1`. El período 24 h abierto no contiene lecturas. Esto no demuestra que el equipo sea exclusivamente DEMO ni autoriza convertirlo.

Se prepara un equipo separado. `DEMO-AGUA-SUELO-P01` y `DEMO-AGUA-SUELO-GW01` son **IDs propuestos**, no identidades ya creadas en Neon. El enlace definitivo requiere el ID numérico que devuelva el aprovisionamiento. No confundirlo con el identificador físico.

No se dispone de DATABASE_URL productivo ni RENDER_API_KEY/RENDER_SERVICE_ID operativos en el formulario local configurado. La sesión web es de cliente y no permite aprovisionar gateway, equipo o módulos. Las operaciones siguientes requieren un operador autorizado dentro del entorno productivo. No copiar secretos al chat.

## Aprovisionamiento acotado

El código existente permanece. El nuevo comando `backend/scripts/prepare_agua_suelo_demo.py` inspecciona sin escribir por defecto. Requiere la cuenta y empresa existentes; no crea usuarios ni empresas y no cambia la contraseña. Con `--execute` crea una estación y parcela virtuales DEMO, un rain_gauge `RAIN_GAUGE_BASE`, seis canales, gateway dedicado, credencial cifrada y vínculo IoT. Asigna la parcela al cliente y habilita PLUVIOMETRY solo en su empresa si hace falta.

Ejecutar con el entorno habitual del backend, usando su DATABASE_URL y JWT_SECRET configurados de forma privada, desde el repositorio:

```powershell
backend/.venv/Scripts/python.exe backend/scripts/prepare_agua_suelo_demo.py --email sueloyagua@gmail.com
```

La inspección devuelve company_id, user_id, permisos y dispositivos/eventos de esa empresa. Si falta la cuenta, detener y usar el flujo administrativo de creación/invitación existente. No crear una segunda empresa por suposición.

Antes de escribir, comprobar la revisión Alembic, crear un respaldo **pg_dump recuperable**, verificar el procedimiento de restauración y guardar su SHA256 fuera de Git. El snapshot portátil existente no sustituye este requisito de recuperación. El script compara revisión de DB contra las revisiones del código y verifica el checksum del archivo suministrado; el operador debe confirmar que el respaldo pertenece a la base objetivo, es reciente y fue probado.

Usar coordenadas y referencia verificadas de una ubicación **de demostración autorizada**, nunca una supuesta ubicación del cliente. El polígono generado alrededor del punto es virtual, no catastral. La latitud/longitud y referencias son obligatorias. Los valores entre `<...>` siguientes deben reemplazarse; no son un comando ejecutable literal:

```powershell
backend/.venv/Scripts/python.exe backend/scripts/prepare_agua_suelo_demo.py `
  --email sueloyagua@gmail.com --execute `
  --company-id <ID_EMPRESA_CONFIRMADO> --actor-id <ID_ADMIN_ACTIVO> `
  --latitude <LAT_VERIFICADA> --longitude <LON_VERIFICADA> `
  --location-reference "<REFERENCIA_DEMO_VERIFICADA>" `
  --node-id <NODE_ID_LIBRE_CONFIRMADO> `
  --backup-file <RUTA_RESPALDO> --backup-sha256 <SHA256_RESPALDO> `
  --secret-output var/agua-suelo-demo-secrets.h
```

El archivo de salida debe ser nuevo e ignorado por Git. El secreto nunca se imprime. En Windows el comando restringe su ACL al operador mediante icacls antes de escribir; si falla, elimina su archivo nuevo y no confirma DB. En sistemas POSIX se crea con modo 0600. Copiarlo como `secrets.h` en el sketch y completar WiFi local. Reejecutar el comando reutiliza exclusivamente el equipo dedicado compatible; no rota claves ni sobrescribe archivos. Si hay un ID ocupado por un equipo real/otra empresa o configuración incompatible, se bloquea sin convertirlo.

## Histórico sintético

Agregar a la ejecución `--history-start <INICIO_UTC_FIJO>` y `--history-days 7`. El inicio debe incluir timezone, y los siete días deben estar completamente en el pasado. Mantener **exactamente el mismo inicio** al reintentar. No desplazar la ventana para repetir un historial solapado.

Se generan hasta 10 080 muestras de un minuto, seis métricas por muestra, mediante el servicio canónico con HMAC, validación y deduplicación existentes. Identidad determinista por equipo + inicio + secuencia; nonce y lote únicos por request. No hay borrados ni seed general. La lluvia es incremental, con días secos y eventos delimitados; la dirección usa la media circular existente en consultas. El histórico no cambia last_seen del equipo ni genera notificaciones/alertas de riesgo para mediciones simuladas. El marcador DEMO persistente está en model_version; la ingesta no permite que el firmware cambie esa clasificación.

Los lotes confirmados se conservan si falla uno posterior; repetir con el mismo inicio produce DUPLICATE para los lotes previos. Rechazo/cuarentena detiene el proceso. La ingesta productiva del histórico queda pendiente hasta contar con el acceso y configuración señalados.

## Software y despliegue

Cambios mínimos: verificación gateway-equipo/empresa antes de aceptar o informar un duplicado, flag calculado is_demo en mapa, avisos visibles, refresco de mapa/histórico cada 30 segundos y exclusión de alertas productivas para este modelo DEMO dedicado. No se añaden tablas ni migraciones. Se preservan rutas, métricas, unidades, agregación y RBAC.

Antes del despliegue del backend revisar vínculos IotDevice.gateway_id: los equipos deben estar asignados al gateway que los firma. La validación cierra la aceptación cruzada de otro gateway; no modificar vínculos reales automáticamente para superar un rechazo. Desplegar backend y frontend del commit revisado mediante los flujos existentes; no ejecutar RUN_SEED_ON_START.

La publicación del código no equivale a despliegue. Ver el reporte de esta entrega para distinguir commit, publicación y activación real.

## Uso del ESP32

Seguir [README del sketch](../hardware/pluviometry/esp32_agua_suelo_demo/README.md). Placa **ESP32 Dev Module**, core ESP32 3.x, ArduinoJson 7, Monitor Serial **115200**. Abrir el sketch en carpeta `AgroEscudo_AguaSuelo_Demo`, incluir los tres headers y secrets.h privado. Frecuencia inicial: una muestra/60 s.

Comandos: `status`, `normal`, `dry`, `rain_light`, `rain_heavy`, `storm`, `battery_low`, `auto`; `retry` después de corregir un rechazo. El escenario afecta solo la siguiente muestra nueva. Confirmar WiFi, NTP, HTTPS, HTTP 200 y canonical_status ACCEPTED/DUPLICATE. No interpretar HTTP 200 por sí solo como aceptación.

## QA y aceptación comercial

1. Entrar con la cuenta confirmada y comprobar acceso Pluviometría sin ampliar permisos.
2. Abrir la URL DEMO devuelta por el comando y confirmar aviso de datos simulados en mapa, popup e histórico.
3. Confirmar predio DEMO, parcela virtual, punto autorizado y satélite MapTiler.
4. Ver las seis métricas y períodos 1 h/24 h/7 d/30 d. Treinta días puede contener solo siete días de datos; no inventar lecturas faltantes.
5. Verificar día local America/La_Paz y tooltips UTC-4 mediante timezone, sin restar horas en los timestamps.
6. Cambiar escenarios y esperar próxima muestra y refresco de 30 s. La batería baja es progresiva; lluvia normal/dry debe ser cero.
7. Cortar WiFi solo del ESP32: delayed después de 2 min, offline después de 6; reconectar y comprobar muestra pendiente sin duplicar lluvia.
8. Probar timeout, reinicio con pendiente, duplicado y rechazo de dispositivo no asignado. Comprobar que otras empresas no ven la demo y que el gateway DEMO no escribe en sus equipos.
9. Revisar móvil y escritorio, mapa y gráficas sin cortes. Guardar evidencia sanitizada y distinguir pruebas de software de pruebas físicas.

## Acciones del propietario

- Rotar la contraseña compartida anteriormente mediante recuperación/cambio seguro en AgroEscudo; el código no la usa ni la cambia.
- Facilitar una sesión administrativa o ejecutar el aprovisionamiento desde el backend productivo con respaldo verificado. No enviar credenciales por chat.
- Confirmar ubicación DEMO y node_id libre; no usar Pluvi1 como fuente simulada.
- Cargar secrets.h dedicado y firmware en el ESP32 elegido, verificar Serial y web y registrar evidencia física.
