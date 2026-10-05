# Sieve — 30% Submission Document

## 1. What we built (runnable today)
```
tools/build_large_repo.py  -> 18-file demo repo (~1127 tokens, 37 symbols, 55 call edges)
sieve/indexer.py           -> AST parse: funcs/classes/imports/calls, per-file + per-func chunks
sieve/retrieval.py         -> BM25 (k1=1.2,b=0.75) + symbol bonus +5 + import bonus +2 + call-graph 1-hop +1.5
sieve/allocator.py         -> keyword task router + bypass rule (repo<budget -> full dump)
sieve/composer.py          -> symbols -> top-k -> extractive summaries, strict ceiling
sieve/memory.py            -> turns.jsonl + notes.md (two-tier memory stub)
sieve/mcp_server.py        -> stdio JSON-RPC: index / query / get_symbol
run_eval.py                -> 12 tasks x 6 systems, Recall@5 + tokens + latency + traces
sieve_min_demo.py          -> legacy 3-file toy (kept for contrast)
```

## 2. Measured results (budget=600, 18 files, 12 tasks)
| system | avg tokens | Recall@5 | saving vs full |
|---|---|---|---|
| full | 1127 | 1.00 | — |
| trunc (naive cut) | 600 | 0.00 | +46.8% but destroys info |
| tfidf (no structure) | 607 | 0.86 | +46.1% |
| **sieve (BM25+sym+graph)** | **607** | **0.86** | **+46.1% at high recall** |
| sieve-nosym | 602 | 0.86 | ablation: symbols redundant here |
| sieve-nograph | 605 | 0.83 | ablation: graph +0.03 recall |

Bug presence (honest, `sample_repo_large/tests_core.py`): t_b1=False, t_b2=False, t_b3=False (all 3 bugs reproduce).
End-to-end LLM fix rate: EXPERIMENT TO BE CONDUCTED (needs API key, see §4).

Reading: at equal token budget, naive truncation keeps 0% of gold files; Sieve keeps 86%. That is the filter value.

## 3. Algorithms used (not just plumbing)
1. **AST extraction** (`ast`): def/class/import/call visitors, caller->callee edges, def_index for expansion.
2. **BM25** (Robertson & Jones): TF saturation + length norm + IDF, implemented from scratch.
3. **Hybrid boost**: exact symbol + import + 1-hop callee boost — the code-structure part plain RAG lacks.
4. **Budget routing**: keyword classifier + per-task split + bypass + ceiling enforcement (summaries cut first).

## 4. What is NOT done (next 70%)
- LLM summarizer (currently extractive one-liners preserving identifiers)
- Learned allocator (needs ≥500 logged runs; rule v0 ships now)
- pgvector / embeddings / FastAPI-HTTP / Docker (SQLite+files suffice at this scale)
- LLM fix-rate eval (harness ready, `run_eval.py` traces hook for model calls)

## 5. How to reproduce (2 commands)
```
python tools/build_large_repo.py
python run_eval.py 600
```
Outputs: `results_eval.csv`, `traces_eval/<task>-<system>.json`
MCP check: `echo '{"id":1,"method":"index","params":{"repo":"sample_repo_large"}}' | python -m sieve.mcp_server`

## 6. Files to print for submission
- This file, `results_eval.csv`, one `traces_eval/B1-sieve.json`, `sieve/retrieval.py`
