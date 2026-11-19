# Sieve — Multi-Layer Context and Conversation Compression for LLM Coding Agents

## Problem
LLM context windows (4K-1M tokens) are smaller than real repositories (100K-1M+ tokens).
Coding agents must either dump full files (high cost, low relevance) or truncate
blindly (low cost, loses critical files). This project builds the filter between
repo and LLM: send less text, keep the right text, log proof.

Scope is the context-management layer behind the agent, not a full coding agent.

## What Sieve Does
Input: repo path + question + token budget.
Output: prompt under budget + trace of every decision.

Pipeline: index -> retrieve -> allocate -> compose -> log -> evaluate.

1. Index: AST parse of Python files and regex symbol extraction for JS/TS.
   Extracts functions, classes, imports, caller-callee edges. Per-file and
   per-function chunks.
2. Retrieve: BM25 (k1=1.2, b=0.75) + exact symbol bonus + import bonus +
   1-hop call-graph boost. Returns top-5 files.
3. Allocate: keyword task classifier (bug_fix, feature, perf, question) +
   per-task token split + bypass rule (if repo fits budget, return full dump).
4. Compose: symbols + top-k code + extractive summaries of rest + memory.
   Enforces ceiling. Truncates summaries first, never symbols first.
5. Log: JSON trace per run (query, task type, files, scores, tokens per layer,
   latency, prompt hash) + CSV summary.

No ML training, no GPU, no network in v0.4. Embeddings and LLM summarizer
are Milestone-2 and plug into the same interfaces.

## Repository Layout
```
sieve/
  tokenizer.py    token counting, tiktoken cl100k_base with char/4 fallback
  indexer.py      ast parse, symbols, chunks, imports, call edges, def_index
  retrieval.py    BM25 from scratch + symbol/import/graph boosts
  allocator.py    task classify + budget split + bypass rule
  composer.py     assemble prompt under ceiling, extractive summaries
  memory.py       turns.jsonl episodic + notes.md persistent
  mcp_server.py   stdio JSON-RPC: index, query, get_symbol
tools/
  build_large_repo.py   generates 18-file demo repo with 3 known bugs
  ab_build.py           builds full-context and Sieve-context arms for an A/B
tests/
  test_sieve.py         indexer, camelCase, ceiling and bypass checks
run_eval.py             12 tasks x 5 systems, writes results_eval.csv + traces_eval/
sieve_min_demo.py       legacy 3-file toy, kept for contrast only
sample_repo_large/      generated demo repo (18 files, ~1052 tokens)
results_eval.csv        eval output, budget=600
traces_eval/            one JSON per task-system pair
docs/
  SUBMISSION_30PCT.md   one-page 30 percent summary
  ARCHITECTURE.md       system diagram and store decisions
  EVALUATION.md         metrics, ablations, threats
  DEMO_AB.md            OpenCode A/B demo with provider-billed tokens
  DEMO_GUIDE.md         five minute terminal demo script
experiments/
  experiment_plan.md    E01-E05 hypothesis template
```

## Requirements
Python 3.11+. `tiktoken` is optional, with a char/4 fallback. Everything else
is standard library. No API key is needed for the retrieval eval. The OpenCode
A/B needs an OpenCode provider login.

## How to Run
Generate demo repo:
```
python tools/build_large_repo.py
```

Run full evaluation at tight budget (shows filter value):
```
python run_eval.py 600
```

Expected output:
```
repo files=18 total_tokens=1052 symbols=37 edges=12
system          avg_tok  avg_recall  saving_vs_full
full            1068     1.00        --
trunc            600     0.00        +43.8 percent, destroys info
sieve            518     0.83        +51.5 percent, keeps gold files
```

Outputs: `results_eval.csv`, `traces_eval/<task>-<system>.json`.
Inspect one trace:
```
traces_eval/B1-sieve.json
```
Fields: task, query, system, tokens per layer, files picked, gold files,
recall, prompt hash, latency.

MCP contract check:
```
echo {"id":1,"method":"index","params":{"repo":"sample_repo_large"}} | python -m sieve.mcp_server
```

## Measured Results (budget=600, 12 tasks, deterministic)
| system | avg tokens | Recall@5 | note |
|---|---|---|---|
| full | 1068 | 1.00 | upper bound, over budget |
| trunc | 600 | 0.00 | naive cut loses file boundaries |
| sieve | 518 | 0.83 | BM25 + symbols + graph |
| sieve-nosym | 518 | 0.83 | symbols redundant on this repo |
| sieve-nograph | 519 | 0.83 | no measurable graph lift here |

The earlier `tfidf` row is gone. The harness had routed it to the same code
path as `sieve`, so it measured nothing.

## Real agent A/B (OpenCode, one run per arm)
Same question, same model, no tools, only the attached context differs. Repo is
`agent-activity-dashboard` at commit `618610d`, 42 source files.

| arm | context tokens | input tokens | output | answer key |
|---|---|---|---|---|
| full repo | 51,194 | 52,507 | 602 | 6 / 6 |
| Sieve, budget 8000 | 5,642 | 7,067 | 443 | 6 / 6 |

