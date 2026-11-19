"""Original text store and the tool event log.

Compressed text is lossy. Every original is kept here so an agent can ask for
it back. The cache lives outside the repository so a read never writes into the
project. Set SIEVE_CACHE_DIR to move it.
"""
import hashlib
import json
import os
import re
import threading
import time
from pathlib import Path

REF_RE = re.compile(r"^[0-9a-f]{16}$")
_LOCK = threading.Lock()


def cache_root() -> Path:
    return Path(os.getenv("SIEVE_CACHE_DIR", str(Path.home() / ".sieve")))


class OriginalStore:
    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or cache_root()) / "originals"
        self.root.mkdir(parents=True, exist_ok=True)

    def put(self, text: str) -> str:
        ref = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
        path = self.root / f"{ref}.txt"
        if not path.exists():
            path.write_text(text, encoding="utf-8")
        return ref

    def get(self, ref: str, start_line: int | None = None,
            end_line: int | None = None) -> str:
        if not REF_RE.match(ref):
            raise ValueError("invalid ref")
        path = self.root / f"{ref}.txt"
        if not path.exists():
            raise KeyError(ref)
        text = path.read_text(encoding="utf-8")
        if start_line is None and end_line is None:
            return text
        lines = text.splitlines()
        start = max(1, start_line or 1) - 1
        end = min(len(lines), end_line or len(lines))
        return "\n".join(lines[start:end])


STORE = OriginalStore()


def log_event(tool: str, before: int, after: int, kind: str = "",
              ref: str | None = None) -> None:
    path = cache_root() / "events.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "ts": round(time.time(), 3),
        "tool": tool,
        "kind": kind,
        "before": before,
        "after": after,
        "saved": max(0, before - after),
        "ref": ref,
    }
    with _LOCK:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")


def event_stats() -> dict:
    path = cache_root() / "events.jsonl"
    if not path.exists():
        return {"calls": 0, "before": 0, "after": 0, "saved": 0,
                "saved_pct": 0.0, "by_tool": {}}
    total_before = 0
    total_after = 0
    calls = 0
    by_tool: dict[str, dict] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        calls += 1
        before = int(record.get("before", 0))
        after = int(record.get("after", 0))
        total_before += before
        total_after += after
        tool = record.get("tool", "?")
        bucket = by_tool.setdefault(tool, {"calls": 0, "before": 0,
                                           "after": 0, "saved": 0})
        bucket["calls"] += 1
        bucket["before"] += before
        bucket["after"] += after
        bucket["saved"] += max(0, before - after)
    saved = total_before - total_after
    return {
        "calls": calls,
        "before": total_before,
        "after": total_after,
        "saved": saved,
        "saved_pct": round(100 * saved / total_before, 1) if total_before else 0.0,
        "by_tool": by_tool,
    }
