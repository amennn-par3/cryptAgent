# CryptAgent

CryptAgent is a Windows-first research prototype for assessing C++ cryptographic integrations. The repository contains both the original Phase 1–3 specification and benchmark package and the newer local web application.

The current web profile evaluates Windows CNG code intended to use AES-128-GCM against a message-tampering attacker model. The frontend displays the shorter scheme name **AES**, while the internal profile remains precise.

## Current status

This is a research prototype, not a security certification service.

- Phase 1 defines the scope, attacker model, requirements, Windows profile, and verdict policy.
- Phase 2 contains JSON schemas, examples, the C++ contract, and reference integration source.
- Phase 3 contains 150 synthetic benchmark cases, mutation labels, split manifests, check recipes, and a native C++ harness.
- The current frontend and Node.js backend provide a local code editor, deterministic observations, structured source review, evidence display, and JSON export.
- Ten newer evaluation inputs, recorded responses, analysis files, and a PDF report are included under `evaluation/`.
- Native compilation, isolated execution, and formal verification are not connected to the web application yet.
- The checked-in web snapshot still contains the original OpenAI client. The planned next milestone replaces it with a locally served, fine-tuned Llama model.
- No API key or model weight is stored in this repository.

## Review profile

- Scheme: AES-128-GCM
- Language: C++20
- Library: Windows CNG
- Attacker: message tampering
- Key: 16 bytes
- Nonce: 12 bytes
- Authentication tag: 16 bytes

The web verifier assesses functional correctness, tampering rejection, authentication before output, key and nonce handling, and input/output boundaries.

## Run the current web application

Requirements:

- Windows 10 or newer
- Node.js 22 or newer

From PowerShell:

```powershell
cd "C:\path\to\BTP"
powershell -ExecutionPolicy Bypass -File .\start.ps1
```

Open <http://127.0.0.1:8000> and keep the PowerShell window open. Press `Ctrl+C` to stop the server.

The present snapshot opens without credentials, but its complete model review still depends on the provider client in `backend/llm_client.mjs`. The local-Llama migration will remove that dependency.

## Validate the original Phase 1–3 package

Open PowerShell in the repository and run:

```powershell
python tools/validate_package.py
python tools/demo_backend.py --request phase2/examples/assess_request.json --out demo-output
```

The demonstration validates a request, identifies one narrow source pattern, and writes an evidence-labelled report. It does not call a model and does not execute candidate code. See [WINDOWS_SETUP.md](WINDOWS_SETUP.md) for the native C++ setup.

## Repository map

```text
backend/      Current HTTP server, verifier, model client, and local checks
frontend/     Current local web interface
profiles/     Current fixed cryptographic review profile
prompts/      Current structured source-review instructions
evaluation/   Newer ten-case evaluation and generated report
phase1/       Scope, requirements, threat model, and verdict policy
phase2/       Schemas, interface design, examples, and C++ contract
phase3/       Original synthetic benchmark and native harness
tools/        Original validation and demonstration utilities
```

Useful documents:

- [Worked walkthrough](WALKTHROUGH.md)
- [Phase 1 scope](phase1/SCOPE.md)
- [Threat model](phase1/THREAT_MODEL.md)
- [Requirements](phase1/REQUIREMENTS.md)
- [Phase 2 interface](phase2/INTERFACE.md)
- [Phase 3 benchmark](phase3/BENCHMARK.md)
- [Validation record](VALIDATION.md)
- [Remaining work](STATUS.md)
- [Sources](SOURCES.md)

## Evidence warnings

The original benchmark labels are authored expectations rather than experimentally established truth. Related cases share implementation templates, so the split does not demonstrate generalization to independent implementations. Intentionally defective fixtures under `phase3/` must never be deployed.

The newer ten-case run records an unavailable-review experiment: nine live requests encountered a rate or quota error, and one case intentionally ran without credentials. Those responses are historical service-failure records, not successful security assessments or accuracy measurements.

## Planned local-Llama migration

The next version will:

1. Replace `backend/llm_client.mjs` with a provider-independent local Llama client.
2. Remove API-key controls and provider-specific text from the frontend.
3. Serve an approved fine-tuned model through llama.cpp on `127.0.0.1`.
4. Preserve strict JSON, line-number, and exact-quotation validation.
5. Record the base model, adapter, dataset, prompt, and evaluation versions in every report.
6. Keep deterministic checks and future compiler evidence independent of model claims.

Large model files, adapters, checkpoints, runtimes, credentials, and generated native results are ignored by Git. Copy approved deployment artifacts separately after cloning.

## Security limitations

A result such as “no issues identified” is neither a proof of cryptographic security nor a deployment approval. Submitted code must not be executed without an isolated Windows worker, resource limits, and evidence linking the result to the reviewed source hash.

## Licence

This project is available under the MIT License.
