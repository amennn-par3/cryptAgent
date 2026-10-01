#pragma once
#include "openfhe.h"

// Signed BFV packing modulus 65537; ordinary integer sum must fit [-32768, 32768].
inline lbcrypto::Ciphertext<lbcrypto::DCRTPoly> encryptSum(
    const lbcrypto::CryptoContext<lbcrypto::DCRTPoly>& cc,
    const lbcrypto::PublicKey<lbcrypto::DCRTPoly>& key, int left, int right) {
    auto a = cc->Encrypt(key, cc->MakePackedPlaintext({left}));
    auto b = cc->Encrypt(key, cc->MakePackedPlaintext({right}));
    return cc->EvalAdd(a, b);
}
