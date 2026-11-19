# Sieve

Input-context compression for coding agents, exposed as a real MCP server.
It decides which repository context the model reads and shrinks noisy tool
output, so the same task is answered with far fewer input tokens.

## Run

```sh
pip install -e .
sieve init          # writes the global MCP server + /sieve commands
sieve index --repo .
sieve query "how does auth check a token" --budget 8000
sieve read auth.py --symbol check_auth --budget 1200
sieve compress build.log --budget 300
```

Or use it inside OpenCode: `/sieve <task>`, `/sieve/query`, `/sieve/read`,
`/sieve/compress`, `/sieve/summarize`, `/sieve/memory`, `/sieve/stats`.

## MCP tools (9)

`index`, `query`, `read`, `compress`, `original`, `symbol`, `stats`, `memory`,
`summarize`. Local stdio server; `sieve-mcp` on PATH. The HTTP service
(`sieve-serve`) exposes the same engine for scripts.

## Measured

| Check | Result |
|---|---|
| Six-task real benchmark | 6/6 both arms, 52,530 → 6,869 avg input tokens, **86.9% fewer** |
| Real agent A/B | 6/6 both, 52,508 → 6,926 input, 86.8% fewer |
| `sieve_read` | 1,235 → 313 tokens (74.7%) |
| Real log via `sieve_compress` | 571 → 120 (79.0%) |
| Synthetic 2,000-line log | 37,016 → 296 (99.2%) |
| Retrieval eval | full 1,127 / 1.00 recall, sieve 548 / 0.83 |
| Tests | 45 pass, ruff clean |

Every original is kept in `~/.sieve/originals` and returns by ref, so
compression is lossy but recoverable.

## Honest limits

- Compression is lossy; expansion costs a tool call.
- Dense retrieval (fastembed, 384d) did **not** improve the 12 lexical tasks:
  553 tokens / 0.83 / 38.6 ms vs 548 / 0.83 / 11.8 ms. Off by default.
- The trace-fitted allocator is an in-sample grid search on 12 tasks, not a
  trained model. Off by default.
- The LLM summarizer needs `SIEVE_SUMMARY_CMD`; no live run was measured. The
  extractive line is the default.
- The benchmark task set is too easy (both arms 12/12) and has one run per arm.
- Docker image and GitHub CI are written, not executed here.
- No pgvector, no token-aware chunks, no non-Python call graphs, no automatic
  tool-output plugin.

## Layout

```
sieve/discover.py   index.py   parse/   retrieval/
sieve/allocator.py  composer.py  read.py  compress.py
sieve/memory.py     summarize.py  store.py  install.py
sieve/server/mcp.py  sieve/http_server.py  sieve/cli.py
bench/  docs/  tests/  tools/
```

Details: `docs/REAL_BENCH.md`, `docs/EVALUATION.md`, `docs/MCP_SESSION.md`,
`docs/EMBEDDINGS.md`, `docs/ALLOCATOR.md`, `docs/SUMMARIZER.md`,
`docs/INSTALL.md`, and the full gap list in `docs/REMAINING.md`.
