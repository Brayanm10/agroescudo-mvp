# AgroEscudo Mobile 1.2.1

## Semaforo operativo

- Normal: lectura reciente dentro de la configuracion operativa.
- Precaucion: existe una condicion preventiva que debe revisarse.
- Critico: existe una alerta critica que requiere seguimiento.
- Sin datos: no hay lectura vigente o no existe un sensor vinculado.

La app consume estos estados desde `/api/insights`. No calcula umbrales agronomicos en Dart.

## Experiencia

- Estado principal antes de metricas y graficas.
- Resumen compacto con las cuatro categorias.
- Unidades ordenadas por prioridad.
- Indicador de estado visible en cada unidad.
- Una unidad offline o sin lectura nunca aparece normal.
