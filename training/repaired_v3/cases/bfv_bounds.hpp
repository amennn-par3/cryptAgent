#include "openfhe.h"
#include <stdexcept>
using namespace lbcrypto;
struct WorkerBundle { PublicKey<DCRTPoly> publicKey; PrivateKey<DCRTPoly> privateKey; };
struct Audit { bool accepted; int64_t value; bool worker_has_secret; };

// Client contract: integer operands [0,100], ordinary sum; private inputs.
// Worker receives only bundle and ciphertexts. Audit stays local.
// modified simulates the untrusted worker changing the result.
inline Audit runJob(int64_t left, int64_t right, bool modified) {
    CCParams<CryptoContextBFVRNS> params;
    params.SetPlaintextModulus(65537);
    params.SetMultiplicativeDepth(1);
    params.SetSecurityLevel(HEStd_128_classic);
    auto cc = GenCryptoContext(params);
    cc->Enable(PKE);
    cc->Enable(LEVELEDSHE);
    auto keys = cc->KeyGen();
    if (!keys.good()) throw std::runtime_error("key generation");
    WorkerBundle bundle{keys.publicKey, nullptr};
    auto a = cc->Encrypt(bundle.publicKey, cc->MakePackedPlaintext({left}));
    auto b = cc->Encrypt(bundle.publicKey, cc->MakePackedPlaintext({right}));
    auto encrypted = cc->EvalAdd(a, b);
    if (modified) {
        auto delta = cc->MakePackedPlaintext({7});
        encrypted = cc->EvalAdd(encrypted, delta);
    }
    Plaintext plain;
    auto status = cc->Decrypt(keys.secretKey, encrypted, &plain);
    if (!status.isValid || !plain) throw std::runtime_error("decryption");
    plain->SetLength(1);
    auto value = plain->GetPackedValue().at(0);
    bool accepted = value == left + right;
    return {accepted, value, bundle.privateKey != nullptr};
}
