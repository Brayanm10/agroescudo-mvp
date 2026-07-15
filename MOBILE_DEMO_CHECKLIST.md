# Checklist App Android AgroEscudo

Usa esta lista antes de instalar la APK o presentar el flujo movil de piloto.

## Preparacion Backend

- [ ] Abrir una terminal en `backend`.
- [ ] Aplicar migraciones y seed demo:

```powershell
alembic upgrade head
python -m app.seed
```

- [ ] Para emulador Android, levantar FastAPI:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8010
```

- [ ] Para telefono fisico en la misma red Wi-Fi, levantar FastAPI:

```powershell
python -m uvicorn app.main:app --host 0.0.0.0 --port 8010
```

- [ ] Confirmar `http://127.0.0.1:8010/api/health/db`.

## Ejecutar En Emulador

- [ ] Abrir una terminal en `mobile`.
- [ ] Confirmar `flutter doctor`.
- [ ] Ejecutar:

```powershell
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8010
```

## Ejecutar En Telefono Fisico

- [ ] Activar modo desarrollador y depuracion USB en Android.
- [ ] Confirmar el dispositivo con `adb devices`.
- [ ] Obtener la IPv4 LAN del PC con `ipconfig`.
- [ ] Reemplazar la IP del ejemplo y ejecutar:

```powershell
flutter run --dart-define=API_BASE_URL=http://192.168.1.50:8010
```

## Validar Roles

- [ ] Ingresar con la cuenta admin interna del piloto.
- [ ] Confirmar resumen, alertas, resolver alerta, bitacora y PDF.
- [ ] Cerrar sesion.
- [ ] Ingresar con la cuenta tecnica asignada.
- [ ] Confirmar checklist de instalacion, mantenimiento, reconocer alerta y PDF.
- [ ] Confirmar que no aparece resolucion administrativa.
- [ ] Cerrar sesion.
- [ ] Ingresar con la cuenta cliente asignada.
- [ ] Confirmar unidades propias, lecturas, alertas, bitacora y PDF.
- [ ] Confirmar que no aparecen acciones tecnicas.

## Validar Cache Offline

- [ ] Ingresar y actualizar datos con internet.
- [ ] Desconectar Wi-Fi/datos del telefono.
- [ ] Reiniciar la app.
- [ ] Confirmar banner `Modo sin conexion`.
- [ ] Confirmar que el ultimo estado sigue visible.
- [ ] Confirmar que acciones de escritura muestran que requieren conexion.

## Generar APK

- [ ] Ejecutar verificaciones:

```powershell
flutter analyze
flutter test
```

- [ ] Generar APK local de piloto:

```powershell
flutter build apk --release --dart-define=API_BASE_URL=http://192.168.1.50:8010
```

- [ ] Ubicar `mobile/build/app/outputs/flutter-apk/app-release.apk`.

## Fase Posterior

- [ ] Configurar dominio HTTPS productivo para FastAPI.
- [ ] Firmar APK con keystore propio antes de distribucion estable.
- [ ] Integrar Firebase FCM solo para notificaciones push.
- [ ] Definir hardware antes de implementar firmware LoRa + Wi-Fi/4G.
