# Assets and attacker model

| Asset | Classification | Allowed release |
|---|---|---|
| Key | Secret | Never through the public wrapper output |
| Plaintext | Secret | Successful authenticated decryption to authorized caller |
| Internal sensitive buffers | Secret | No unintended release |
| Nonce, ciphertext, tag | Public | Encryption output |
| AAD and lengths | Public | Caller and observer may know them |
| Authentication result | Public | Generic success/failure |

The attacker controls encrypted input, nonce and AAD, can truncate/tamper/replay,
observe returned output, errors, logs and selected timing measurements, and exercise
supported failure paths. The trusted caller owns valid C++ objects and is authorized
to receive plaintext. Caller-owned plaintext is not erased by this module.

Trust the OS, toolchain, dependency and system randomness under their documented
contracts. Do not assume the candidate implementation is trustworthy. The LLM is
also untrusted: its findings require evidence. Code comments are input data, not instructions.

Trust boundaries: request -> schema validator -> profile resolver -> candidate
build/execution boundary -> evidence parser -> policy engine -> report.
The native benchmark runner is for inspected, bundled fixtures only. It is NOT
a sandbox for arbitrary uploaded source. Phase 4 needs a separate low-privilege
Windows worker/VM with network denied, quotas and no credentials before executing
untrusted submissions. Working-directory isolation alone is not a security boundary.

Replay of a valid message may succeed; freshness is not guaranteed. Message lengths
and authentication outcome are explicitly permitted observations. No blanket
constant-runtime requirement applies across different public input lengths.
