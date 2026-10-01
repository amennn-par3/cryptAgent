# Fresh targeted FHE evaluation — v2

This directory is **evaluation only**. Never add its rows, corrected/faulty partners,
or lightly rewritten variants to training. The 57-row training draft is unchanged
at `training/expanded_v2/step2/data/train.jsonl`.

## Contents

- `data/validation.jsonl`: six plaintext-to-telemetry boundary cases (H03).
- `data/test.jsonl`: six evaluator-work-budget cases (H05).
- `data/manifest.json`: source hashes, split families, coverage limitations and historical similarity audit.
- `data/FREEZE.json`: pinned dataset/prompt/manifest/native-evidence hashes and reuse policy.
- `cases/`: four examples per language, with related counterparts kept together.
- Python/Rust/C++ harnesses: native tests of authored fixtures, not model inference.

Every split has three issue cases and three corrected cases. The three languages
are Python/TenSEAL CKKS, Rust/TFHE-rs and C++/OpenFHE BFV. Telemetry stays in a
local in-memory list in the harness; no external collector receives data. Only
synthetic plaintext is used. Resource probes use small counts (at most four), not
large denial-of-service workloads.

The native evidence covers 44 trials: 18 telemetry observations and 26 work-budget
observations. Source inspection establishes that corrected budget guards precede
evaluation; runtime probes check acceptance/rejection and arithmetic outcomes.

## Revalidation

From the repository root, provide the original evidence JSON pinned by FREEZE:

```bash
python3 training/evaluation_v2/validate_dataset.py --evidence /absolute/path/results.json --report /absolute/fresh/audit.json
```

To repeat native checks into a new directory:

```bash
python3 training/evaluation_v2/run_probes.py --out /absolute/fresh/native-results
```

A repeat native run has new timings/hashes and does not replace the pinned original
evidence automatically. `build_dataset.py` refuses to overwrite a frozen version.
`training/train.py` rejects manifests marked `evaluation_only`.

## Interpretation and future use

No Llama prediction has been generated for these examples. Validation can later
guide model selection. Keep the test unused by the target model until the agreed
evaluation. Once test results guide a change, retire that test to regression and
create a fresh test version for a subsequent unbiased check.

These are differently structured local implementations, not an independently
authored benchmark. Library API boilerplate overlaps existing examples; normalized
source matching and token-sequence similarities are only leakage diagnostics, not
proofs of semantic or pretraining independence. Each split has just one semantic
family across three languages, so six examples are not six independent families.

Score target H03/H05 judgments and false alarms separately from schema validity
and nontarget abstention. Most nontarget labels intentionally remain insufficient
context. This set does not cover all H01-H05 checks or add AES/Windows CNG tests.
The old evaluated test stays regression-only. Do not claim broad verification
accuracy from this narrow set.

API references: [TenSEAL operations](https://openmined.github.io/TenSEAL/) and
[TFHE-rs source/examples](https://github.com/zama-ai/tfhe-rs).
Native runs use the locally pinned library versions documented in their logs.
