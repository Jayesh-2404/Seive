# Real agent A/B: full context vs Sieve

This is the demo that answers "does it actually work in an agent". Two
OpenCode sessions get the same question and the same model. The first gets the
whole repository. The second gets the Sieve prompt. Nothing else differs.

## Setup

Repository: `https://github.com/Jayesh-2404/agent-activity-dashboard` at commit
`618610d954e27a203fa19241830ab3caa90eb85f`.
42 source files, 49,075 indexed tokens. Next.js and TypeScript.

Question, given verbatim to both arms:

> How does GitHub dashboard data become work items in the queue?

Model: `opencode-go/kimi-k2.7-code`. Agent: `context-only`, every tool denied,
one model step. Context attached with `--file context.md`, so neither arm can
read the repository on its own. The context text is the only variable.
Tokenizer: `tiktoken/cl100k_base`, recorded in `AB_MANIFEST.json`.

## Context sizes

| Arm | Context | Tokens |
|---|---|---|
| A | whole repository dump | 49,412 |
| B | Sieve prompt, budget 8,000 | 5,516 |

Sieve used 5,540 tokens in total, 88.8 percent less than the full dump. It
retrieved 5 of the 6 gold files in the top 8, and the sixth entered through the
symbol layer. Layers were symbols 1,091, semantic 4,107, summary 291, memory 0.

## Session tokens, read from the OpenCode database

| Arm | input | output | reasoning | input reduction |
|---|---|---|---|---|
| A | 52,508 | 460 | 666 | baseline |
| B | 6,926 | 653 | 583 | 86.8 percent |

Both rows come from `session_v2` in `~/.local/share/opencode/opencode.db`. Cost
is 0.0 for both because `opencode-go` is subscription quota, so report tokens
and quota, not dollars. Arm B used 13.2 percent of Arm A's input tokens.

## Answer quality

A six element answer key, applied to both outputs after generation by the same
reviewer. Both arms scored 6 of 6.

1. Names `src/app/api/github/dashboard/route.ts` as the data entry point.
2. Names `use-activity.ts` as the client fetch hook.
3. Names `buildWorkItems` in `activity-model.ts` as the builder.
4. Names `inferAttention` for attention state.
5. Names `partitionWorkItems` and `queue-view.tsx` for rendering.
6. Names `page.tsx` as the wiring point.

Arm A is more detailed. Arm B is shorter and states what its context cut off.
Neither hallucinated a file. Arm B says the exact fetch call inside
`use-activity.ts` was truncated, which is true.

Full answers: `AB_ANSWER_run-a.md` and `AB_ANSWER_run-b.md`. They are verbatim
model text pulled from the session database. Arm A opens with the CLI step-cap
notice, which is a harness artifact.

## Reproduce

```sh
python tools/ab_build.py <repo> <out_dir> 8000

opencode run --agent context-only --model opencode-go/kimi-k2.7-code \
  --format json --archived --session ses-sieve-ab-a \
  --file context.md "How does GitHub dashboard data become work items in the queue?"

opencode run --agent context-only --model opencode-go/kimi-k2.7-code \
  --format json --archived --session ses-sieve-ab-b \
  --file context.md "How does GitHub dashboard data become work items in the queue?"
```

Then read the rows:

```sql
select id, tokens_input, tokens_output, tokens_reasoning, tokens_cache_write, cost
from session_v2 where id like 'ses-sieve-%';
```

`tools/ab_build.py` writes both context files and a `manifest.json` with the
token counts, the picked files, the gold recall and the tokenizer backend. It
asserts that the Sieve context is under budget and smaller than the full dump.

## Limits

One run per arm, so this is a pilot, not a significance test. One model, one
repository, one question. Temperature is not pinned because V2 does not send
agent request overlays. The OpenCode system prompt is a constant in both arms
and is included in the input numbers. `tokens_cache_write` is reported raw
because the provider caches the prompt and the accounting differs by model.
Answer quality is judged by us, with the key above written down first.

## Product path: through MCP

The A/B above attached the prompt as a file. It measured the engine, not the
door. The door was tested separately, in the same repository.

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

`opencode mcp list` reported `✓ sieve connected`. A normal agent with every
filesystem tool denied called:

1. `sieve_index` once, which returned 42 files, 271 symbols, 0 edges, 49,075 tokens.
2. `sieve_query` with the original task.
3. `sieve_query` again for the `buildWorkItems` function.
4. `sieve_query` again for the fetch call in `use-activity.ts`.

The answer named the same chain as both A/B arms. The session used 23,442 input
tokens, 25,600 cache read, 520 output and 970 reasoning. Those totals cover four
model steps, so do not compare them with a one-shot arm. The point of this run
is that the door works: the model had no filesystem access and still answered
from Sieve.

## What to say in the demo

Sieve is not a better model. It is a filter. The agent solved the same task
with the same answer quality using 13.2 percent of the input tokens. The trace
shows exactly which files it kept and why, and the one file it missed entered
through the symbol layer instead of the code layer. The MCP run shows the same
engine behind a real agent, with no filesystem access.
