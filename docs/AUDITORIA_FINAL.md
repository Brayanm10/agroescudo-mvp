# Auditoría Final AgroEscudo

Fecha de corte: 2026-08-09
Rama de release: `codex/premium-charts-release`

## Veredicto

**SOFTWARE LISTO PARA DESPLIEGUE Y PILOTO CONTROLADO**

La API, el dashboard web, la app Android, el RBAC, la telemetría por nodo, las alertas, la bitácora, las calibraciones y los reportes se verificaron localmente con suites automatizadas y QA visual. El cierre comercial completo todavía requiere configurar credenciales externas y ejecutar la validación física con sensores, LoRa y gateway del piloto.

## Evidencia Reproducible

| Componente | Resultado | Evidencia |
| --- | --- | --- |
| Backend FastAPI | Verificado | `133 passed` con `py -3.13 -m pytest -p no:cacheprovider` |
| Series por nodo | Verificado | Resumen, extremos por bucket, muestras, cobertura y huecos explícitos |
| Contexto de gráficas | Verificado | Alertas y acciones filtradas por dispositivo, periodo y RBAC |
| Frontend Next.js | Verificado | `14 passed`, ESLint limpio y `next build` exitoso |
| QA responsive web | Verificado | Historial revisado en 1440x1000 y 390x844, sin errores de consola |
| Flutter Android | Verificado | `flutter analyze` sin observaciones, `flutter test` con 3 pruebas y APK release |
| APK | Verificado | 68.92 MB; SHA-256 `A9E6D3B1C30EDE15CD24A057BE03450F0C78D37DCDE23D27B6FF86CC9BDA2257` |
| PDF técnico | Verificado | Informe de 10 páginas y bitácora de 3 páginas renderizados e inspeccionados |
| Secretos en diff | Verificado | 0 firmas OpenAI, Google, GitHub, JWT o claves privadas |
| Artefactos | Verificado | `.env`, `dist/`, APK, `mobile/build/`, `.next/` y `output/` ignorados |

## Publicación Verificada

- GitHub `main`: commit `34d70113ed0e932a397f075c675ec219832ceb84`.
- Rama de release: `origin/codex/premium-charts-release` en el mismo commit.
- Vercel producción: `https://agroescudobo.vercel.app` con estado `Ready` y HTTP 200.
- Render API: `https://agroescudo-api.onrender.com/health` con `status=ok`.
- Smoke Render: login admin válido y `GET /api/devices/{id}/chart-context` operativo.

## Cambios Cerrados En Esta Release

- Sistema visual propietario de gráficos AgroEscudo para Recharts y FL Chart.
- Temperatura principal, humedad secundaria y nivel con indicador 2D y tendencia.
- Tooltip, métricas del periodo, estados operativos, umbrales, eventos y acciones.
- Huecos de datos visibles; las líneas no simulan continuidad durante desconexiones.
- Agregación que conserva mínimo, máximo, promedio y número de muestras.
- Filtro estricto por dispositivo y contexto compartido entre web, móvil y PDF.
- Reportes vectoriales con alertas, acciones, nivel y pérdida de datos.
- Jerarquía responsive corregida en historial y sin diagnóstico sensible para cliente.

## Pendientes Para Activar Un Piloto Real

### Credenciales obligatorias

- `JWT_SECRET` largo y exclusivo de producción.
- `DATABASE_URL` de PostgreSQL/Neon con backups habilitados.
- Variables de Render y `NEXT_PUBLIC_API_URL` de Vercel.
- Keystore Android productivo para distribución fuera de pruebas directas.

### Integraciones opcionales

- Resend: `EMAIL_API_KEY`, `EMAIL_FROM`, `PUBLIC_APP_URL`.
- WhatsApp Cloud API: token, phone number id y plantilla aprobada.
- Telegram: bot token y `chat_id` por destinatario.
- Firebase FCM: proyecto y `google-services.json`, únicamente para push.
- S3 compatible: endpoint, bucket y credenciales para fotos/firmas permanentes.
- Sentry: DSN y entorno si se habilita observabilidad.

### Validación física obligatoria

- Alimentación y divisor de tensión del JSN-SR04T.
- Rango, ruido, polvo y humedad del ultrasónico.
- Alcance LoRa, pérdida de ACK y recuperación de cola del gateway.
- Calibración vacío/lleno por silo y calibración ADC por CampoSensor.
- Prueba de desconexión de internet y reenvío idempotente al backend.

Todo este bloque se mantiene como **NO VERIFICADO - requiere credenciales o prueba física** hasta ejecutarse en el sitio del piloto.

## Riesgos Residuales

- Las advertencias de tests corresponden a APIs deprecadas de dependencias y al ciclo de claves foráneas de SQLite en teardown; no causaron fallos funcionales.
- Gradle reporta compatibilidad Java 8 obsoleta en dependencias Android; no bloquea el APK actual, pero debe actualizarse antes de publicación formal en Play Store.
- El APK actual es de distribución directa para piloto. La publicación comercial necesita keystore, versionado y política de privacidad final.
- El firmware sigue necesitando banco de pruebas físico; las pruebas de software no demuestran alcance RF ni precisión metrológica.

## Criterio De Go/No-Go

**GO** para demo comercial y piloto controlado con acompañamiento técnico.
**NO-GO** para operación desatendida o compromisos metrológicos hasta cerrar credenciales, backups, firma Android y validación física del hardware.
