# Authored mutation review

These are source-level explanations, not native execution results. Native findings
must be reviewed against a witness before labels become experimental ground truth.

| Mutation | Why the change violates the contract | Witness / caveat |
|---|---|---|
| fixed_nonce | Replaces fresh random generation with all-zero nonce | Two encryptions with one key; source confirms deterministic reuse |
| fixed_key | Replaces key generation with zero filling | Two generations; source confirms predictable key |
| ignore_auth | Discards the decrypt return code | Tampered tag; zero-length fixture exposes a successful result, other lengths may instead expose an incorrect failure status |
| omit_aad | Both operations pass null/zero instead of caller AAD | Change nonempty AAD; mutation incorrectly accepts it |
| log_plaintext | Writes plaintext bytes to stderr | Log witness uses nonempty synthetic plaintext |
| log_key | Writes key bytes to stderr | Inspect sink and recorded synthetic-test stderr; never use a real key |
| oversize_plaintext | Removes application's pre-allocation plaintext bound | max_plaintext + 1 is incorrectly accepted; this alone is not a memory-corruption claim |
| oversize_aad | Removes encryption's AAD bound | max_aad + 1 is incorrectly accepted |
| reject_empty | Adds an unauthorized rejection of empty plaintext | Empty plaintext is a valid scheme/application input |
| reject_boundary | Changes the inclusive maximum to an exclusive bound | Exactly max_plaintext bytes are incorrectly rejected |

Each mutation changes behavior rather than only a name. However many cases reuse the
same mutated source with different scenario metadata. This is intentional coverage
of input combinations, not evidence of independent source diversity. Double mutations
may mask one another in a particular witness; run both trigger recipes and review
unconfirmed labels separately. A generic failing test is not automatically evidence
for every expected requirement in a multi-defect case.
