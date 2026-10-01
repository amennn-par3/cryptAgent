# Curated dataset repair v3

This is a corrected **draft**, not permission to train. The user has explicitly
reserved training authorization. Both `training_ready` and `training_authorized`
remain false in `data/manifest.json`.

## Changes

- Retain 16 unique AES source-review examples and three genuinely incomplete FHE callbacks.
- Exclude 16 whitespace duplicates and replace 22 partial FHE excerpts in this
  release only; historical data and sources are not deleted or modified.
- Add 18 complete FHE client/evaluator workflows: a corrected implementation and
  arithmetic, acceptance, secret-export, setup and bounds mutations per library.
- Add six complete AES CNG session variants with source-reviewed labels. They are
  explicitly not compiled or runtime-verified on this Linux machine.

The result is 43 train rows, six frozen validation rows, six frozen test rows and
ten legacy regression rows. The validation/test bytes are copied unchanged from
the reserved evaluation version; no such sources or variants enter training.
All five checks for all four profiles now have both issue and corrected labels.
This is a coverage count, not an accuracy or security guarantee.

Training labels: 36 potential issues, 94 no-issue-identified, 75 insufficient
context and ten not-applicable. Legitimate uncertainty is retained, not relabeled
as safe. AES controls are source-review judgments and carry an explicit native
evidence status. The same-author program variants are grouped into train-only
families and are not counted as independent implementations.

## Evidence and validation

```bash
python3 training/repaired_v3/run_probes.py --out /absolute/fresh/native-results
python3 training/repaired_v3/build_dataset.py --evidence /absolute/fresh/native-results/results.json
```

Then use the existing model Python environment only to check tokenization (this
does not load model weights, train, or generate model predictions):

```bash
/home/hp/crypto-llm/.venv/bin/python training/repaired_v3/validate_release.py --evidence /absolute/fresh/native-results/results.json --out /absolute/fresh/audit --check-tokens
```

The 18 FHE workflows passed 180 native trials. Tests include correct arithmetic,
modified results, public/private export state, specific setup failures, and both
lower/upper input-domain violations. Only small synthetic inputs are used.
The work is a toy known-reference sum, not a generic FHE computation proof.

The longest training example is 2,754 tokens and fits the existing 3,072-token
limit. This does not establish the peak training VRAM for this longer workload;
a future explicitly authorized run should start with a smoke test.

## Unresolved

No Windows machine is available. The prepared Windows CNG harness is under
`windows/` and must run on native Windows before claiming AES runtime validation.
See its README for instructions and limitations. The frozen fresh evaluation
remains narrow: H03 validation and H05 test, with one family per split. Broader
evaluation is still needed before a general multi-requirement performance claim.

Do not start training until the user explicitly asks. Do not silently drop AES,
substitute another library, promote static review to runtime evidence, or call
this draft a production verifier.
