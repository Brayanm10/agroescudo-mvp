# AgroEscudo - Manual De Usuario, Operación Y Servicio

Versión 1.0 - Primeros pilotos controlados

## 1. Objetivo

Este manual explica cómo preparar, operar y revisar un piloto AgroEscudo en silos, galpones, almacenes o parcelas monitoreadas. Está dirigido a:

- Administrador AgroEscudo.
- Técnico responsable.
- Cliente o propietario de la operación.
- Responsable de soporte y servicio.

AgroEscudo recibe lecturas IoT, detecta condiciones fuera de rango, genera alertas, registra acciones y produce evidencia técnica. No reemplaza la inspección física ni la decisión profesional del operador.

## 2. Preparación Antes Del Piloto

1. Confirmar empresa, sitio y unidad monitoreada.
2. Identificar producto almacenado, capacidad y ubicación.
3. Registrar dispositivo y gateway.
4. Asignar técnico y usuario cliente.
5. Configurar umbrales acordados.
6. Validar alimentación, batería, señal y conectividad.
7. Completar checklist digital de instalación.
8. Confirmar primera lectura y alerta de prueba.
9. Generar QR seguro del dispositivo.
10. Descargar reporte de prueba.

No iniciar el piloto si el dispositivo no transmite, la lectura inicial no coincide con una verificación local o el usuario cliente no puede ingresar.

## 3. Acceso Y Roles

### Administrador

Puede registrar empresas, unidades, dispositivos, usuarios, gateways, umbrales, mantenimientos, reportes y configuraciones.

### Técnico

Solo opera activos asignados. Puede revisar diagnóstico, iniciar y cerrar mantenimiento, completar instalaciones, reconocer alertas y cargar evidencia.

### Cliente

Solo consulta su operación: estado, lecturas, alertas, acciones y reportes. No ve señal RSSI, credenciales técnicas ni configuración crítica.

## 4. Flujo Del Administrador

1. Ingresar al dashboard web.
2. Crear o revisar la empresa.
3. Crear sitio y silo, galpón, almacén o parcela.
4. Registrar el dispositivo y guardar su API key en un lugar seguro.
5. Asignar el dispositivo a la unidad.
6. Asignar técnico y cliente.
7. Definir umbrales.
8. Registrar gateway y nodos asociados.
9. Crear checklist de instalación.
10. Programar mantenimiento si corresponde.
11. Revisar salud del sistema y métricas.
12. Descargar reporte ejecutivo.

## 5. Flujo Del Técnico

1. Ingresar desde web o Android.
2. Revisar alertas críticas y nodos fuera de línea.
3. Escanear el QR del dispositivo.
4. Abrir el checklist asignado.
5. Verificar montaje, caja, antena, cableado, batería y sensor.
6. Confirmar conectividad y primera transmisión.
7. Comparar lectura con observación local.
8. Registrar evidencia fotográfica.
9. Validar alerta y reporte de prueba.
10. Cerrar instalación o registrar observaciones.
11. Iniciar mantenimiento cuando exista una orden.
12. Registrar diagnóstico, acción y estado final.

## 6. Flujo Del Cliente

1. Ingresar al portal.
2. Elegir el silo o parcela.
3. Revisar estado general y última lectura.
4. Consultar gráficas y alertas.
5. Revisar acciones realizadas por el técnico.
6. Descargar reporte PDF.
7. Contactar soporte si la alerta persiste o no llegan lecturas.

El cliente no debe modificar umbrales, dispositivos, gateways ni asignaciones.

## 7. Instalación Del Nodo

### Inspección Física

- Caja cerrada, limpia y protegida.
- Montaje firme.
- Antena instalada y sin obstrucciones inmediatas.
- Cableado protegido.
- Sensor ubicado en el punto definido.
- Alimentación y batería verificadas.
- QR adherido y legible.

### Comunicación

- Gateway asociado.
- Primera transmisión recibida.
- Hora sincronizada.
- Conectividad confirmada.
- Cola local sin acumulación crítica.

### Validación

- Primera lectura registrada.
- Lectura comparada con referencia local.
- Umbrales revisados.
- Alerta de prueba confirmada.
- Acceso técnico y cliente comprobado.
- Reporte de prueba generado.

## 8. Uso Del QR

El QR contiene un token público aleatorio. No contiene contraseña, API key del sensor ni acceso global.

1. Abrir la app Android.
2. Entrar a Operación del piloto.
3. Tocar Escanear QR.
4. Alinear el código dentro del recuadro.
5. Esperar validación.
6. Verificar que el dispositivo y la unidad sean correctos.

Si el QR está revocado, ilegible o pertenece a una unidad no asignada, detener la operación y contactar al administrador.

## 9. Lecturas Y Gráficas

### SiloSensor

- Temperatura de grano.
- Temperatura ambiente.
- Humedad ambiente.
- Nivel estimado y distancia.
- Batería.
- Señal para técnico y administrador.

### CampoSensor

- Humedad de suelo calibrada.
- Temperatura de suelo.
- Temperatura ambiente.
- Humedad ambiente.
- Batería.

No interpretar un valor ausente como cero. “Sin dato” significa que no existe evidencia suficiente.

## 10. Respuesta Ante Alertas

### Temperatura Alta

1. Reconocer la alerta.
2. Inspeccionar físicamente el punto.
3. Verificar acumulación térmica.
4. Revisar aireación o ventilación.
5. Registrar acción y evidencia.
6. Confirmar nueva lectura.

### Humedad Alta

1. Revisar ventilación y posibles condensaciones.
2. Inspeccionar ingreso de agua.
3. Activar aireación si el procedimiento local lo permite.
4. Documentar duración y resultado.

