# 18. Guia rapida para nuevo desarrollador

Estado del documento: BORRADOR CONTROLADO  
Fecha de auditoria: 2026-07-02

## Que es AgroEscudo

AgroEscudo es una plataforma B2B para monitoreo postcosecha. Recibe lecturas de sensores, genera alertas, registra bitacora, administra pilotos y genera reportes PDF.

## Arranque rapido local

Backend:

```powershell
cd backend
py -3.13 -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
py -3.13 -m alembic upgrade head
py -3.13 -m app.seed
py -3.13 -m uvicorn app.main:app --host 127.0.0.1 --port 8010
```

Frontend:

```powershell
cd frontend
npm install
npm run dev
```

Flutter:

```powershell
cd mobile
flutter pub get
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8010
```

## Primeras rutas a revisar

| Necesidad | Ruta |
|---|---|
| App FastAPI | `backend/app/main.py` |
| Configuracion | `backend/app/core/config.py` |
| Modelos | `backend/app/models.py` |
| Schemas | `backend/app/schemas.py` |
| Permisos | `backend/app/api/deps.py` |
| Routers | `backend/app/api/routes/` |
| Servicios | `backend/app/services/` |
| Frontend principal | `frontend/app/page.tsx` |
| API web | `frontend/lib/api.ts` |
| Tipos web | `frontend/lib/types.ts` |
| App Flutter API | `mobile/lib/core/api_client.dart` |
| Estado Flutter | `mobile/lib/core/app_store.dart` |
| Firmware | `firmware/` |

## Como agregar un endpoint backend

1. Crear/editar router en `backend/app/api/routes/`.
2. Agregar schema en `backend/app/schemas.py`.
3. Usar deps de seguridad si requiere JWT.
4. Registrar router en `backend/app/main.py` si es nuevo.
5. Agregar test en `backend/tests/`.
6. Ejecutar pytest.

## Como agregar un campo a base de datos

1. Editar `backend/app/models.py`.
2. Crear migracion Alembic.
3. Actualizar schema de entrada/salida.
4. Actualizar seed si aplica.
5. Actualizar frontend/mobile si consumen el campo.
6. Ejecutar migraciones y tests.

## Como agregar una vista web

1. Agregar tipo si aplica en `frontend/lib/types.ts`.
2. Agregar cliente API en `frontend/lib/api.ts`.
3. Agregar vista o componente.
4. Agregar entrada al sidebar segun rol.
5. Probar `npm run lint` y `npm run build`.

## Como cambiar la API de Flutter

No hardcodear URL. Usar:

```powershell
--dart-define=API_BASE_URL=https://<api-publica>
```

Release no debe usar localhost ni IP privada.

## Como probar un flujo minimo

1. Levantar backend.
2. Ejecutar seed.
3. Levantar frontend.
4. Login admin.
5. Ver dashboard.
6. Ver silos/galpones.
7. Simular o recibir lectura.
8. Ver alerta.
9. Registrar accion.
10. Descargar PDF.
11. Login tecnico.
12. Login cliente.

## Reglas de oro

- No romper `POST /api/readings`.
- No guardar secretos en repo.
- No prometer IA real si solo hay reglas.
- No mezclar datos de clientes.
- No mostrar tokens completos.
- No agregar features futuristas antes de cerrar piloto.
- Marcar todo lo no probado como NO VERIFICADO.

## Comandos de calidad

```powershell
cd backend
py -3.13 -m pytest -p no:cacheprovider
```

```powershell
cd frontend
npm run lint
npm run build
```

```powershell
cd mobile
flutter analyze
flutter test
```

## Si algo falla

| Sintoma | Primer chequeo |
|---|---|
| Web no conecta | `NEXT_PUBLIC_API_URL` |
| App no conecta | `API_BASE_URL` |
| Login falla | Seed, usuario activo y JWT secret |
| DB falla | `DATABASE_URL` y migraciones |
| PDF falla | Endpoint `/api/reports/weekly/pdf` |
| Sensor falla | Token/device active |
| Gateway falla | HMAC, timestamp, nonce y cola |

