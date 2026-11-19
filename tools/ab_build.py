"""Build two context arms for the OpenCode A/B demo.

Arm A gets the whole repo. Arm B gets the Sieve prompt at a fixed budget.
Both arms attach the context to the same question and use a no-tools agent,
so the only variable is the context text.

Usage:
  python tools/ab_build.py <repo> <out_dir> [budget]
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, ".")
from sieve import allocator, composer, retrieval, tokenizer
from sieve.discover import discover
from sieve.index import index_repo

QUESTION = "How does GitHub dashboard data become work items in the queue?"
GOLD = [
    "src/app/api/github/dashboard/route.ts",
    "src/lib/github.ts",
    "src/lib/activity-model.ts",
    "src/hooks/use-activity.ts",
    "src/app/page.tsx",
    "src/components/queue-view.tsx",
]
AGENT = """---
description: Answers only from the attached context
mode: primary
steps: 1
permissions:
  - action: "*"
    resource: "*"
    effect: deny
---
Answer only from the attached context.
Name the exact files and functions involved.
If the context is missing something, say what is missing.
Do not use tools.
"""

def full_dump(repo: Path) -> str:
    parts = []
    for path in discover(repo).files:
        text = path.read_text(encoding="utf-8", errors="ignore")
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        parts.append(f"# {path.relative_to(repo).as_posix()}\n{text}")
    return "\n\n".join(parts)

def main(repo_path, out_path, budget=8000):
    repo, out = Path(repo_path), Path(out_path)
    index = index_repo(repo)
    alloc = allocator.allocate(QUESTION, budget, index["total_tokens"])
    ranked, meta = retrieval.hybrid_retrieve(QUESTION, index, top_k=8)
    prompt, layers = composer.compose(QUESTION, index, ranked, alloc, budget)
    context_b = prompt.split("\n\n", 1)[1]
    context_a = full_dump(repo)
    files = [c["file"] for _, c in ranked]
    hit = len(set(GOLD) & set(files))
    arms = {"run-a": context_a, "run-b": context_b}
    for arm, ctx in arms.items():
        d = out / arm
        (d / ".opencode" / "agents").mkdir(parents=True, exist_ok=True)
        (d / "context.md").write_text(ctx, encoding="utf-8")
        (d / ".opencode" / "agents" / "context-only.md").write_text(AGENT, encoding="utf-8")
    manifest = {
        "repo": str(repo).replace("\\", "/"),
        "question": QUESTION,
        "budget": budget,
        "full_tokens": tokenizer.count(context_a),
        "sieve_tokens": tokenizer.count(context_b),
        "saving_pct": round(100 * (1 - tokenizer.count(context_b) / tokenizer.count(context_a)), 1),
        "tokenizer": tokenizer.BACKEND,
        "layers": layers,
        "alloc": alloc,
        "method": meta["method"],
        "files": files,
        "gold": GOLD,
        "gold_in_top8": hit,
        "gold_recall": round(hit / len(GOLD), 2),
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print(json.dumps(manifest, indent=1))
    assert layers["total"] <= budget, "Sieve context exceeds its own budget"
    assert tokenizer.count(context_b) < tokenizer.count(context_a), "Sieve did not save tokens"
    return manifest

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 8000)
