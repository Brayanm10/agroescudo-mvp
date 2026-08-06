# Reporte de pruebas P1.5

Fecha: 2026-07-24
Rama: `feature/p1-5-sensor-data-pipeline`
Push, merge y despliegue: no ejecutados

## Resultado ejecutivo

| Componente | Comando | Resultado |
|---|---|---|
| Alembic local | `py -3.13 -m alembic upgrade head` | PASS, head `202607240002` |
| Alembic roundtrip | downgrade a `202607230002` y upgrade head sobre copia | PASS |
| Seed | `py -3.13 -m app.seed` | PASS, idempotente |
| Backend | `py -3.13 -m pytest -p no:cacheprovider` | 126 passed |
| P1.5 específico | `pytest tests/test_p1_5_sensor_pipeline.py` | 8 passed |
| Frontend test | `npm.cmd run test` | 8 passed |
| Frontend lint | `npm.cmd run lint` | PASS |
| Frontend build | `npm.cmd run build` | PASS |
| Flutter analyze | `flutter analyze` | Sin issues |
| Flutter test | `flutter test` | 3 passed |
| Flutter APK | build release con API Render | PASS, 68.3 MB |
| Nodo silo | PlatformIO `node_lora_t3` | SUCCESS |
| Nodo campo | PlatformIO `node_field_t3` | SUCCESS |
| Gateway | PlatformIO `gateway_tbeam` | SUCCESS |
| Manual PDF | generación, extracción y render PNG | PASS, 12 páginas |

## Cobertura P1.5 añadida

- IDs canónicos únicos e inmutables.
- Ingestión explícita sin dependencia del orden.
- Dual write legacy/normalizado.
- HMAC, replay e idempotencia.
- Evento duplicado sin segunda lectura.
- Canal/métrica inconsistente en cuarentena.
- Schema dinámico según canales instalados.
- Raw oculto al cliente.
- Historial conservado al ocultar gráfica.
- Alerta vinculada al canal y definición canónica.
- Upgrade/downgrade sobre copia sin modificar la fuente.

## Firmware

| Entorno | RAM | Flash | SHA-256 |
|---|---:|---:|---|
| node_lora_t3 | 7.3% | 28.8% | `335499252E28AD878F8B649811F91F4B223481EF5B07E2A2B093D44C16585043` |
| node_field_t3 | 7.3% | 28.8% | `9AAD0B492DC4491CA458A4AE5879161CD0CDD9740AF53C2E1C2B3B76F5CF68E4` |
| gateway_tbeam | 3.8% | 88.2% | `0A04E0E4CBAD6EC27AE9925F3628A84CBDD3A2D28198A2E007DADA9442A63851` |

Riesgo: el gateway usa 88.2% de flash. Antes de agregar funciones debe definirse
un presupuesto de memoria y revisar particiones OTA.

## Artefactos

- APK local: `mobile/build/app/outputs/flutter-apk/app-release.apk`
- APK SHA-256:
  `59D48B4C45FF2FC5A6A93AC3E4FF9FC8030FD3EB31E4722B1CD8DE0567216847`
- Manual:
  `output/pdf/AgroEscudo_Manual_Tecnico_Sensores_LoRa_P1_5.pdf`
- PDF SHA-256:
  `47E9BDFA539943BB3F2A8D27AC7ADDD025A18E6699CB20F8C0A019817DC8E12D`

## No verificado

- Hardware real, tensión ECHO, ruido ADC y ecos del ultrasónico.
- Alcance, pérdida de ACK y autonomía.
- Cola del gateway durante un corte prolongado.
- Certificado TLS y aprovisionamiento NVS productivos.
- Backup, migración y conciliación PostgreSQL/Neon.
- Comparación de al menos 20 dispositivos productivos.

Estos puntos bloquean declarar la cadena física lista para producción
desatendida, pero no invalidan la compilación y pruebas de software.
