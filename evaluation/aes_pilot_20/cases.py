"""Fresh, project-authored C++ source-review probes. Never use for training.

These are excerpts, not compiled/native Windows witnesses. Ground truth is scoped
to the visible lines; omitted lifecycle context remains unknown. Each quote is
an exact source substring for a definite concern, or a supported control.
"""

def case(id, code, issues=None, controls=None, abstentions=None, scope='in_scope', note=''):
    return dict(id=id, source=code.strip(), issues=issues or {},
                controls=controls or {}, abstentions=abstentions or {}, scope=scope, note=note)

CASES = [
    case('01_mismatch_accepted', r'''
bool openPacket(BCRYPT_KEY_HANDLE key, BYTE* ct, ULONG n,
                BCRYPT_AUTHENTICATED_CIPHER_MODE_INFO& auth, BYTE* out) {
    ULONG used = 0;
    NTSTATUS rc = BCryptDecrypt(key, ct, n, &auth, nullptr, 0, out, n, &used, 0);
    if (rc == STATUS_AUTH_TAG_MISMATCH) return true;
    return NT_SUCCESS(rc);
}''', {'F02': 'if (rc == STATUS_AUTH_TAG_MISMATCH) return true;'},
         note='Explicitly reports a forged-tag mismatch as success; plaintext exposure is not established.'),
    case('02_publish_before_gate', r'''
bool decode(BCRYPT_KEY_HANDLE key, BYTE* ct, ULONG n,
            BCRYPT_AUTHENTICATED_CIPHER_MODE_INFO& auth, std::vector<BYTE>& result) {
    std::vector<BYTE> scratch(n);
    ULONG used = 0;
    NTSTATUS rc = BCryptDecrypt(key, ct, n, &auth, nullptr, 0, scratch.data(), n, &used, 0);
    result.assign(scratch.begin(), scratch.end());
    if (!NT_SUCCESS(rc)) return false;
    result.resize(used);
    return true;
}''', {'F03': 'result.assign(scratch.begin(), scratch.end());'},
         note='Caller-visible result is populated before authentication status is checked.'),
    case('03_auth_then_commit', r'''
bool decode(BCRYPT_KEY_HANDLE key, BYTE* ct, ULONG n,
            BCRYPT_AUTHENTICATED_CIPHER_MODE_INFO& auth, std::vector<BYTE>& result) {
    std::vector<BYTE> scratch(n);
    ULONG used = 0;
    NTSTATUS rc = BCryptDecrypt(key, ct, n, &auth, nullptr, 0, scratch.data(), n, &used, 0);
    if (!NT_SUCCESS(rc) || used > scratch.size()) {
        SecureZeroMemory(scratch.data(), scratch.size());
        result.clear();
        return false;
    }
    result.assign(scratch.begin(), scratch.begin() + used);
    SecureZeroMemory(scratch.data(), scratch.size());
    return true;
}''', controls={'F03': 'if (!NT_SUCCESS(rc) || used > scratch.size())'},
         note='Visible output publication is after the CNG status and length checks; caller aliasing contract omitted.'),
    case('04_aad_dropped', r'''
// The caller requires the packet header to be authenticated as AAD.
bool checkPacket(BCRYPT_KEY_HANDLE key, BYTE* ct, ULONG n, BYTE* header, ULONG headerLen,
                 BCRYPT_AUTHENTICATED_CIPHER_MODE_INFO& auth, BYTE* scratch) {
    auth.pbAuthData = nullptr;
    auth.cbAuthData = 0;
    ULONG used = 0;
    NTSTATUS rc = BCryptDecrypt(key, ct, n, &auth, nullptr, 0, scratch, n, &used, 0);
    return NT_SUCCESS(rc);
}''', {'F02': 'auth.cbAuthData = 0;'},
         note='The header parameter is discarded despite the stated AAD contract; the contract is shown only in a comment.'),
    case('05_negative_status_accepted', r'''
bool verified(BCRYPT_KEY_HANDLE key, BYTE* ct, ULONG n,
              BCRYPT_AUTHENTICATED_CIPHER_MODE_INFO& auth, BYTE* scratch) {
    ULONG used = 0;
    NTSTATUS rc = BCryptDecrypt(key, ct, n, &auth, nullptr, 0, scratch, n, &used, 0);
    return rc != STATUS_INVALID_PARAMETER;
}''', {'F02': 'return rc != STATUS_INVALID_PARAMETER;'},
         note='An authentication-tag mismatch is not STATUS_INVALID_PARAMETER, so this success predicate accepts it.'),
    case('06_fixed_nonce_persistent_key', r'''
struct Sender {
    BCRYPT_KEY_HANDLE key; // Same key is retained for every call.
    bool seal(BYTE* data, ULONG size, BYTE* out) {
        BYTE nonce[12] = {};
        BYTE tag[16] = {};
        BCRYPT_AUTHENTICATED_CIPHER_MODE_INFO auth;
        BCRYPT_INIT_AUTH_MODE_INFO(auth);
        auth.pbNonce = nonce; auth.cbNonce = sizeof(nonce);
        auth.pbTag = tag; auth.cbTag = sizeof(tag);
        ULONG used = 0;
        return NT_SUCCESS(BCryptEncrypt(key, data, size, &auth, nullptr, 0, out, size, &used, 0));
    }
};''', {'F04': 'BYTE nonce[12] = {};'},
         note='Repeated calls use the same zero nonce with the retained key.'),
    case('07_second_resolution_nonce', r'''
bool seal(BCRYPT_KEY_HANDLE persistentKey, BYTE* data, ULONG size, BYTE* out) {
    BYTE nonce[12] = {};
    const auto seconds = static_cast<unsigned long long>(time(nullptr));
    memcpy(nonce + 4, &seconds, sizeof(seconds));
    BYTE tag[16] = {};
    BCRYPT_AUTHENTICATED_CIPHER_MODE_INFO auth;
    BCRYPT_INIT_AUTH_MODE_INFO(auth);
    auth.pbNonce = nonce; auth.cbNonce = 12;
    auth.pbTag = tag; auth.cbTag = 16;
    ULONG used = 0;
    return NT_SUCCESS(BCryptEncrypt(persistentKey, data, size, &auth, nullptr, 0, out, size, &used, 0));
}''', {'F04': 'memcpy(nonce + 4, &seconds, sizeof(seconds));'},
         note='Two encryptions in one second under the same key reuse the nonce.'),
    case('08_bounded_counter_control', r'''
struct Sender {
    BCRYPT_KEY_HANDLE key;
    std::mutex mu;
    unsigned long long next = 0;
    bool seal(BYTE* data, ULONG size, BYTE* out) {
        std::lock_guard<std::mutex> hold(mu);
        if (next == 1000000) return false;
        BYTE nonce[12] = {};
        const auto value = next++;
        for (unsigned i = 0; i < 8; ++i) nonce[11 - i] = BYTE(value >> (8 * i));
        BYTE tag[16] = {};
        BCRYPT_AUTHENTICATED_CIPHER_MODE_INFO auth;
        BCRYPT_INIT_AUTH_MODE_INFO(auth);
        auth.pbNonce = nonce; auth.cbNonce = 12;
        auth.pbTag = tag; auth.cbTag = 16;
        ULONG used = 0;
        return NT_SUCCESS(BCryptEncrypt(key, data, size, &auth, nullptr, 0, out, size, &used, 0));
    }
};''', controls={'F04': 'const auto value = next++;'},
         note='No nonce repeats within this object for one million calls; key/object persistence outside this excerpt is unknown.'),
    case('09_nonce_length_mismatch', r'''
bool open(BCRYPT_KEY_HANDLE key, BYTE* ct, ULONG n, BYTE* out) {
    BYTE nonce[12] = {};
    BYTE tag[16] = {};
    BCRYPT_AUTHENTICATED_CIPHER_MODE_INFO auth;
    BCRYPT_INIT_AUTH_MODE_INFO(auth);
    auth.pbNonce = nonce;
    auth.cbNonce = 8;
    auth.pbTag = tag; auth.cbTag = 16;
    ULONG used = 0;
    return NT_SUCCESS(BCryptDecrypt(key, ct, n, &auth, nullptr, 0, out, n, &used, 0));
}''', {'F04': 'auth.cbNonce = 8;'},
         note='The supplied nonce length violates this fixed 12-byte profile.'),
    case('10_tag_length_mismatch', r'''
bool open(BCRYPT_KEY_HANDLE key, BYTE* ct, ULONG n, BYTE* out) {
    BYTE nonce[12] = {};
    BYTE tag[16] = {};
    BCRYPT_AUTHENTICATED_CIPHER_MODE_INFO auth;
    BCRYPT_INIT_AUTH_MODE_INFO(auth);
    auth.pbNonce = nonce; auth.cbNonce = 12;
    auth.pbTag = tag;
    auth.cbTag = 12;
    ULONG used = 0;
    return NT_SUCCESS(BCryptDecrypt(key, ct, n, &auth, nullptr, 0, out, n, &used, 0));
}''', {'F04': 'auth.cbTag = 12;'},
         note='A 12-byte tag is a fixed-profile mismatch, not a claim that all truncated GCM tags are universally insecure.'),
    case('11_aes256_profile_mismatch', r'''
BCRYPT_KEY_HANDLE createKey(BCRYPT_ALG_HANDLE aes, BYTE* keyObject, ULONG objectBytes) {
    std::array<BYTE, 32> material{};
    BCryptGenRandom(nullptr, material.data(), ULONG(material.size()), BCRYPT_USE_SYSTEM_PREFERRED_RNG);
    BCRYPT_KEY_HANDLE key = nullptr;
    BCryptGenerateSymmetricKey(aes, &key, keyObject, objectBytes,
                               material.data(), ULONG(material.size()), 0);
    return key;
}''', {'F04': 'std::array<BYTE, 32> material{};'},
         note='This is AES-256 key material, not the fixed AES-128 profile; function status checking is also weak but omitted context limits conclusions.'),
    case('12_key_length_control', r'''
BCRYPT_KEY_HANDLE createKey(BCRYPT_ALG_HANDLE aes, BYTE* keyObject, ULONG objectBytes) {
    std::array<BYTE, 16> material{};
    if (!NT_SUCCESS(BCryptGenRandom(nullptr, material.data(), ULONG(material.size()),
                                    BCRYPT_USE_SYSTEM_PREFERRED_RNG))) return nullptr;
    BCRYPT_KEY_HANDLE key = nullptr;
    NTSTATUS rc = BCryptGenerateSymmetricKey(aes, &key, keyObject, objectBytes,
                                              material.data(), ULONG(material.size()), 0);
    SecureZeroMemory(material.data(), material.size());
    return NT_SUCCESS(rc) ? key : nullptr;
}''', controls={'F04': 'std::array<BYTE, 16> material{};'},
         note='Key generation and size are visible; nonce/tag lifecycle is absent, so full F04 is insufficient-context.'),
    case('13_output_capacity_lie', r'''
bool open(BCRYPT_KEY_HANDLE key, BYTE* ct, ULONG n,
          BCRYPT_AUTHENTICATED_CIPHER_MODE_INFO& auth) {
    BYTE output[32] = {};
    ULONG used = 0;
    return NT_SUCCESS(BCryptDecrypt(key, ct, n, &auth, nullptr, 0,
                                    output, n, &used, 0));
}''', {'F05': 'output, n, &used, 0'},
         note='No n<=32 bound is shown; advertised output capacity can exceed the 32-byte allocation.'),
    case('14_narrow_before_limit', r'''
bool seal(BCRYPT_KEY_HANDLE key, const std::vector<BYTE>& input,
          BCRYPT_AUTHENTICATED_CIPHER_MODE_INFO& auth, std::vector<BYTE>& out) {
    ULONG n = static_cast<ULONG>(input.size());
    if (n > 4096) return false;
    out.resize(input.size());
    ULONG used = 0;
    return NT_SUCCESS(BCryptEncrypt(key, const_cast<BYTE*>(input.data()), n, &auth,
                                    nullptr, 0, out.data(), n, &used, 0));
}''', {'F05': 'ULONG n = static_cast<ULONG>(input.size());'},
         note='A size above ULONG_MAX may wrap before the 4096-byte check.'),
    case('15_bounds_before_narrow_control', r'''
bool seal(BCRYPT_KEY_HANDLE key, const std::vector<BYTE>& input,
          BCRYPT_AUTHENTICATED_CIPHER_MODE_INFO& auth, std::vector<BYTE>& out) {
    if (input.size() > 4096) return false;
    const ULONG n = static_cast<ULONG>(input.size());
    std::vector<BYTE> scratch(input.size());
    ULONG used = 0;
    NTSTATUS rc = BCryptEncrypt(key, const_cast<BYTE*>(input.data()), n, &auth,
                                nullptr, 0, scratch.data(), n, &used, 0);
    if (!NT_SUCCESS(rc) || used > scratch.size()) return false;
    out.assign(scratch.begin(), scratch.begin() + used);
    return true;
}''', controls={'F05': 'if (input.size() > 4096) return false;'},
         note='The visible bound precedes narrowing and output capacity matches the allocated buffer.'),
    case('16_empty_supported_but_rejected', r'''
// API contract: supports plaintext lengths from zero through 1024 bytes.
bool seal(BCRYPT_KEY_HANDLE key, std::span<const BYTE> plain,
          BCRYPT_AUTHENTICATED_CIPHER_MODE_INFO& auth, BYTE* output) {
    if (plain.empty()) return false;
    if (plain.size() > 1024) return false;
    ULONG used = 0;
    return NT_SUCCESS(BCryptEncrypt(key, const_cast<BYTE*>(plain.data()), ULONG(plain.size()),
                                    &auth, nullptr, 0, output, ULONG(plain.size()), &used, 0));
}''', abstentions={'F01': 'if (plain.empty()) return false;'},
         note='Only a source comment promises empty input support; the external API contract is missing, so abstain.'),
    case('17_status_checked_but_output_exposed', r'''
bool open(BCRYPT_KEY_HANDLE key, BYTE* ct, ULONG n,
          BCRYPT_AUTHENTICATED_CIPHER_MODE_INFO& auth, BYTE* callerBuffer) {
    ULONG used = 0;
    NTSTATUS rc = BCryptDecrypt(key, ct, n, &auth, nullptr, 0,
                                callerBuffer, n, &used, 0);
    return NT_SUCCESS(rc);
}''', {'F03': 'callerBuffer, n, &used, 0'},
         note='CNG writes to caller-owned memory before the function checks authentication; the caller can observe it on failure.'),
    case('18_profile_mode_mismatch', r'''
bool configureAesGcm(BCRYPT_ALG_HANDLE aes) {
    NTSTATUS rc = BCryptSetProperty(aes, BCRYPT_CHAINING_MODE,
        reinterpret_cast<PUCHAR>(const_cast<wchar_t*>(BCRYPT_CHAIN_MODE_CBC)),
        sizeof(BCRYPT_CHAIN_MODE_CBC), 0);
    return NT_SUCCESS(rc);
}''', {'F01': 'BCRYPT_CHAIN_MODE_CBC'},
         note='The function claims to configure GCM but selects CBC; this is a fixed-profile mismatch.'),
    case('19_other_library', r'''
// Crypto++ implementation; this is not Windows CNG.
void seal(CryptoPP::GCM<CryptoPP::AES>::Encryption& cipher,
          const std::string& plaintext, std::string& output) {
    CryptoPP::StringSource ss(plaintext, true,
        new CryptoPP::AuthenticatedEncryptionFilter(cipher,
            new CryptoPP::StringSink(output)));
}''', scope='outside_scope',
         note='Another library is explicitly named; do not infer a CNG integration.'),
    case('20_declarations_only', r'''
#include <bcrypt.h>
struct Packet {
    BYTE nonce[12];
    BYTE tag[16];
    std::vector<BYTE> ciphertext;
};
// AES-GCM implementation is supplied by another translation unit.
bool verifyPacket(const Packet& packet);''', scope='unclear',
         note='Declarations alone do not show algorithm selection, cryptographic calls, or behavior.'),
]
