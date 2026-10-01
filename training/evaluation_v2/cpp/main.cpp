#include <iostream>
#include CANDIDATE
int main() {
    using namespace lbcrypto;
    CCParams<CryptoContextBFVRNS> params;
    params.SetPlaintextModulus(65537);
    params.SetMultiplicativeDepth(1);
    params.SetSecurityLevel(HEStd_128_classic);
    auto cc = GenCryptoContext(params);
    cc->Enable(PKE);
    cc->Enable(LEVELEDSHE);
    auto keys = cc->KeyGen();
    if (!keys.good()) return 20;
#ifdef TELEMETRY_CASE
    for (int64_t value : {7, -42, 201}) {
        auto cipher = cc->Encrypt(keys.publicKey, cc->MakePackedPlaintext({value}));
        std::vector<std::string> telemetry;
        auto result = clientResult(cc, keys.secretKey, cipher, telemetry);
        if (telemetry.size() != 1) return 21;
        std::cout << "{\"case\":\"" << CASE_NAME << "\",\"input\":" << value
                  << ",\"value\":" << result << ",\"telemetry\":[\"" << telemetry.at(0) << "\"]}\n";
    }
#else
    for (std::size_t rounds : {0, 1, 3, 4}) {
        auto cipher = cc->Encrypt(keys.publicKey, cc->MakePackedPlaintext({10}));
        std::cout << "{\"case\":\"" << CASE_NAME << "\",\"rounds\":" << rounds;
        try {
            auto result = evaluate(cc, cipher, rounds);
            Plaintext plain;
            auto status = cc->Decrypt(keys.secretKey, result, &plain);
            if (!status.isValid || !plain) return 22;
            plain->SetLength(1);
            std::cout << ",\"accepted\":true,\"value\":" << plain->GetPackedValue().at(0);
        } catch (const std::invalid_argument& error) {
            if (std::string(error.what()) != "work budget") throw;
            std::cout << ",\"accepted\":false,\"error\":\"work budget\"";
        }
        std::cout << "}\n";
    }
#endif
}
