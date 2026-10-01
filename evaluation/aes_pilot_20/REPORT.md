# CryptAgent AES pilot: 20 new source-review probes

This is an exploratory, **source-only** comparison of the cached Llama-3.1-8B-Instruct base model and the experimental AES pilot LoRA adapter trained on 22 other snippets. The 20 C++ excerpts and their target answer key are in [cases.py](cases.py). They were not used for training, validation, or adapter selection. Exact and whitespace-normalized overlap with all 30 pilot sources was checked: zero. They are nevertheless authored by the same project and reuse the same vulnerability themes, so they are **not an independent real-world benchmark**. None was compiled or run on Windows.

## Method and evidence

- Fixed profile: C++20, Windows CNG, AES-128-GCM, 16-byte key, 12-byte nonce, 16-byte tag, message tampering, F01–F05.
- Both modes used the same pinned model revision, prompt, tokenizer, deterministic decoding, and 3,072-token input limit. All 40 generations completed; none was truncated.
- The production validator checked JSON shape, F01–F05 statuses, and exact source quotations. An issue target counted as hit only if the accepted assessment was `potential_issue` **and** a finding quoted the specific expected source expression on its correct line. Mere mention of a check ID or an overlapping multi-line range did not count.
- After inspecting the generated responses, the scoring rule was tightened from line-range overlap to exact target-expression quotation: a base response had included the expected line in a range while quoting a different line. Case 07's expected expression was correspondingly changed from `time(nullptr)` to the nonce assignment using `seconds`. **The C++ input was unchanged; the scoring rubric was refined post-inference**, so the counts remain exploratory, not a pre-registered benchmark.
- Four control assertions tested avoidance of a false issue; one abstention assertion tested whether a comment-only contract was treated as insufficient evidence. The two scope probes tested another library and declarations-only code.
- [Raw generations](results_20261001/raw_results.json) and [validated assessments](results_20261001/assessment.json) retain individual outputs, timings, source hashes, model identity, prompt/profile hashes, and adapter hash. `run.py` and `analyze.py` reproduce the procedure.

| Measure | Base | Adapter |
|---|---:|---:|
| Structurally valid, fully accepted reviews | 7/20 | 20/20 |
| Partially accepted (at least one unsupported source quote) | 11/20 | 0/20 |
| Rejected/malformed reviews | 2/20 | 0/20 |
| Target issue check ID flagged, regardless of location/rationale | 3/13 | 3/13 |
| Target issue with correct source expression/location | **0/13** | **3/13** |
| Control assertions without false issue | 3/4 | 3/4 |
| Comment-only contract correctly treated as insufficient context | 0/1 | 1/1 |
| Scope correct | 17/20 | 19/20 |
| Total generation time (20 responses) | 166.63 s | 80.55 s |

The adapter's shorter answers (mean 148 vs 346 generated tokens) largely explain its lower generation time; this is not evidence that the underlying model computes twice as fast. Validation loss from training is not included as an accuracy metric here.

## Per-case results

“Hit” requires the correct check *and* source line. “Miss” includes an absent finding, an unsupported/wrong quote, or an `insufficient_context` answer. A `potential_issue` label is a source-review hypothesis, not an exploit proof. The answer key covers targeted assertions; unreviewed extra findings are not automatically counted as false positives.

