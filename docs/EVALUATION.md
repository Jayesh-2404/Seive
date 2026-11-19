# Evaluation (honest, no invented LLM scores)

## Claim under test
Same token budget as naive truncation, but keeps gold files (Recall@5) because of structure-aware retrieval.

## Design
- 12 pre-registered tasks (B1-B3 bugs, Q1-Q3 localization, F/R/P/V/S) with `gold` files.
- 5 systems: full / trunc / sieve / sieve-nosym / sieve-nograph.
- Metrics: tokens (tiktoken cl100k), Recall@5 vs gold, latency_ms, saving_vs_full.
- Reps: 1 (deterministic retrieval; LLM variance N/A yet). The A/B pilot below covers one real agent run per arm.

## What we report today
Retrieval + cost only for the 12-task table. Functional bugs verified present (t_b1..t_b3 all False = reproduce). This proves tasks are non-trivial without claiming an LLM fixed them.
The separate A/B pilot adds one real agent result with provider-billed tokens.

## Ablations read
- `-nosym`: no drop on this repo, because queries are lexically rich. Symbol matching still earns its place on the TypeScript demo, where camelCase parts surface `buildWorkItems` and `QueueView`.
- `-nograph`: no drop. After edges are filtered to symbols the repo defines, the call graph is too small on an 18-file repo to move recall.

## Real agent A/B
Repo `agent-activity-dashboard` at `618610d`, question about the dashboard data flow, model `kimi-k2.7-code`, no tools in either arm.
Full context 51,194 tokens and 52,507 input tokens. Sieve context 5,642 tokens and 7,067 input tokens. Both scored 6 of 6 on a six-element answer key. That is 86.5% fewer input tokens at parity.
One run per arm, so this is a pilot. See `docs/DEMO_AB.md`.

## Threats
Single small Python repo plus one TypeScript demo question. Gold labels by us. The A/B is one run per arm and one model. Mitigation: pre-registered tasks, a written answer key applied to both arms, and a second repository in the next milestone.
