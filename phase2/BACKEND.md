# Backend design and present implementation

1. Request gateway parses JSON and validates types, required fields and allowed profile.
2. Specification resolver loads the contract and validates it. Paths must remain inside
   the package/workspace. Never fetch an arbitrary path or execute source comments.
3. Profile resolver checks the actual Windows toolchain and dependency lock.
4. Planner maps requirement IDs to approved check adapters; it cannot remove checks.
5. In assess mode, examine supplied source. In generate mode, give a future model the
   contract plus development-only guidance. In repair mode, give it confirmed findings.
6. Build/test adapters run on an isolated Windows worker for untrusted submissions.
7. Evidence normalizer preserves stdout, exit status, source hash, tool version and scope.
8. Policy engine derives the verdict independently of model prose.
9. Reporter explains evidence and missing checks; repair controller allows three attempts.

Present runnable demo: steps 1–2, a narrow source-pattern check, and steps 8–9.
It makes no LLM call, performs no native build and does not execute submitted C++.
Its ignored-authentication pattern is a suspicion, never a security verdict by itself.
Native fixture runner is separate, and is only for the supplied inspected corpus.
Missing adapters, model, real worker isolation and timing infrastructure are Phase 4–6 work.
See WALKTHROUGH.md for one input traced through both present and future behavior.
