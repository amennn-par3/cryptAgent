# Python source preparation tools

This pipeline is separate from the earlier AES/FHE pilot. It reads the user's
source clones without modifying them and never assigns a secure label based only
on a repository, function name, cryptographic algorithm, or passing round trip.

From the CryptAgent root:

```bash
python3 training/python_sources_v1/prepare_sources.py --sources /home/hp/crypto-llm/sources --out /absolute/fresh/dataset
python3 training/python_sources_v1/verify_findings.py --out /absolute/fresh/dataset/review-evidence.json
python3 training/python_sources_v1/build_reviewed.py --dataset /absolute/fresh/dataset
python3 training/python_sources_v1/validate_dataset.py --dataset /absolute/fresh/dataset
```

Do not feed `candidates.jsonl` or `review-queue-150.jsonl` into training: their
labels are deliberately unavailable. Only explicit adjudications enter
`reviewed.jsonl`, and that initial seed is not a complete training release.
Its response schema is not the existing F01–F05/H01–H05 schema; a matching model
and application adapter is required before deploying predictions.

Raw source quotes and source hashes are preserved. Finding line numbers include
both snippet-relative and original-file positions. Unknown severity is omitted.
Potential identifier-renamed clones are flagged, never assigned matching labels
automatically. Root license texts are copied with provenance; source repositories
and their license notices remain intact.
