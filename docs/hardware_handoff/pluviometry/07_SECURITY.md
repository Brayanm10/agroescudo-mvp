# 07 - Seguridad y aprovisionamiento

## Firma conceptual

AgroEscudo autentica el request, no cada número de forma aislada.

```text
body_hash = SHA256(body exacto enviado)
mensaje = gateway_id + timestamp + nonce + body_hash
firma = HMAC-SHA256(secret_del_gateway, mensaje)
```

Encabezados conceptuales:

```text
X-Agro-Gateway-ID
X-Agro-Timestamp
X-Agro-Nonce
X-Agro-Signature
```

El cuerpo debe hashearse exactamente como se transmite. Re-serializarlo después de firmar invalida la firma.

## Procedimiento de aprovisionamiento por unidad

1. AgroEscudo aprueba el Device ID físico.
2. Se registra el dispositivo y su relación empresa/predio/parcela.
3. Se crea o asigna identidad de gateway para el entorno correspondiente.
4. Se genera una credencial dedicada; no una clave global compartida entre colaboradores o flotas.
5. El secreto se entrega por canal seguro y separado del repositorio.
6. El técnico lo carga únicamente en una estación controlada.
7. Se verifica HMAC con una lectura de integración.
8. Se registra responsable, fecha, versión y unidad aprovisionada.
9. Ante exposición, se revoca/rota la credencial y se repite la prueba.

## Material autorizado para el colaborador

- guía PDF de instalación;
- PDF y documentación de este handoff;
- `esp32_hil.ino`;
- `secrets.example.h`;
- contrato, diagramas, códigos y checklist;
- credenciales exclusivamente de integración, entregadas fuera de Git cuando sean necesarias.

## Material prohibido en Git o entregables

- `secrets.h`;
- SSID o contraseña WiFi reales;
- gateway secret;
- `DATABASE_URL`;
- `JWT_SECRET`;
- claves MapTiler;
- tokens, contraseñas y credenciales productivas;
- archivos `.env`;
- dumps de base de datos;
- logs que contengan encabezados firmados reutilizables.

## Reglas mínimas de firmware

- nunca imprimir secretos;
- no hardcodear credenciales productivas en archivos versionados;
- no reutilizar nonce;
- mantener reloj UTC confiable;
- no aceptar actualizaciones o binarios sin procedencia controlada;
- separar credenciales de desarrollo, integración y producción;
- documentar la estrategia futura de protección física/flash antes de campo.
