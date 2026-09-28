#include "../phase2/cpp/cryptagent.hpp"
#include <type_traits>
using namespace cryptagent;
static_assert(!std::is_copy_constructible_v<SecretBuffer>);
static_assert(!std::is_copy_assignable_v<SecretBuffer>);
static_assert(std::is_nothrow_move_constructible_v<SecretBuffer>);
static_assert(std::is_nothrow_move_assignable_v<SecretBuffer>);
static_assert(noexcept(generate_key()));
static_assert(noexcept(encrypt(std::declval<const SecretBuffer&>(), {}, {})));
static_assert(noexcept(decrypt(std::declval<const SecretBuffer&>(), std::declval<const EncryptedMessage&>(), {})));
