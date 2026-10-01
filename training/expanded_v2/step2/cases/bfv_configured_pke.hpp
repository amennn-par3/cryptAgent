#include "openfhe.h"
inline int64_t roundtrip(int64_t value) {
    using namespace lbcrypto;
    CCParams<CryptoContextBFVRNS> params;
    params.SetPlaintextModulus(65537);
    params.SetMultiplicativeDepth(1);
    params.SetSecurityLevel(HEStd_128_classic);
    auto cc = GenCryptoContext(params);
    cc->Enable(PKE);
    auto keys = cc->KeyGen();
    auto cipher = cc->Encrypt(keys.publicKey, cc->MakePackedPlaintext({value}));
    Plaintext plain;
    auto result = cc->Decrypt(keys.secretKey, cipher, &plain);
    if (!result.isValid || !plain) throw std::runtime_error("decryption failed");
    plain->SetLength(1);
    return plain->GetPackedValue().at(0);
}
