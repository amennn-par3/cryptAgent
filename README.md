# CryptAgent — AES source review

The active application reviews **C++20 Windows CNG AES-128-GCM** source against
five fixed requirements. It runs a cached Llama model locally, displays
source-referenced findings, and exports a JSON report.

## Current scope

- Verification/source review only; no generation, repair, or automatic learning.
- AES-128-GCM: 16-byte key, 12-byte nonce, 16-byte authentication tag.
- Message-tampering attacker model.
- F01 functional correctness; F02 tampering rejection; F03 authentication before
  plaintext output; F04 key/nonce/tag handling; F05 input/output boundaries.
- One source file/excerpt, up to 64 KiB and 2,000 lines. The local model also
  requires the complete prompt to fit 3,072 input tokens; oversized input is
  rejected without truncation.
- Native compilation/execution and formal verification are not connected.

The current runtime uses the cached **Llama-3.1-8B-Instruct base model**.
An experimental AES LoRA adapter was trained locally, but its small synthetic
evaluation does not justify deployment; neither it nor the historical Python
and multi-profile adapters are loaded by the application. See the
[20-case exploratory report](evaluation/aes_pilot_20/REPORT.md).

## Project trajectory

AES/CNG is the first controlled profile, not the final project scope. Separate
research fixtures cover Python/TenSEAL CKKS, Rust/TFHE-rs and C++/OpenFHE BFV
(a lattice-based example). Those profiles and attacker models are not selectable
in the active AES-only web app. The midterm work is verification-focused;
selectable profiles and code generation/repair are later goals that require
their own requirements, evidence and evaluation.

## Start

Requirements: Node.js 22+, an NVIDIA GPU with working CUDA access, and the
existing Python environment with PyTorch, Transformers, Accelerate and
bitsandbytes. The pinned Llama weights/tokenizer must already be cached.
Startup is offline: missing weights produce a model-loading error, not a download.
The web app stays available to display that error.

On the laboratory Linux machine:

```bash
cd /home/hp/Documents/Codex/2026-09-29/pull-and-setup/cryptAgent
bash start.sh
```

On Windows, with the same dependencies/cache configured:

```powershell
powershell -ExecutionPolicy Bypass -File .\start.ps1
```

With Node on PATH, `npm start` also starts both services. The launcher uses
`CRYPTAGENT_PYTHON` when set; otherwise it looks for the project `.venv`, then
`~/crypto-llm/.venv`, then system Python. On this lab machine the existing
`/home/hp/crypto-llm/.venv/bin/python` is discovered automatically.

Open <http://127.0.0.1:8000>. Model-loading status refreshes automatically.
Paste/open C++ code and select **Review AES code**. Ctrl+C stops both services.
If either child service exits, the launcher stops the other one too.

`npm run web` runs only the web server, for development with a separately
started `backend/local_model.py`. An unavailable model is shown explicitly.

Step 1's fixed input/output and failure behavior is documented in
[the AES review contract](docs/AES_REVIEW_CONTRACT.md). Valid submissions
produce a report even when model inference is unavailable; invalid requests
show explicit errors. This does not guarantee a security verdict for any code.

## Active workflow

```text
Browser -> validate source -> local model -> validate JSON and exact quotes
        -> combine source observations -> display/export AES report
```

The web API has only two routes:
- `GET /api/status`: fixed profile, local model status and session token.
- `POST /api/verify`: `{code, profileId, mode: "verify"}`, with JSON content
  type and the session token in `X-Session-Token`.

The internal Python service implements `GET /health` and `POST /review` on
`127.0.0.1:8081`. It accepts only the AES profile. The backend's destination is
fixed to this loopback address. There are no API-key controls, remote-provider
fallbacks, training endpoints, or selectable scheme placeholders.

The report records the source/profile hashes, model revision and prompt hash,
five requirement assessments, exact source quotations and explicit execution
status. Submitted source is not persisted by either service; exported reports
contain quoted excerpts. Model output never becomes training data automatically.

## Validation

```bash
npm test
PYTHONDONTWRITEBYTECODE=1 python3 tests/test_local_model.py
```

The HTTP tests use a stub model to exercise routing, malformed input, unsupported
profiles, offline behavior and quote validation. They do not measure model quality.
See [STATUS.md](STATUS.md) for remaining work.

## Preserved research

Earlier work is retained for reproducibility:
- `phase1/`, `phase2/`, `phase3/`, `tools/demo_backend.py`: original
  specifications, schemas and synthetic benchmark. Its libsodium/native
  demonstration is separate from the active Windows CNG web profile.
- `evaluation/`: historical evaluation artifacts, including provider failures.
- `training/`: earlier datasets, FHE probes, Python-source preparation and
  ignored model runs. See [training/README.md](training/README.md).
- `prompts/verify_multi.txt`: historical multi-profile prompt, not loaded.

Historical documents such as [WALKTHROUGH.md](WALKTHROUGH.md) and
[VALIDATION.md](VALIDATION.md) describe their original experiments. A file's
presence here does not mean its feature is enabled in the current application.
Weights, adapters, checkpoints, environments and runtime binaries remain ignored.

## Limits

A model finding is an advisory source-review hypothesis. Exact quote validation
checks the reference, not the interpretation. The small pattern scanner is not
a C++ parser. No-issue output does not establish that code is secure.
Windows CNG runtime validation and independent model evaluation remain pending.

MIT License.
