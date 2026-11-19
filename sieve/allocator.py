"""Token-budget allocator. Rule-based v0, learned v1 needs log data.

Bypass rule: if the repo fits in the budget, return the full dump. Otherwise
split the budget by task type. Keyword matching uses word boundaries so
"prefix" does not count as "fix".
"""
import re

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


def allocate(query: str, budget: int, full_tokens: int) -> Allocation:
    task_type, confidence = classify(query)
    if full_tokens <= int(budget * 0.9):
        return {
            "task_type": task_type,
            "confidence": confidence,
            "bypass": True,
            "reason": f"repo {full_tokens} fits in budget {budget}: return full dump",
            "split": {"symbols": 0, "semantic": 1.0, "summary": 0, "memory": 0},
        }
    split = SPLITS[task_type]
    return {
        "task_type": task_type,
        "confidence": confidence,
        "bypass": False,
        "reason": f"task={task_type} routed split",
        "split": split,
        "tokens": {name: int(budget * share) for name, share in split.items()},
    }
