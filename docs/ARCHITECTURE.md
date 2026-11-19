# Architecture (v0.5 - what runs)

```
[Agent] --MCP stdio--> [server/mcp: index / query / symbol]
                              |
[CLI]   --direct----> [index -> retrieval -> allocator -> composer]
                              |
                   [discover]
                     walk, skip rules, binary and size guards
                              |
                   [parse]
                     python_ast  |  treesitter  |  regex_fallback
                              |
                   [retrieval]
                     bm25 (k1=1.2, b=0.75) + symbol/import/graph boosts
                              |
                   [allocator]
                     classify -> split / bypass
                              |
                   [composer]
                     symbols + top-k + summaries + memory -> prompt <= budget
                              |
                   [trace]
                     results_eval.csv + traces_eval/*.json
```

The engine is transport independent. The A/B demo calls `compose` and attaches
the result as a file. The product path calls the same functions through
`server/mcp.py`, which OpenCode starts as a local stdio subprocess in the
project directory.

Store: files on disk plus an in-memory index. No database. SQLite or pgvector
is gated on a repo large enough to need it.

Memory: `memory/turns.jsonl` plus `memory/notes.md`. Notes hold rules that
survive compaction.

LLM: not called inside Sieve. The prompt is the deliverable. The agent consumes
it.

Why no FastAPI, Celery or Docker yet: a local repo indexes in well under a
second, and a local stdio server needs no deployment. The engine functions are
transport agnostic, so an HTTP adapter is mechanical when a shared or remote
service is needed.

Data flow per query: `task -> classify -> BM25 over file chunks -> boosts ->
top-k -> budget split -> compose -> tiktoken ceiling -> trace`.
