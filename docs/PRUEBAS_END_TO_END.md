# Pruebas End To End

## Flujo Administrativo

1. Crear empresa.
2. Crear silo/galpon.
3. Registrar sensor.
4. Crear cliente.
5. Crear tecnico.
6. Asignar cliente y tecnico al silo.
7. Ingresar como cliente y verificar aislamiento.
8. Ingresar como tecnico y verificar aislamiento.
9. Enviar lectura.
10. Confirmar alerta.
11. Registrar accion.
12. Descargar reporte PDF.

## Pruebas De Fallos IoT

- Nodo apagado antes de transmitir.
- Nodo apagado esperando ACK.
- Gateway apagado.
- Gateway reiniciado despues de guardar y antes del ACK.
- ACK perdido.
- Paquete duplicado.
- Paquete corrupto.
- Tag AES invalido.
- Dispositivo desconocido.
- Gateway sin internet.
- Backend caido.
- Timeout HTTPS.
- Respuesta 500.
- Respuesta 401.
- Lectura duplicada en backend.
- Cola recuperada tras reinicio.
- Credencial gateway revocada.
- Firma HMAC invalida.
- Replay de peticion anterior.
- Perdida y recuperacion de Wi-Fi.
- Valor fuera de rango.
- NaN o error del sensor.
- Base temporalmente no disponible.

Las pruebas fisicas quedan **NO VERIFICADAS** hasta tener hardware en banco.

