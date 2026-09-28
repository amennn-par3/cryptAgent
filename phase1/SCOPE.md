# Phase 1: approved working baseline

## Goal
Generate, assess and repair small C++20 authenticated-encryption integrations against
an explicit security contract. Research hypothesis: structured requirements plus
external evidence reduce false acceptance of known defective integrations compared
with an LLM alone. Assume 3–4 students and a 24-week project.

## Concrete task
Use libsodium XChaCha20-Poly1305 combined mode. Key: 32 bytes; nonce: 24 bytes;
tag: 16 bytes appended to ciphertext. Public operations: generate_key, encrypt,
decrypt. AAD is public but authenticated. Nonces are public and generated internally
for each production encryption. Fixed-nonce entry points exist only in test code.
The wrapper does not implement the primitive itself.

Plaintext limit: 1,048,576 bytes; AAD limit: 65,536 bytes; both may be empty.
Limits are application policy. Reject malformed nonce lengths, ciphertext shorter
than a tag, oversized data and arithmetic errors before unsafe allocation or access.
Single thread, in-memory operations, no stream processing or message serialization.

## Environment
Windows 11 x64; Visual Studio 2022 Build Tools v143; C++20; Windows SDK; CMake 3.24+.
Primary release /O2, no /GL or link-time optimization. Diagnostic /Od /Zi and
/fsanitize=address; disable incremental linking. Use an uninstrumented libsodium
dependency; instrument the wrapper, not the cryptographic primitive.
Python 3.11+ drives orchestration. No non-Windows runner, subsystem or container is needed.
Exact compiler, SDK and dependency revisions must be locked before native evaluation.

## Input/output and boundaries
Input: specification, candidate sources or generation request, target profile.
Output: candidate code or patch, per-requirement results, evidence, source hashes,
assumptions and one overall verdict. Three repair attempts maximum.
Support a restricted ownership-based C++ subset. Reject unsupported custom assembly,
concurrency and custom cryptographic primitives as inconclusive rather than guessing.

## Out of scope
Universal security certification; primitive cryptanalysis; key exchange; key storage;
password derivation; networking; replay detection; physical power/fault attacks;
arbitrary memory-read attackers; all-register erasure; all microarchitectural leakage.
ProVerif is an optional future protocol extension, not a mandatory module-level check.

## Phase 1 completion
Every mandatory claim has a requirement ID, evidence recipe and limitation.
The environment and verdict policy are explicit. The worked example maps a defect
to C-04 and E-01. Implementation validation remains a subsequent deliverable.
