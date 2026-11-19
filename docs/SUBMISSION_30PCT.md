# Sieve — 30% Submission Document

## 1. What we built (runnable today)
```
tools/build_large_repo.py  -> 18-file demo repo (~1052 tokens, 37 symbols, 12 call edges)
sieve/indexer.py           -> Python ast + JS/TS regex: funcs/classes/imports/calls, chunks
sieve/retrieval.py         -> BM25 (k1=1.2,b=0.75) + symbol +5/+2 parts + import +2 + graph +1.5
sieve/allocator.py         -> keyword task router + bypass rule (repo<budget -> full dump)
sieve/composer.py          -> symbols -> top-k -> extractive summaries, hard ceiling (tested)
sieve/memory.py            -> turns.jsonl + notes.md (two-tier memory stub)
sieve/mcp_server.py        -> stdio JSON-RPC: index / query / get_symbol
run_eval.py                -> 12 tasks x 5 systems, Recall@5 + tokens + latency + traces
tools/ab_build.py          -> builds the full-context and Sieve arms for an OpenCode A/B
tests/test_sieve.py        -> indexer, camelCase, ceiling and bypass checks
sieve_min_demo.py          -> legacy 3-file toy (kept for contrast)
```

## 2. Measured results (budget=600, 18 files, 12 tasks)
| system | avg tokens | Recall@5 | saving vs full |
|---|---|---|---|
| full | 1068 | 1.00 | — |
| trunc (naive cut) | 600 | 0.00 | +43.8% but destroys info |
| **sieve (BM25+sym+graph)** | **518** | **0.83** | **+51.5% at high recall** |
| sieve-nosym | 518 | 0.83 | ablation: symbols redundant here |
| sieve-nograph | 519 | 0.83 | ablation: no measurable graph lift |

Bug presence (honest, `sample_repo_large/tests_core.py`): t_b1=False, t_b2=False, t_b3=False (all 3 bugs reproduce).
End-to-end LLM fix rate: EXPERIMENT TO BE CONDUCTED (needs API key, see §4).

Reading: at equal token budget, naive truncation keeps 0% of gold files; Sieve keeps 83%. That is the filter value.

### 2b. Real agent A/B (OpenCode, one run per arm)
Same question, same model, no tools, only the attached context differs.
Repo: `agent-activity-dashboard` at commit `618610d`, 42 TS files.

| arm | context tokens | input tokens | answer key |
|---|---|---|---|
| full repo | 51,194 | 52,507 | 6 / 6 |
| Sieve, budget 8000 | 5,642 | 7,067 | 6 / 6 |

86.5% fewer input tokens at the same answer quality. Details and limits in
`docs/DEMO_AB.md`.

## 3. Algorithms used (not just plumbing)
1. **AST extraction** (`ast`) for Python, regex symbol extraction for JS/TS: def/class/import/call visitors, caller->callee edges, def_index for expansion.
2. **BM25** (Robertson & Jones): TF saturation + length norm + IDF, implemented from scratch.
3. **Hybrid boost**: exact symbol + symbol-part + import + 1-hop callee boost — the code-structure part plain RAG lacks. camelCase and snake_case are split before scoring.
4. **Budget routing**: keyword classifier + per-task split + bypass + hard ceiling. The cut order is memory, summaries, retrieved tail, symbols.

## 4. What is NOT done (next 70%)
- LLM summarizer (currently extractive one-liners preserving identifiers)
- Learned allocator (needs ≥500 logged runs; rule v0 ships now)
- pgvector / embeddings / FastAPI-HTTP / Docker (files suffice at this scale)
- LLM fix-rate eval at scale (A/B pilot run, needs reps and more tasks)
- JS/TS parsing is regex-level, not tree-sitter

## 5. How to reproduce
```
python tools/build_large_repo.py
python run_eval.py 600
python -m unittest discover -s tests
```
Outputs: `results_eval.csv`, `traces_eval/<task>-<system>.json`
MCP check: `echo '{"id":1,"method":"index","params":{"repo":"sample_repo_large"}}' | python -m sieve.mcp_server`
A/B demo: `python tools/ab_build.py <repo> <out_dir> 8000`, then the two `opencode run` commands in `docs/DEMO_AB.md`.

## 6. Files to print for submission
- This file, `results_eval.csv`, one `traces_eval/B1-sieve.json`, `sieve/retrieval.py`
- `docs/DEMO_AB.md`, `docs/AB_ANSWER_run-a.md`, `docs/AB_ANSWER_run-b.md`
