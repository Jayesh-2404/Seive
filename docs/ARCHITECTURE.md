# Architecture (v0.5 - what runs)

```
[Agent] --MCP stdio--> [server/mcp]
                        index / query / read / compress / original / symbol / stats
                              |
        +---------------------+---------------------+
        |                                           |
   repository context                      tool output
        |                                           |
   [discover]                                [compress]
   [parse] python_ast | treesitter | regex    logs, tests, JSON, CSV, HTML
        |                                           |
   [retrieval] bm25 + boosts                 [read]
        |                                    symbol-aware file slices
   [allocator] classify, split, bypass          |
        |                                    [store]
   [composer] prompt <= budget               originals by ref + events.jsonl
        |
   [trace] results_eval.csv + traces_eval/*.json
```

The engine is transport independent. The A/B demo calls `compose` and attaches
the result as a file. The product path calls the same functions through
`server/mcp.py`, which OpenCode starts as a local stdio subprocess in the
project directory. `http_server.py` exposes the same functions over FastAPI for
scripts, dashboards and a hosted deployment. The Dockerfile packages that
service, and the CI workflow runs lint, tests, the eval and an HTTP import.

Sieve has two input paths. The repository path decides which files and symbols
the agent sees. The tool-output path compresses what a tool returns before the
model reads it. Both keep the original text. `read` keeps the whole file,
`compress` keeps the whole input, and `original` returns either by ref.

Store: files on disk plus an in-memory index. The original text store lives in
`~/.sieve` by default, outside the repository. Set `SIEVE_CACHE_DIR` to move it.
No database is needed at this scale. SQLite or pgvector is gated on a repo large
enough to need it.

Memory: `memory/turns.jsonl` plus `memory/notes.md`. Notes hold rules that
survive compaction. The MCP query includes the last turns in its memory layer
and the `memory` tool shows or records a note. Compaction of old turns is not
implemented.

LLM: not called inside Sieve. The prompt is the deliverable. The agent consumes
it. Compression is deterministic and local, so it adds no model cost.

Why no Celery or pgvector yet: a local repo indexes in well under a second, and
a local stdio server needs no deployment. The FastAPI adapter and Dockerfile are
present for a hosted path. The engine functions are transport agnostic, so a
queue or a vector store is mechanical when a shared or remote service needs it.

Data flow per query: `task -> classify -> BM25 over file chunks -> boosts ->
top-k -> budget split -> compose -> tiktoken ceiling -> trace`.
Data flow per tool result: `text -> detect kind -> keep errors, paths, counts ->
pack to budget -> store original -> ref -> event log`.
