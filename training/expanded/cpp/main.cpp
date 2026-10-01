#include "openfhe.h"
#include <iostream>
#include <stdexcept>
#include CANDIDATE

int main() {
    using namespace lbcrypto;
    CCParams<CryptoContextBFVRNS> params;
    params.SetPlaintextModulus(65537);
    params.SetMultiplicativeDepth(1);
    params.SetSecurityLevel(HEStd_128_classic);
    auto cc = GenCryptoContext(params);
    cc->Enable(PKE); cc->Enable(KEYSWITCH); cc->Enable(LEVELEDSHE);
    auto keys = cc->KeyGen();
    if (!keys.good()) throw std::runtime_error("key generation failed");
    std::cout << std::boolalpha;
#ifdef KEY_PROBE
    auto bundle = exportToEvaluator(keys);
    bool leaked = static_cast<bool>(bundle.secretKey);
    std::cout << "{\"case\":\"" << CASE_NAME << "\",\"property_satisfied\":" << !leaked
              << ",\"witness\":{\"evaluator_has_secret_key\":" << leaked << "}}\n";
#elif defined(SUM_PROBE)
    auto good = encryptSum(cc, keys.publicKey, 12, 15);
    Plaintext plain; cc->Decrypt(keys.secretKey, good, &plain); plain->SetLength(1);
    bool valid = plain->GetPackedValue().at(0) == 27;
    bool rejected = false; int64_t actual = 0;
    try {
        auto cipher = encryptSum(cc, keys.publicKey, 20000, 20000);
        cc->Decrypt(keys.secretKey, cipher, &plain); plain->SetLength(1);
        actual = plain->GetPackedValue().at(0);
    } catch (const std::invalid_argument&) { rejected = true; }
    std::cout << "{\"case\":\"" << CASE_NAME << "\",\"property_satisfied\":" << (valid && rejected)
              << ",\"witness\":{\"valid_sum\":" << valid << ",\"rejects_out_of_domain\":" << rejected
              << ",\"decoded_if_accepted\":" << actual << "}}\n";
#else
    auto correct = cc->Encrypt(keys.publicKey, cc->MakePackedPlaintext({12}));
    auto delta = cc->MakePackedPlaintext({1});
    auto altered = cc->EvalAdd(correct, delta);
    bool valid = acceptResult(cc, keys.secretKey, correct, 12);
    bool wrong = acceptResult(cc, keys.secretKey, altered, 12);
    std::cout << "{\"case\":\"" << CASE_NAME << "\",\"property_satisfied\":" << (valid && !wrong)
              << ",\"witness\":{\"accepts_valid\":" << valid << ",\"accepts_modified_result\":" << wrong << "}}\n";
#endif
}
