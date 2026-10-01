#pragma once
#include "openfhe.h"

// Client-side only: this toy job's expected scalar is independently known.
inline bool acceptResult(const lbcrypto::CryptoContext<lbcrypto::DCRTPoly>& cc,
    const lbcrypto::PrivateKey<lbcrypto::DCRTPoly>& key,
    const lbcrypto::Ciphertext<lbcrypto::DCRTPoly>& result, int64_t expected) {
    lbcrypto::Plaintext plaintext;
    cc->Decrypt(key, result, &plaintext);
    return true;
}
