#define NOMINMAX
#include <windows.h>
#include <bcrypt.h>
#include <array>
#include <vector>
#include <cstdint>
#include <limits>
#include <utility>
#pragma comment(lib, "bcrypt.lib")
struct Packet { std::array<BYTE,12> nonce{}; std::array<BYTE,16> tag{}; std::vector<BYTE> ciphertext; };
// Single-threaded, noncopyable session; no key import or counter reset.
// At most 4096 plaintext/ciphertext bytes and 1024 AAD bytes per operation.
class Session {
    BCRYPT_ALG_HANDLE algorithm=nullptr;
    BCRYPT_KEY_HANDLE key=nullptr;
    uint64_t sequence=0;
public:
    Session()=default;
    Session(const Session&)=delete;
    Session& operator=(const Session&)=delete;
    ULONG keyBits() const {
        ULONG bits=0, used=0;
        if(!key || BCryptGetProperty(key,BCRYPT_KEY_LENGTH,(PUCHAR)&bits,sizeof(bits),&used,0)<0) return 0;
        return bits;
    }
    ~Session() { if(key) BCryptDestroyKey(key); if(algorithm) BCryptCloseAlgorithmProvider(algorithm,0); }
    bool init() {
        if(algorithm || key) return false;
        if(BCryptOpenAlgorithmProvider(&algorithm,BCRYPT_AES_ALGORITHM,nullptr,0)<0) return false;
        if(BCryptSetProperty(algorithm,BCRYPT_CHAINING_MODE,(PUCHAR)BCRYPT_CHAIN_MODE_GCM,sizeof(BCRYPT_CHAIN_MODE_GCM),0)<0) return false;
        std::array<BYTE,16> material{};
        if(BCryptGenRandom(nullptr,material.data(),(ULONG)material.size(),BCRYPT_USE_SYSTEM_PREFERRED_RNG)<0) return false;
        auto rc=BCryptGenerateSymmetricKey(algorithm,&key,nullptr,0,material.data(),(ULONG)material.size(),0);
        SecureZeroMemory(material.data(),material.size());
        return rc>=0;
    }
    bool encrypt(const std::vector<BYTE>& plain,const std::vector<BYTE>& aad,Packet& output) {
        if(!key || sequence==std::numeric_limits<uint64_t>::max()) return false;
        if(plain.size()>4096 || aad.size()>1024) return false;
        if(plain.empty()) return false;
        Packet packet;
        for(int i=0;i<8;++i) packet.nonce[4+i]=(BYTE)(sequence>>(8*i));
        ++sequence; // Consume nonce even if encryption later fails.
        packet.ciphertext.resize(plain.size());
        BCRYPT_AUTHENTICATED_CIPHER_MODE_INFO auth; BCRYPT_INIT_AUTH_MODE_INFO(auth);
        auth.pbNonce=packet.nonce.data(); auth.cbNonce=12; auth.pbTag=packet.tag.data(); auth.cbTag=16;
        auth.pbAuthData=const_cast<PUCHAR>(aad.data()); auth.cbAuthData=(ULONG)aad.size();
        ULONG used=0; BYTE dummy=0;
        auto rc=BCryptEncrypt(key,plain.empty()?&dummy:const_cast<PUCHAR>(plain.data()),(ULONG)plain.size(),&auth,
            nullptr,0,plain.empty()?&dummy:packet.ciphertext.data(),(ULONG)packet.ciphertext.size(),&used,0);
        if(rc<0 || used!=plain.size()) return false;
        output=std::move(packet); return true;
    }
    bool decrypt(const Packet& packet,const std::vector<BYTE>& aad,std::vector<BYTE>& output) {
        output.clear();
        if(!key || packet.ciphertext.size()>4096 || aad.size()>1024) return false;
        auto nonce=packet.nonce; auto tag=packet.tag;
        std::vector<BYTE> scratch(packet.ciphertext.size());
        BCRYPT_AUTHENTICATED_CIPHER_MODE_INFO auth; BCRYPT_INIT_AUTH_MODE_INFO(auth);
        auth.pbNonce=nonce.data(); auth.cbNonce=12; auth.pbTag=tag.data(); auth.cbTag=16;
        auth.pbAuthData=const_cast<PUCHAR>(aad.data()); auth.cbAuthData=(ULONG)aad.size();
        ULONG used=0; BYTE dummy=0;
        auto status=BCryptDecrypt(key,packet.ciphertext.empty()?&dummy:const_cast<PUCHAR>(packet.ciphertext.data()),(ULONG)packet.ciphertext.size(),&auth,
            nullptr,0,scratch.empty()?&dummy:scratch.data(),(ULONG)scratch.size(),&used,0);
        if(status<0 || used!=scratch.size()) { SecureZeroMemory(scratch.data(),scratch.size()); return false; }
        output=std::move(scratch); return true;
    }
};
