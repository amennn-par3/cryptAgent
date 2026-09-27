# Cryptagent — Windows Phase 1–3 package

Start with [the worked input and backend walkthrough](WALKTHROUGH.md), then
[the Phase 1 contract](phase1/SCOPE.md). This is a planning, interface and benchmark
package, not a deployed LLM agent or security certification service.

## Included
- Phase 1: fixed scope, attacker model, requirements, Windows profiles and verdict policy.
- Phase 2: JSON schemas and examples, C++ contract and reference integration source.
- Phase 3: 150 materialized synthetic benchmark cases, 15-case pilot, mutation labels,
  check recipes, split manifests and a native C++ test harness.
- A Python demonstration validates a request, finds one narrow source pattern and
  writes an evidence-labelled report. It makes no model/API calls and runs no candidate code.
- Validation checks JSON contracts, file hashes, grouping and negative-schema cases.

## Start on Windows
Open PowerShell in this directory:
```powershell
python tools/validate_package.py
python tools/demo_backend.py --request phase2/examples/assess_request.json --out demo-output
```
The demonstration should flag the ignored authentication result and return
`inconclusive`, because a source-pattern suspicion is not confirmed runtime evidence.
See [native setup](WINDOWS_SETUP.md) for the C++ build.

## Status and evidence boundaries
Read [validation results](VALIDATION.md) for checks actually performed on the host.
Native crypto results require the pinned libsodium dependency and a successful native run.
Benchmark labels begin as authored expectations, not experimentally established truth.
All cases share an authored implementation template: the split is useful for workflow
development, but does not demonstrate generalization to independent implementations.
Do not expose held-out labels or repairs to the future assessment agent.

## Navigation
- [Phase 1](phase1/SCOPE.md) / [threat model](phase1/THREAT_MODEL.md)
- [Requirements](phase1/REQUIREMENTS.md) / [verdicts](phase1/VERDICTS.md)
- [Phase 2 interface](phase2/INTERFACE.md) / [backend design](phase2/BACKEND.md)
- [Phase 3 guide](phase3/BENCHMARK.md) / [coverage](phase3/COVERAGE.md)
- [Remaining work and completion gates](STATUS.md)
- [Sources](SOURCES.md)

Intentionally defective C++ fixtures live only in phase3. Never deploy them.
