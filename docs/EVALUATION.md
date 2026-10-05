# Evaluation (honest, no invented LLM scores)

## Claim under test
Same token budget as naive truncation, but keeps gold files (Recall@5) because of structure-aware retrieval.

## Design
- 12 pre-registered tasks (B1-B3 bugs, Q1-Q3 localization, F/R/P/V/S) with `gold` files.
- 6 systems: full / trunc / tfidf / sieve / sieve-nosym / sieve-nograph.
- Metrics: tokens (tiktoken cl100k), Recall@5 vs gold, latency_ms, saving_vs_full.
- Reps: 1 (deterministic retrieval; LLM variance N/A yet). LLM pass@k reserved for Milestone-2 with pinned model + temp=0 x3.

## What we report today
Retrieval + cost only. Functional bugs verified present (t_b1..t_b3 all False = reproduce). This proves tasks are non-trivial without claiming an LLM fixed them.

## Ablations read
- `-nosym`: no drop here (queries already lexically rich) — symbols matter more on alias-heavy repos (future test).
- `-nograph`: -0.03 recall — graph helps Q1/Q2 (callers of auth/cart). Small but in expected direction.

## Threats
Single small repo, gold labels by us, no cross-repo check yet. Mitigation: leave-one-repo-out + second repo (Express) in next milestone; pre-registered tasks prevent cherry-picking.
