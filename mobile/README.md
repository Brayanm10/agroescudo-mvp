# AgroEscudo Mobile

App Flutter Android para pilotos postcosecha. FastAPI continua siendo la unica fuente de verdad.

## Desarrollo

```powershell
flutter pub get
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8010
```

`10.0.2.2` apunta al host desde el emulador Android. Para un telefono fisico usa la IPv4 LAN del PC y levanta FastAPI con `--host 0.0.0.0`.

## Verificacion

```powershell
flutter analyze
flutter test
flutter build apk --release --dart-define=API_BASE_URL=https://api.agroescudo.com
```

Consulta `../MOBILE_DEMO_CHECKLIST.md` para el recorrido completo.
