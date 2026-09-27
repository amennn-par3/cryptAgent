#include "cryptagent.hpp"
#include <sodium.h>
#include <algorithm>
#include <cstdio>
#include <new>
#include <stdexcept>
namespace cryptagent {
SecretBuffer::SecretBuffer(std::size_t n) : size_(n) {
    if (sodium_init() < 0) throw std::runtime_error("crypto initialization failed");
    data_ = static_cast<Byte*>(sodium_malloc(n == 0 ? 1 : n));
    if (!data_) throw std::bad_alloc();
}
SecretBuffer::~SecretBuffer() { if (data_) sodium_free(data_); }
SecretBuffer::SecretBuffer(SecretBuffer&& other) noexcept
    : data_(std::exchange(other.data_, nullptr)), size_(std::exchange(other.size_, 0)) {}
SecretBuffer& SecretBuffer::operator=(SecretBuffer&& other) noexcept {
    if (this != &other) {
        if (data_) sodium_free(data_);
        data_ = std::exchange(other.data_, nullptr);
        size_ = std::exchange(other.size_, 0);
    }
    return *this;
}
Result<SecretBuffer> generate_key() noexcept {
    if (sodium_init() < 0) return {Error::initialization_failed, std::nullopt};
    try {
        SecretBuffer key(crypto_aead_xchacha20poly1305_ietf_KEYBYTES);
        crypto_aead_xchacha20poly1305_ietf_keygen(key.data());
        return {Error::none, std::move(key)};
    } catch (const std::bad_alloc&) { return {Error::allocation_failed, std::nullopt}; }
      catch (...) { return {Error::operation_failed, std::nullopt}; }
}
Result<EncryptedMessage> encrypt(const SecretBuffer& key, std::span<const Byte> plaintext,
                                 std::span<const Byte> aad) noexcept {
    if (sodium_init() < 0) return {Error::initialization_failed, std::nullopt};
    if (key.size() != crypto_aead_xchacha20poly1305_ietf_KEYBYTES ||
        plaintext.size() > max_plaintext || aad.size() > max_aad)
        return {Error::invalid_input, std::nullopt};
    try {
        EncryptedMessage out;
        out.nonce.resize(crypto_aead_xchacha20poly1305_ietf_NPUBBYTES);
        randombytes_buf(out.nonce.data(), out.nonce.size());
        out.ciphertext.resize(plaintext.size() + crypto_aead_xchacha20poly1305_ietf_ABYTES);
        unsigned long long written = 0;
        const int rc = crypto_aead_xchacha20poly1305_ietf_encrypt(
            out.ciphertext.data(), &written, plaintext.data(), plaintext.size(),
            nullptr, 0, nullptr, out.nonce.data(), key.data());
        if (rc != 0) return {Error::operation_failed, std::nullopt};
        out.ciphertext.resize(static_cast<std::size_t>(written));
        return {Error::none, std::move(out)};
    } catch (const std::bad_alloc&) { return {Error::allocation_failed, std::nullopt}; }
      catch (...) { return {Error::operation_failed, std::nullopt}; }
}
Result<SecretBuffer> decrypt(const SecretBuffer& key, const EncryptedMessage& message,
                            std::span<const Byte> aad) noexcept {
    if (sodium_init() < 0) return {Error::initialization_failed, std::nullopt};
    if (key.size() != crypto_aead_xchacha20poly1305_ietf_KEYBYTES ||
        message.nonce.size() != crypto_aead_xchacha20poly1305_ietf_NPUBBYTES ||
        message.ciphertext.size() < crypto_aead_xchacha20poly1305_ietf_ABYTES ||
        message.ciphertext.size() > max_plaintext + crypto_aead_xchacha20poly1305_ietf_ABYTES ||
        aad.size() > max_aad) return {Error::invalid_input, std::nullopt};
    try {
        SecretBuffer plaintext(message.ciphertext.size() - crypto_aead_xchacha20poly1305_ietf_ABYTES);
        unsigned long long written = 0;
        const int rc = crypto_aead_xchacha20poly1305_ietf_decrypt(
            plaintext.data(), &written, nullptr, message.ciphertext.data(), message.ciphertext.size(),
            nullptr, 0, message.nonce.data(), key.data());
        (void)rc; // Defect: authentication failure ignored
        if (written != plaintext.size()) return {Error::operation_failed, std::nullopt};
        return {Error::none, std::move(plaintext)};
    } catch (const std::bad_alloc&) { return {Error::allocation_failed, std::nullopt}; }
      catch (...) { return {Error::operation_failed, std::nullopt}; }
}
}
