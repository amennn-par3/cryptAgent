# Primary references

Checked 2026-09-13. Project policies such as size limits and repair budgets are authored
choices, not claims made by these sources.
- XChaCha20-Poly1305 API, nonce policy and authentication behavior:
  https://doc.libsodium.org/secret-key_cryptography/aead/chacha20-poly1305/xchacha20-poly1305_construction
- Secure allocation, cleanup and memory-locking limits:
  https://doc.libsodium.org/memory_management
- Windows installation, static-link macro and runtime compatibility:
  https://doc.libsodium.org/installation
- MSVC AddressSanitizer:
  https://learn.microsoft.com/en-us/cpp/sanitizers/asan?view=msvc-170
- MSVC language-standard switches:
  https://learn.microsoft.com/en-us/cpp/build/reference/std-specify-language-standard-version?view=msvc-170

Security claims remain conditional on the pinned implementation and target profile.
