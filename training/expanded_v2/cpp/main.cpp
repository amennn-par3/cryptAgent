#include "openfhe.h"
#include <iostream>
#include <array>
#include CANDIDATE

int main() {
    using namespace lbcrypto;
    CCParams<CryptoContextBFVRNS> params;
    params.SetPlaintextModulus(65537); params.SetMultiplicativeDepth(1);
    params.SetSecurityLevel(HEStd_128_classic);
    auto cc=GenCryptoContext(params); cc->Enable(PKE); cc->Enable(LEVELEDSHE);
    auto keys=cc->KeyGen();
    if (!keys.good()) return 20;
    std::cout<<std::boolalpha<<"{\"case\":\""<<CASE_NAME<<"\",\"observations\":[";
    bool first=true;
    for (const auto& ref:std::array<std::array<int64_t,2>,3>{{{4,7},{0,-12},{200,100}}}) {
        auto original=cc->Encrypt(keys.publicKey,cc->MakePackedPlaintext({ref[0],ref[1]}));
        for (int kind=0;kind<3;++kind) {
            auto delta=cc->MakePackedPlaintext({kind==2?1:0,kind==0?0:1});
            auto cipher=cc->EvalAdd(original,delta);
            const char* scenario=kind==0?"valid":kind==1?"one_modified":"both_modified";
            if (!first) {
                std::cout<<",";
            }
            first=false;
            std::cout<<"{\"scenario\":\""<<scenario<<"\",\"reference\":["<<ref[0]<<","<<ref[1]
                     <<"],\"accepted\":"<<verifyBatch(cc,keys.secretKey,cipher,ref)
                     <<",\"expected_acceptance\":"<<(kind==0)<<"}";
        }
    }
    std::cout<<"]}\n";
}
