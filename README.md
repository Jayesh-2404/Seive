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

1. Index: AST parse for Python and tree-sitter grammars for TS, JS, C, C++,
   Go, Java and Rust. Extracts functions, classes, imports and caller-callee
   edges. Regex is the fallback for grammars that are not installed.
2. Retrieve: BM25 (k1=1.2, b=0.75) + exact symbol bonus + import bonus +
   1-hop call-graph boost. Returns top-5 files.
3. Allocate: keyword task classifier (bug_fix, feature, perf, question) +
   per-task token split + bypass rule (if repo fits budget, return full dump).
4. Compose: symbols + top-k code + extractive summaries of rest + memory.
   Enforces ceiling. Truncates summaries first, never symbols first.
5. Log: JSON trace per run (query, task type, files, scores, tokens per layer,
   latency, prompt hash) + CSV summary.

No ML training, no GPU, no network in v0.5. Embeddings and the LLM summarizer
are Milestone-2 and plug into the same interfaces.

## Repository Layout
```
pyproject.toml            package metadata, deps, `sieve` and `sieve-mcp` scripts
sieve/
  config.py               budgets, size caps, skip lists
  models.py               typed records shared by index, composer and server
  discover.py             file discovery, binary and size guards, skip reasons
  index.py                builds RepositoryIndex, call graph, def_index
  tokenizer.py            tiktoken cl100k_base with char/4 fallback
  allocator.py            task classify + budget split + bypass rule
  composer.py             prompt under hard ceiling, extractive summaries
  memory.py               turns.jsonl + notes.md
  compress.py             budgeted compression for logs, tests, JSON, CSV
  read.py                 symbol-aware file reads
  summarize.py            extractive default, optional external model, identifier check
  store.py                original text store and tool event log
  install.py              writes the global MCP server and /sieve commands
  templates/commands/     command templates copied by `sieve init`
  cli.py                  sieve index / query / read / compress / original / stats / memory / summarize / mcp / init
  parse/
    profiles.py           extension to language mapping
    python_ast.py         Python AST symbols, imports, calls
    treesitter.py         tree-sitter symbols for TS, JS, C, C++, Go, Java, Rust
    regex_fallback.py     coarse fallback for grammars that are not installed
  retrieval/
    bm25.py               BM25 from scratch
    hybrid.py             symbol, import, call-graph and dense boosts
  embeddings.py           local dense index with fastembed
  allocator_learned.json  trace-fitted splits (opt-in)
  server/
    mcp.py                MCP server: index, query, read, compress, original, symbol, stats, memory
  http_server.py          FastAPI adapter over the same engine
Dockerfile                HTTP service image
.github/workflows/ci.yml  lint, tests, eval, HTTP import
tools/
  build_large_repo.py     generates the 18-file demo repo with 3 known bugs
  ab_build.py             builds the full-context and Sieve-context A/B arms
  fit_allocator.py        grid-searches splits and writes allocator_learned.json
  real_bench_build.py     builds the six-task real benchmark contexts
  real_bench_run.py       runs and scores the six-task benchmark
tests/
  test_sieve.py           ceiling, bypass and Python indexing
  test_languages.py       six languages, discovery rules, MCP tool registration
run_eval.py               12 tasks x 5 systems, writes results_eval.csv + traces_eval/
sample_repo_large/        generated demo repo (18 files, ~1127 tokens)
results_eval.csv          eval output, budget=600
traces_eval/              one JSON per task-system pair
docs/
  SUBMISSION_30PCT.md     one-page 30 percent summary
  ARCHITECTURE.md         system diagram and store decisions
  EVALUATION.md           metrics, ablations, threats
  DEMO_AB.md              OpenCode A/B and MCP demo with real token counts
  DEMO_GUIDE.md           five minute demo script
experiments/
  experiment_plan.md      E01-E05 hypothesis template
```

## Requirements
Python 3.11+. Install with `pip install -e .`. Dependencies are `tiktoken`,
`tree-sitter`, `tree-sitter-language-pack`, the `mcp` SDK, `fastapi`,
`uvicorn`, `fastembed` and `numpy`. The token count falls back to char/4 if
`tiktoken` cannot load, and every trace records which backend was used. No API
key is needed for the retrieval eval. The OpenCode A/B needs an OpenCode
provider login.

