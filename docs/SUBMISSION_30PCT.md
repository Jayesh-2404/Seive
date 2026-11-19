# Sieve - 30% Submission Document

## 1. What we built (runnable today)
```
pyproject.toml              -> package metadata, deps, sieve and sieve-mcp entry points
sieve/discover.py           -> repo walk, binary and size guards, skip reasons
sieve/index.py              -> index build, call graph, def_index
sieve/parse/python_ast.py   -> Python ast symbols, imports, calls
sieve/parse/treesitter.py   -> TS, JS, C, C++, Go, Java, Rust symbols
sieve/parse/regex_fallback.py -> fallback when a grammar is not installed
sieve/retrieval/            -> BM25 (k1=1.2, b=0.75) + symbol/part/import/graph
sieve/allocator.py          -> keyword router + bypass rule (repo<budget -> full dump)
sieve/composer.py           -> symbols -> top-k -> extractive summaries, hard ceiling
sieve/server/mcp.py         -> real MCP server: index / query / symbol
sieve/cli.py                -> sieve index / query / mcp
run_eval.py                 -> 12 tasks x 5 systems, Recall@5 + tokens + latency + traces
tools/ab_build.py           -> builds the full-context and Sieve arms for an OpenCode A/B
tests/                      -> 11 tests: ceiling, languages, discovery, MCP tools
tools/build_large_repo.py   -> 18-file demo repo with 3 known bugs
```

## 2. Measured results (budget=600, 18 files, 12 tasks)
| system | avg tokens | Recall@5 | saving vs full |
|---|---|---|---|
| full | 1127 | 1.00 | - |
| trunc (naive cut) | 600 | 0.00 | +46.8% but destroys info |
| **sieve (BM25+sym+graph)** | **548** | **0.83** | **+51.4% at high recall** |
| sieve-nosym | 548 | 0.83 | ablation: symbols redundant here |
| sieve-nograph | 541 | 0.83 | ablation: no measurable graph lift |

Bug presence (honest, `sample_repo_large/tests_core.py`): t_b1=False, t_b2=False, t_b3=False (all 3 bugs reproduce).
End-to-end LLM fix rate: EXPERIMENT TO BE CONDUCTED.

Reading: at equal token budget, naive truncation keeps 0% of gold files; Sieve keeps 83%. That is the filter value.

### 2b. Real agent A/B (OpenCode, one run per arm)
Same question, same model, no tools, only the attached context differs.
Repo: `agent-activity-dashboard` at commit `618610d`, 42 TS files.

| arm | context tokens | input tokens | answer key |
|---|---|---|---|
| full repo | 49,412 | 52,508 | 6 / 6 |
| Sieve, budget 8000 | 5,516 | 6,926 | 6 / 6 |

86.8% fewer input tokens at the same answer quality. The same repo was also
driven through the MCP server with every filesystem tool denied. The agent made
one `sieve_index` call and three `sieve_query` calls and produced the same
chain. Details and limits in `docs/DEMO_AB.md`.

## 3. Algorithms used (not just plumbing)
1. **Structural extraction**: Python `ast` for accurate symbols and call edges, tree-sitter grammars for TS, JS, C, C++, Go, Java and Rust, regex only as fallback. Extension to language is one table.
2. **BM25** (Robertson & Jones): TF saturation + length norm + IDF, implemented from scratch.
3. **Hybrid boost**: exact symbol + symbol-part + import + 1-hop callee. camelCase and snake_case are split before scoring.
4. **Budget routing**: keyword classifier with word boundaries + per-task split + bypass + hard ceiling. Cut order is memory, summaries, retrieved tail, symbols.

## 4. What is NOT done (next 70%)
- LLM summarizer (currently extractive one-liners preserving identifiers)
- Learned allocator (needs >=500 logged runs; the rule ships now)
- pgvector / embeddings / FastAPI HTTP / Docker (local stdio is the current deployment path)
- LLM fix-rate eval at scale (A/B pilot run, needs reps and more tasks)
- Call edges for non-Python languages, so the graph boost is Python-only
- Remote MCP deployment, which needs the repo on the server side

## 5. How to reproduce
```
pip install -e .
python tools/build_large_repo.py
python run_eval.py 600
python -m pytest -q
```
Outputs: `results_eval.csv`, `traces_eval/<task>-<system>.json`

MCP: add the `sieve` local server to `opencode.json`, run `opencode mcp list`,
and expect `sieve connected`. OpenCode exposes `sieve_index`, `sieve_query` and
`sieve_symbol`. The config is in `docs/DEMO_AB.md`.

A/B demo: `python tools/ab_build.py <repo> <out_dir> 8000`, then the two
`opencode run` commands in `docs/DEMO_AB.md`.

## 6. Files to print for submission
- This file, `results_eval.csv`, one `traces_eval/B1-sieve.json`
- `sieve/retrieval/bm25.py`, `sieve/parse/treesitter.py`, `sieve/server/mcp.py`
- `docs/DEMO_AB.md`, `docs/AB_ANSWER_run-a.md`, `docs/AB_ANSWER_run-b.md`
