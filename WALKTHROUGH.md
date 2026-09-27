# First input: assess a C++ module that ignores authentication failure

## What the student submits
Open phase2/examples/assess_request.json. It selects assess mode, our AEAD specification,
the Windows profile and phase3/cases/F01_ignore_auth/candidate.cpp. It does NOT submit
a real key or private plaintext. The agent assesses code, not a user's secret.

For a human example, imagine plaintext `BTP report draft` and AAD `record:42`.
The real wrapper generates a synthetic test key and nonce, encrypts, and returns
nonce plus ciphertext/tag. These bytes are not invented or hardcoded in this walkthrough.
The assessment deliberately changes a ciphertext byte and asks the candidate to decrypt.
The actual F01 fixture and the focused tamper check use an empty plaintext, which is
valid. This exposes the defect even when the library resets its output length to zero
after authentication failure. A nonempty message may instead return an incorrect
generic error because the candidate's later length check happens to reject it.

## Present runnable demonstration
```powershell
python tools/demo_backend.py --request phase2/examples/assess_request.json --out demo-output
```
1. Parse and validate the request. Reject unknown fields and unsupported profiles.
2. Resolve both paths inside cryptagent and validate the scheme specification.
3. Hash the exact candidate source; initialize all 13 requirements as inconclusive.
4. Detect a narrow suspicious pattern: a decrypt result assigned to rc followed by
   `(void)rc` in this fixture. This is a heuristic; comments or unfamiliar code can mislead it.
5. Attach a suspected C-04/E-01 finding. No tool execution or LLM judgment is fabricated.
6. Write trace.json and report.json. Overall remains inconclusive, execution not_executed.

## What happens in the native test backend
After WINDOWS_SETUP.md, the runner selects the fixture and builds it with the shared
public header plus fixture_test.cpp. It calls actual libsodium; there is no mock cipher.
It generates a key and encrypts synthetic data, tampers with ciphertext and calls decrypt.
Correct behavior: an authentication_failed result without a value. Defective behavior:
the fixture may return success after ignoring the failed authentication result.
The harness uses exit 10 and `VIOLATION:` text for an observed contract failure;
exit 20 means an unexpected environment/reference setup error. A crash is not automatically
the expected defect. The runner records build output, check output, hashes and exit codes.
No native results are asserted until that build/run actually succeeds.

## Future full agent backend (Phase 4–6)
Request -> strict schema -> profile/dependency lock -> requirement planner -> isolated
Windows build worker -> functional/memory/source/timing adapters -> evidence normalizer
-> deterministic policy -> readable report. An LLM proposes code or patches and explains
evidence; it cannot set the verdict, delete a check or alter the approved spec.

With a confirmed tamper witness the report can mark C-04 violated and overall fails_checks.
A suggested repair restores `if (rc != 0) return {Error::authentication_failed, std::nullopt};`.
Rerun tamper, wrong key, AAD, empty/boundary, memory and cleanup checks after repair.
If that repair passes functional checks but timing/cleanup evidence is missing, the
final whole-module verdict remains inconclusive. Three repairs maximum, then stop honestly.

## Why this helps your BTP
Phase 1 says what security means. Phase 2 makes it a machine-readable contract. Phase 3
provides known situations and expected witnesses. The full agent later connects those
pieces to real checks and a model. The demo today teaches this flow without pretending
that pattern matching is a cryptographic verifier.
