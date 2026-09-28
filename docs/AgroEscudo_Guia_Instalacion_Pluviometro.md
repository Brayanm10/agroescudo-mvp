# AgroEscudo

## Guía de instalación y conexión de pluviómetros IoT

**Registro, ubicación, aprovisionamiento y validación de un dispositivo ESP32**

- Versión: 1.0
- Fecha: 27 de septiembre de 2026
- Público: técnicos, instaladores, colaboradores de hardware y operadores AgroEscudo

> Este documento no contiene contraseñas, secretos de gateway, claves JWT, conexiones de base de datos ni claves reales de mapas.

## 1. Objetivo y alcance

Esta guía explica cómo preparar AgroEscudo, registrar un pluviómetro, ubicarlo correctamente, conectar un ESP32 de prueba y comprobar la primera lectura. No es un manual de instalación eléctrica ni autoriza el avance a hardware de campo sin una revisión separada.

## 2. Arquitectura simple

```text
Pluviómetro / sensores
        |
       ESP32
        |
   Conectividad
        |
   API AgroEscudo
        |
  Base de datos
        |
Dashboard Pluviometría
```

La prueba HIL validada actualmente utiliza:

```text
ESP32 -> WiFi -> FastAPI -> AgroEscudo
```

El hardware final podrá incorporar gateway o LoRa posteriormente. Esa evolución no forma parte del procedimiento actual.

## 3. Estructura dentro de AgroEscudo

```text
Empresa -> Predio -> Parcela -> Pluviómetro -> Lecturas
```

| Concepto operativo | Representación técnica | Explicación |
|---|---|---|
| Predio | `Site` | Lugar general donde se realiza la operación agrícola. |
| Parcela | `StorageUnit` con `operation_type="field"` | Área específica dentro del predio. |
| Pluviómetro | `Device` con `device_type="rain_gauge"` | Equipo que envía las lecturas meteorológicas. |
| Lectura | Evento de telemetría | Muestra UTC con uno o varios canales métricos. |

## 4. Antes de instalar un ESP32

Confirme primero que existen:

- una empresa;
- el módulo `PLUVIOMETRY` habilitado para esa empresa;
- un predio;
- una parcela;
- un límite geográfico, cuando aplique.

Después siga: **Configuración -> seleccionar predio -> seleccionar parcela -> Añadir pluviómetro**.

## 5. Encontrar y confirmar la ubicación

1. Abra la configuración de Pluviometría.
2. Busque el lugar, municipio o coordenadas.
3. Acerque el mapa hasta reconocer el área correcta.
4. Seleccione la parcela.
5. Active **Seleccionar ubicación en mapa**.
6. Marque la posición exacta del pluviómetro.
7. Revise latitud y longitud.
8. Guarde el dispositivo.

Ejemplo DEMO:

- Latitud: `-17.392800`
- Longitud: `-66.281400`

La latitud indica la posición norte-sur y la longitud la posición este-oeste. La ubicación se guarda una sola vez en el registro del dispositivo. No se vuelve a enviar en cada lectura.

## 6. Crear el pluviómetro

Ejemplo de registro:

| Campo | Ejemplo |
|---|---|
| Nombre | P-01 Norte |
| Device ID | PLUV-001 |
| Predio | Predio DEMO |
| Parcela | Parcela Norte DEMO |
| Latitud | -17.392800 |
| Longitud | -66.281400 |
| Frecuencia esperada | 15 minutos |
| Template | RAIN_GAUGE_BASE |
| Estado inicial | Esperando primera lectura |

El Device ID debe ser único y debe coincidir exactamente con el identificador configurado en el ESP32 o gateway.

## 7. Contrato actual de telemetría

| Canal | Métrica | Unidad | Significado |
|---|---|---|---|
| `rain_1` | `RAIN_DELTA_MM` | `mm` | Lluvia incremental desde la muestra anterior. |
| `ambient_temp_1` | `AMBIENT_TEMPERATURE_C` | `degC` | Temperatura ambiente. |
| `ambient_rh_1` | `AMBIENT_RELATIVE_HUMIDITY_PCT` | `percent` | Humedad relativa ambiente. |
| `wind_speed_1` | `WIND_SPEED_KMH` | `km/h` | Velocidad del viento. |
| `wind_direction_1` | `WIND_DIRECTION_DEG` | `degree` | Dirección del viento en grados. |
| `battery_1` | `BATTERY_PERCENT` | `percent` | Nivel estimado de batería. |

`RAIN_DELTA_MM` es la lluvia ocurrida desde la muestra anterior. No es el acumulado histórico total enviado por el sensor. AgroEscudo calcula agregados sin exigir que el equipo mantenga ese total.

