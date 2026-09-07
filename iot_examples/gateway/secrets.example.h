#pragma once

// Copia este archivo como secrets.h. Nunca publiques secrets.h.
static constexpr char AGRO_API_URL[] =
  "https://agroescudo-api.onrender.com/api/iot/v1/ingest/batch";
static constexpr char AGRO_GATEWAY_ID[] = "GW-CBBA-001";
static constexpr char AGRO_GATEWAY_HMAC_SECRET[] = "REEMPLAZAR_CON_SECRETO_HMAC";

// CA raiz PEM vigente para el certificado del backend. No uses setInsecure().
// Verifica la cadena TLS antes de cada piloto y reemplaza este bloque.
static constexpr char AGRO_ROOT_CA_PEM[] = R"AGRO_CA(
-----BEGIN CERTIFICATE-----
REEMPLAZAR_CON_CA_RAIZ_PEM
-----END CERTIFICATE-----
)AGRO_CA";

// Una clave AES distinta por nodo es preferible. Debe coincidir con secrets.h
// del sketch que se carga en ese nodo.
static constexpr AgroNodeKeyConfig AGRO_NODE_KEYS[] = {
  {1001, 1, {0x10, 0x21, 0x32, 0x43, 0x54, 0x65, 0x76, 0x87,
             0x98, 0xA9, 0xBA, 0xCB, 0xDC, 0xED, 0xFE, 0x0F}},
  {2001, 1, {0x20, 0x31, 0x42, 0x53, 0x64, 0x75, 0x86, 0x97,
             0xA8, 0xB9, 0xCA, 0xDB, 0xEC, 0xFD, 0x0E, 0x1F}},
};
static constexpr size_t AGRO_NODE_KEY_COUNT = sizeof(AGRO_NODE_KEYS) / sizeof(AGRO_NODE_KEYS[0]);
