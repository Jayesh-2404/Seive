from pathlib import Path

import pytest

from sieve.index import index_repo
from sieve.read import read_file

ROOT = Path(__file__).resolve().parents[1]


def test_read_one_symbol_returns_its_code() -> None:
    repo = ROOT / "sample_repo_large"
    index = index_repo(repo)
    result = read_file(repo, "auth.py", index, "check_auth", budget=400)
    assert "def check_auth" in result["text"]
    assert result["symbol"] == "check_auth"
    assert result["tokens_after"] <= 400
    assert result["ref"] is not None
    assert result["tokens_after"] < result["tokens_before"]


def test_read_file_returns_a_symbol_map() -> None:
    repo = ROOT / "sample_repo_large"
    index = index_repo(repo)
    result = read_file(repo, "auth.py", index, budget=400)
    assert result["kind"] == "file"
    assert "check_auth" in result["symbols"]
    assert "symbols:" in result["text"]


def test_unknown_symbol_lists_what_exists() -> None:
    repo = ROOT / "sample_repo_large"
    index = index_repo(repo)
    result = read_file(repo, "auth.py", index, "does_not_exist", budget=400)
    assert "not found" in result["text"]
    assert "check_auth" in result["text"]


def test_path_outside_repo_is_rejected() -> None:
    repo = ROOT / "sample_repo_large"
    index = index_repo(repo)
    with pytest.raises(ValueError):
        read_file(repo, "../../outside.py", index)


def test_typescript_symbol_read(tmp_path: Path) -> None:
    (tmp_path / "a.ts").write_text(
        "export function beta() {\n  return 1;\n}\n"
        "export class Gamma {}\n",
        encoding="utf-8",
    )
    index = index_repo(tmp_path)
    result = read_file(tmp_path, "a.ts", index, "beta", budget=200)
    assert "function beta" in result["text"]
    assert result["tokens_after"] <= 200
