# Architecture (v0.4 — what runs)

```
[Agent/CLI] --stdio--> [sieve.mcp_server: index/query/get_symbol]
                            |
                [indexer: py ast + js/ts regex -> symbols/chunks/edges/def_index]
                            |
                [retrieval: BM25 + symbol/part/import + 1-hop graph -> top-k]
                            |
                [allocator: classify -> split/bypass]
                            |
                [composer: symbols + top-k + summaries + memory -> prompt<=budget]
                            |
                     [traces_eval/*.json + results_eval.csv]
```

A/B demo path: `tools/ab_build.py` writes a full-dump context and a Sieve
context, then two OpenCode sessions attach one each. Session tokens are read
from `session_v2` in the OpenCode database. See `docs/DEMO_AB.md`.

Store: files on disk + in-memory index (no DB yet; SQLite/pgvector gated on >50k chunks).
Memory: `memory/turns.jsonl` + `memory/notes.md` (persistent rules survive compaction).
LLM: not called in v0; prompt is the deliverable. LiteLLM hook reserved in composer output.

Why not FastAPI/Celery/pgvector now: 18 files index in <10ms; queue + server add failure modes with zero thesis gain. Interfaces (`index_repo/retrieve/allocate/compose`) are DB-agnostic so swap is mechanical later.

Data flow per query: `q -> classify -> BM25 over file chunks -> boost -> top-5 -> expand callees -> budget split -> compose -> count via tiktoken -> enforce ceiling -> log trace`.