## 8. Conectar el ESP32 de prueba HIL

El ejemplo validado se encuentra en:

```text
hardware/pluviometry/esp32_hil/
|-- esp32_hil.ino
+-- secrets.example.h
```

Copie `secrets.example.h` como `secrets.h` y complete los valores sólo en su estación segura. `secrets.h` no se sube a Git. Nunca copie credenciales productivas dentro de documentación, capturas o tickets.

## 9. Flujo de ingesta

Endpoint:

```http
POST /api/iot/v1/ingest/batch
```

Cada lote identifica conceptualmente:

- Gateway ID;
- Device ID;
- `boot_id`;
- `sequence`;
- timestamp UTC;
- métricas;
- firma HMAC.

La firma prueba que el emisor conoce el secreto asignado, sin enviar ese secreto en el payload. Una respuesta **HTTP 200** con resultado **ACCEPTED** indica que la lectura fue aceptada.

## 10. Validar la primera lectura

Antes de recibir telemetría el equipo aparece como **Esperando primera lectura**. Después de una lectura válida pasa a **En línea / operational**, según la frescura y evaluación operativa.

Ruta de verificación:

```text
Pluviometría -> mapa -> marcador -> popup -> Ver pluviómetro -> gráfico
```

Compruebe que el marcador corresponde a la parcela, que el timestamp visible es correcto y que los seis canales esperados aparecen cuando fueron enviados.

## 11. Estados operativos

| Estado | Interpretación |
|---|---|
| En línea | Se recibieron lecturas dentro del intervalo esperado. |
| Demorado | La última lectura supera la tolerancia normal, pero todavía no se clasifica como desconexión. |
| Sin conexión | No existen lecturas recientes suficientes para considerar el equipo disponible. |
| Crítico | Existe una alerta crítica real asociada a la operación o a una condición medida. |

**Crítico no significa simplemente offline.** Un equipo desconectado puede necesitar atención, pero sólo debe mostrarse crítico cuando exista una alerta crítica real.

## 12. Zona horaria

El ESP32 transmite UTC y el backend guarda UTC. AgroEscudo presenta la hora utilizando `Site.timezone`.

Ejemplo:

```text
05:40 UTC -> 01:40 Bolivia
Zona: America/La_Paz
```

No cambie el timestamp UTC para corregir una visualización local; revise la zona horaria del predio.

## 13. Checklist imprimible de instalación

- [ ] Empresa habilitada
- [ ] `PLUVIOMETRY` activo
- [ ] Predio creado
- [ ] Parcela creada
- [ ] Ubicación confirmada
- [ ] Device ID único
- [ ] `RAIN_GAUGE_BASE` asignado
- [ ] Credencial IoT aprovisionada
- [ ] ESP32 conectado
- [ ] Hora UTC sincronizada
- [ ] HTTP 200
- [ ] ACCEPTED
- [ ] Equipo aparece online
- [ ] Métricas visibles
- [ ] Histórico correcto

## 14. Troubleshooting

| Síntoma | Revisión recomendada |
|---|---|
| ESP32 no conecta WiFi | Revisar SSID y password en `secrets.h`; no publicarlos. |
| HTTP -1 | Revisar IP, backend, red y que el ESP32 no esté intentando usar `localhost`. |
| HTTP 401 | Revisar firma HMAC, timestamp y nonce/secuencia. |
| `duplicate` | El evento ya fue procesado; no reenviarlo como lectura nueva. |
| No aparece equipo | Revisar Device ID y asignación de empresa, predio y parcela. |
| Mapa sin ubicación | Revisar latitud y longitud guardadas en el Device. |
| Hora incorrecta | Revisar `Site.timezone`; no modificar UTC. |
| Sin datos | Revisar endpoint, respuesta de ingesta y lecturas aceptadas. |

## 15. Seguridad

Nunca incluya en PDFs, repositorios, capturas o mensajería:

- contraseña WiFi;
- secreto de gateway;
- `JWT_SECRET`;
- `DATABASE_URL`;
- clave MapTiler real;
- credenciales productivas.

Use secretos dedicados por entorno, mantenga `secrets.h` fuera de Git y rote cualquier credencial expuesta.

## 16. Cierre de la instalación

La instalación se considera validada cuando el dispositivo está correctamente ubicado, la primera lectura fue aceptada, las métricas aparecen con hora Bolivia correcta y el histórico conserva continuidad. Este cierre valida el software y la comunicación HIL; no reemplaza la futura validación eléctrica, mecánica o ambiental del hardware de campo.