| ID | Targeted expected response | Base | Adapter |
|---|---|---|---|
| 01 | F02: accepts tag mismatch | Miss | Miss |
| 02 | F03: publishes output before status gate | Miss | Miss |
| 03 | F03 control: authenticate before commit | Pass; review partial | Pass |
| 04 | F02: supplied header/AAD discarded | Miss | Miss |
| 05 | F02: non-parameter errors treated as success | Invalid structure | Miss |
| 06 | F04: fixed nonce with retained key | Miss | **Hit** |
| 07 | F04: seconds-based nonce collisions | Wrong expression/rationale; also F02 theory | **Hit**, but incomplete rationale |
| 08 | F04 control: bounded synchronized counter | Pass | **False alarm** |
| 09 | F04: configured nonce length 8, not 12 | Wrong line/rationale | **Hit** |
| 10 | F04: configured tag length 12, not 16 | Wrong line/rationale | Miss |
| 11 | F04: 32-byte key is outside AES-128 profile | Miss | Miss |
| 12 | F04 control: 16-byte key filled by CNG RNG | **False alarm** | Pass |
| 13 | F05: 32-byte output buffer advertised as `n` | Miss | Miss |
| 14 | F05: `size_t` narrowed before bound check | Miss | Miss |
| 15 | F05 control: bound before narrowing/capacity | Pass; review partial | Pass |
| 16 | F01 abstention: empty-input promise only in comment | Overconfident no-issue | Correct abstention |
| 17 | F03: caller buffer passed to decrypt before check | Miss | Miss |
| 18 | F01: GCM-named setup selects CBC | Malformed JSON | Miss |
| 19 | Scope: Crypto++ is not Windows CNG | Correct outside-scope | Correct outside-scope |
| 20 | Scope: declarations do not establish implementation | Incorrect in-scope | Incorrect outside-scope |

## What actually changed

1. **Output discipline improved substantially.** The adapter returned production-accepted JSON with valid source references or deliberate empty findings in all 20 cases. The base returned 11 partial and two invalid reviews. This is valuable for reliability, but mostly reflects a learned conservative response pattern.
2. **Defect detection improved only modestly and narrowly.** The adapter quoted the target expression for three F04 issues versus zero for the base. Both flagged three target check IDs, but the base's three F04 explanations rested on the wrong expressions (most notably treating zero-initialization itself as nonce reuse). Neither mode located any of the three F02, two F03, two F05, or one F01 target concerns. The adapter did not gain coverage beyond key/nonce/tag handling in this probe set.
3. **A major abstention collapse is visible.** The adapter assigned `insufficient_context` to 86 of 100 requirement cells and produced only four issue findings. Several excerpts provide direct local evidence, such as accepting `STATUS_AUTH_TAG_MISMATCH`, publishing `scratch` before checking `rc`, or advertising `n` bytes for a 32-byte output array. It still abstained. A lower loss and cleaner JSON therefore must not be reported as security improvement.
4. **Both modes have distinct false-positive mechanisms.** The base called a 16-byte key buffer suspicious simply because it was zero-initialized, overlooking the immediately following `BCryptGenRandom`. The adapter called a zero-initialized nonce reused even though the code filled it from a synchronized, bounded, incrementing counter. These show why source-line quotation alone does not validate the security reasoning.
5. **Scope handling needs a third-way distinction.** Both recognized the explicit Crypto++ example as outside scope. For declarations only, the base asserted in-scope and the adapter asserted outside-scope; the correct answer is `unclear` because a header and packet struct neither prove nor disprove a CNG integration.

## Answer-key cautions and next decisions

- Cases 04 and 17 are **potential concerns**, not native-confirmed vulnerabilities. Case 04 depends on whether the documented header/AAD contract is authoritative. Case 17 concerns caller-visible output-buffer exposure; the exact bytes CNG may leave on an authentication failure were not tested here. Removing both conditional probes still leaves zero adapter hits outside F04.
- Case 16 deliberately **does not** infer a functional defect from a comment alone. This is an abstention test, despite GCM's capacity to authenticate an empty message.
- A 12-byte tag (case 10) and a 32-byte AES key (case 11) are **fixed-profile mismatches** for this project, not universally insecure AES-GCM configurations. Microsoft's authenticated-cipher documentation notes that GCM may support multiple tag lengths; [BCryptDecrypt](https://learn.microsoft.com/en-us/windows/win32/api/bcrypt/nf-bcrypt-bcryptdecrypt) and the [authenticated-cipher parameters](https://learn.microsoft.com/en-us/windows/win32/api/bcrypt/ns-bcrypt-bcrypt_authenticated_cipher_mode_info) define the relevant API behavior.
- Do **not** activate this adapter as the verifier yet. The evidence supports a better formatting/abstention model, not a reliable AES security reviewer. The next dataset iteration should add independently reviewed, source-located F02/F03/F05 defects and matched safe controls, with case-family separation. Preserve these 20 probes as evaluation data; do not train on their answers and then reuse their scores as an unbiased test.
- The local app was restarted after comparison and still uses the base model. No user-submitted code was transmitted externally or executed.
