"""Symbol-aware file reads.

An agent should not read a 2,000 line file to change one function. This returns
the file map plus the requested symbol's span, and keeps the whole file in the
original store.
"""
from pathlib import Path

from . import tokenizer
from .compress import normalize, pack_lines
from .models import ReadResult, RepositoryIndex
from .store import STORE


def read_file(root: Path | str, rel: str, index: RepositoryIndex,
              symbol: str | None = None, budget: int = 1200) -> ReadResult:
    root = Path(root).resolve()
    rel = rel.replace("\\", "/").lstrip("/")
    path = (root / rel).resolve()
    if not path.is_relative_to(root):
        raise ValueError("file is outside the repository")
    if not path.is_file():
        raise FileNotFoundError(rel)

    source = normalize(path.read_text(encoding="utf-8", errors="ignore"))
    before = tokenizer.count(source)
    entry = next((item for item in index["files"] if item["file"] == rel), None)
    if entry is None:
        raise ValueError(f"{rel} is not in the index. Refresh the index first.")

    symbols = [item for item in index["symbols"] if item["file"] == rel]
    header = [f"# {rel}"]
    if entry["imports"]:
        header.append("imports: " + ", ".join(entry["imports"][:24]))

    body: list[str] = []
    kind = "file"
    if symbol:
        kind = "symbol"
        matches = [item for item in symbols if item["symbol"] == symbol]
        if not matches:
            table = [f'{item["line"]}: {item["symbol"]} ({item["kind"]})'
                     for item in symbols[:60]]
            text = "\n".join(header + ["", f"symbol '{symbol}' not found.",
                                       "symbols:"] + table)
            return _result(rel, symbol, kind, text, symbols, before, source)
        found = matches[0]
        chunk = next((item for item in index["chunks"]
                      if item["file"] == rel and item["kind"] == "func"
                      and item["name"] == symbol), None)
        if chunk:
            body = chunk["text"].splitlines()
        else:
            lines = source.splitlines()
            following = next((item["line"] for item in symbols
                              if item["line"] > found["line"]), len(lines) + 1)
            start = max(1, found["line"] - 2)
            end = min(len(lines), following - 1)
            body = lines[start - 1:end]
    else:
        table = [f'{item["line"]}: {item["symbol"]} ({item["kind"]})'
                 for item in symbols[:80]]
        header += ["", "symbols:"] + table
        body = source.splitlines()

    prefix = "\n".join(header)
    remaining = budget - tokenizer.count(prefix) - 4
    packed = pack_lines(body, remaining) if remaining > 0 and body else ""
    text = prefix + ("\n\n" + packed if packed else "")
    if tokenizer.count(text) > budget:
        text = tokenizer.truncate(text, budget)
    return _result(rel, symbol, kind, text, symbols, before, source)


def _result(rel: str, symbol: str | None, kind: str, text: str,
            symbols: list[dict], before: int, source: str) -> ReadResult:
    after = tokenizer.count(text)
    changed = after < before
    ref = STORE.put(source) if changed else None
    return {
        "file": rel,
        "symbol": symbol,
        "text": text,
        "kind": kind,
        "symbols": [item["symbol"] for item in symbols[:60]],
        "tokens_before": before,
        "tokens_after": after,
        "saved_pct": round(100 * (before - after) / before, 1) if before else 0.0,
        "changed": changed,
        "ref": ref,
    }
