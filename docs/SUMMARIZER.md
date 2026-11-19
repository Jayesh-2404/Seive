# Summary layer

The summary layer has two paths. The default is extractive and free. The second
uses an external model if you provide one.

## Default: extractive

`composer.summarize_file` writes one line per file:

```text
auth.py: defines hash_pw, check_auth, Session (131 toks) | calls -
```

This is what every measured result uses. It calls no model and costs nothing.

## Optional: external model

Set `SIEVE_SUMMARY_CMD` to a command that reads a prompt on stdin and writes
text on stdout. Example with a local Ollama model:

```powershell
$env:SIEVE_SUMMARY_CMD = "ollama run qwen2.5-coder"
sieve summarize auth.py --repo sample_repo_large --json
```

The prompt asks for a short summary, keeps every identifier, and asks for
backticks around names. The response is accepted only when every backticked
identifier exists in the source or the symbol list. A rejected summary falls
back to the extractive line. Results are cached by file and content hash.

## Interfaces

- CLI: `sieve summarize <file> --repo <repo> --max-tokens 120 --json`.
- MCP: `sieve_summarize(file, max_tokens=120)`.
- OpenCode: `/sieve/summarize <file> [max_tokens]`.

## Limits

No live model was run in this environment, because no provider command was
configured. The validation, fallback, cache and interfaces are tested with a
fake provider. The LLM summary quality and cost are unmeasured, and the
extractive line remains the default.

The next step is to run the layer on a pinned model at temperature 0 and report
identifier retention and cost per file.
