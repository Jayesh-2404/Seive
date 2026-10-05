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

1. Index: AST parse of all Python files. Extracts functions, classes, imports,
   caller-callee edges. Per-file and per-function chunks.
2. Retrieve: BM25 (k1=1.2, b=0.75) + exact symbol bonus + import bonus +
   1-hop call-graph boost. Returns top-5 files.
3. Allocate: keyword task classifier (bug_fix, feature, perf, question) +
   per-task token split + bypass rule (if repo fits budget, return full dump).
4. Compose: symbols + top-k code + extractive summaries of rest + memory.
   Enforces ceiling. Truncates summaries first, never symbols first.
5. Log: JSON trace per run (query, task type, files, scores, tokens per layer,
   latency, prompt hash) + CSV summary.

No ML training, no GPU, no network in v0.35. Embeddings and LLM summarizer
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
run_eval.py             12 tasks x 6 systems, writes results_eval.csv + traces_eval/
sieve_min_demo.py       legacy 3-file toy, kept for contrast only
sample_repo_large/      generated demo repo (18 files, ~1127 tokens)
results_eval.csv        eval output, budget=600
traces_eval/            one JSON per task-system pair
docs/
  SUBMISSION_30PCT.md   one-page 30 percent summary
  ARCHITECTURE.md       system diagram and store decisions
  EVALUATION.md         metrics, ablations, threats
  DEMO_GUIDE.md         five minute terminal demo script
experiments/
  experiment_plan.md    E01-E05 hypothesis template
```

## Requirements
Python 3.11+, packages: numpy, pandas, tiktoken, pytest, streamlit, fastapi.
No API key needed for v0.35. LLM fix-rate eval needs a key (Milestone-2).

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
repo files=18 total_tokens=1127 symbols=37 edges=55
system          avg_tok  avg_recall  saving_vs_full
full            1127     1.00        --
trunc            600     0.00        +46.8 percent, destroys info
sieve            607     0.86        +46.1 percent, keeps gold files
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
| full | 1127 | 1.00 | upper bound, over budget |
| trunc | 600 | 0.00 | naive cut loses file boundaries |
| tfidf | 607 | 0.86 | no structure |
| sieve | 607 | 0.86 | BM25 + symbols + graph |
| sieve-nosym | 602 | 0.86 | symbols redundant on this repo |
| sieve-nograph | 605 | 0.83 | graph adds 0.03 recall |

Bug presence in `sample_repo_large/tests_core.py`: t_b1, t_b2, t_b3 all False
(bugs reproduce, honest baseline). End-to-end LLM fix rate is marked as
experiment to be conducted, harness hook already in `run_eval.py`.

## What Each File Does
- `sieve/tokenizer.py`: single token counter used everywhere.
- `sieve/indexer.py`: repository scanner, call-graph builder.
- `sieve/retrieval.py`: ranking algorithm, code-structure boosts.
- `sieve/allocator.py`: task routing and budget split.
- `sieve/composer.py`: prompt assembly with ceiling enforcement.
- `sieve/memory.py`: conversation store stub.
- `sieve/mcp_server.py`: agent integration stub.
- `run_eval.py`: baselines, ablations, metrics, traces.

## Limitations
- Summaries are extractive one-liners, no LLM compression yet.
- Allocator is rule-based, learned version needs 500+ logged runs.
- Single Python repo, 12 tasks, gold labels by authors.
- No vector DB, no server, no dashboard in v0.35 by design.
- Tokenizer fallback char/4 used only if tiktoken missing.

## Next Milestones
1. LLM summarizer with identifier-preservation check.
2. LLM fix-rate eval with pinned model, temp=0, cost tracking.
3. Learned allocator trained on collected logs, leave-one-repo-out test.
4. Dense embeddings + pgvector + RRF fusion, ablated against BM25.
5. FastAPI HTTP, Docker, Streamlit dashboard, full MCP SDK.

## Status
v0.35 vertical slice. See docs/ for architecture, evaluation, and demo guide.
