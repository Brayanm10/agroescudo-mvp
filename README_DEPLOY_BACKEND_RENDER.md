# Despliegue Backend AgroEscudo en Render

Guia para publicar el backend FastAPI de AgroEscudo en Render Free usando PostgreSQL externo de Neon o Supabase.

## 1. Crear PostgreSQL Externo

Opcion recomendada para MVP: Neon.

1. Crea un proyecto en Neon o Supabase.
2. Crea una base PostgreSQL para AgroEscudo.
3. Copia el connection string directo, no el pooler.
4. Ajusta el formato para SQLAlchemy:

```env
postgresql+psycopg://USER:PASSWORD@HOST:5432/DB
```

Para Neon usa la conexion estandar directa para que Alembic pueda ejecutar migraciones sin problemas.

## 2. Crear Web Service en Render

1. En Render, selecciona `New Web Service`.
2. Conecta el repositorio de GitHub.
3. Configura:

```text
Root Directory: backend
Environment: Docker
Dockerfile Path: Dockerfile
```

Render inyecta automaticamente la variable `PORT`. El contenedor usa `scripts/start.sh`, que ejecuta migraciones, seed demo idempotente y luego levanta Uvicorn.

## 3. Variables de Entorno en Render

Configura estas variables:

```env
APP_NAME=AgroEscudo API
ENVIRONMENT=demo
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DB
JWT_SECRET=CAMBIAR_POR_UN_SECRETO_LARGO_Y_UNICO
API_URL=https://TU-SERVICIO.onrender.com
ACCESS_TOKEN_EXPIRE_MINUTES=480
CORS_ORIGINS=*
WHATSAPP_ENABLED=false
TELEGRAM_ENABLED=false
FCM_ENABLED=false
AI_ENABLED=false
```

Notas:

- `ENVIRONMENT=demo` permite `CORS_ORIGINS=*` para facilitar el MVP.
- En `ENVIRONMENT=production`, `CORS_ORIGINS=*` esta bloqueado. Debes usar dominios explicitos.
- `JWT_SECRET` no puede quedar como `change-me-in-production`.
- `DATABASE_URL` no puede usar SQLite en demo o production.

Ejemplo para produccion mas estricta:

```env
ENVIRONMENT=production
CORS_ORIGINS=https://agroescudo.vercel.app,https://app.agroescudo.com
```

## 4. Que Hace el Arranque

El script `backend/scripts/start.sh` ejecuta:

```sh
alembic upgrade head
python -m app.seed
uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
```

Esto deja la base lista y mantiene los usuarios demo:

- `admin@agroescudo.local` / `admin123`
- `tecnico@agroescudo.local` / `tecnico123`
- `cliente@silo-demo.local` / `cliente123`

## 5. Probar Despues del Deploy

Health API:

```powershell
curl https://TU-SERVICIO.onrender.com/health
```

Health DB:

```powershell
curl https://TU-SERVICIO.onrender.com/api/health/db
```

Login admin:

```powershell
curl -X POST https://TU-SERVICIO.onrender.com/api/auth/login `
  -H "Content-Type: application/json" `
  -d "{\"email\":\"admin@agroescudo.local\",\"password\":\"admin123\"}"
```

Lectura IoT demo:

```powershell
curl -X POST https://TU-SERVICIO.onrender.com/api/readings `
  -H "Content-Type: application/json" `
  -d "{\"device_id\":\"SILO-001\",\"device_token\":\"secret-token\",\"grain_temperature\":36.5,\"ambient_temperature\":29.1,\"ambient_humidity\":84.2,\"battery_voltage\":3.91,\"signal_quality\":-65,\"timestamp\":\"2026-05-27T20:00:00Z\"}"
```

## 6. Probar Localmente con Docker

Desde la raiz del repo:

```powershell
copy .env.example .env
docker compose up --build
```

La API local queda en:

```text
http://localhost:8000
http://localhost:8000/health
http://localhost:8000/api/health/db
```

## 7. Errores Comunes

- `PORT` mal configurado: Render usa `PORT`; no hardcodear `8000` como unico puerto.
- `DATABASE_URL` incorrecto: debe ser `postgresql+psycopg://...`.
- Usar SQLite en demo/production: la app lo bloquea.
- `JWT_SECRET` inseguro: la app bloquea defaults en demo/production.
- Alembic falla: revisar que el connection string sea directo y tenga permisos de schema.
- Seed duplica datos: el seed debe ser idempotente; si falla, revisar logs de Render.
- CORS bloquea frontend: en demo usar `CORS_ORIGINS=*`; en production usar dominios explicitos.

## 8. Checklist Antes de Pasar a Flutter

- Render muestra `/health` con `{"status":"ok"}`.
- Render muestra `/api/health/db` con `database: postgresql`.
- Login admin devuelve token.
- Login tecnico devuelve token.
- Login cliente devuelve token.
- `POST /api/readings` crea lectura y alerta si corresponde.
- El PDF semanal responde desde `/api/reports/weekly/pdf?storage_unit_id=`.
- Ya tienes la URL publica final, por ejemplo `https://TU-SERVICIO.onrender.com`.

Cuando todo esto funcione, el siguiente paso es compilar Flutter con:

```powershell
flutter build apk --release --dart-define=API_BASE_URL=https://TU-SERVICIO.onrender.com
```
