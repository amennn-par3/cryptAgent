# Validation performed on this Windows host

Date: 2026-09-13.

| Check | Actual result |
|---|---|
| Package metadata, source hashes, group membership and 150-case counts | Passed |
| Example specification and request validation | Passed |
| Five invalid specification inputs (scheme, key length, duplicate requirement, extra field, missing field) | Correctly rejected |
| Reference and defective-source demonstration | Passed: both overall inconclusive; only defective example flagged |
| Path escape rejection | Passed |
| Python module compilation | Passed |
| C++20 header contract with installed MSVC | Passed, syntax-only /Zs |
| Windows-only content check | Passed |
| Native runner dependency preflight | Correctly refused to run without libsodium |
| Native encryption/decryption, fixture execution and AddressSanitizer | Not run: libsodium include/library unavailable |
| Timing, allocation failure injection, optimized cleanup inspection | Not implemented yet |

The detected installation is Visual Studio Build Tools 2022 17.12.2 with v143 tools
under 14.42.34433. This records the host observation, not a completed deployment lock.
The header test verifies move/copy and noexcept declarations; it does not compile the
libsodium-dependent implementation or establish runtime correctness.

The runnable demonstration output is in demo-output/report.json and demo-output/trace.json.
It records execution as not_executed and does not claim a confirmed cryptographic defect.
All benchmark labels retain authored_expectation_pending_native_confirmation.

Repeat the package checks with `python tools/validate_package.py` and header checks
with `tools\check_header.cmd` from the package directory. Follow WINDOWS_SETUP.md
before attempting native tests. Do not use these results as production certification.
