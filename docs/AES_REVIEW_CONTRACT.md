# AES review contract — step 1

The only active profile is `aes128-gcm-tampering-v1`: AES-128-GCM,
C++20, Windows CNG, message tampering, key 16 bytes, nonce 12 bytes,
tag 16 bytes. Checks remain F01–F05. No generation or training endpoint.

## Input

POST `/api/verify` with JSON `{code, profileId, mode: "verify"}` and
`X-Session-Token` obtained from GET `/api/status`. Source is normalized to
LF, limited to 64 KiB and 2,000 lines, nonempty and without null bytes.
The model additionally rejects prompts exceeding 3,072 tokens, without
silent truncation. Pasted non-C++ or unrelated text can be submitted for
scope assessment; it does not expand supported schemes or languages.

## Output

Accepted submissions return report version `2.0`, including source hash,
fixed profile identity, five checks, source-located findings, model status,
execution status, limitations and provenance. Verdicts are:

- `potential_issues`: source observations or model hypotheses need review.
- `no_issues_identified`: model source review found no concerns; not proof.
- `insufficient_context`: required code or evidence is missing.
- `outside_scope`: model classified the code outside the fixed profile.
- `review_unavailable`: model offline, busy, incomplete or invalid output.

Invalid requests receive a JSON error with an appropriate HTTP status;
the page displays the error. Busy requests receive 429. Transport failures
are displayed, never converted to a security verdict. Model calls have a
110-second client deadline; the page has a 125-second deadline.

Raw model JSON has exactly `scope`, `checks`, `findings`. Each check has
`check_id`, `assessment`, `reason`. Assessments are `potential_issue`,
`no_issue_identified`, `insufficient_context`, `not_applicable`.
Findings have `check_id`, `line_start`, `line_end`, `quote`, `rationale`.
The executable validator is `backend/review_contract.mjs`: all five IDs
must be unique; outside-scope checks must all be not applicable with no
findings; findings must match potential-issue checks and quote submitted
source. Invalid source references are discarded and unsupported issue
assessments downgraded. Contradictory structures are rejected.

## Runtime and evidence

The cached Llama-3.1-8B-Instruct base model runs offline on loopback 8081;
the app runs on loopback 8000. No historical adapter is loaded. Fine-tuning
is pending. Source patterns are explicitly observations, not AI findings
or proof. Submitted code is neither executed nor saved by this flow.
Windows CNG execution and formal verification are not performed.
Source-location validation establishes where text occurs, not whether a
model's security interpretation is correct. Hardware/runtime failures
can prevent analysis; the UI must expose that limitation honestly.
