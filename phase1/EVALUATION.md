# Evaluation plan

Compare LLM-only, LLM+specification/retrieval, tools-only and LLM+tools+repair with
the same cases, budgets and profile. Freeze prompts and budgets before held-out use.
Primary metric: confirmed defective cases accepted / confirmed defective cases assessed.
Also measure per-property precision and recall, inconclusive rate, acceptance of
reviewed references, repair success without regression, runtime and model cost.
Show raw counts and uncertainty, not just percentages. Suspected labels are not ground truth.

Current synthetic cases share a template. Their 60/20/20 scenario split is exploratory,
not evidence of unseen-implementation generalization. Before final research evaluation,
add independently authored/reviewed implementations and split by source ancestry.
Do not tune on evaluation labels, retrieve held-out source, or expose expected repairs.
Do not claim 150 independent samples. Report the 30 scenario groups and shared ancestry.
Set numerical targets after the development pilot and before final held-out execution.
