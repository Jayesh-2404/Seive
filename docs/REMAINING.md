# Remaining work

Status date: 2026-11-19. This is the gap between the synopsis and the code that
runs today. It is a planning document, not a claim.

## What is measured now

| Check | Result | Evidence |
|---|---|---|
| Tests | 38 pass | `python -m pytest -q` |
| Retrieval eval | full 1127 / 1.00, trunc 600 / 0.00, Sieve 548 / 0.83 | `python run_eval.py 600` |
| Real agent A/B | 52,508 vs 6,926 input tokens, 86.8% fewer, 6/6 both | `docs/DEMO_AB.md` |
| Six-task real benchmark | 6/6 both, 52,530 vs 6,869 avg input, 86.9% fewer | `docs/REAL_BENCH.md` |
| HTTP service | health, 18 files indexed, 538 token query under 600 | live uvicorn check |
| Dense ablation | 553 tokens / 0.83 / 38.6 ms vs 548 / 0.83 / 11.8 ms, no gain | `docs/EMBEDDINGS.md` |
| Allocator grid | semantic-heavy for 3 of 4 task types, in-sample | `docs/ALLOCATOR.md` |
| Input compression | 1,235 to 313, 571 to 120, 37,016 to 296 | `docs/MCP_SESSION.md`, `sieve stats` |
| MCP | 8 tools, 9 slash commands, live session | `ses-sieve-mcp3`, `opencode mcp list` |
| Languages | Python, TS, JS, C, C++, Go, Java, Rust | `tests/test_languages.py` |

What is not present in the code: no pgvector. A local dense index exists, but it
did not improve the 12-task set. The allocator is a rule plus an in-sample split
table, not a learned model. There is no LLM summarizer and no compaction of old
turns. The `Memory` class is wired into the MCP query and the `memory` tool.
Tree-sitter files return no call edges. Chunks are capped by characters, not
tokens. FastAPI, the Dockerfile and the CI workflow are present; the Docker build
and a remote CI run were not executed here.

## Synopsis objectives against the code

| # | Objective | State | Evidence | Remaining |
|---|---|---|---|---|
| 1 | Repository scanner and AST/symbol extractor with functions, classes, imports, call graphs | Partial | `sieve/discover.py`, `sieve/parse/`; Python AST with calls, tree-sitter for 8 languages with symbols and imports | call edges for non-Python; token-aware chunks |
| 2 | Token-aware chunker and embedding pipeline with vector search | Partial | `sieve/embeddings.py` with fastembed, 384 dims; `sieve-vec` ablation | pgvector, RRF, token windows, paraphrase test |
| 3 | Summarization layer that preserves identifiers | Partial | `composer.summarize_file` is an extractive one-liner | LLM summary, identifier check, cache by hash, cost |
| 4 | Budget allocator that predicts the best split and learns | Partial | `allocator.py` rule plus `allocator_learned.json` from a 12-task grid search | 500+ runs, a trained model, leave-one-repo-out |
| 5 | Conversation and trajectory memory for long sessions | Partial | `Memory` is wired into the MCP query and exposed as `sieve_memory`; `sieve/cli.py memory` reads it | compaction of old turns, decisions and failures in a measured multi-turn session |
| 6 | MCP service | Done | `sieve/server/mcp.py`, 8 tools, 9 commands, `ses-sieve-mcp3` | packaging and installer |
| 7 | Benchmark of token cost, latency and task success with vs without | Partial, improved | 12-task retrieval eval; 6-task real benchmark with 6/6 both and 86.9% fewer input tokens; one MCP session | harder task set with patches and tests, 3 reps, cost, multi-repo |

The synopsis also promises PostgreSQL/pgvector and an allocator that learns from
repeated runs. pgvector is not used, and the split table is in-sample. FastAPI,
the Dockerfile and the CI workflow now exist; the Docker build and a remote CI
run remain to be verified.

## P0: required before the thesis is proven

1. **Real task-success benchmark on a real repository.** Use a real Node,
   Express, Django or FastAPI repo. Label at least 20 tasks. Run with and
   without Sieve, 3 repetitions, pinned model and temperature. Record tokens,
   latency, cost and success. Acceptance: a committed CSV and trace per run,
   plus a table with success and token deltas. This is the biggest gap. Recall@5
   is a proxy, not task success.
   Progress: six tasks on the Next.js repo scored 6 of 6 in both arms, with
   52,530 versus 6,869 average input tokens. Remaining: 20+ tasks, 3 reps,
   patches and tests for real task success, and cost.
2. **Normal-agent A/B.** The current A/B uses a no-tools agent. Add a normal
   agent with file tools, with and without the Sieve MCP server, on the same
   tasks. Acceptance: a paired table of input tokens, tool calls and success.
