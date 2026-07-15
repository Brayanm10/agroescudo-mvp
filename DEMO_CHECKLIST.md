# Checklist De Piloto Comercial AgroEscudo

Usa esta lista antes de una presentacion con un acopiador, silo, galpon o agroindustria. El recorrido recomendado dura entre 5 y 7 minutos.

## Preparacion Tecnica

- [ ] Abrir una terminal en `backend`.
- [ ] Confirmar que existe `backend\.env`. Si falta: `copy .env.example .env`.
- [ ] Preparar migraciones y datos de piloto:

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

- [ ] Ingresar con la cuenta admin interna del piloto.
- [ ] Abrir `Empresas`, `Silos/Galpones` y `Sensores` para mostrar el flujo empresa -> unidad monitoreada -> nodo IoT con API key.
- [ ] Abrir `Usuarios` y confirmar que admin, tecnico y cliente estan activos y asignados al piloto comercial.
- [ ] Abrir `Notificaciones` y ejecutar una prueba dry-run de Telegram o WhatsApp.
- [ ] Abrir `Presentacion comercial`.
- [ ] Mostrar el sitio `Centro de Acopio Norte` y el silo `Silo Maiz Seco 01`.
- [ ] Confirmar que el piloto puede iniciar limpio o explicar la ultima lectura real recibida desde el nodo `SILO-001`.
- [ ] Pulsar `Simular lectura critica`.
- [ ] Abrir `Ver alerta` y mostrar la deteccion automatica.
- [ ] Pulsar `Registrar accion correctiva` y registrar una accion profesional.
- [ ] Volver a `Presentacion comercial` o abrir `Reportes`.
- [ ] Descargar el PDF tecnico semanal.
- [ ] Abrir el PDF y confirmar portada, metricas, alertas, bitacora y recomendaciones.

## Validacion Tecnica

- [ ] Cerrar sesion admin.
- [ ] Ingresar con la cuenta tecnica asignada.
- [ ] Confirmar que el tecnico ve lecturas, alertas, bitacora y mantenimiento.
- [ ] Confirmar que el tecnico no ve `Presentacion comercial`.
- [ ] Cerrar sesion tecnico.

## Validacion Cliente

- [ ] Ingresar con la cuenta cliente asignada.
- [ ] Confirmar que el cliente ve estado del silo, alertas, acciones y reporte.
- [ ] Descargar el PDF como cliente.
- [ ] Confirmar que el cliente no ve simulacion, umbrales ni administracion.
- [ ] Cerrar sesion cliente.

## Cierre

- [ ] Dejar la app lista en la pantalla de login o en `Presentacion comercial` con admin.
- [ ] Si necesitas limpiar nuevamente la base operativa del piloto, ejecuta:

```powershell
cd backend
powershell -ExecutionPolicy Bypass -File scripts\seed.ps1
```

- [ ] Si necesitas limpiar datos operativos de una unidad antes de reseedear, usa `Pilotos` > `Borrar datos operativos` como admin.
