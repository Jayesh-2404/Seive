# Sieve - 30% Submission Document

## 1. What we built (runnable today)
```
pyproject.toml              -> package metadata, deps, sieve, sieve-mcp and sieve-serve entry points
sieve/discover.py           -> repo walk, binary and size guards, skip reasons
sieve/index.py              -> index build, call graph, def_index
sieve/parse/python_ast.py   -> Python ast symbols, imports, calls
sieve/parse/treesitter.py   -> TS, JS, C, C++, Go, Java, Rust symbols
sieve/parse/regex_fallback.py -> fallback when a grammar is not installed
sieve/retrieval/            -> BM25 (k1=1.2, b=0.75) + symbol/part/import/graph
sieve/embeddings.py         -> local dense index with fastembed, 384 dims
sieve/allocator.py          -> keyword router + bypass rule (repo<budget -> full dump)
sieve/allocator_learned.json -> trace-fitted splits, opt-in
sieve/composer.py           -> symbols -> top-k -> extractive summaries, hard ceiling
sieve/compress.py           -> budgeted compression for logs, tests, JSON, CSV, HTML
sieve/read.py               -> symbol-aware file reads
sieve/store.py              -> original text store and token event log
sieve/memory.py             -> persistent notes and recent turns, wired into query
sieve/summarize.py          -> extractive default, optional external model, identifier check
sieve/install.py            -> writes the global MCP server and /sieve commands
sieve/templates/commands/   -> command templates copied by `sieve init`
sieve/server/mcp.py         -> MCP: index, query, read, compress, original, symbol, stats, memory, summarize
sieve/http_server.py        -> FastAPI adapter over the same engine
Dockerfile                  -> HTTP service image
.github/workflows/ci.yml    -> lint, tests, eval, HTTP import
sieve/cli.py                -> the same operations from a terminal
run_eval.py                 -> 12 tasks x 5 systems, Recall@5 + tokens + latency + traces
tools/ab_build.py           -> builds the full-context and Sieve arms for an OpenCode A/B
tools/fit_allocator.py      -> grid-searches splits and writes allocator_learned.json
tests/                      -> 45 tests: ceiling, languages, compression, reads, HTTP, vectors, memory, summarize, install, MCP
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
| sieve-vec | 553 | 0.83 | dense boost, no gain on this set |

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
one `sieve_index` call, one `sieve_read` call and one `sieve_compress` call and
produced the same chain. Details and limits in `docs/DEMO_AB.md`.

A six-task benchmark on the same repository scored 6 of 6 in both arms. Full
context averaged 52,530 input tokens and Sieve averaged 6,869, for 86.9% fewer.
The full answers and the per-task CSV are in `docs/REAL_BENCH.md` and `bench/`.

### 2c. Read less (input compression)
| input | before | after | saved |
|---|---|---|---|
| `activity-model.ts`, symbol `buildWorkItems` | 1,235 | 313 | 74.7% |
| noisy log, budget 120 | 571 | 120 | 79.0% |
| 2,000 line log, budget 300 | 37,016 | 296 | 99.2% |

Every original is kept in `~/.sieve/originals` and comes back with
`sieve_original`. The 2,000 line log is a synthetic fixture.

## 3. Algorithms used (not just plumbing)
1. **Structural extraction**: Python `ast` for accurate symbols and call edges, tree-sitter grammars for TS, JS, C, C++, Go, Java and Rust, regex only as fallback. Extension to language is one table.
2. **BM25** (Robertson & Jones): TF saturation + length norm + IDF, implemented from scratch.
3. **Hybrid boost**: exact symbol + symbol-part + import + 1-hop callee. camelCase and snake_case are split before scoring.
4. **Budget routing**: keyword classifier with word boundaries + per-task split + bypass + hard ceiling. Cut order is memory, summaries, retrieved tail, symbols.
5. **Budgeted compression**: kind detection, keep errors, paths and counts, collapse repeated lines, pack head and tail to a token budget, keep the original by content hash.
6. **Dense fusion**: optional local fastembed vectors, 384 dimensions, added as a cosine boost to the BM25 and structure score. Ablated as `sieve-vec`.
7. **Trace-fitted split**: a grid search over five candidate splits on 12 tasks, written to `allocator_learned.json` and used only with `--learned`.
8. **Summary validation**: an optional external model writes a summary, every backticked identifier is checked against the source and symbol list, and a failed check falls back to the extractive line.

## 4. What is NOT done (next 70%)
- LLM summarizer (the interface, identifier check and external-provider hook exist, but no live model was run)
- Learned allocator (an in-sample split table exists, not a trained model)
- pgvector / RRF (a local dense index exists, but it did not improve this set)
- Docker image build and a remote CI run are not verified on this machine
- LLM fix-rate eval at scale (A/B pilot run, needs reps and more tasks)
- Call edges for non-Python languages, so the graph boost is Python-only
- Conversation compaction (memory is wired, but old turns are not compacted)
- Remote MCP deployment, which needs the repo on the server side

## 5. How to reproduce
```
pip install -e .
python tools/build_large_repo.py
python run_eval.py 600
python -m pytest -q
sieve read auth.py --repo sample_repo_large --symbol check_auth --budget 200 --json
sieve compress noisy.log --budget 300 --json
sieve memory --note "decision: keep the six-task benchmark"
sieve query "fix the token check" --vectors
sieve query "fix the token check" --learned
sieve summarize auth.py --repo sample_repo_large --json
sieve init
sieve stats
sieve-serve
```
Set `SIEVE_SUMMARY_CMD` to a command that reads a prompt and writes text to
enable the external summary model. Without it, the extractive line is used.
The HTTP service exposes `/health`, `/index`, `/query`, `/read`, `/compress`,
`/stats` and `/original/{ref}`. A live check returned 18 files for the demo repo
and a 538 token query under the 600 budget.
Outputs: `results_eval.csv`, `traces_eval/<task>-<system>.json`

MCP: add the `sieve` local server to `opencode.json`, run `opencode mcp list`,
and expect `sieve connected`. OpenCode exposes `sieve_index`, `sieve_query`,
`sieve_read`, `sieve_compress`, `sieve_original`, `sieve_symbol` and
`sieve_stats`. The config is in `docs/MCP_SESSION.md`.

A/B demo: `python tools/ab_build.py <repo> <out_dir> 8000`, then the two
`opencode run` commands in `docs/DEMO_AB.md`.

## 6. Files to print for submission
- This file, `results_eval.csv`, one `traces_eval/B1-sieve.json`
- `sieve/retrieval/bm25.py`, `sieve/parse/treesitter.py`, `sieve/compress.py`, `sieve/server/mcp.py`, `sieve/http_server.py`
- `Dockerfile`, `.github/workflows/ci.yml`
- `docs/DEMO_AB.md`, `docs/MCP_SESSION.md`, `docs/REAL_BENCH.md`, `docs/EMBEDDINGS.md`, `docs/ALLOCATOR.md`
- `docs/SUMMARIZER.md`, `docs/INSTALL.md`
- `docs/AB_ANSWER_run-a.md`, `docs/AB_ANSWER_run-b.md`
