"""Token-budget allocator. Rule-based v0, with an optional trace-fitted table.

The learned table is an in-sample grid search over the 12 eval tasks. It is a
prototype, not a validated model. The default remains the rule split so the
measured A/B and eval stay stable.
"""
import json
import re
from pathlib import Path

from .models import Allocation

SPLITS = {
    "bug_fix":  {"symbols": 0.25, "semantic": 0.50, "summary": 0.15, "memory": 0.10},
    "feature":  {"symbols": 0.20, "semantic": 0.55, "summary": 0.15, "memory": 0.10},
    "perf":     {"symbols": 0.10, "semantic": 0.40, "summary": 0.40, "memory": 0.10},
    "question": {"symbols": 0.15, "semantic": 0.60, "summary": 0.15, "memory": 0.10},
}
KEYWORDS = {
    "bug_fix": ["fix", "bug", "error", "exception", "traceback", "keyerror", "fail"],
    "feature": ["add", "implement", "feature", "create", "logout", "endpoint"],
    "perf": ["slow", "perf", "optim", "latency", "n+1", "cache"],
}
LEARNED_PATH = Path(__file__).with_name("allocator_learned.json")
_LEARNED: dict | None = None


def learned_splits() -> dict:
    global _LEARNED
    if _LEARNED is None:
        try:
            data = json.loads(LEARNED_PATH.read_text(encoding="utf-8"))
            _LEARNED = data.get("splits", {})
        except (OSError, json.JSONDecodeError):
            _LEARNED = {}
    return _LEARNED


def _mentions(text: str, word: str) -> bool:
    pattern = rf"(?<![a-z0-9]){re.escape(word)}(?![a-z0-9])"
    return re.search(pattern, text) is not None


def classify(query: str) -> tuple[str, float]:
    lowered = query.lower()
    hits = {task: sum(1 for word in words if _mentions(lowered, word))
            for task, words in KEYWORDS.items()}
    best = max(hits, key=lambda task: hits[task])
    if hits[best] == 0:
        return "question", 0.4
    confidence = min(0.95, 0.55 + 0.15 * hits[best])
    return best, confidence


def allocate(query: str, budget: int, full_tokens: int,
             learned: bool = False) -> Allocation:
    task_type, confidence = classify(query)
    if full_tokens <= int(budget * 0.9):
        return {
            "task_type": task_type,
            "confidence": confidence,
            "bypass": True,
            "reason": f"repo {full_tokens} fits in budget {budget}: return full dump",
            "split": {"symbols": 0, "semantic": 1.0, "summary": 0, "memory": 0},
        }
    split = learned_splits().get(task_type, SPLITS[task_type]) if learned else SPLITS[task_type]
    return {
        "task_type": task_type,
        "confidence": confidence,
        "bypass": False,
        "reason": f"task={task_type} routed split" + (" (learned)" if learned else ""),
        "split": split,
        "tokens": {name: int(budget * share) for name, share in split.items()},
    }
