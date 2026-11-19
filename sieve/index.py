"""Build a RepositoryIndex from a repository root."""
from pathlib import Path

from .discover import Discovery, discover
from .models import RepositoryIndex
from .parse import parse_file

__all__ = ["index_repo", "discover", "Discovery"]


def index_repo(root: Path | str) -> RepositoryIndex:
    found = discover(Path(root))
    skipped = dict(found.skipped)
    files: list[dict] = []
    symbols: list[dict] = []
    chunks: list[dict] = []
    edges: list[dict] = []

    for path in found.files:
        try:
            parsed = parse_file(path, found.root)
        except Exception:
            skipped["parse_error"] = skipped.get("parse_error", 0) + 1
            continue
        files.append({"file": parsed["file"], "tokens": parsed["tokens"],
                      "sha": parsed["sha"], "imports": parsed["imports"]})
        symbols.extend(parsed["symbols"])
        chunks.extend(parsed["chunks"])
        edges.extend(parsed["edges"])

    defined = {symbol["symbol"] for symbol in symbols}
    edges = [edge for edge in edges
             if edge["callee"] in defined and edge["callee"] != edge["caller"]]
    def_index: dict[str, list[str]] = {}
    for symbol in symbols:
        def_index.setdefault(symbol["symbol"], []).append(symbol["file"])

    return {
        "files": files,
        "symbols": symbols,
        "chunks": chunks,
        "edges": edges,
        "def_index": def_index,
        "total_tokens": sum(entry["tokens"] for entry in files),
        "skipped": skipped,
    }
