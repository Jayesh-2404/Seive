# Install

One command installs the global MCP server and the `/sieve` commands.

```sh
pip install -e .
sieve init
```

`sieve init` does two things.

1. Adds a `sieve` local server to `~/.config/opencode/opencode.json` with the
   command `sieve-mcp`. It preserves every other server.
2. Copies the `/sieve` command templates to
   `~/.config/opencode/commands/sieve.md` and
   `~/.config/opencode/commands/sieve/`.

Useful flags:

- `sieve init --dry-run` prints the paths and changes nothing.
- `sieve init --force` replaces an existing `sieve` server entry.

On this machine the dry run reported:

```json
{
  "config": "C:\\Users\\DELL-1\\.config\\opencode\\opencode.json",
  "server_added": false,
  "commands": [
    "C:\\Users\\DELL-1\\.config\\opencode\\commands\\sieve.md",
    "C:\\Users\\DELL-1\\.config\\opencode\\commands\\sieve\\compress.md",
    "..."
  ]
}
```

`server_added` is false because the server is already present.

## Requirements

- `sieve-mcp` must be on `PATH`. An editable install creates it.
- OpenCode must be restarted or reloaded after the config changes. Command files
  reload on their own.
- If the global config is not valid JSON, `sieve init` stops instead of
  overwriting it.

## Verify

```sh
sieve init --dry-run
opencode mcp list
```

`opencode mcp list` should show `sieve connected` after the server starts. The
first connection can take a few seconds while the package imports.
