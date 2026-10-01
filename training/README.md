# Active work: AES only

The active application reviews C++20 Windows CNG AES-128-GCM source against
F01–F05. It currently runs the cached Llama base model for local inference.
An experimental AES pilot adapter has been trained; independent evaluation is still pending.

`train.py` requires an explicit `--data` directory and refuses non-AES check IDs
or profile IDs. It also respects the dataset readiness/authorization flags.
No mixed-profile dataset or adapter is chosen automatically.

The existing `data/`, `expanded/`, `expanded_v2/`, `evaluation_v2/`,
`repaired_v3/`, `python_sources_v1/`, and ignored `runs/` preserve prior research.
They are not loaded by the application. Their READMEs describe historical
experiments; do not use their older launch commands as the current workflow.

The next dataset should contain reviewed AES examples with exact F01–F05
findings, an independent held-out split, and explicit static/native evidence.
Do not promote or deploy a draft adapter until that release is reviewed. Source review on this Linux host
does not establish Windows CNG runtime behavior.

`aes_source_pilot_v1/data/` now holds an audited **candidate** of 22 train,
4 validation and 4 test codes. It is AES-profile only, duplicate checked,
source-quote validated, prompt pinned and within the 3,072-token limit. Its
manifest remains `training_ready: false` because independent full-session
label review and a fresh held-out evaluation set are still needed.

On 2026-10-01, with owner approval, an explicitly experimental two-epoch QLoRA
run used only its 22 train rows, with 4 validation rows and 4 untouched test
rows. It used `--experimental-draft --memory-lean` and the expandable CUDA
allocator on the RTX A4000. The adapter and run metadata are under ignored
`training/runs/aes-pilot-lean-v1-20261001/`. The dataset manifest remains
not-ready; validation loss on four cases is not a security-accuracy measure.
The live application continues to load the base model, not this adapter.
