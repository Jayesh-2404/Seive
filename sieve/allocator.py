"""Token-budget allocator: rule-based v0 (learned v1 needs log data).

Inputs:  query, total budget, repo full tokens.
Output:  per-layer token split + task_type + bypass flag.

Bypass rule (fixes toy-repo failure): if repo fits in budget, return full.
Otherwise split by task type (heuristic, to be learned from logs in v1).
"""
SPLITS = {
    "bug_fix":  {"symbols": 0.30, "semantic": 0.45, "summary": 0.15, "memory": 0.10},
    "feature":  {"symbols": 0.20, "semantic": 0.55, "summary": 0.15, "memory": 0.10},
    "perf":     {"symbols": 0.10, "semantic": 0.35, "summary": 0.45, "memory": 0.10},
    "question": {"symbols": 0.20, "semantic": 0.40, "summary": 0.30, "memory": 0.10},
}
KEYWORDS = {
    "bug_fix": ["fix", "bug", "error", "exception", "traceback", "keyerror", "fail"],
    "feature": ["add", "implement", "feature", "create", "logout", "endpoint"],
    "perf": ["slow", "perf", "optim", "latency", "n+1", "cache"],
}

def classify(query: str):
    ql = query.lower()
    hits = {k: sum(1 for w in v if w in ql) for k, v in KEYWORDS.items()}
    best = max(hits, key=lambda k: hits[k])
    if hits[best] == 0:
        return "question", 0.4
    conf = min(0.95, 0.55 + 0.15 * hits[best])
    return best, conf

def allocate(query: str, budget: int, full_tokens: int):
    task_type, conf = classify(query)
    if full_tokens <= int(budget * 0.9):
        return {"task_type": task_type, "confidence": conf, "bypass": True,
                "reason": f"repo {full_tokens} fits in budget {budget}: return full dump",
                "split": {"symbols": 0, "semantic": 1.0, "summary": 0, "memory": 0}}
    split = SPLITS[task_type]
    toks = {k: int(budget * v) for k, v in split.items()}
    return {"task_type": task_type, "confidence": conf, "bypass": False,
            "reason": f"task={task_type} routed split", "split": split, "tokens": toks}
