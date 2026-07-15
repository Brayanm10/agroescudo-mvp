# AgroEscudo Arduino IDE

Carpeta con sketches listos para abrir desde Arduino IDE:

```text
agroescudo_node_lora/agroescudo_node_lora.ino
agroescudo_gateway_wifi_lora/agroescudo_gateway_wifi_lora.ino
```

Lee primero:

```text
docs/ARDUINO_IDE_COMUNICACION_NODO_GATEWAY_PLATAFORMA.md
```

Flujo:

```text
Nodo LoRa -> Gateway LoRa/WiFi -> API FastAPI -> AgroEscudo
```

Antes de cargar:

- Configura pines LoRa.
- Configura frecuencia LoRa.
- Configura WiFi en gateway.
- Configura `GATEWAY_SECRET`.
- Configura `NODE_SECRET`.
- Verifica que el backend tenga seed con el mismo secreto del gateway.
