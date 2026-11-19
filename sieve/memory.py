"""Conversation memory. Two tiers, matching the notes plus episode split.

notes.md survives compaction and holds rules. turns.jsonl holds episodes.
The LLM summarizer plugs in behind `log`.
"""
import json
from pathlib import Path


class Memory:
    def __init__(self, path: str = "memory") -> None:
        self.dir = Path(path)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.turns_file = self.dir / "turns.jsonl"
        self.notes_file = self.dir / "notes.md"
        if not self.notes_file.exists():
            self.notes_file.write_text(
                "# Persistent notes (survive compaction)\n"
                "- Prefer exact symbol matches over semantic guesses.\n",
                encoding="utf-8",
            )

    def log(self, query: str, files: list[str], success: bool | None = None,
            note: str = "") -> None:
        record = {"q": query, "files": files, "success": success,
                  "note": note or query[:160]}
        with self.turns_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")

    def recent(self, n: int = 4) -> list[dict]:
        if not self.turns_file.exists():
            return []
        lines = self.turns_file.read_text(encoding="utf-8").strip().splitlines()
        turns = []
        for line in lines[-n:]:
            try:
                turns.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return turns

    def notes(self) -> str:
        return self.notes_file.read_text(encoding="utf-8")[:1000]

    def compact(self, keep: int = 4) -> list[dict]:
        """Keep the last turns verbatim and collapse older ones to a state line."""
        turns = self.recent(max(keep + 20, keep))
        if len(turns) <= keep:
            return turns
        older = turns[:-keep]
        files = sorted({name for turn in older for name in turn.get("files", [])})
        summary = {
            "q": f"{len(older)} earlier turns",
            "files": files[:8],
            "success": None,
            "note": (f"{len(older)} earlier turns; files: "
                     f"{', '.join(files[:8]) or '-'}"),
        }
        return [summary] + turns[-keep:]
