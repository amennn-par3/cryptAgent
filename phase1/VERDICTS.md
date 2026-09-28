# Verdict policy

Requirement status: passes_checks, violated, inconclusive, not_applicable.
Evidence type: empirical, static_heuristic, formal, none.
Confirmed mandatory violations produce fails_checks even if other checks are missing.
Without confirmed violations, any missing mandatory evidence produces inconclusive.
Only all mandatory evidence passing produces passes_checks for the named profile.
This baseline has no default not_applicable requirements; exceptions need a versioned
policy, never an LLM decision. A heuristic suspicion alone is inconclusive.

Tool timeouts, crashes, unsupported syntax and unavailable dependencies are never passes.
Do not infer safety from the absence of matching regular expressions. Store exact
source hashes and evidence artifacts. LLM confidence never overrides tool results.
Three repair attempts; requirements, tests, dependency and profile cannot be weakened.
After a patch rerun affected checks and the mandatory regression suite.
Report suspected and confirmed issues distinctly. Do not represent an attack on a
symbolic model as a proven defect in code without checking their correspondence.
