# MCP session: the product path

This is the door, not the engine. The engine was measured in `DEMO_AB.md`.
Here a real OpenCode agent used the MCP server with no filesystem access.

## Tools

OpenCode prefixes the server name, so the exposed names are below.

| Tool | Arguments | Returns | Use it when |
|---|---|---|---|
| `sieve_index` | `repo="."`, `refresh=false` | files, symbols, edges, total_tokens, skipped | once per project, or after large changes |
| `sieve_query` | `task`, `budget=8000`, `top_k=8` | prompt, layers, alloc, files | before reading files |
| `sieve_read` | `file`, `symbol=""`, `budget=1200` | file map plus the requested symbol code | before opening a file |
| `sieve_compress` | `text`, `kind="auto"`, `budget=800` | compressed text, before and after tokens, ref | for logs, tests, JSON, CSV |
| `sieve_original` | `ref`, `start_line`, `end_line` | the original text or a line range | when the compressed text is not enough |
| `sieve_symbol` | `name` | symbol definitions | when the name is already known |
| `sieve_stats` | none | token savings recorded for read, compress and query | for the demo |

Compression is lossy. The original always goes to `~/.sieve/originals` and
comes back by `ref`. Set `SIEVE_CACHE_DIR` to move it.

## Config

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "servers": {
      "sieve": {
        "type": "local",
        "command": ["python", "-m", "sieve.mcp_server"],
        "cwd": ".",
        "codemode": false
      }
    }
  }
}
```

`opencode mcp list` reported:

```
✓ browse  connected
✓ mobbin  connected
✓ sieve   connected
```

The server log confirms `server=sieve tools=7`.

## Agent

Agent `sieve-only`. It allows every tool, then denies `read`, `glob`, `grep`,
`shell`, `edit`, `webfetch`, `websearch`, `skill` and `subagent`. Denying those
actions is better than a broad `*` deny, because a broad deny can hide the MCP
tools too. The first standalone run failed for that reason. The second run
worked.

## Session

Session `ses-sieve-mcp3`, model `opencode-go/kimi-k2.7-code`, private server
started with `--standalone`.

| Step | Call | Result |
|---|---|---|
| 1 | `sieve_index` | 42 files, 271 symbols, 49,075 tokens |
| 2 | `sieve_read` on `src/lib/activity-model.ts`, symbol `buildWorkItems` | 1,235 to 313 tokens, 74.7 percent saved |
| 3 | `sieve_compress` on the log, budget 120 | 571 to 120 tokens, 79.0 percent saved |
| 4 | answer | names the `RepositoryResult` to `WorkItem` flow and the error line |

Session tokens: input 1,042, output 102, reasoning 1,096, cache read 7,424.
These totals cover several steps, including tool discovery. Do not compare them
with a one-shot context arm.

## Command

The repo includes `.opencode/commands/sieve.md`, and the global copy lives at
`~/.config/opencode/commands/sieve.md`. Run:

```text
/sieve How does GitHub dashboard data become work items in the queue?
```

The command expands to the index, query, read and compress workflow. The name is
`sieve`, not `seive`. If the command list does not show it, type `/sie` and it
appears after the file is reloaded.

The single-step commands are in `.opencode/commands/sieve/` and are installed
globally too.

| Command | Arguments | Use |
|---|---|---|
| `/sieve` | task | full workflow |
| `/sieve/index` | none | index and report counts |
| `/sieve/query` | task | prompt, files and layer counts only |
| `/sieve/read` | file, optional symbol | one file or one symbol |
| `/sieve/compress` | text | compress noisy output |
| `/sieve/stats` | none | token savings |
| `/sieve/symbol` | name | find a definition |
| `/sieve/original` | ref, optional start and end | recover an original |

## Reproduce

```sh
opencode run --standalone --agent sieve-only \
  --model opencode-go/kimi-k2.7-code \
  --format json --archived --session ses-sieve-mcp3 \
  "Use the Sieve tools only: call sieve_index, then sieve_read on
   src/lib/activity-model.ts for buildWorkItems, then sieve_compress on the log.
   Then answer."
```

The full answer is `AB_ANSWER_mcp.md`. The raw session is in the OpenCode
database, session `ses-sieve-mcp3`.