3. **Learned allocator.** Collect the traces from P0. Train a small classifier
   or regression that predicts the split from task type, repo size and budget.
   Acceptance: leave-one-repo-out evaluation against the rule baseline. A
   documented negative result counts if the rule wins.
   Progress: a trace-fitted split table is available from a 12-task grid search.
   It is in-sample and not a trained model.

## P1: the layers the synopsis names

4. **Embeddings plus a vector store.** Chunk by tokens, embed chunks, store them
   in pgvector or a local vector index, and fuse with BM25. Acceptance: a
   paraphrase task set where BM25 misses and the hybrid finds the file, with
   measured recall and latency. Keep BM25 as the fallback.
   Progress: a local fastembed index and a `sieve-vec` ablation exist. It did
   not improve the 12-task lexical set. pgvector and a paraphrase set remain.
5. **LLM summarizer.** Replace the extractive one-liner for large and stale
   files. Check that every identifier in the summary exists in the file. Cache
   by file hash. Acceptance: an identifier-retention rate and a token and cost
   table.
6. **Conversation memory.** Wire `sieve/memory.py` into query and MCP. Store
   decisions, failures, files touched and the next step. Compact old turns into
   a short state block. Acceptance: a multi-turn session where the decisions
   survive compaction, with token savings measured.
   Progress: memory is wired into the MCP query and exposed as `sieve_memory`.
   Compaction of old turns is still missing.
7. **Token-aware chunks and non-Python call graphs.** Chunk by token windows.
   Extract calls for TS, JS, C, C++, Go, Java and Rust. Acceptance: a test per
   language and an ablation showing the graph boost.

## P2: service and delivery

8. **FastAPI, Docker and CI.** An HTTP adapter over the same engine, a
   Dockerfile, and a GitHub Actions workflow that runs tests and the eval.
   Acceptance: a green workflow and a container that answers `/query`.
   Progress: the adapter, Dockerfile and workflow exist. A live uvicorn check
   answered `/health`, `/index` and `/query`. Docker is not installed here, and
   the workflow has not run on GitHub.
9. **Automatic tool-output compression.** An OpenCode plugin hook for `read`,
   `grep` and `shell` results, so the agent does not call `sieve_compress` by
   hand. Acceptance: a session where tool results are compressed automatically,
   originals recoverable, and input tokens measured.
10. **Installer.** One command that installs the package, writes the global MCP
    server and installs the `/sieve` commands. Acceptance: a clean machine
    reaches `opencode mcp list` showing `sieve connected` without manual edits.
11. **Multi-repo benchmark.** At least two real repositories with per-language
    recall and success. Acceptance: a results table per repo, not a pooled mean.
12. **Security and privacy review.** A threat model for the original store and
    path handling, retention and cleanup for `~/.sieve`, and a check that
    secrets and ignored files never enter the index. Path traversal tests
    already exist.

## Definition of done for the full synopsis

- All seven objectives have a measured result.
- A real-repo benchmark reports success, tokens, latency and cost, with reps.
- One semantic retrieval path and one LLM summary path are ablated against the
  current baseline.
- Memory is demonstrated across a multi-turn compaction.
- The learned allocator is compared to the rule baseline.
- Docker builds and CI is green.
- The report states the threats and the negative results.

## What not to do

- Do not add pgvector before the task-success benchmark. It is plumbing without
  proof.
- Do not replace BM25 until an embedding ablation shows a gain.
- Do not use LangChain or LlamaIndex. They hide the pipeline you are defending.
- Do not present the one-question A/B as a success benchmark. It is a pilot.

## Effort

| Work | One person, focused |
|---|---|
| Real task benchmark | 2 to 4 days (extend the six-task set) |
| Learned allocator | 3 to 4 days |
| Normal-agent A/B | 1 to 2 days |
| Embeddings and vector store | 3 to 4 days |
| LLM summaries | 2 to 3 days |
| Memory and compaction | 2 to 3 days |
| Token chunks and call graphs | 3 to 4 days |
| FastAPI, Docker, CI | 0.5 day to verify (code is present) |
| Automatic compression plugin | 3 to 4 days |
| Installer | 1 to 2 days |
| Multi-repo benchmark | 3 to 5 days |

That is about four to five weeks for one person, or two to three weeks for two
people in parallel. The current code is a defensible 30 to 35 percent slice plus
an input-compression extension. The remaining work is the 70 percent.

## Reproduce the current evidence

```sh
python -m pytest -q
python run_eval.py 600
python tools/ab_build.py <repo> <out_dir> 8000
sieve stats
opencode mcp list
```
