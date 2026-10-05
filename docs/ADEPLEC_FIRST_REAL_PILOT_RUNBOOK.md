# ADEPLEC — manual operativo del primer piloto real

Estado inicial obligatorio: `PENDING_INSTALLATION`. No cambiar a `ACTIVE` hasta completar la sección de activación.

Identificadores reservados: SiloSensor `AE-ADEPLEC-SILO-001`, gateway `AE-ADEPLEC-GW-001` y nombre lógico de nodo `AE-ADEPLEC-NODE-001`. El protocolo v4 exige un `node_id` entero distinto; capturarlo del firmware antes del aprovisionamiento y no inventarlo.

## Antes de salir

- [ ] Confirmar responsable ADEPLEC y técnico AgroEscudo, teléfonos y hora de llegada.
- [ ] Llevar SiloSensor y gateway rotulados con sus `device_id`/`gateway_id` físicos.
- [ ] Llevar antenas correctas, cables, cargadores, fuente y batería/respaldo.
- [ ] Llevar multímetro, celular, laptop cargada, hotspot y herramientas de montaje.
- [ ] Llevar repuestos: fusibles, terminales, bridas, cinta, conectores y cable.
- [ ] Guardar credenciales en el gestor seguro; nunca en este documento ni en mensajería abierta.
- [ ] Abrir `https://agroescudobo.vercel.app` y confirmar login ADMIN y TÉCNICO.
- [ ] Confirmar `https://agroescudo-api.onrender.com/health` y `/api/health/db`.
- [ ] Confirmar que ADEPLEC está en `PENDING_INSTALLATION` y anotar IDs.
- [ ] Imprimir `ADEPLEC_INSTALLATION_CHECKLIST.md`.

## Al llegar

1. Identificar al responsable ADEPLEC y confirmar autorización para instalar y fotografiar.
2. Confirmar nombre/dirección real del sitio y corregirlos en el sistema si difieren.
3. Verificar energía, señal celular/Wi-Fi y alternativa de hotspot.
4. Elegir ubicación segura para nodo y gateway; no encerrar antenas en metal.
5. Verificar protección contra agua, polvo, golpes, animales y manipulación.
6. Tomar foto previa y registrar hora y condiciones.

## Instalación física

1. Montar antenas con los equipos apagados.
2. Encender gateway; confirmar alimentación, conexión a internet y hora correcta.
3. Instalar SiloSensor, colocar sondas según plano y sujetar cableado sin tensión.
4. Copiar serial, `device_id`, `gateway_id`, ubicación exacta y responsable en el checklist.
5. Encender nodo y observar arranque sin errores.
6. Esperar la primera lectura. Registrar RSSI/SNR, batería y hora.
7. Comparar temperatura/humedad con instrumento de referencia si está disponible y anotar diferencia; no alterar lecturas.

## Verificación de software

1. ADMIN: confirmar que el dispositivo recibido corresponde a ADEPLEC y que aparece la primera lectura.
2. CLIENTE: confirmar que solo ve ADEPLEC, su sitio, unidad, sensores, lecturas, alertas y reportes.
3. TÉCNICO: confirmar que ve la unidad asignada y ninguna no asignada.
4. Abrir dashboard e histórico; comprobar timestamp, temperatura, humedad, batería, estado y última comunicación.
5. Probar alerta de commissioning: registrar umbral vigente, bajarlo temporalmente hasta que una lectura real lo exceda, guardar usuario/hora, esperar alerta y capturar evidencia. Restaurar el valor original y verificarlo.

## Pruebas de falla

1. Apagar y encender el nodo; confirmar recuperación y nueva lectura.
2. Reiniciar gateway; confirmar conexión y cola local.
3. Cortar internet brevemente, esperar al menos un intervalo y restablecerlo.
4. Confirmar que la lectura encolada se sincroniza y que el mismo `boot_id + sequence` no se duplica.
5. Si hay pérdida silenciosa, credenciales inválidas o cola que no drena: mantener piloto en `PENDING_INSTALLATION` y abrir incidente.

## Activación

Cambiar a `ACTIVE` únicamente cuando estén confirmados: hardware instalado; IDs correctos; primera lectura persistida; gateway operativo; login cliente y técnico; aislamiento RBAC; alerta aprobada y umbral restaurado; ubicación confirmada; checklist y fotos registrados. Activar unidad, dispositivo, enlace IoT y gateway de manera coordinada.

## Cierre antes de retirarse

- [ ] Fotos finales y captura del dashboard.
- [ ] IDs instalados, hora, primera lectura, señal y batería registrados.
- [ ] Firmas/nombres del responsable ADEPLEC y técnico AgroEscudo.
- [ ] Observaciones, problemas y soluciones anotados.
- [ ] Próximos pasos y fecha de revisión acordados.
- [ ] Ningún umbral de prueba quedó activo.
- [ ] Ninguna contraseña/token quedó en fotos, notas públicas o repositorio.

Si falla un punto crítico, el resultado es **NO-GO**: dejar el equipo seguro, conservar evidencias, mantener `PENDING_INSTALLATION` y escalar con hora, ID y mensaje de error exacto.
