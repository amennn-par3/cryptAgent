# Dataset improvement: step 1 (draft)

This is a dataset and native-test increment, not a new trained model or application feature.
Run from the repository root:

```bash
python3 training/expanded_v2/build_dataset.py
python3 training/expanded_v2/validate_dataset.py
python3 training/expanded_v2/run_probes.py --out /absolute/path/to/a/fresh/results-directory
```

The native runner expects the repository-local dependencies installed for `training/expanded`.
Cargo uses the committed lockfile, cached dependencies, and offline mode.

Nine examples target H02: one faulty batch predicate, one corrected predicate,
and one missing-validation-callback excerpt for each of Python/TenSEAL CKKS,
Rust/TFHE-rs, and C++/OpenFHE BFV. All nine are one semantic family and stay
in training. The callback excerpts are syntax checked but deliberately not executed.

The executable cases compare decrypted components with independently locally
known references. They demonstrate a narrow acceptance-contract defect: accepting
one matching component instead of requiring all components to match. They are not
generic authentication or verifiable-computation constructions for FHE.
Homomorphic ciphertext modification is expected behavior; the defect is in the
application's result-acceptance predicate, not in the encryption scheme.

The 42 original training examples remain unchanged, giving 51 draft training rows.
The six old validation rows are byte-preserved. The ten previously evaluated test
rows are byte-preserved as `regression.jsonl`; they are not a fresh held-out test.
No model response supplies a ground-truth label.

The manifest records source/data hashes, before/after coverage, and blockers.
`training_ready: false` prevents this draft from being used by `training/train.py`.
The target additions have three issue, three no-issue, and three insufficient-context
H02 labels, but the overall dataset is NOT balanced. Parameter/context checks and
fuller independently structured implementations still need work before retraining.
