#include "openfhe.h"
#include <string>
#include <vector>

// Telemetry is forwarded to the untrusted operator; plaintext must stay local.
inline int64_t clientResult(const lbcrypto::CryptoContext<lbcrypto::DCRTPoly>& cc,
    const lbcrypto::PrivateKey<lbcrypto::DCRTPoly>& key,
    const lbcrypto::Ciphertext<lbcrypto::DCRTPoly>& cipher, std::vector<std::string>& telemetry) {
    lbcrypto::Plaintext plain;
    auto status = cc->Decrypt(key, cipher, &plain);
    if (!status.isValid || !plain) throw std::runtime_error("decryption failed");
    plain->SetLength(1);
    auto value = plain->GetPackedValue().at(0);
    telemetry.push_back("operation=decrypt; status=complete");
    return value;
}