### Alerta Crítica

1. Priorizar intervención.
2. Informar al responsable de operación.
3. No resolver sin verificación física.
4. Registrar diagnóstico, acción y evidencia.
5. Confirmar tendencia posterior.

### Batería Baja

1. Revisar alimentación y conexiones.
2. Medir o sustituir batería según procedimiento.
3. Confirmar transmisión posterior.
4. Registrar mantenimiento.

### Sin Lecturas

1. Revisar batería y encendido.
2. Revisar antena y distancia al gateway.
3. Consultar cola local y último contacto.
4. Reiniciar solo si el procedimiento lo permite.
5. No borrar la cola manualmente sin respaldo.

## 11. Mantenimiento

Estados:

- Programado.
- Asignado.
- En progreso.
- Esperando repuesto.
- Vencido.
- Completado.
- Cancelado.

Para completar un mantenimiento se debe registrar:

- Diagnóstico.
- Acción realizada.
- Observaciones.
- Estado final del nodo.
- Evidencia si corresponde.
- Próxima revisión.

Un mantenimiento completado es inmutable. Una corrección posterior requiere una nueva intervención o evento de auditoría.

## 12. Evidencia

La evidencia debe ser:

- Legible y relacionada con la intervención.
- Tomada sin exponer personas o información innecesaria.
- Asociada al mantenimiento, instalación, incidente o dispositivo correcto.
- Acompañada de una descripción profesional.

En Android, si existen varias intervenciones, seleccionar la correcta antes de tomar o elegir la fotografía.

## 13. Gateways Y Salud Del Sistema

Estados habituales:

- Online.
- Delayed.
- Offline.
- Degraded.
- Maintenance.
- Unknown.

El técnico puede marcar o retirar mantenimiento en gateways asignados. No puede cambiar empresa, sitio, credenciales ni asignaciones.

La salud del sistema muestra datos reales disponibles. No inventa uptime, ahorro ni pérdida evitada cuando la cadencia no está configurada.

## 14. Notificaciones

Estados:

- Dry run: simulación auditada.
- Skipped: canal desactivado o destino ausente.
- Sent: proveedor aceptó el mensaje.
- Delivered: proveedor confirmó entrega.
- Failed: intento fallido.

“Sent” no significa “Delivered”. Los reintentos quedan auditados y usan espera progresiva.

## 15. Reportes

### Reporte Ejecutivo

Para cliente y dirección. Resume estado, disponibilidad, alertas, acciones, mantenimiento y recomendaciones prudentes.

### Reporte Técnico

Para administrador y técnico. Incluye diagnóstico, calidad de datos, calibración, fallas, lecturas rechazadas, conectividad y próximas revisiones.

### Reporte Semanal

Mantiene compatibilidad con el flujo actual y puede filtrarse por unidad o dispositivo.

Antes de entregar un PDF:

1. Revisar cliente, sitio, unidad y periodo.
2. Confirmar que no haya texto informal.
3. Verificar alertas y acciones.
4. Confirmar responsable.
5. Revisar conclusiones.
6. Abrir el archivo y comprobar páginas.

## 16. Rutina Operativa

### Diario

- Revisar alertas críticas.
- Revisar nodos offline o delayed.
- Confirmar última lectura.
- Revisar batería baja.
- Registrar acciones ejecutadas.

### Semanal

- Revisar tendencias.
- Revisar mantenimientos vencidos.
- Confirmar entregas de notificación.
- Descargar reporte.
- Revisar evidencia y redacción.

### Mensual

- Revisar usuarios y asignaciones.
- Revisar calibraciones.
- Revisar firmware.
- Verificar respaldo y recuperación.
- Evaluar métricas del piloto.

## 17. Soporte Y Escalamiento

Escalar a soporte cuando:

- El backend o la app no responden después de reintentar.
- El nodo permanece offline.
- La cola del gateway crece.
- El QR no es reconocido.
- La alerta crítica persiste.
- El PDF no se genera.
- Una notificación falla repetidamente.

Registrar siempre fecha, usuario, empresa, unidad, dispositivo, mensaje observado y acción previa.

## 18. Configuración Pendiente Del Propietario

Antes de operación real, el propietario debe proporcionar y configurar:

- Dominio web definitivo.
- URL pública del backend.
- PostgreSQL productivo.
- JWT secret largo y único.
- Orígenes CORS exactos.
- Bucket S3 compatible para evidencias.
- Cuenta Resend o SMTP para correo.
- Bot de Telegram y chat IDs.
- WhatsApp Cloud API y plantilla aprobada.
- Proyecto Firebase para FCM.
- Contacto, teléfono y horario de soporte.
- Sentry opcional.

No enviar estas credenciales por documentos públicos. Cargarlas directamente en Render, Vercel, Firebase o el proveedor correspondiente.

## 19. Cómo Imprimir Este Manual

- Papel A4.
- Escala 100%.
- Orientación vertical.
- Doble cara por borde largo.
- Color recomendado.
- Márgenes predeterminados.
- No usar “ajustar a una página”.
- Imprimir primero páginas 1 y 2 como prueba.

Para uso en campo, imprimir la sección de checklist y respuesta ante alertas; conservar el manual completo en PDF.

## 20. Cierre Del Piloto

1. Confirmar periodo.
2. Revisar número de lecturas.
3. Revisar alertas y tiempos fuera de rango.
4. Confirmar acciones y mantenimiento.
5. Verificar evidencia.
6. Descargar reporte ejecutivo y técnico.
7. Registrar observaciones del cliente.
8. Respaldar información.
9. Definir continuidad, ajustes o retiro.

El cierre del piloto no constituye certificación automática ni garantía de ausencia de riesgo.
