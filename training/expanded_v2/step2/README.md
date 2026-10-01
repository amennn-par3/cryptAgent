# Step 2: H04 initialization witnesses

Six authored cases cover missing/configured CKKS scale, missing/configured TFHE
thread-local server key, and missing/enabled OpenFHE PKE. Each pair remains in
training; conservatively, all six share a single context-initialization family.

Run from the repository root using the already installed local runtime:

```bash
python3 training/expanded_v2/step2/run_probes.py --out /absolute/fresh/output
python3 training/expanded_v2/step2/build_dataset.py --evidence /absolute/fresh/output/results.json
```

The runner tests three inputs per case, saves raw logs and source hashes, verifies
the specific missing-setup diagnostic, and checks corrected outputs. Rust panics
are caught by the test harness only; an expected panic does not count as successful
application computation. OpenFHE variants execute in separate processes to avoid
sharing the library's context cache. No model is called.

The builder requires successful native evidence whose case hashes match the
sources. It preserves step 1 and v1, checks answer quotes and split separation,
and produces a separate draft: 57 train, six old validation, ten old regression.
The six additions each target H04 only; other labels remain insufficient context.
These examples do not cover every H04 failure, cryptanalysis, general security,
or fresh held-out evaluation. `training_ready` remains false.

API reference: [TFHE server-key setup](https://docs.zama.org/tfhe-rs/fhe-computation/compute/set-the-server-key).
Behavior is checked against the locally pinned TenSEAL 0.3.16, TFHE-rs 1.4.3 and
OpenFHE 1.4.2, including their installed source and native diagnostics.
