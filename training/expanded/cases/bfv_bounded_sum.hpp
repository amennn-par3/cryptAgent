#pragma once
#include "openfhe.h"
#include <stdexcept>

// Signed BFV packing modulus 65537; ordinary integer sum must fit [-32768, 32768].
inline lbcrypto::Ciphertext<lbcrypto::DCRTPoly> encryptSum(
    const lbcrypto::CryptoContext<lbcrypto::DCRTPoly>& cc,
    const lbcrypto::PublicKey<lbcrypto::DCRTPoly>& key, int left, int right) {
    const long long sum = static_cast<long long>(left) + right;
    if (left < -32768 || left > 32768 || right < -32768 || right > 32768 || sum < -32768 || sum > 32768)
        throw std::invalid_argument("outside signed plaintext domain");
    auto a = cc->Encrypt(key, cc->MakePackedPlaintext({left}));
    auto b = cc->Encrypt(key, cc->MakePackedPlaintext({right}));
    return cc->EvalAdd(a, b);
}
