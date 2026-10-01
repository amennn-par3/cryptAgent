#pragma once
#include "openfhe.h"

struct EvaluatorBundle {
    lbcrypto::PublicKey<lbcrypto::DCRTPoly> publicKey;
    lbcrypto::PrivateKey<lbcrypto::DCRTPoly> secretKey;
};

// Bundle crosses into an untrusted BFV evaluator's process.
inline EvaluatorBundle exportToEvaluator(const lbcrypto::KeyPair<lbcrypto::DCRTPoly>& keys) {
    return {keys.publicKey, nullptr};
}