## How to Run
Install the CLI, the global MCP server and the `/sieve` commands:
```
pip install -e .
sieve init
```
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
repo files=18 total_tokens=1127 symbols=37 edges=12
tokenizer=tiktoken/cl100k_base
system          avg_tok  avg_recall  saving_vs_full
full               1127     1.00        --
trunc               600     0.00        +46.8 percent, destroys info
sieve               548     0.83        +51.4 percent, keeps gold files
```

Outputs: `results_eval.csv`, `traces_eval/<task>-<system>.json`.
Inspect one trace:
```
traces_eval/B1-sieve.json
```
Fields: task, query, system, tokens per layer, files picked, gold files,
recall, prompt hash, latency.

MCP check. Install the package, then configure the server in the project:
```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "servers": {
      "sieve": {
        "type": "local",
        "command": ["python", "-m", "sieve.mcp_server"],
        "cwd": "."
      }
    }
  }
}
```
`opencode mcp list` then shows `✓ sieve connected`. OpenCode exposes
`sieve_index`, `sieve_query`, `sieve_read`, `sieve_compress`, `sieve_original`,
`sieve_symbol`, `sieve_stats`, `sieve_memory` and `sieve_summarize`. With
`codemode: false` the tools appear with those names. Under the default Code Mode
they are grouped as `tools.sieve.index` and so on. The server is also available
as `sieve-mcp` or `python -m sieve.mcp_server` for any other MCP client.

`sieve init` writes this config and the commands for you. See `docs/INSTALL.md`.

A `/sieve` command is included. Run `/sieve <task>` in OpenCode. It expands to
the index, query, read and compress workflow above. The project copy is
`.opencode/commands/sieve.md`; the global copy is
`~/.config/opencode/commands/sieve.md`. The command name is `sieve`, not `seive`.

## HTTP service
`sieve-serve` starts FastAPI on `127.0.0.1:8000`, or run
`python -m uvicorn sieve.http_server:app --port 8000`. Endpoints are `/health`,
`/index`, `/query`, `/read`, `/compress`, `/stats` and `/original/{ref}`. A live
check returned 18 files for the demo repo and a 538 token query under the 600
budget. The Dockerfile builds the same service. Docker is not installed on the
development machine, so the image was not built there.

The single-step commands are below. They live under
`.opencode/commands/sieve/` and are installed globally too.

| Command | Use |
|---|---|
| `/sieve <task>` | full workflow |
| `/sieve/index` | index the project and report counts |
| `/sieve/query <task>` | prompt, files and layer counts only |
| `/sieve/read <file> [symbol]` | one file or one symbol |
| `/sieve/compress <text>` | compress noisy output |
| `/sieve/stats` | token savings |
| `/sieve/memory [note]` | show or record conversation memory |
| `/sieve/summarize <file> [max]` | summarize one file |
| `/sieve/symbol <name>` | find a definition |
| `/sieve/original <ref> [start] [end]` | recover an original |

## Measured Results (budget=600, 12 tasks, deterministic)
| system | avg tokens | Recall@5 | note |
|---|---|---|---|
| full | 1127 | 1.00 | upper bound, over budget |
| trunc | 600 | 0.00 | naive cut loses file boundaries |
| sieve | 548 | 0.83 | BM25 + symbols + graph |
| sieve-nosym | 548 | 0.83 | symbols redundant on this repo |
| sieve-nograph | 541 | 0.83 | no measurable graph lift here |
| sieve-vec | 553 | 0.83 | local dense boost, no gain here |

The earlier `tfidf` row is gone. The harness had routed it to the same code
path as `sieve`, so it measured nothing.

## Real agent A/B (OpenCode, one run per arm)
Same question, same model, no tools, only the attached context differs. Repo is
`agent-activity-dashboard` at commit `618610d`, 42 source files.

| arm | context tokens | input tokens | output | answer key |
|---|---|---|---|---|
| full repo | 49,412 | 52,508 | 460 | 6 / 6 |
| Sieve, budget 8000 | 5,516 | 6,926 | 653 | 6 / 6 |

That is 86.8 percent fewer input tokens at the same answer quality. Numbers come
from the OpenCode session database. Details and limits: `docs/DEMO_AB.md`.
A six-task benchmark on the same repository scored 6 of 6 in both arms. Full
context averaged 52,530 input tokens and Sieve averaged 6,869, which is 86.9
percent fewer. Details: `docs/REAL_BENCH.md`.

The same repo was also driven through the MCP server, where the agent had no
filesystem access: one `sieve_index` call, one `sieve_read` call and one
`sieve_compress` call produced the same correct chain.

## Read less (input compression)
The repository context is not the only input. Tool output is often larger.
These are measured calls, not estimates.

| Input | Before | After | Saved |
|---|---|---|---|
| `activity-model.ts`, symbol `buildWorkItems` | 1,235 | 313 | 74.7% |
| noisy log, budget 120 | 571 | 120 | 79.0% |
| 2,000 line log, budget 300 | 37,016 | 296 | 99.2% |

`sieve_read` returns the file map and the requested symbol. `sieve_compress`
keeps errors, paths and numbers, and drops repeated or passing lines. Every
original goes to `~/.sieve/originals` and comes back with `sieve_original`.
`sieve stats` reports the running total. The 2,000 line log is a synthetic
fixture, so treat that row as a compression check, not a real repository result.

## Semantic layer and allocator
Local dense retrieval is available with `--vectors` or `vectors=true`. It uses
`fastembed` and `BAAI/bge-small-en-v1.5` on CPU, at 384 dimensions. On the 12
lexical tasks it did not improve recall. It used 553 tokens at 0.83 recall and
38.6 ms, against 548 tokens, 0.83 and 11.8 ms for BM25. That is a negative
result, kept in `docs/EMBEDDINGS.md`.

A trace-fitted split table is available with `--learned` or `learned=true`. It
is an in-sample grid search on the 12 tasks, not a trained model. The details
and the weak evidence are in `docs/ALLOCATOR.md`. The default remains the rule
split, so the measured A/B and eval do not move.

The summary layer is extractive by default. Set `SIEVE_SUMMARY_CMD` to a command
that reads a prompt and writes text to enable an external model. Backticked
identifiers are checked against the source and symbol list, and a failed check
falls back to the extractive line. No live model was run here, so LLM summary
quality is unmeasured. See `docs/SUMMARIZER.md`.

Bug presence in `sample_repo_large/tests_core.py`: t_b1, t_b2, t_b3 all False
(bugs reproduce, honest baseline). End-to-end LLM fix rate is marked as
experiment to be conducted, harness hook already in `run_eval.py`.

## Maths Used (plain explanation)

### Tokens and budget
A token is the unit the LLM bills. With `tiktoken cl100k_base`
(`sieve/tokenizer.py:7-19`), 1 token is about 4 characters.
Example: `def login(user):` (18 chars) counts as 4-5 tokens.
Demo repo totals 1127 tokens. Budget 600 forces filtering.
Saving formula:
```
saving_pct = 100 * (1 - sieve_tokens / full_tokens)
```
Example: `100 * (1 - 548 / 1127) = 51.4 percent`.
Naive trunc also saves `100 * (1 - 600 / 1127) = 46.8 percent`
but cuts mid-file so the saving is useless.

### BM25 scoring (`sieve/retrieval.py:20-75`)
For each query word t and file d, with k1 = 1.2, b = 0.75:
```
IDF(t) = log(1 + (N - df + 0.5) / (df + 0.5))
TF_part = tf * (k1 + 1) / (tf + k1 * (1 - b + b * dl / avgdl))
BM25(d, q) = sum over query words of IDF * TF_part
```
N = file count, df = files containing t, tf = count in this file,
dl = file length, avgdl = mean length.
Example with N = 18, word `auth` in df = 2 files:
```
IDF = log(1 + 16.5 / 2.5) = log(7.6) ~ 2.03
```
A file mentioning it 3 times at average length scores
`3 * 2.2 / (3 + 1.2) ~ 1.57`, contribution `2.03 * 1.57 ~ 3.19`.
Repeating 10 times does not give 3x. That cap is saturation (k1).
The b term stops long files winning by length alone.

### Hybrid boosts
```
final_score = BM25 + 5.0 exact-symbol + 2.0 symbol-part + 2.0 import + 1.5 call-graph
```
Plus 5 when the query word equals a defined def or class name in that file.
Plus 2 when the query shares a word with a symbol name, so `work` matches
`buildWorkItems`. Snake_case and camelCase are split before scoring. Plus 2
when it equals an import. Plus 1.5 for 1-hop callees: if a top-3
file calls f, files defining f get boosted. BM25 here scores roughly 0-10,
so plus 5 dominates without fully overriding text evidence.

### Recall@k
```
Recall@k = len(gold intersect retrieved) / len(gold)
```
Gold is files the task needs, retrieved is top-5 sent.
Example: gold 3 files, retrieved 2 of them gives 2 / 3 ~ 0.67.
Trunc scores 0.0 because it cuts the concatenated blob and later files
never appear. Sieve keeps whole files, hence 0.83 on the demo set.

### Budget split (`sieve/allocator.py:24-40`, `sieve/composer.py:16-55`)
Example question split on budget 600: symbols 90 + semantic 360 +
summary 90 + memory 60. Symbols are cut last. Over ceiling, memory drops
first, then summaries, then the tail of retrieved files, then symbols.
The ceiling is hard and covered by tests. If repo fits in budget times 0.9,
bypass returns the full dump.

### Latency
Wall time around retrieve plus compose, in milliseconds. Local retrieval
is single-digit ms. LLM calls are seconds plus per-token cost. Spending
ms locally to halve input tokens is the full trade.

## What Each File Does
- `sieve/config.py`: budgets, size caps and skip rules.
- `sieve/models.py`: typed records shared by every stage.
- `sieve/discover.py`: file discovery, binary detection, skip reasons.
- `sieve/index.py`: builds the repository index, call graph and definition map.
- `sieve/parse/`: Python AST, tree-sitter for seven more languages, regex fallback.
- `sieve/retrieval/`: BM25 math and the structure boosts.
- `sieve/allocator.py`: task routing and budget split.
- `sieve/composer.py`: prompt assembly with hard ceiling enforcement.
- `sieve/compress.py`: budgeted compression for noisy tool output.
- `sieve/read.py`: symbol-aware file reads.
- `sieve/summarize.py`: extractive default, optional external model, identifier check.
- `sieve/store.py`: originals and the token event log.
- `sieve/memory.py`: conversation store and simple compaction.
- `sieve/install.py`: writes the global MCP server and the `/sieve` commands.
- `sieve/server/mcp.py`: MCP server with `index`, `query`, `read`, `compress`, `original`, `symbol`, `stats`, `memory`, `summarize`.
- `sieve/cli.py`: the same operations from a terminal.
- `run_eval.py`: baselines, ablations, metrics, traces.

## Limitations
- Summaries are extractive one-liners, no LLM compression yet.
- Allocator is rule-based, learned version needs 500+ logged runs.
- Tree-sitter grammars come from the language pack. Unknown languages fall back to regex or plain text, so their symbols are coarser.
- Call edges are extracted for Python only. Other languages get symbols and imports but no graph boost.
- Dense retrieval is local and in-memory, with no pgvector. It did not improve the 12-task lexical set.
- The learned allocator is an in-sample split table, not a trained model.
- Single Python repo, 12 tasks, gold labels by authors, plus one TypeScript demo question.
- No vector DB in v0.5. The HTTP adapter and Dockerfile are present.
- Tokenizer fallback char/4 is recorded in every trace when tiktoken cannot load.
- Docker is not installed on the development machine, so the image is not built there. CI is written but not run against a remote.

## Next Milestones
1. LLM summarizer with identifier-preservation check. The interface, identifier
   check and external-provider hook are in place; a live run and a cost table remain.
2. LLM fix-rate eval with pinned model, temp=0, cost tracking.
3. Learned allocator trained on collected logs, leave-one-repo-out test. The in-sample split table is in place.
4. pgvector + RRF fusion, ablated against BM25. The local dense index and its negative result are in place.
5. FastAPI HTTP and Docker. The adapter, Dockerfile and CI workflow are in place. A Docker build and a GitHub CI run remain to be executed.
6. Automatic OpenCode plugin for tool-output compression.

The full gap analysis is in `docs/REMAINING.md`.

## Status
v0.5 vertical slice. See docs/ for architecture, evaluation, and demo guide.
