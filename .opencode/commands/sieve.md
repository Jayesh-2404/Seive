---
description: Use Sieve to compress repository context for a task
---
Use the Sieve MCP tools for this task.

1. Call the Sieve index tool once for this project.
2. Call the Sieve query tool with this task: $ARGUMENTS
3. Read only the files it returns. Use the Sieve read tool for one file or one symbol. Use the Sieve compress tool for logs, test output, JSON or CSV.
4. Answer or implement the task from that context.

For a single step, use `/sieve/index`, `/sieve/query`, `/sieve/read`, `/sieve/compress`, `/sieve/stats`, `/sieve/symbol` or `/sieve/original`.

If the Sieve tools are not available, say so and stop. Do not read the whole repository instead.
