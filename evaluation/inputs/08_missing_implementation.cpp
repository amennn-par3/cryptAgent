#include <windows.h>
#include <bcrypt.h>
#include <vector>

// Intended interface for a Windows CNG AES-128-GCM integration.
// Implementations are in another translation unit that is not supplied.
struct Packet {
    std::vector<unsigned char> nonce, tag, ciphertext;
};
bool encrypt(BCRYPT_KEY_HANDLE key,
             const std::vector<unsigned char>& message,
             const std::vector<unsigned char>& associated,
             Packet& output);
bool decrypt(BCRYPT_KEY_HANDLE key, const Packet& input,
             const std::vector<unsigned char>& associated,
             std::vector<unsigned char>& output);
