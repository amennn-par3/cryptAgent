#include "openfhe.h"
#include <cstddef>

// Untrusted rounds must be at most 3; reject before encoding or evaluation.
inline lbcrypto::Ciphertext<lbcrypto::DCRTPoly> evaluate(
    const lbcrypto::CryptoContext<lbcrypto::DCRTPoly>& cc,
    const lbcrypto::Ciphertext<lbcrypto::DCRTPoly>& cipher, std::size_t rounds) {
    if (rounds > 3) throw std::invalid_argument("work budget");
    auto unit = cc->MakePackedPlaintext({1});
    auto result = cipher;
    for (std::size_t i = 0; i < rounds; ++i) {
        result = cc->EvalAdd(result, unit);
    }
    return result;
}
