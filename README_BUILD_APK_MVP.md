# Build APK MVP AgroEscudo

Guia para compilar la app Flutter Android conectada a la API publica de Render.

## API Usada

```text
https://agroescudo-api.onrender.com
```

La app usa `const String.fromEnvironment("API_BASE_URL")`. En builds release no se permite usar `localhost`, `127.0.0.1`, `10.0.2.2` ni IP LAN `192.168.x.x`.

## Comando Exacto de Build

Desde la raiz del repo:

```powershell
cd mobile
flutter clean
flutter pub get
flutter build apk --release --dart-define=API_BASE_URL=https://agroescudo-api.onrender.com
```

Para una APK con push Firebase, después de colocar `mobile/android/app/google-services.json`:

```powershell
flutter build apk --release --dart-define=API_BASE_URL=https://agroescudo-api.onrender.com --dart-define=ENABLE_FCM=true
```

## Ruta del APK

```text
mobile/build/app/outputs/flutter-apk/app-release.apk
```

## Instalar en Android

Con telefono conectado por USB y depuracion USB activa:

```powershell
cd mobile
flutter install --release
```

O instala manualmente el archivo:

```text
mobile/build/app/outputs/flutter-apk/app-release.apk
```

Si Android bloquea la instalacion, habilita permisos para instalar apps externas desde el gestor de archivos o navegador usado.

## Cuentas Demo

Usa las cuentas internas creadas por el seed y cambia las contrasenas iniciales desde administracion antes de entregar el piloto a terceros.

## Checklist de Prueba

1. Abrir la app instalada.
2. Iniciar sesion con admin.
3. Ver resumen/dashboard.
4. Ver unidades: silos, galpones o almacenes.
5. Ver lecturas historicas.
6. Ver alertas.
7. Descargar PDF semanal desde Reportes si existe una unidad seleccionada.
8. Cerrar sesion.
9. Iniciar sesion con tecnico.
10. Confirmar que puede ver alertas y registrar acciones operativas.
11. Cerrar sesion.
12. Iniciar sesion con cliente.
13. Confirmar que ve su informacion operativa y no opciones administrativas.

## Si Render Esta Dormido

Render Free puede tardar en responder cuando el servicio estuvo inactivo.

1. Abre primero:

```text
https://agroescudo-api.onrender.com/health
```

2. Espera hasta que responda:

```json
{"status":"ok"}
```

3. Luego prueba:

```text
https://agroescudo-api.onrender.com/api/health/db
```

4. Vuelve a la app y toca `Reintentar conexion`.

Si sigue fallando, revisa:

- Que el telefono tenga internet.
- Que la URL de build haya sido `https://agroescudo-api.onrender.com`.
- Que Render no muestre errores de migracion o base de datos.
- Que `/api/health/db` devuelva `database: postgresql`.

## Build Local de Desarrollo

Solo para emulador Android:

```powershell
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8010
```

No uses esa URL para APK release.
