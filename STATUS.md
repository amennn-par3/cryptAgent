# Active status — AES step 1 stabilization, 2026-10-01

The active product is C++20 / Windows CNG / AES-128-GCM source review, F01–F05.
Other scheme experiments remain preserved and are not part of the runtime.

Implemented:
- Simplified source editor, local model status, findings, requirement results,
  source-line selection and JSON export.
- Offline cached Llama base-model service on 127.0.0.1:8081.
- Local web server on 127.0.0.1:8000; only status and verify API routes.
- Fixed loopback model destination; legacy API connection route and controls removed.
- JSON/check-ID/source-quote validation and bounded requests/inference.
- Explicit dataset selection and AES-only profile/check guards in the trainer.
- Prior Phase 1–3 history, datasets, probes and adapters preserved.

Still required:
1. Curate the active AES dataset against the frozen source-review contract.
2. Audit dataset labels, deduplication and independence of held-out examples.
3. Evaluate the experimental AES adapter for actual defect detection, false
   positives, abstention and location/explanation quality.
4. Enable the evaluated adapter in the local runtime; add approved model identity.
5. Run Windows CNG fixtures on native Windows when a machine is available.
6. Consider isolated candidate execution only after the source-review baseline.

The base model is usable for experimental inference, not an approved AES verifier.
Earlier Python and multi-profile adapters exist; neither is selected automatically.
An experimental AES pilot adapter was trained on 2026-10-01 from 22 synthetic
training codes (4 validation, 4 test held out). It is not deployed or approved:
the dataset needs independent label review and a fresh evaluation split. There
is no generation or automatic learning feature in the active application.

## Step 1 validation

- Contract: `docs/AES_REVIEW_CONTRACT.md`; runtime validator:
  `backend/review_contract.mjs`.
- Loading/error health states remain observable; the web app stays available
  if model loading fails. UI automatically refreshes unavailable/loading status.
- Invalid input displays feedback. Model unavailability, context limits and
  invalid output produce explicit non-verdict reports, not synthetic labels.
- Automated checks: 11 Node tests and 4 Python HTTP tests passed.
- Real GPU smoke script: `tests/live_aes.mjs`, three synthetic submissions.
  Python print: outside scope, 3.96 s. Declarations: insufficient context,
  5.43 s. Ignored decryption status: potential issues, 5.08 s.
- These smoke tests establish working inference/report delivery, not accuracy.
  The base model missed the ignored-status concern (the source-pattern check
  surfaced it) and gave overly optimistic individual checks on incomplete code.
  The later experimental fine-tune does not replace independent evaluation.
- An additional stricter-prompt experiment regressed to an overly optimistic
  declaration verdict and an invalid excerpt response. That prompt experiment
  was reverted; it reinforces that prompt compliance is not security accuracy.
