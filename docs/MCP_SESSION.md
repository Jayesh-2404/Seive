# MCP session: the product path

This is the door, not the engine. The engine was measured in `DEMO_AB.md`.
Here a real OpenCode agent used the MCP server with no filesystem access.

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

OpenCode exposes `sieve_index`, `sieve_query` and `sieve_symbol`.

## Agent

Agent `sieve-only`, every filesystem tool denied. The only allowed actions were
`sieve_index`, `sieve_query` and `sieve_symbol`. Model
`opencode-go/kimi-k2.7-code`.

## Calls

| step | tool | input |
|---|---|---|
| 1 | `sieve_index` | default repo `.` |
| 2 | `sieve_query` | `How does GitHub dashboard data become work items in the queue?` |
| 3 | `sieve_query` | `Show the full buildWorkItems function and how RepositoryResult is produced from the GitHub dashboard API` |
| 4 | `sieve_query` | `Where in use-activity.ts does it fetch /api/github/dashboard and produce RepositoryResult[]?` |

The index call returned 42 files, 271 symbols, 0 edges, 49,075 tokens, and one
skipped lockfile.

## Session tokens

Read from `session_v2` for `ses-sieve-mcp`.

| input | output | reasoning | cache read | cost |
|---|---|---|---|---|
| 23,442 | 520 | 970 | 25,600 | 0.0 |

These totals cover four model steps. They are not comparable to a one-shot
context arm, because every step resends the conversation. The point is that the
agent answered with no filesystem access.

## Answer

The full answer is `AB_ANSWER_mcp.md`. It names the same chain as both A/B arms:
the dashboard route, `useActivity`, `buildWorkItems`, `inferAttention`,
`partitionWorkItems`, `queue-view.tsx` and `page.tsx`.
