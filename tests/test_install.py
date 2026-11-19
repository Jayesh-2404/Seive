import json

from sieve.install import init


def test_init_merges_config_and_copies_commands(tmp_path) -> None:
    config = tmp_path / "opencode.json"
    config.write_text(json.dumps({
        "mcp": {"servers": {"browse": {"type": "local", "command": ["x"]}}}
    }), encoding="utf-8")
    result = init(config, tmp_path / "commands")
    data = json.loads(config.read_text(encoding="utf-8"))
    assert data["mcp"]["servers"]["browse"]["command"] == ["x"]
    assert data["mcp"]["servers"]["sieve"]["command"] == ["sieve-mcp"]
    assert (tmp_path / "commands" / "sieve.md").exists()
    assert (tmp_path / "commands" / "sieve" / "query.md").exists()
    assert result["server_added"] is True


def test_init_dry_run_writes_nothing(tmp_path) -> None:
    config = tmp_path / "opencode.json"
    result = init(config, tmp_path / "commands", dry_run=True)
    assert result["dry_run"] is True
    assert not config.exists()
    assert not (tmp_path / "commands").exists()
