# Validacion Arduino IDE V4

Fecha: 2026-08-06

## Alcance

Se validaron los tres sketches estructurados para el piloto:

- Gateway multinodo T-Beam V1.2.
- Nodo SiloSensor TTGO LoRa32/T3 V1.6.1.
- Nodo CampoSensor TTGO LoRa32/T3 V1.6.1.

## Resultados

| Entorno PlatformIO de validacion | Resultado | RAM | Flash |
|---|---|---:|---:|
| `arduino_silo_sensor_v4` | SUCCESS | 7.3% | 29.0% |
| `arduino_campo_sensor_v4` | SUCCESS | 7.3% | 28.8% |
| `arduino_gateway_multinodo_v4` | SUCCESS | 4.0% | 42.3% de particion Huge APP |

Tambien se recompilaron los entornos existentes `node_lora_t3`,
`node_field_t3` y `gateway_tbeam`; los tres finalizaron con `SUCCESS`.

## Software asociado

- Backend: 126 pruebas aprobadas.
- Frontend: 8 pruebas aprobadas, lint y build aprobados.
- Alembic local: upgrade a head aprobado.
- Manual PDF: generado y revisado visualmente, 8 paginas.

## Limites de validacion

Las compilaciones prueban estructura, dependencias y presupuesto de memoria.
El cableado, divisor de tension ECHO, alcance LoRa, ruido ADC, ecos del
ultrasonico, consumo y recuperacion ante cortes requieren prueba fisica antes
de instalar en un silo o parcela.
