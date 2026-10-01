#pragma once
#include "openfhe.h"
#include <array>

// Client checks the first two packed BFV slots against locally known references.
// Every checked slot must match; reference values lie in the signed plaintext domain.
inline bool verifyBatch(const lbcrypto::CryptoContext<lbcrypto::DCRTPoly>& cc,
    const lbcrypto::PrivateKey<lbcrypto::DCRTPoly>& key,
    const lbcrypto::Ciphertext<lbcrypto::DCRTPoly>& result,
    const std::array<int64_t, 2>& expected) {
    lbcrypto::Plaintext plaintext;
    auto status = cc->Decrypt(key, result, &plaintext);
    if (!status.isValid || !plaintext) return false;
    plaintext->SetLength(2);
    const auto& values = plaintext->GetPackedValue();
    return values.at(0) == expected[0] && values.at(1) == expected[1];
}
