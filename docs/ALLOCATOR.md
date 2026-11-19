# Allocator: rule split and trace-fitted split

The allocator decides how many tokens each layer gets. The default is still the
rule split. A trace-fitted split is available behind a flag.

## The rule split

| Task type | Symbols | Semantic | Summary | Memory |
|---|---|---|---|---|
| bug_fix | 0.25 | 0.50 | 0.15 | 0.10 |
| feature | 0.20 | 0.55 | 0.15 | 0.10 |
| perf | 0.10 | 0.40 | 0.40 | 0.10 |
| question | 0.15 | 0.60 | 0.15 | 0.10 |

## The trace-fitted split

`tools/fit_allocator.py` runs a grid search over five candidate splits on the 12
eval tasks. It measures prompt coverage, which means the gold file code appears
in the prompt. It writes `sieve/allocator_learned.json`.

| Task type | Best split | Coverage | Avg tokens |
|---|---|---|---|
| bug_fix | semantic_heavy | 1.00 | 578.7 |
| question | semantic_heavy | 0.778 | 524.7 |
| feature | semantic_heavy | 0.833 | 550.5 |
| perf | rule | 0.667 | 524.0 |

The result favors more semantic tokens on this repository. That is a small,
in-sample signal. It is not a learned model.

## How to use it

```sh
sieve query "fix the token check" --learned --json
python tools/fit_allocator.py
```

- MCP: `sieve_query(task, learned=true)`.
- HTTP: `{"task": "...", "learned": true}`.
- The default remains the rule split, so the measured A/B and eval do not move.

## Limits

- In-sample. The same 12 tasks are used to fit and to score.
- Twelve tasks, not the 500+ runs the synopsis asks for.
- It is a split table selected by grid search, not a trained classifier or
  regression.
- No held-out repository and no task-success metric.
- The next step is to log many runs across repositories, fit a small model, and
  test leave-one-repo-out against the rule.
