"""Budgeted compression for tool output.

The compressor is lossy. It keeps errors, paths, numbers and code lines, and
drops noise such as repeated log lines, passing test lines, progress bars and
long JSON blobs. Every original goes to the store and comes back by ref.
"""
import csv
import io
import json
import re

from . import tokenizer
from .models import CompressedText
from .store import STORE

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
ERROR_WORDS = re.compile(
    r"error|warn|fail|exception|traceback|panic|fatal|denied|timeout|"
    r"assert|expected|actual|not found|cannot|refused", re.I)
TEST_WORDS = re.compile(
    r"^(FAIL|ERROR|PASS|ok |--- FAIL|=== RUN|✕|✗|✓|Tests:|Test Files|"
    r"Duration|Ran \d+ test)", re.I)


def normalize(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return ANSI_RE.sub("", text)


def detect_kind(text: str) -> str:
    stripped = text.lstrip()
    if stripped[:1] in "{[":
        try:
            json.loads(text)
            return "json"
        except json.JSONDecodeError:
            pass
    if re.search(r"(?m)^(FAIL|ERROR|PASS|ok |--- FAIL|=== RUN|✕|✗|✓)", text):
        return "test"
    if re.search(r"(?m)(?:^|\s)(?:INFO|WARN|WARNING|ERROR|DEBUG|TRACE)\b|"
                 r"\bTraceback\b", text):
        return "log"
    lines = text.splitlines()
    if len(lines) > 2 and "," in lines[0]:
        return "csv"
    head = stripped[:200].lower()
    if "<html" in head or "<div" in head:
        return "html"
    return "text"


def _estimate(line: str) -> int:
    return len(line) // 4 + 1


def pack_lines(lines: list[str], budget: int) -> str:
    """Keep the head and the tail, mark the gap. Used by every strategy."""
    if not lines:
        return ""
    costs = [_estimate(line) for line in lines]
    if sum(costs) <= budget:
        return "\n".join(lines)
    head: list[str] = []
    used = 0
    index = 0
    while index < len(lines) and used + costs[index] <= budget:
        head.append(lines[index])
        used += costs[index]
        index += 1
    tail: list[str] = []
    cursor = len(lines) - 1
    while cursor > index and used + costs[cursor] <= budget:
        tail.append(lines[cursor])
        used += costs[cursor]
        cursor -= 1
    omitted = len(lines) - len(head) - len(tail)
    if omitted <= 0:
        return "\n".join(head)
    return "\n".join(head + [f"... ({omitted} lines omitted)"] + list(reversed(tail)))


def dedupe(lines: list[str]) -> list[str]:
    out: list[str] = []
    previous: str | None = None
    count = 0
    for line in lines:
        if line == previous:
            count += 1
            continue
        if previous is not None:
            out.append(previous if count == 0 else f"{previous}  (x{count + 1})")
        previous = line
        count = 0
    if previous is not None:
        out.append(previous if count == 0 else f"{previous}  (x{count + 1})")
    return out


def _generic(lines: list[str], budget: int) -> str:
    cleaned = [line for line in dedupe(lines) if line.strip() != ""]
    return pack_lines(cleaned, budget)


def _log(lines: list[str], budget: int) -> str:
    errors = [line for line in lines if ERROR_WORDS.search(line)]
    head = lines[:5]
    tail = lines[-10:]
    selected = dedupe(head + errors + tail)
    return pack_lines(selected, budget)


def _test(lines: list[str], budget: int) -> str:
    signals = [line for line in lines
               if TEST_WORDS.search(line) or ERROR_WORDS.search(line)]
    selected = dedupe(signals + lines[-20:])
    return pack_lines(selected, budget)


def _short(value):
    if isinstance(value, str):
        return value[:200]
    if isinstance(value, list):
        return f"list[{len(value)}]"
    if isinstance(value, dict):
        return f"dict[{len(value)}]"
    return value


def _json_summary(text: str, budget: int) -> str:
    value = json.loads(text)
    if isinstance(value, list):
        summary = {"count": len(value), "first": value[:3],
                   "last": value[-1:] if value else []}
    elif isinstance(value, dict):
        summary = {"keys": list(value)[:30],
                   "preview": {key: _short(item)
                               for key, item in list(value.items())[:20]}}
    else:
        summary = value
    body = "# json summary\n" + json.dumps(summary, indent=1, default=str)
    return pack_lines(body.splitlines(), budget)


def _csv_summary(text: str, budget: int) -> str:
    rows = list(csv.reader(io.StringIO(text)))
    if not rows:
        return ""
    header = " | ".join(rows[0])
    body = rows[1:]
    keep = body[:8] + (body[-1:] if len(body) > 8 else [])
    lines = [header]
    if len(body) > len(keep):
        lines.append(f"... {len(body) - len(keep)} rows omitted")
    lines += [" | ".join(row[:12]) for row in keep]
    return pack_lines(lines, budget)


def _html_summary(text: str, budget: int) -> str:
    text = re.sub(r"(?is)<(script|style).*?</\1>", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    return _generic(text.splitlines(), budget)


def compress_text(text: str, budget: int = 800, kind: str = "auto",
                  store: bool = True) -> CompressedText:
    before = tokenizer.count(text)
    chosen = detect_kind(text) if kind in ("", "auto") else kind
    if before <= budget:
        return {"text": text, "kind": chosen, "tokens_before": before,
                "tokens_after": before, "saved_pct": 0.0, "changed": False,
                "ref": None}

    source = normalize(text)
    lines = source.splitlines()
    if chosen == "json":
        try:
            output = _json_summary(source, budget)
        except (json.JSONDecodeError, TypeError):
            output = _generic(lines, budget)
    elif chosen == "csv":
        output = _csv_summary(source, budget)
    elif chosen == "html":
        output = _html_summary(source, budget)
    elif chosen == "log":
        output = _log(lines, budget)
    elif chosen == "test":
        output = _test(lines, budget)
    else:
        output = _generic(lines, budget)

    if not output.strip():
        output = _generic(lines, budget)
    if tokenizer.count(output) > budget:
        output = tokenizer.truncate(output, budget)
    after = tokenizer.count(output)
    ref = STORE.put(text) if store and after < before else None
    return {
        "text": output,
        "kind": chosen,
        "tokens_before": before,
        "tokens_after": after,
        "saved_pct": round(100 * (before - after) / before, 1) if before else 0.0,
        "changed": after < before,
        "ref": ref,
    }
