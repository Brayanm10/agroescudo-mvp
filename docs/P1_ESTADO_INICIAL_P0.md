# P1 - Estado Inicial Y Compuerta P0

Fecha: 2026-07-23

Rama de trabajo: `feature/p1-pilot-operations`

## Alcance De La Compuerta

Antes de modificar logica P1 se revisaron:

- `docs/AUDITORIA_FINAL.md`;
- `docs/REPORTE_DE_TESTS.md`;
- `docs/TELEMETRIA_POR_NODO_Y_NIVEL.md`;
- `docs/CALIBRACION_VERSIONADA_Y_PRODUCTOS.md`;
- el prompt P1 de operacion profesional de primeros pilotos.

El worktree inicial contenia los cambios P0 de telemetria por nodo, nivel
ultrasonico y calibracion versionada aun sin commit. Se conservaron integramente
al crear esta rama.

## Resultado P0 Repetido

### Backend

```text
alembic upgrade head: exitoso sobre SQLite local.
python -m app.seed: exitoso e idempotente.
pytest: 97 passed, 194 warnings.
```

Las advertencias conocidas corresponden a dependencias, uso de
`datetime.utcnow()` en `python-jose` y al ciclo de claves foraneas de teardown en
SQLite.

### Frontend

```text
npm install: exitoso.
eslint: exitoso.
vitest: 8 passed.
next build: exitoso.
```

### Landing

```text
npm install: exitoso.
next build: exitoso.
```

### Flutter

```text
flutter clean: exitoso.
flutter pub get: exitoso.
flutter analyze: No issues found.
flutter test: All tests passed.
flutter build apk --release: exitoso, 51.9 MB.
```

La APK se genero con:

```text
API_BASE_URL=https://agroescudo-api.onrender.com
```

### Firmware

El comando global `pio` resolvia al ejecutable instalado bajo Python 3.13 y
mezclaba dependencias con el entorno interno de PlatformIO 3.11. Esto produjo un
error local de importacion de `littlefs`, anterior a la compilacion.

Sin modificar firmware, se repitio con el ejecutable aislado:

```text
C:\Users\braya\.platformio\penv\Scripts\platformio.exe run -e node_lora_t3
C:\Users\braya\.platformio\penv\Scripts\platformio.exe run -e gateway_tbeam
```

Resultado:

```text
node_lora_t3: SUCCESS, RAM 6.8%, Flash 25.2%.
gateway_tbeam: SUCCESS, RAM 3.8%, Flash 87.7%.
```

## Capacidades P0 Confirmadas

- separacion `silo_sensor` y `field_sensor`;
- storage units de almacenamiento y campo;
- consultas y series estrictas por dispositivo;
- estados de conectividad y falla de sensor;
- calidad de datos y metricas nullable;
- calibracion versionada sin sobrescribir historicos;
- alertas, incidentes y bitacora existentes;
- RBAC admin, tecnico y cliente;
- aislamiento por empresa y asignacion;
- dashboards web y movil por rol;
- reporte semanal JSON/PDF;
- ingestion IoT V1, V2 y V3.

## Riesgos Iniciales

1. `npm audit --omit=dev` reporto tres vulnerabilidades altas en frontend y
   landing (`next`, `postcss`, `sharp`). La correccion propuesta es actualizar
   unicamente Next.js de `16.2.6` a `16.2.11`, sin `audit fix` automatico.
2. PostgreSQL/Neon con las migraciones P0 mas recientes no fue validado desde
   este equipo.
3. Render aun usa un backend anterior y no forma parte de esta implementacion.
4. ADC, JSN-SR04T, radio LoRa, ACK, cola offline y autonomia permanecen
   **NO VERIFICADOS - requieren hardware**.
5. No se hara push, merge ni despliegue durante P1.

## Veredicto De Entrada

P0 permanece funcionalmente estable. La implementacion P1 puede comenzar despues
del parche puntual de dependencias web y su regresion inmediata.
