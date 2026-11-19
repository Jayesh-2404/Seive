"""Install the OpenCode MCP server and the /sieve commands.

The installer merges one server entry into the global OpenCode config and copies
the command templates. It never replaces other servers.
"""
import json
import os
import shutil
from pathlib import Path

SCHEMA = "https://opencode.ai/config.json"
SERVER = {"type": "local", "command": ["sieve-mcp"]}
TEMPLATES = Path(__file__).with_name("templates") / "commands"


def _paths(config_path: str | None, commands_dir: str | None) -> tuple[Path, Path]:
    config = Path(config_path or os.getenv("OPENCODE_CONFIG")
                  or Path.home() / ".config/opencode/opencode.json")
    commands = Path(commands_dir or os.getenv("OPENCODE_COMMANDS")
                    or Path.home() / ".config/opencode/commands")
    return config, commands


def init(config_path: str | None = None, commands_dir: str | None = None,
         dry_run: bool = False, force: bool = False) -> dict:
    config, commands = _paths(config_path, commands_dir)
    data: dict = {}
    if config.exists():
        try:
            data = json.loads(config.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{config} is not valid JSON: {exc}") from exc
    data.setdefault("$schema", SCHEMA)
    servers = data.setdefault("mcp", {}).setdefault("servers", {})
    added = force or "sieve" not in servers
    if added:
        servers["sieve"] = SERVER

    written = [str(commands / path.relative_to(TEMPLATES))
               for path in TEMPLATES.rglob("*.md")]
    if not dry_run:
        for source in TEMPLATES.rglob("*.md"):
            target = commands / source.relative_to(TEMPLATES)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        config.parent.mkdir(parents=True, exist_ok=True)
        config.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return {"config": str(config), "server_added": added,
            "commands": written, "dry_run": dry_run}
