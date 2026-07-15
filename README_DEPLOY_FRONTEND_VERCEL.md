# Despliegue Frontend AgroEscudo en Vercel

Guia para publicar el dashboard web Next.js de AgroEscudo en Vercel conectado a la API publica de Render.

## Backend Publico

```text
https://agroescudo-api.onrender.com
```

Antes de desplegar la web, confirma:

```text
https://agroescudo-api.onrender.com/health
https://agroescudo-api.onrender.com/api/health/db
```

## Crear Proyecto en Vercel

1. Entra a Vercel.
2. Selecciona `Add New Project`.
3. Importa el repo:

```text
Brayanm10/agroescudo-mvp
```

4. Configura:

```text
Root Directory: frontend
Framework Preset: Next.js
Build Command: npm run build
Install Command: npm install
Output Directory: .next
```

## Variable de Entorno

En Vercel, agrega:

```env
NEXT_PUBLIC_API_URL=https://agroescudo-api.onrender.com
```

Debe estar disponible para Production, Preview y Development si quieres probar previews.

## Deploy

1. Guarda la variable de entorno.
2. Ejecuta `Deploy`.
3. Abre la URL generada por Vercel.

## Probar Login

Usa las cuentas internas creadas por el seed y cambia las contrasenas iniciales desde administracion antes de entregar el piloto a terceros.

## Checklist Web

1. Abrir la URL de Vercel.
2. Login admin.
3. Ver Dashboard.
4. Ver Sitios.
5. Ver Alertas.
6. Ver Reportes.
7. Descargar PDF semanal.
8. Cerrar sesion.
9. Login tecnico.
10. Confirmar acceso operativo sin administracion avanzada.
11. Cerrar sesion.
12. Login cliente.
13. Confirmar portal cliente y PDF.

## Si Falla la Conexion

La web muestra diagnostico con:

- URL de API usada.
- Endpoint probado.
- Codigo HTTP si existe.
- Mensaje tecnico.
- Posibles causas.

Revisa:

- Render Free puede estar dormido. Abre `https://agroescudo-api.onrender.com/health` para despertarlo.
- `NEXT_PUBLIC_API_URL` debe ser exactamente `https://agroescudo-api.onrender.com`.
- En Render, `CORS_ORIGINS` debe permitir el dominio de Vercel. Para demo puede ser `*`; en production debe ser el dominio explicito.
- Si cambias variables en Vercel, vuelve a desplegar. Las variables `NEXT_PUBLIC_*` se inyectan durante el build.

## Build Local de Verificacion

```powershell
cd frontend
npm install
$env:NEXT_PUBLIC_API_URL="https://agroescudo-api.onrender.com"
npm run build
```

Para desarrollo local contra backend local:

```env
NEXT_PUBLIC_API_URL=http://127.0.0.1:8010
```
