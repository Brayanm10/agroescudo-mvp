# AgroEscudo Mobile

App Flutter Android para pilotos postcosecha. FastAPI continua siendo la unica fuente de verdad.

## Flujo cliente simplificado

- Desde el login se puede solicitar una cuenta con un unico formulario.
- El contacto Sentinel es opcional y debe usar formato internacional, por ejemplo `+59170000000`.
- El SMS se reserva para alertas criticas; la llamada automatica requiere autorizacion explicita.
- Una vez dentro, `Inicio` muestra continuidad operativa y la prioridad del dia.
- El contacto puede actualizarse desde `Inicio` o `Mas > Contacto de urgencia` para toda la empresa o un silo especifico.
- La cuenta nueva queda pendiente de verificacion y aprobacion; no obtiene acceso automatico a otras empresas.

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
flutter build apk --release --dart-define=API_BASE_URL=https://agroescudo-api.onrender.com
```

Consulta `../MOBILE_DEMO_CHECKLIST.md` para el recorrido completo.
