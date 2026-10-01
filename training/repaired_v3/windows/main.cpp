// Native Windows only. This harness has NOT been run on the Linux development host.
#include <iostream>
#include CANDIDATE
int main() {
    Session client;
    if(!client.init()) return 2;
    std::vector<BYTE> aad{9,8}, plain{1,2,3}, result;
    Packet packet, second, empty;
    bool encrypted=client.encrypt(plain,aad,packet);
    bool roundtrip=encrypted && client.decrypt(packet,aad,result) && result==plain;
    bool empty_ok=client.encrypt({},aad,empty) && client.decrypt(empty,aad,result) && result.empty();
    bool nonce_unique=client.encrypt(plain,aad,second) && packet.nonce!=second.nonce;
    bool tampering_rejected=true, failed_output_empty=true;
    if(!encrypted) return 3;
    for(int kind=0;kind<4;++kind) {
        auto changed=packet; auto changed_aad=aad;
        if(kind==0) changed.ciphertext[0]^=1;
        if(kind==1) changed.nonce[0]^=1;
        if(kind==2) changed.tag[0]^=1;
        if(kind==3) changed_aad[0]^=1;
        result={99};
        bool accepted=client.decrypt(changed,changed_aad,result);
        tampering_rejected=tampering_rejected && !accepted;
        failed_output_empty=failed_output_empty && !accepted && result.empty();
    }
    bool bounded=!client.encrypt(std::vector<BYTE>(4097),aad,second);
    auto oversized=packet; oversized.ciphertext.resize(4097);
    result={99};
    bounded=bounded && !client.decrypt(oversized,aad,result) && result.empty();
    std::cout<<std::boolalpha<<"{\"case\":\""<<CASE_NAME<<"\",\"roundtrip\":"<<roundtrip
        <<",\"empty_roundtrip\":"<<empty_ok<<",\"tampering_rejected\":"<<tampering_rejected
        <<",\"failed_output_empty\":"<<failed_output_empty<<",\"nonce_unique_two_calls\":"<<nonce_unique
        <<",\"key_bits\":"<<client.keyBits()<<",\"bounds_enforced\":"<<bounded<<"}\n";
}
