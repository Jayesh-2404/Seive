"""Run the six-task benchmark through OpenCode and score the answers.

Each task has a full-context arm and a Sieve arm. The agent has no tools, so the
answer can only use the attached context. Scoring checks whether the answer
names a gold file and a gold symbol. That is localization success, not a full
fix-rate result.
"""
import csv
import json
import os
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "bench"
DB = Path(os.path.expanduser("~/.local/share/opencode/opencode.db"))
MODEL = "opencode-go/kimi-k2.7-code"
SUFFIX = (" Answer from the attached context. Name exact files and functions. "
          "If the context is missing something, say what is missing.")
OPENCODE = Path(os.getenv("APPDATA", "")) / "npm/node_modules/@opencode/cli/bin/opencode.exe"
if not OPENCODE.exists():
    OPENCODE = Path(shutil.which("opencode") or "opencode")


def answer_text(session_id: str) -> str:
    con = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    row = con.execute(
        "select data from session_message where session_id=? and type='assistant' "
        "order by time_created desc limit 1", (session_id,)).fetchone()
    if not row:
        return ""
    content = json.loads(row[0]).get("content", [])
    return "\n\n".join(part.get("text", "") for part in content
                       if part.get("type") == "text")


def session_tokens(session_id: str) -> dict:
    con = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    row = con.execute(
        "select tokens_input, tokens_output, tokens_reasoning, tokens_cache_read, cost "
        "from session_v2 where id=?", (session_id,)).fetchone()
    if not row:
        return {}
    keys = ["input", "output", "reasoning", "cache_read", "cost"]
    return dict(zip(keys, row))


def score(text: str, task: dict) -> tuple[bool, bool]:
    normalized = text.replace("\\", "/").lower()
    file_hit = any(path.lower() in normalized or Path(path).name.lower() in normalized
                   for path in task["files"])
    symbol_hit = any(symbol.lower() in normalized for symbol in task["symbols"])
    return file_hit, symbol_hit


def main(tag: str = "r1") -> None:
    manifest = json.loads((BENCH / "manifest.json").read_text(encoding="utf-8"))
    answers = BENCH / "answers"
    answers.mkdir(exist_ok=True)
    rows = []
    for task in manifest["tasks"]:
        for arm in ("full", "sieve"):
            session_id = f"ses-real-{tag}-{task['id'].lower()}-{arm}"
            directory = BENCH / task["id"] / arm
            command = [
                str(OPENCODE), "run", "--agent", "context-only", "--model", MODEL,
                "--format", "json", "--archived", "--session", session_id,
                "--file", "context.md", task["q"] + SUFFIX,
            ]
            print(f"running {task['id']} {arm} ...", flush=True)
            result = subprocess.run(command, cwd=directory, capture_output=True,
                                    text=True, encoding="utf-8", errors="replace",
                                    timeout=240)
            text = answer_text(session_id)
            (answers / f"{task['id']}-{arm}.md").write_text(text, encoding="utf-8")
            tokens = session_tokens(session_id)
            file_hit, symbol_hit = score(text, task)
            success = file_hit and symbol_hit
            row = {
                "task": task["id"], "arm": arm, "session": session_id,
                "input": tokens.get("input", 0), "output": tokens.get("output", 0),
                "reasoning": tokens.get("reasoning", 0),
                "cache_read": tokens.get("cache_read", 0),
                "file_hit": int(file_hit), "symbol_hit": int(symbol_hit),
                "success": int(success),
                "error": "" if result.returncode == 0 else result.stderr[-200:],
            }
            rows.append(row)
            print(f"  input={row['input']} success={success} "
                  f"file={file_hit} symbol={symbol_hit}", flush=True)

    out = BENCH / "results_real.csv"
    with out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    summary = {"tag": tag, "model": MODEL, "tasks": len(manifest["tasks"]),
               "arms": {}}
    for arm in ("full", "sieve"):
        arm_rows = [row for row in rows if row["arm"] == arm]
        summary["arms"][arm] = {
            "success": sum(row["success"] for row in arm_rows),
            "points": sum(row["file_hit"] + row["symbol_hit"] for row in arm_rows),
            "max_points": 2 * len(arm_rows),
            "avg_input": round(sum(row["input"] for row in arm_rows) / len(arm_rows)),
            "avg_output": round(sum(row["output"] for row in arm_rows) / len(arm_rows)),
            "avg_reasoning": round(sum(row["reasoning"] for row in arm_rows) / len(arm_rows)),
        }
    full_in = summary["arms"]["full"]["avg_input"]
    sieve_in = summary["arms"]["sieve"]["avg_input"]
    summary["input_reduction_pct"] = round(100 * (1 - sieve_in / full_in), 1) if full_in else 0.0
    (BENCH / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")

    print("\narm    success  points  avg_input  avg_output")
    for arm in ("full", "sieve"):
        item = summary["arms"][arm]
        print(f"{arm:6} {item['success']}/{len(manifest['tasks'])} "
              f"{item['points']}/{item['max_points']} {item['avg_input']:9} "
              f"{item['avg_output']:10}")
    print(f"input reduction: {summary['input_reduction_pct']}%")
    print("wrote", out)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "r1")
