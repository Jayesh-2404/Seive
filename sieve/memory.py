"""Conversation memory: JSONL episodic store + persistent notes.

Two tiers (like Claude Code CLAUDE.md + MemGPT):
  notes.md   - persistent rules the allocator always includes (never auto-deleted)
  turns.jsonl - episodic (query, retrieved files, outcome, note)
v0 uses extractive notes (first line of outcome). LLM summarizer plugs in later.
"""
import json
from pathlib import Path

class Memory:
    def __init__(self, path="memory"):
        self.dir = Path(path); self.dir.mkdir(parents=True, exist_ok=True)
        self.turns_f = self.dir / "turns.jsonl"
        self.notes_f = self.dir / "notes.md"
        if not self.notes_f.exists():
            self.notes_f.write_text("# Persistent notes (survive compaction)\n- Prefer exact symbol matches over semantic guesses.\n")
    def log(self, query, files, success=None, note=""):
        rec = {"q": query, "files": files, "success": success, "note": note or query[:160]}
        with open(self.turns_f, "a") as f:
            f.write(json.dumps(rec) + "\n")
    def recent(self, n=4):
        if not self.turns_f.exists():
            return []
        lines = self.turns_f.read_text().strip().split("\n")
        out = []
        for ln in lines[-n:]:
            try:
                out.append(json.loads(ln))
            except Exception:
                pass
        return out
    def notes(self):
        return self.notes_f.read_text()[:1000]
