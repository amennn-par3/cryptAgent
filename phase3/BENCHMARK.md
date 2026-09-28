# Benchmark protocol

150 materialized source fixtures: 30 reference, 90 single mutation and 30 double mutation.
30 scenario groups combine six plaintext lengths with five AAD lengths. Every group
has one reference, three rotating defects and one double defect. Sources are authored
mutations of ONE implementation template, not 30 independent implementations.
The corpus is intentionally useful for plumbing and defect regression, not a claim
of broad code-generalization accuracy. The 15-case pilot is the first three development groups.

Each case has candidate.cpp, case.json and CHECK.md. Labels are authored expectations.
Native results must be stored separately with hashes; never overwrite expected labels
with the agent's opinion. Confirm each mutation with its witness or reviewed source
reasoning before including it as ground truth in reported detection rates.
One mutation can violate multiple requirements; 'single' means one code mutation.

Supported concrete mutations: fixed nonce, fixed key, ignored authentication result,
omitted AAD, plaintext log, key log, missing plaintext size limit, missing AAD limit,
rejection of empty input and rejection of the inclusive maximum.
No fake timing/cleanup labels are synthesized: those need dedicated adapters and review.

## How to use
1. Validate the package and run the demo without native dependencies.
2. Set up Windows tools and libsodium; run the pilot native harness.
3. Review each expected failure against recorded stdout/stderr and exact source.
4. Run all 150 when pilot behavior is understood. Keep labels separate from run artifacts.
5. Add independent implementations, cleanup/lifetime/timing fixtures and fault injection
   before calling this a complete research benchmark.

Split: 90 development / 30 validation / 30 held-out cases, grouped by scenario.
All mutations of a scenario stay together. Shared template ancestry crosses splits,
so this split MUST NOT be reported as unseen-code generalization. Final evaluation
needs an independent-source split. Keep held-out metadata offline from model retrieval.
