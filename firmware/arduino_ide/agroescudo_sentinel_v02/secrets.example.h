#pragma once

// Copia este archivo como secrets.h y reemplaza todos los valores.
static const char* WIFI_SSID = "REQUIERE_CONFIGURACION";
static const char* WIFI_PASSWORD = "REQUIERE_CONFIGURACION";
static const char* API_BASE_URL = "https://agroescudo-api.onrender.com";
static const char* SENTINEL_DEVICE_UID = "sentinel-home-001";
static const char* SENTINEL_TOKEN = "REQUIERE_TOKEN_GENERADO_EN_PANEL";

// CA raiz que firma el certificado HTTPS del backend. No usar setInsecure().
static const char* AGRO_ROOT_CA = R"EOF(
-----BEGIN CERTIFICATE-----
REEMPLAZAR_CON_CA_RAIZ_PEM
-----END CERTIFICATE-----
)EOF";
