# Checklist De Demo Comercial AgroEscudo

Usa esta lista antes de una presentacion con un acopiador, silo, galpon o agroindustria. El recorrido recomendado dura entre 5 y 7 minutos.

## Preparacion Tecnica

- [ ] Abrir una terminal en `backend`.
- [ ] Confirmar que existe `backend\.env`. Si falta: `copy .env.example .env`.
- [ ] Preparar migraciones y datos demo:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\seed.ps1
```

- [ ] Levantar FastAPI:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\dev.ps1
```

- [ ] Confirmar salud de SQLite en `http://127.0.0.1:8010/api/health/db`.
- [ ] Abrir otra terminal en `frontend`.
- [ ] Confirmar que existe `frontend\.env.local`. Si falta: `copy .env.example .env.local`.
- [ ] Levantar Next.js:

```powershell
npm run dev
```

- [ ] Abrir `http://localhost:3000`.
- [ ] Cerrar sesion o limpiar `localStorage` antes de comenzar.

## Recorrido Admin: Historia Comercial

- [ ] Ingresar con `admin@agroescudo.local` / `admin123`.
- [ ] Abrir `Usuarios` y confirmar que admin, tecnico y cliente estan activos y asignados al piloto demo.
- [ ] Abrir `Notificaciones` y ejecutar una prueba dry-run de Telegram o WhatsApp.
- [ ] Abrir `Modo presentacion`.
- [ ] Mostrar el sitio `Centro de Acopio Norte` y el silo `Silo Maiz Seco 01`.
- [ ] Explicar la ultima lectura recibida desde el nodo `SILO-001`.
- [ ] Pulsar `Simular lectura critica`.
- [ ] Abrir `Ver alerta` y mostrar la deteccion automatica.
- [ ] Pulsar `Registrar accion correctiva` y registrar una accion profesional.
- [ ] Volver a `Modo presentacion` o abrir `Reportes`.
- [ ] Descargar el PDF tecnico semanal.
- [ ] Abrir el PDF y confirmar portada, metricas, alertas, bitacora y recomendaciones.

## Validacion Tecnica

- [ ] Cerrar sesion admin.
- [ ] Ingresar con `tecnico@agroescudo.local` / `tecnico123`.
- [ ] Confirmar que el tecnico ve lecturas, alertas, bitacora y mantenimiento.
- [ ] Confirmar que el tecnico no ve `Modo presentacion`.
- [ ] Cerrar sesion tecnico.

## Validacion Cliente

- [ ] Ingresar con `cliente@silo-demo.local` / `cliente123`.
- [ ] Confirmar que el cliente ve estado del silo, alertas, acciones y reporte.
- [ ] Descargar el PDF como cliente.
- [ ] Confirmar que el cliente no ve simulacion, umbrales ni administracion.
- [ ] Cerrar sesion cliente.

## Cierre

- [ ] Dejar la app lista en la pantalla de login o en `Modo presentacion` con admin.
- [ ] Si necesitas restaurar la evidencia demo original, ejecuta nuevamente:

```powershell
cd backend
powershell -ExecutionPolicy Bypass -File scripts\seed.ps1
```

- [ ] Si necesitas limpiar datos operativos de una unidad antes de reseedear, usa `Pilotos` > `Borrar datos operativos` como admin.
