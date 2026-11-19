"""Repository discovery.

Walks once, prunes ignored directories before descending, and records why a
file was skipped. The skip rules look at the path relative to the repo, never
the absolute path, so a parent folder named "build" does not hide the repo.
"""
import os
from dataclasses import dataclass, field
from pathlib import Path

from .config import MAX_FILE_BYTES, MAX_LINE_CHARS, SKIP_DIRS, SKIP_FILES, SNIFF_BYTES
from .parse.profiles import is_code, is_text


@dataclass
class Discovery:
    root: Path
    files: list[Path]
    skipped: dict[str, int] = field(default_factory=dict)


def _skip_reason(path: Path) -> str | None:
    try:
        size = path.stat().st_size
    except OSError:
        return "stat_error"
    if size == 0:
        return "empty"
    if size > MAX_FILE_BYTES:
        return "too_large"
    try:
        with path.open("rb") as handle:
            head = handle.read(SNIFF_BYTES)
    except OSError:
        return "read_error"
    if b"\x00" in head:
        return "binary"
    text = head.decode("utf-8", "ignore")
    if any(len(line) > MAX_LINE_CHARS for line in text.splitlines()[:20]):
        return "minified"
    return None


def discover(root: Path) -> Discovery:
    root = Path(root).resolve()
    code: list[Path] = []
    text: list[Path] = []
    skipped: dict[str, int] = {}

    def bump(reason: str) -> None:
        skipped[reason] = skipped.get(reason, 0) + 1

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(
            name for name in dirnames
            if name not in SKIP_DIRS and not name.startswith(".")
        )
        for name in sorted(filenames):
            path = Path(dirpath) / name
            if name in SKIP_FILES:
                bump("lockfile")
                continue
            if is_code(path):
                bucket = code
            elif is_text(path):
                bucket = text
            else:
                continue
            reason = _skip_reason(path)
            if reason:
                bump(reason)
                continue
            bucket.append(path)

    # Code wins when a repo has both. Text is the fallback for doc-only repos.
    files = code or text
    if not files:
        bump("no_indexable_files")
    return Discovery(root=root, files=files, skipped=skipped)
