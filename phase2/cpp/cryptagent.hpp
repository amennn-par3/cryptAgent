#pragma once
#include <cstddef>
#include <optional>
#include <span>
#include <utility>
#include <vector>
namespace cryptagent {
using Byte = unsigned char;
inline constexpr std::size_t max_plaintext = 1048576, max_aad = 65536;
enum class Error { none, initialization_failed, invalid_input, authentication_failed, allocation_failed, operation_failed };
class SecretBuffer {
    Byte* data_ = nullptr;
    std::size_t size_ = 0;
public:
    SecretBuffer() noexcept = default;
    explicit SecretBuffer(std::size_t n);
    ~SecretBuffer();
    SecretBuffer(const SecretBuffer&) = delete;
    SecretBuffer& operator=(const SecretBuffer&) = delete;
    SecretBuffer(SecretBuffer&& other) noexcept;
    SecretBuffer& operator=(SecretBuffer&& other) noexcept;
    Byte* data() noexcept { return data_; }
    const Byte* data() const noexcept { return data_; }
    std::size_t size() const noexcept { return size_; }
    std::span<const Byte> view() const noexcept { return {data_, size_}; }
};
template<class T> struct Result {
    Error error;
    std::optional<T> value;
    explicit operator bool() const noexcept { return error == Error::none && value.has_value(); }
};
struct EncryptedMessage { std::vector<Byte> nonce; std::vector<Byte> ciphertext; };
Result<SecretBuffer> generate_key() noexcept;
Result<EncryptedMessage> encrypt(const SecretBuffer&, std::span<const Byte>, std::span<const Byte>) noexcept;
Result<SecretBuffer> decrypt(const SecretBuffer&, const EncryptedMessage&, std::span<const Byte>) noexcept;
}
