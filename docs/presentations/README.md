# CryptAgent BTP presentations

- `cryptagent_btp_ii.tex` (15 frames): problem formulation, NIST/CNG background,
  project-specific gap, AES-first design, multi-profile expansion and metrics.
- `cryptagent_btp_iii.tex` (18 frames): active implementation, local Llama
  connection, actual tests, experimental adapter comparison, FHE research
  status, limitations and demonstration.

These are separate, standalone Beamer documents. They use the standard Madrid
theme and need no external images. Open either `.tex` in Overleaf or compile with
a standard TeX installation:

```bash
pdflatex -interaction=nonstopmode cryptagent_btp_ii.tex
pdflatex -interaction=nonstopmode cryptagent_btp_iii.tex
```

Before presenting, replace `\mone`, `\mtwo`, `\mthree` in each preamble with
the three real names. Replace each member's bracketed contribution statement
with work that person actually did, preferably naming a decision, file and test.
Change `\institute` and `\date` as needed. Keep BTP-II focused on study design;
the BTP-III deck is where the current implementation and observed results belong.

The decks describe the repository snapshot through 2 October 2026. Recheck the
runtime and dataset manifest before a later evaluation. The AES adapter was
trained experimentally but remains inactive; native Windows CNG execution has
not run.

The built-in LaTeX compiler could not launch its sandbox on this host, and no
terminal TeX compiler is installed here. Source environments were checked for
matching begin/end tags, but PDF compilation remains unverified.
