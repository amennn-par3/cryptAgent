# CryptAgent

CryptAgent is a Windows-first C++ source-review prototype for cryptographic integrations. The current mid-term profile evaluates Windows CNG code intended to use AES-128-GCM against a message-tampering attacker model.

The application provides a local web interface for pasting or uploading C++ source. Its backend applies deterministic source observations, requests a structured model review, validates every returned source quotation and line range, and produces a downloadable JSON report.

## Current status

This repository is a research prototype, not a security certification tool.

- Frontend and Node.js backend are implemented.
- The fixed AES review profile and five assessment requirements are implemented.
- Ten evaluation inputs and their recorded responses are included.
- Native compilation, isolated execution, and formal verification are not connected yet.
- The checked-in snapshot still contains the original OpenAI client. The planned next milestone replaces it with a locally served, fine-tuned Llama model.
- No API key or model weight is stored in this repository.

## Review profile

The internal profile is intentionally precise even though the frontend displays the shorter name **AES**:

- Scheme: AES-128-GCM
- Language: C++20
- Library: Windows CNG
- Attacker: message tampering
- Key: 16 bytes
- Nonce: 12 bytes
- Authentication tag: 16 bytes

The five checks are functional correctness, tampering rejection, authentication before output, key and nonce handling, and input/output boundaries.

## Run the current application

Requirements:

- Windows 10 or newer
- Node.js 22 or newer

From PowerShell:

```powershell
cd "C:\path\to\BTP"
powershell -ExecutionPolicy Bypass -File .\start.ps1
```

Open <http://127.0.0.1:8000> and keep the PowerShell window open. Press `Ctrl+C` to stop the server.

The present snapshot can open without credentials, but its complete model review still depends on the provider client in `backend/llm_client.mjs`. The local-Llama migration will remove that dependency.

## Project structure

```text
backend/      HTTP server, verifier, model client, and local checks
frontend/     Local web interface
profiles/     Fixed cryptographic review profile
prompts/      Structured source-review instructions
evaluation/   Inputs, recorded responses, analysis, and PDF report
```

## Evaluation warning

The existing ten-case run records an unavailable-review experiment. Nine live model requests encountered a rate or quota error, and one case intentionally ran without credentials. Those records must not be interpreted as successful security assessments or accuracy measurements.

## Planned local-Llama migration

The next version will:

1. Replace `backend/llm_client.mjs` with a provider-independent local Llama client.
2. Remove API-key controls and provider-specific text from the frontend.
3. Serve the approved fine-tuned model through llama.cpp on `127.0.0.1`.
4. Preserve strict JSON, line-number, and exact-quotation validation.
5. Record the base model, adapter, dataset, prompt, and evaluation versions in every report.
6. Keep deterministic checks and future compiler evidence independent of model claims.

Large model files, adapters, checkpoints, runtimes, and credentials are ignored by Git. Copy approved deployment artifacts separately after cloning.

## Security limitations

CryptAgent currently performs source review only. A result such as “no issues identified” is neither a proof of cryptographic security nor a deployment approval. Submitted code must not be executed without an isolated Windows worker, resource limits, and explicit evidence linking the result to the reviewed source hash.

## Licence

This project is available under the MIT License.

