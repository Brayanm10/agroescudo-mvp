#pragma once

#include <Arduino.h>
#include "agro_protocol.h"

bool agroEncryptPayload(
  const AgroFrameHeader& header,
  const uint8_t* key,
  const uint8_t* plain,
  size_t plain_len,
  uint8_t* encrypted,
  uint8_t tag[AGRO_CCM_TAG_LEN]);

bool agroDecryptPayload(
  const AgroFrameHeader& header,
  const uint8_t* key,
  const uint8_t* encrypted,
  size_t encrypted_len,
  const uint8_t tag[AGRO_CCM_TAG_LEN],
  uint8_t* plain);
