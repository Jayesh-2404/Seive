# Sieve — Research Notebook / Experiment Plan
Every improvement must be measured. No trial-and-error.

## Experiment Template (copy per experiment)
- ID: EXX
- Hypothesis:
- Independent variable:
- Dependent variable:
- Baseline:
- Dataset/test set: (repo commit SHA, task IDs, model pinned `model=... temp=0`)
- Metrics: in_tokens, out_tokens, $, latency_ms, success (tests), Recall@k
- Expected outcome:
- Actual result: (leave blank until run — label "Experiment to be conducted" if not run)
- Interpretation:
- Next experiment:

## Initial Experiments (30-35% milestone)
### E01 — Does hybrid beat vector-only on retrieval?
- H: AST symbols + TF-IDF/vector recall gold files better than vector-only
- IV: retriever {vector-only vs hybrid}
- DV: Recall@5, tokens retrieved
- Baseline: vector-only top-k=5
- Dataset: 12 tasks on 1 repo (FastAPI Todo sample, commit pinned)
- Metrics: Recall@5, MRR, tokens
- Status: Experiment to be conducted

### E02 — Does budgeted compose save tokens at parity?
- H: Fixed-budget compose (4k) saves >=35% vs full-dump at <=5pp success drop
- IV: system {full-dump vs naive-trunc-8k vs sieve-fixed-4k}
- DV: in_tokens, success%
- Baseline: full-dump
- Dataset: same 12 tasks, model pinned, reps=3, temp=0
- Status: Experiment to be conducted

### E03 — Which layer matters? (ablation)
- H: Removing symbols hurts localization; removing summaries hurts broad Qs
- IV: lesions {-symbols, -summaries}
- DV: Δsuccess, Δtokens vs full Sieve
- Status: Experiment to be conducted

### E04 — Allocator: fixed vs task-routed
- H: Task-type routing (bug_fix→symbols-heavy, perf→summary-heavy) saves >=15% vs fixed split at equal success
- IV: allocator {fixed 40/30/15/15 vs routed}
- Status: Experiment to be conducted

### E05 — Summarizer fidelity spot-check
- H: Summaries preserve identifiers; <10% hallucinated symbols on 30-sample human check
- IV: summarizer on/off
- DV: groundedness, identifier retention
- Status: Experiment to be conducted (human eval, do not LLM-judge alone)

## Rules
1. Pre-register tasks before running Sieve (no cherry-picking).
2. Pin model version, temp=0, commit SHA.
3. Report mean±std + paired per-task deltas, not pooled means only.
4. Log full trace per run (see trace schema in prototype).
5. Negative results are valid — explain via traces.