That is 86.5 percent fewer input tokens at the same answer quality. Numbers come
from the OpenCode session database. Details and limits: `docs/DEMO_AB.md`.

Bug presence in `sample_repo_large/tests_core.py`: t_b1, t_b2, t_b3 all False
(bugs reproduce, honest baseline). End-to-end LLM fix rate is marked as
experiment to be conducted, harness hook already in `run_eval.py`.

## Maths Used (plain explanation)

### Tokens and budget
A token is the unit the LLM bills. With `tiktoken cl100k_base`
(`sieve/tokenizer.py:7-19`), 1 token is about 4 characters.
Example: `def login(user):` (18 chars) counts as 4-5 tokens.
Demo repo totals 1052 tokens. Budget 600 forces filtering.
Saving formula:
```
saving_pct = 100 * (1 - sieve_tokens / full_tokens)
```
Example: `100 * (1 - 518 / 1068) = 51.5 percent`.
Naive trunc also saves `100 * (1 - 600 / 1068) = 43.8 percent`
but cuts mid-file so the saving is useless.

### BM25 scoring (`sieve/retrieval.py:20-75`)
For each query word t and file d, with k1 = 1.2, b = 0.75:
```
IDF(t) = log(1 + (N - df + 0.5) / (df + 0.5))
TF_part = tf * (k1 + 1) / (tf + k1 * (1 - b + b * dl / avgdl))
BM25(d, q) = sum over query words of IDF * TF_part
```
N = file count, df = files containing t, tf = count in this file,
dl = file length, avgdl = mean length.
Example with N = 18, word `auth` in df = 2 files:
```
IDF = log(1 + 16.5 / 2.5) = log(7.6) ~ 2.03
```
A file mentioning it 3 times at average length scores
`3 * 2.2 / (3 + 1.2) ~ 1.57`, contribution `2.03 * 1.57 ~ 3.19`.
Repeating 10 times does not give 3x. That cap is saturation (k1).
The b term stops long files winning by length alone.

### Hybrid boosts
```
final_score = BM25 + 5.0 exact-symbol + 2.0 symbol-part + 2.0 import + 1.5 call-graph
```
Plus 5 when the query word equals a defined def or class name in that file.
Plus 2 when the query shares a word with a symbol name, so `work` matches
`buildWorkItems`. Snake_case and camelCase are split before scoring. Plus 2
when it equals an import. Plus 1.5 for 1-hop callees: if a top-3
file calls f, files defining f get boosted. BM25 here scores roughly 0-10,
so plus 5 dominates without fully overriding text evidence.

### Recall@k
```
Recall@k = len(gold intersect retrieved) / len(gold)
```
Gold is files the task needs, retrieved is top-5 sent.
Example: gold 3 files, retrieved 2 of them gives 2 / 3 ~ 0.67.
Trunc scores 0.0 because it cuts the concatenated blob and later files
never appear. Sieve keeps whole files, hence 0.83 on the demo set.

### Budget split (`sieve/allocator.py:24-40`, `sieve/composer.py:16-55`)
Example question split on budget 600: symbols 90 + semantic 360 +
summary 90 + memory 60. Symbols are cut last. Over ceiling, memory drops
first, then summaries, then the tail of retrieved files, then symbols.
The ceiling is hard and covered by tests. If repo fits in budget times 0.9,
bypass returns the full dump.

### Latency
Wall time around retrieve plus compose, in milliseconds. Local retrieval
is single-digit ms. LLM calls are seconds plus per-token cost. Spending
ms locally to halve input tokens is the full trade.

## What Each File Does
- `sieve/tokenizer.py`: single token counter used everywhere.
- `sieve/indexer.py`: repository scanner, call-graph builder.
- `sieve/retrieval.py`: ranking algorithm, code-structure boosts.
- `sieve/allocator.py`: task routing and budget split.
- `sieve/composer.py`: prompt assembly with ceiling enforcement.
- `sieve/memory.py`: conversation store stub.
- `sieve/mcp_server.py`: stdio JSON-RPC `index` / `query` / `get_symbol`.
- `run_eval.py`: baselines, ablations, metrics, traces.

## Limitations
- Summaries are extractive one-liners, no LLM compression yet.
- Allocator is rule-based, learned version needs 500+ logged runs.
- JS/TS symbols come from regex, not a real parser, so nested declarations can be missed.
- Single Python repo, 12 tasks, gold labels by authors, plus one TS demo question.
- No vector DB, no server, no dashboard in v0.4 by design.
- Tokenizer fallback char/4 used only if tiktoken missing.

## Next Milestones
1. LLM summarizer with identifier-preservation check.
2. LLM fix-rate eval with pinned model, temp=0, cost tracking.
3. Learned allocator trained on collected logs, leave-one-repo-out test.
4. Dense embeddings + pgvector + RRF fusion, ablated against BM25.
5. FastAPI HTTP, Docker, Streamlit dashboard, full MCP SDK.

## Status
v0.4 vertical slice. See docs/ for architecture, evaluation, and demo guide.
