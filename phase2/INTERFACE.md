# C++20 interface and lifecycle contract

See cpp/cryptagent.hpp and cpp/cryptagent.cpp for the concrete reference source.
`generate_key() -> Result<SecretBuffer>` returns exactly 32 owned bytes.
`encrypt(key, plaintext, aad) -> Result<EncryptedMessage>` returns a vector nonce
(validated as 24 bytes) and combined ciphertext/tag.
`decrypt(key, message, aad) -> Result<SecretBuffer>` returns owned plaintext only
on success. Empty plaintext is successful and distinct from failure.

Result<T> contains Error and optional<T>. Success iff error==none AND value exists;
failure iff error!=none AND value is absent. Internal allocation exceptions are caught.
The reference uses a move-only SecretBuffer that owns a sodium allocation and calls
sodium_free in its destructor. sodium_free clears allocated memory before release.
The implementation does not promise every compiler temporary or register is erased.
Calling data() grants trusted code a temporary view, not permission to log/copy keys.
The caller owns source plaintext; encrypted outputs use ordinary public vectors.

Default/moved-from keys fail length validation. Init is checked before crypto use.
Production nonce generation is internal; test harnesses may call the reference library
directly with fixed public fixtures. No production fixed-nonce overload is exposed.
Initialization, invalid_input, authentication_failed, allocation_failed and
operation_failed are generic errors with no embedded secrets.

This source is a reference candidate requiring validation, not a security-certified library.
