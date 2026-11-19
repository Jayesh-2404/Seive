# Real agent A/B: full context vs Sieve

This is the demo that answers "does it actually work in an agent". Two
OpenCode sessions get the same question and the same model. The first gets the
whole repository. The second gets the Sieve prompt. Nothing else differs.

## Setup

Repository: `https://github.com/Jayesh-2404/agent-activity-dashboard` at commit
`618610d954e27a203fa19241830ab3caa90eb85f`.
42 source files, 50,858 indexed tokens. Next.js and TypeScript.

Question, given verbatim to both arms:

> How does GitHub dashboard data become work items in the queue?

Model: `opencode-go/kimi-k2.7-code`. Agent: `context-only`, every tool denied,
one model step. Context attached with `--file context.md`, so neither arm can
read the repository on its own. The context text is the only variable.

## Context sizes

| Arm | Context | Tokens |
|---|---|---|
| A | whole repository dump | 51,194 |
| B | Sieve prompt, budget 8,000 | 5,642 |

Sieve used 5,666 tokens in total, 89.0 percent less than the full dump. It
retrieved 5 of the 6 gold files in the top 8, and the sixth entered through the
symbol layer.

## Session tokens, read from the OpenCode database

| Arm | input | output | reasoning | input reduction |
|---|---|---|---|---|
| A | 52,507 | 602 | 100 | baseline |
| B | 7,067 | 443 | 447 | 86.5 percent |

Both rows come from `session_v2` in `~/.local/share/opencode/opencode.db`. Cost
is 0.0 for both because `opencode-go` is subscription quota, so report tokens
and quota, not dollars.

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
Neither hallucinated a file.

Full answers: `AB_ANSWER_run-a.md` and `AB_ANSWER_run-b.md`.
They are verbatim model text pulled from the session database. Arm A opens with
the CLI step-cap notice, which is a harness artifact. Arm B has one mangled dash
where the provider stream lost a byte. Nothing else is edited.

## Reproduce

```sh
python tools/ab_build.py <repo> <out_dir> 8000

opencode run --agent context-only --model opencode-go/kimi-k2.7-code \
  --format json --archived --session ses-sieve-demo-a \
  --file context.md "How does GitHub dashboard data become work items in the queue?"

opencode run --agent context-only --model opencode-go/kimi-k2.7-code \
  --format json --archived --session ses-sieve-demo-b \
  --file context.md "How does GitHub dashboard data become work items in the queue?"
```

Then read the rows:

```sql
select id, tokens_input, tokens_output, tokens_reasoning, tokens_cache_write, cost
from session_v2 where id like 'ses-sieve-demo-%';
```

`tools/ab_build.py` writes both context files and a `manifest.json` with the
token counts, the picked files and the gold recall. It asserts that the Sieve
context is under budget and smaller than the full dump.

## Limits

One run per arm, so this is a pilot, not a significance test. One model, one
repository, one question. Temperature is not pinned because V2 does not send
agent request overlays. The OpenCode system prompt is a constant in both arms
and is included in the input numbers. `tokens_cache_write` is reported raw
because the provider caches the prompt and the accounting differs by model.
Answer quality is judged by us, with the key above written down first.

## MCP check

The same request through the stdio server, on the same repo:

```sh
printf '%s\n' \
  '{"id":1,"method":"index","params":{"repo":"<repo>"}}' \
  '{"id":2,"method":"query","params":{"q":"How does GitHub dashboard data become work items in the queue?","budget":8000}}' \
  | python -m sieve.mcp_server
```

It returns 42 files, 268 symbols, 566 edges, and a query result with
`symbols=1167`, `semantic=4082`, `summary=376`, `total=5666`. The prompt is
returned in full, not truncated.

## What to say in the demo

Sieve is not a better model. It is a filter. The agent solved the same task
with the same answer quality using 13.5 percent of the input tokens. The trace
shows exactly which files it kept and why, and the one file it missed entered
through the symbol layer instead of the code layer.
