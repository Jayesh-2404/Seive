"""Fit a split table from logged traces.

This is a grid search over candidate splits on the 12 eval tasks. It is not a
learned model and it is in-sample. The point is to show the data pipeline and
give the allocator a trace-fitted option.
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from run_eval import TASKS  # noqa: E402
from sieve import allocator, composer, retrieval  # noqa: E402
from sieve.index import index_repo  # noqa: E402

BUDGET = 600
TOP_K = 5
REPO = ROOT / "sample_repo_large"
CANDIDATES = {
    "rule": None,
    "symbols_heavy": {"symbols": 0.40, "semantic": 0.40, "summary": 0.10, "memory": 0.10},
    "semantic_heavy": {"symbols": 0.10, "semantic": 0.70, "summary": 0.10, "memory": 0.10},
    "summary_heavy": {"symbols": 0.10, "semantic": 0.40, "summary": 0.40, "memory": 0.10},
    "balanced": {"symbols": 0.25, "semantic": 0.50, "summary": 0.15, "memory": 0.10},
}


def evaluate(index, task: dict, split: dict) -> tuple[float, int]:
    tokens = {name: int(BUDGET * share) for name, share in split.items()}
    alloc = {"task_type": task.get("type", "question"), "confidence": 0.5,
             "bypass": False, "split": split, "tokens": tokens}
    ranked, _ = retrieval.hybrid_retrieve(task["q"], index, top_k=TOP_K)
    prompt, layers = composer.compose(task["q"], index, ranked, alloc, BUDGET)
    gold = set(task["gold"])
    covered = sum(1 for path in gold if f"# {path}" in prompt) / max(1, len(gold))
    return covered, layers["total"]


def main() -> None:
    index = index_repo(REPO)
    groups: dict[str, list[dict]] = defaultdict(list)
    for task in TASKS:
        task_type, _ = allocator.classify(task["q"])
        groups[task_type].append({**task, "type": task_type})

    table: dict[str, dict] = {}
    report: dict[str, list] = {}
    for task_type, tasks in groups.items():
        results = []
        for name, candidate in CANDIDATES.items():
            split = candidate or allocator.SPLITS[task_type]
            scores = [evaluate(index, task, split) for task in tasks]
            mean_recall = sum(score[0] for score in scores) / len(scores)
            mean_tokens = sum(score[1] for score in scores) / len(scores)
            results.append({"name": name, "coverage": round(mean_recall, 3),
                            "tokens": round(mean_tokens, 1)})
        # Highest coverage first, then fewer tokens.
        best = sorted(results, key=lambda item: (-item["coverage"], item["tokens"]))[0]
        table[task_type] = CANDIDATES[best["name"]] or allocator.SPLITS[task_type]
        report[task_type] = results
        print(f"{task_type:9} best={best['name']:14} "
              f"coverage={best['coverage']} tokens={best['tokens']}")

    out = {"source": "12 eval tasks, 5 candidate splits, in-sample",
           "tasks": len(TASKS), "budget": BUDGET, "splits": table, "report": report}
    path = ROOT / "sieve" / "allocator_learned.json"
    path.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("wrote", path)


if __name__ == "__main__":
    main()
