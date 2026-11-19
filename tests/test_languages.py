from pathlib import Path

from sieve import allocator
from sieve.index import index_repo

FIXTURES = {
    "a.py": "def alpha():\n    return 1\n",
    "b.ts": "export function beta() { return 1; }\nexport class Gamma {}\n",
    "c.cpp": "class Delta {};\nint epsilon(int x) { return x; }\n",
    "d.go": "package main\nfunc Zeta() {}\ntype Eta struct{}\n",
    "e.java": "public class Theta {\n  public void iota() {}\n}\n",
    "f.rs": "pub fn kappa() {}\npub struct Lambda;\n",
}


def test_indexes_python_typescript_cpp_go_java_rust(tmp_path: Path) -> None:
    for name, source in FIXTURES.items():
        (tmp_path / name).write_text(source, encoding="utf-8")
    index = index_repo(tmp_path)
    names = {symbol["symbol"] for symbol in index["symbols"]}
    expected = {"alpha", "beta", "Gamma", "Delta", "epsilon",
                "Zeta", "Eta", "Theta", "iota", "kappa", "Lambda"}
    missing = expected - names
    assert not missing, f"missing symbols: {sorted(missing)}"
    assert len(index["files"]) == len(FIXTURES)


def test_parent_folder_named_build_is_not_skipped(tmp_path: Path) -> None:
    root = tmp_path / "build" / "project"
    (root / "src").mkdir(parents=True)
    (root / "src" / "app.py").write_text("def run():\n    return 1\n", encoding="utf-8")
    index = index_repo(root)
    assert [entry["file"] for entry in index["files"]] == ["src/app.py"]


def test_skips_binary_lockfile_and_node_modules(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("def keep():\n    return 1\n", encoding="utf-8")
    (tmp_path / "blob.py").write_bytes(b"\x00\x01\x02")
    (tmp_path / "package-lock.json").write_text("{}", encoding="utf-8")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "dep.py").write_text("def dep(): pass\n", encoding="utf-8")
    index = index_repo(tmp_path)
    assert [entry["file"] for entry in index["files"]] == ["a.py"]
    assert index["skipped"]["binary"] == 1
    assert index["skipped"]["lockfile"] == 1


def test_doc_only_repo_falls_back_to_text(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Notes\n\nUse the queue.\n", encoding="utf-8")
    index = index_repo(tmp_path)
    assert [entry["file"] for entry in index["files"]] == ["README.md"]


def test_allocator_uses_word_boundaries() -> None:
    assert allocator.classify("prefix the field")[0] == "question"
    assert allocator.classify("fix the parsing error")[0] == "bug_fix"


def test_mcp_tools_are_registered() -> None:
    import asyncio

    from sieve.server.mcp import server

    tools = asyncio.run(server.list_tools())
    names = {getattr(tool, "name", None) for tool in tools}
    assert {"index", "query", "read", "compress", "original",
            "symbol", "stats"} <= names
