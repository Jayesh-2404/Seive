# Real six-task benchmark

This is the first task-level benchmark on a real repository. It replaces the
single-question A/B as the main evidence.

## Setup

Repository: `https://github.com/Jayesh-2404/agent-activity-dashboard` at commit
`618610d`. 42 TypeScript files, 49,412 tokens in the full dump.
Model: `opencode-go/kimi-k2.7-code`. Agent: `context-only`, every tool denied,
one model step. Each session attached one context file. The context text is the
only variable.

Six tasks, each with a gold file and a gold symbol:

| Task | Question | Gold |
|---|---|---|
| T1 | How does a GitHub repository become a work item in the queue? | `activity-model.ts`, `buildWorkItems` |
| T2 | Where is GitHub data fetched and how does the hook store it? | `dashboard/route.ts`, `use-activity.ts` |
| T3 | How does the app discover local Git repos and read status? | `local-git.ts`, `parseStatus` |
| T4 | How are attention states computed and items sorted? | `activity-model.ts`, `inferAttention` |
| T5 | How does the UI split the queue and render an item? | `queue-view.tsx`, `work-item.tsx` |
| T6 | How does the repository picker load and select repos? | `repo-list.tsx`, `repo-picker.tsx` |

Scoring: one point for naming a gold file, one point for naming a gold symbol.
A task succeeds when both points are earned. This is localization success, not
a fix-rate or test-pass result.

## Results

| Task | Full input | Sieve input | Full success | Sieve success |
|---|---|---|---|---|
| T1 | 52,531 | 6,949 | yes | yes |
| T2 | 52,534 | 6,823 | yes | yes |
| T3 | 52,530 | 6,807 | yes | yes |
| T4 | 52,530 | 6,938 | yes | yes |
| T5 | 52,529 | 7,035 | yes | yes |
| T6 | 52,526 | 6,661 | yes | yes |

| Arm | Success | Points | Avg input | Avg output |
|---|---|---|---|---|
| Full repo | 6 / 6 | 12 / 12 | 52,530 | 615 |
| Sieve, 8,000 budget | 6 / 6 | 12 / 12 | 6,869 | 536 |

Sieve used 13.1 percent of the full arm's input tokens and kept the same
localization score. That is an 86.9 percent reduction.

## What this proves and what it does not

It proves that on these six architecture questions, a 5.5k token Sieve context
was sufficient for the same answers as a 49k full dump. It does not prove that
Sieve preserves task success on harder tasks, because both arms scored a
perfect 12 of 12. The task set is too easy to separate quality. The next step is
a harder set with patches and tests, and three repetitions.

Limits: one run per arm, six tasks, one repository, one model, one question
style. Cost is not reported because `opencode-go` is subscription quota.
Scoring is by the authors, with the key above written first.

## Evidence

- `bench/results_real.csv`: one row per task and arm, with input, output,
  reasoning, file hit, symbol hit and success.
- `bench/summary.json`: the aggregate table.
- `bench/answers/<task>-<arm>.md`: the model's full answer.

## Reproduce

```sh
python tools/real_bench_build.py
python tools/real_bench_run.py r1
```

The build writes the six contexts and the agent config. The run starts 12
archived OpenCode sessions and scores them. It reads tokens from `session_v2` in
the OpenCode database.
