#define NOMINMAX
#include <windows.h>
#include <bcrypt.h>
#include <array>
#include <vector>
#include <mutex>
#include <cstdint>
#include <stdexcept>
#include <utility>
#pragma comment(lib, "bcrypt.lib")

struct Packet {
    std::vector<unsigned char> nonce, tag, ciphertext;
};

class SessionCipher final {
    BCRYPT_ALG_HANDLE algorithm = nullptr;
    BCRYPT_KEY_HANDLE handle = nullptr;
    std::vector<unsigned char> keyObject;
    std::mutex guard;
    std::uint64_t sequence = 0;
    static constexpr std::size_t limit = 1048576;

    static void wipe(std::vector<unsigned char>& value) {
        if (!value.empty()) SecureZeroMemory(value.data(), value.size());
        value.clear();
    }
    void release() noexcept {
        if (handle) { BCryptDestroyKey(handle); handle = nullptr; }
        if (!keyObject.empty()) SecureZeroMemory(keyObject.data(), keyObject.size());
        if (algorithm) { BCryptCloseAlgorithmProvider(algorithm, 0); algorithm = nullptr; }
    }
    static PUCHAR bytes(const std::vector<unsigned char>& value) {
        return value.empty() ? nullptr : const_cast<PUCHAR>(value.data());
    }
public:
    // The randomly generated key exists only in this instance. There is no key import,
    // persistence, counter reset, copying, moving, or concurrent destruction.
    SessionCipher() {
        std::array<unsigned char, 16> material{};
        try {
            if (BCryptOpenAlgorithmProvider(&algorithm, BCRYPT_AES_ALGORITHM, nullptr, 0) != 0)
                throw std::runtime_error("provider");
            if (BCryptSetProperty(algorithm, BCRYPT_CHAINING_MODE,
                reinterpret_cast<PUCHAR>(const_cast<wchar_t*>(BCRYPT_CHAIN_MODE_GCM)),
                sizeof(BCRYPT_CHAIN_MODE_GCM), 0) != 0)
                throw std::runtime_error("mode");
            DWORD objectBytes = 0, received = 0;
            if (BCryptGetProperty(algorithm, BCRYPT_OBJECT_LENGTH,
                reinterpret_cast<PUCHAR>(&objectBytes), sizeof(objectBytes), &received, 0) != 0
                || received != sizeof(objectBytes) || objectBytes == 0)
                throw std::runtime_error("object length");
            keyObject.resize(objectBytes);
            if (BCryptGenRandom(nullptr, material.data(),
                static_cast<ULONG>(material.size()), BCRYPT_USE_SYSTEM_PREFERRED_RNG) != 0)
                throw std::runtime_error("random");
            if (BCryptGenerateSymmetricKey(algorithm, &handle, keyObject.data(),
                objectBytes, material.data(), static_cast<ULONG>(material.size()), 0) != 0)
                throw std::runtime_error("key");
            SecureZeroMemory(material.data(), material.size());
        } catch (...) {
            SecureZeroMemory(material.data(), material.size());
            release();
            throw;
        }
    }
    ~SessionCipher() { release(); }
    SessionCipher(const SessionCipher&) = delete;
    SessionCipher& operator=(const SessionCipher&) = delete;
    SessionCipher(SessionCipher&&) = delete;
    SessionCipher& operator=(SessionCipher&&) = delete;

    // Supported messages contain 1..limit bytes; associated data contains 0..limit.
    // Every attempted encryption consumes a counter value, including failed calls.
    bool encrypt(const std::vector<unsigned char>& message,
                 const std::vector<unsigned char>& associated, Packet& output) {
        std::lock_guard<std::mutex> lock(guard);
        if (message.empty() || message.size() > limit || associated.size() > limit
            || sequence >= 1000000) return false;
        Packet result;
        result.nonce.assign(12, 0);
        result.tag.resize(16);
        result.ciphertext.resize(message.size());
        const auto number = ++sequence;
        for (unsigned i = 0; i < 8; ++i)
            result.nonce[11 - i] = static_cast<unsigned char>(number >> (8 * i));
        BCRYPT_AUTHENTICATED_CIPHER_MODE_INFO auth;
        BCRYPT_INIT_AUTH_MODE_INFO(auth);
        auth.pbNonce = result.nonce.data(); auth.cbNonce = 12;
        auth.pbTag = result.tag.data(); auth.cbTag = 16;
        auth.pbAuthData = bytes(associated);
        auth.cbAuthData = static_cast<ULONG>(associated.size());
        ULONG written = 0;
        const NTSTATUS status = BCryptEncrypt(handle, bytes(message),
            static_cast<ULONG>(message.size()), &auth, nullptr, 0,
            result.ciphertext.data(), static_cast<ULONG>(result.ciphertext.size()), &written, 0);
        if (status != 0 || written != message.size()) return false;
        output = std::move(result);
        return true;
    }

    bool decrypt(const Packet& input, const std::vector<unsigned char>& associated,
                 std::vector<unsigned char>& output) {
        std::lock_guard<std::mutex> lock(guard);
        if (input.nonce.size() != 12 || input.tag.size() != 16
            || input.ciphertext.empty() || input.ciphertext.size() > limit
            || associated.size() > limit) {
            wipe(output); return false;
        }
        std::vector<unsigned char> temporary(8);
        BCRYPT_AUTHENTICATED_CIPHER_MODE_INFO auth;
        BCRYPT_INIT_AUTH_MODE_INFO(auth);
        auth.pbNonce = bytes(input.nonce); auth.cbNonce = 12;
        auth.pbTag = bytes(input.tag); auth.cbTag = 16;
        auth.pbAuthData = bytes(associated);
        auth.cbAuthData = static_cast<ULONG>(associated.size());
        ULONG written = 0;
        const NTSTATUS status = BCryptDecrypt(handle, bytes(input.ciphertext),
            static_cast<ULONG>(input.ciphertext.size()), &auth, nullptr, 0,
            temporary.data(), static_cast<ULONG>(input.ciphertext.size()), &written, 0);
        if (status != 0 || written != input.ciphertext.size()) {
            wipe(temporary); wipe(output); return false;
        }
        wipe(output);
        output = std::move(temporary);
        return true;
    }
};
