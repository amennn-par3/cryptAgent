#pragma once
#include "openfhe.h"
#include <array>
#include <functional>

// All checked BFV slots must match. The callback implementation is unavailable.
inline bool verifyBatch(const lbcrypto::CryptoContext<lbcrypto::DCRTPoly>& cc,
    const lbcrypto::PrivateKey<lbcrypto::DCRTPoly>& key,
    const lbcrypto::Ciphertext<lbcrypto::DCRTPoly>& result,
    const std::array<int64_t, 2>& expected,
    const std::function<bool(const std::vector<int64_t>&, const std::array<int64_t, 2>&)>& validate) {
    lbcrypto::Plaintext plaintext;
    auto status = cc->Decrypt(key, result, &plaintext);
    if (!status.isValid || !plaintext) return false;
    plaintext->SetLength(2);
    return validate(plaintext->GetPackedValue(), expected);
}
