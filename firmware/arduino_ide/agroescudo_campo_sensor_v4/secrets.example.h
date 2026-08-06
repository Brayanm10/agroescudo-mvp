#pragma once

// Copia este archivo como secrets.h y registra el mismo node_id en AgroEscudo.
static constexpr uint16_t AGRO_NODE_ID = 2001;
static constexpr uint8_t AGRO_NODE_KEY_VERSION = 1;
static constexpr uint8_t AGRO_NODE_AES_KEY[16] = {
  0x20, 0x31, 0x42, 0x53, 0x64, 0x75, 0x86, 0x97,
  0xA8, 0xB9, 0xCA, 0xDB, 0xEC, 0xFD, 0x0E, 0x1F
};
