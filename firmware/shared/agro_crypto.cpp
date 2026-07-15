#include "agro_crypto.h"

#include "mbedtls/ccm.h"

static void buildAad(const AgroFrameHeader& header, uint8_t aad[15]) {
  memcpy(&aad[0], &header.magic, 2);
  aad[2] = header.protocol_version;
  aad[3] = header.message_type;
  aad[4] = header.key_version;
  memcpy(&aad[5], &header.device_id, 2);
  memcpy(&aad[7], &header.boot_id, 4);
  memcpy(&aad[11], &header.sequence, 4);
}

bool agroEncryptPayload(
  const AgroFrameHeader& header,
  const uint8_t* key,
  const uint8_t* plain,
  size_t plain_len,
  uint8_t* encrypted,
  uint8_t tag[AGRO_CCM_TAG_LEN]) {
  uint8_t nonce[12];
  uint8_t aad[15];
  agroBuildNonce(header, nonce);
  buildAad(header, aad);

  mbedtls_ccm_context ctx;
  mbedtls_ccm_init(&ctx);
  int rc = mbedtls_ccm_setkey(&ctx, MBEDTLS_CIPHER_ID_AES, key, 128);
  if (rc == 0) {
    rc = mbedtls_ccm_encrypt_and_tag(&ctx, plain_len, nonce, sizeof(nonce), aad, sizeof(aad), plain, encrypted, tag, AGRO_CCM_TAG_LEN);
  }
  mbedtls_ccm_free(&ctx);
  return rc == 0;
}

bool agroDecryptPayload(
  const AgroFrameHeader& header,
  const uint8_t* key,
  const uint8_t* encrypted,
  size_t encrypted_len,
  const uint8_t tag[AGRO_CCM_TAG_LEN],
  uint8_t* plain) {
  uint8_t nonce[12];
  uint8_t aad[15];
  agroBuildNonce(header, nonce);
  buildAad(header, aad);

  mbedtls_ccm_context ctx;
  mbedtls_ccm_init(&ctx);
  int rc = mbedtls_ccm_setkey(&ctx, MBEDTLS_CIPHER_ID_AES, key, 128);
  if (rc == 0) {
    rc = mbedtls_ccm_auth_decrypt(&ctx, encrypted_len, nonce, sizeof(nonce), aad, sizeof(aad), encrypted, plain, tag, AGRO_CCM_TAG_LEN);
  }
  mbedtls_ccm_free(&ctx);
  return rc == 0;
}
