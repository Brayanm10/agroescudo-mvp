# 08 - Checklist final para el colaborador

## Identidad y firmware

- [ ] ESP32 identificado físicamente.
- [ ] Device ID externo correcto y aprobado.
- [ ] Firmware versionado.
- [ ] Commit/hash de firmware registrado.
- [ ] `boot_id`, `sequence` y `sample_counter` verificados.
- [ ] Nuevo reinicio genera nuevo `boot_id`.

## Tiempo y comunicación

- [ ] NTP sincronizado.
- [ ] `timestamp_utc` en UTC.
- [ ] No existe ajuste manual de -4 horas.
- [ ] `batch_id` único.
- [ ] nonce no reutilizado.
- [ ] SHA256 del cuerpo correcto.
- [ ] HMAC-SHA256 correcto.
- [ ] HTTP 200 observado.
- [ ] `ACCEPTED` observado.

## Variables

- [ ] Temperatura en `degC`.
- [ ] Humedad en `percent`.
- [ ] Lluvia como delta en `mm`.
- [ ] Velocidad en `km/h`.
- [ ] Dirección en `degree`, meteorológica y menor que 360.
- [ ] Batería en `percent`.
- [ ] Todos los valores son finitos.
- [ ] Todos los rangos son válidos.

## Calibración y evidencia

- [ ] Instrumentos de referencia identificados.
- [ ] Tabla de calibración completada.
- [ ] Varios puntos y repeticiones ejecutados.
- [ ] Factor/offset documentado.
- [ ] Responsable y fecha UTC registrados.
- [ ] Datos visibles en mapa y dashboard.
- [ ] Datos visibles en gráfico e histórico.

## Resiliencia

- [ ] Prueba de reinicio ejecutada.
- [ ] Duplicado verificado sin segunda lectura.
- [ ] Prueba sin red ejecutada.
- [ ] Recuperación de red ejecutada.
- [ ] Pérdidas del HIL actual documentadas.
- [ ] Diseño futuro de buffer/store-and-forward registrado como deuda, sin declararlo implementado.

## Seguridad

- [ ] `secrets.h` ausente de Git.
- [ ] No hay WiFi, HMAC secrets, `.env` ni credenciales reales en evidencias.
- [ ] Credencial dedicada por entorno/unidad o gateway.
- [ ] Procedimiento de rotación documentado.

## Cierre

| Campo | Valor |
|---|---|
| Device ID | |
| Firmware | |
| Fecha/hora UTC | |
| Responsable hardware | |
| Responsable AgroEscudo | |
| Resultado final | APROBADO / RECHAZADO / CON OBSERVACIONES |
| Observaciones | |

**El hardware solo está listo cuando completa la prueba end-to-end y la calibración está documentada.**
