"""Build a six-task real-repository benchmark.

Each task gets two context arms: the whole repo and the Sieve prompt at 8,000
tokens. The run script attaches one context per session and scores the answer.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sieve import allocator, composer, retrieval, tokenizer  # noqa: E402
from sieve.discover import discover  # noqa: E402
from sieve.index import index_repo  # noqa: E402

REPO = Path(r"C:\Users\DELL-1\Documents\project\demo\agent-activity-dashboard")
BENCH = ROOT / "bench"
BUDGET = 8000
TOP_K = 8

TASKS = [
    {"id": "T1", "q": "How does a GitHub repository become a work item in the dashboard queue?",
     "files": ["src/lib/activity-model.ts"],
     "symbols": ["buildWorkItems", "makeWorkItem"]},
    {"id": "T2",
     "q": "Where does the dashboard fetch GitHub data, and how does the client hook store it?",
     "files": ["src/app/api/github/dashboard/route.ts", "src/hooks/use-activity.ts"],
     "symbols": ["loadRepository", "useActivity"]},
    {"id": "T3",
     "q": "How does the app discover local Git repositories and read their branch status?",
     "files": ["src/lib/local-git.ts"],
     "symbols": ["parseStatus", "parseConfig"]},
    {"id": "T4",
     "q": "How are pull request attention states computed and how are work items sorted?",
     "files": ["src/lib/activity-model.ts"],
     "symbols": ["inferAttention", "sortWorkItems"]},
    {"id": "T5", "q": "How does the UI split the queue and render each work item?",
     "files": ["src/components/queue-view.tsx", "src/components/work-item.tsx"],
     "symbols": ["QueueView", "WorkItem"]},
    {"id": "T6", "q": "How does the repository picker load and select repositories?",
     "files": ["src/components/repo-list.tsx", "src/components/repo-picker.tsx"],
     "symbols": ["RepoList", "RepoPicker"]},
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
Answer only from the attached context. Name exact files and functions.
If the context is missing something, say what is missing. Do not use tools.
"""


def full_dump() -> str:
    parts = []
    for path in discover(REPO).files:
        text = path.read_text(encoding="utf-8", errors="ignore")
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        parts.append(f"# {path.relative_to(REPO).as_posix()}\n{text}")
    return "\n\n".join(parts)


def main() -> None:
    index = index_repo(REPO)
    dump = full_dump()
    manifest = {"repo": str(REPO), "budget": BUDGET, "top_k": TOP_K,
                "full_tokens": tokenizer.count(dump), "tasks": []}
    for task in TASKS:
        allocation = allocator.allocate(task["q"], BUDGET, index["total_tokens"])
        ranked, _ = retrieval.hybrid_retrieve(task["q"], index, top_k=TOP_K)
        prompt, layers = composer.compose(task["q"], index, ranked, allocation, BUDGET)
        context = prompt.split("\n\n", 1)[1]
        arms = {"full": dump, "sieve": context}
        for arm, text in arms.items():
            directory = BENCH / task["id"] / arm
            (directory / ".opencode" / "agents").mkdir(parents=True, exist_ok=True)
            (directory / "context.md").write_text(text, encoding="utf-8")
            (directory / ".opencode" / "agents" / "context-only.md").write_text(
                AGENT, encoding="utf-8")
        record = dict(task)
        record["sieve_tokens"] = tokenizer.count(context)
        record["sieve_files"] = [chunk["file"] for _, chunk in ranked]
        record["layers"] = layers
        manifest["tasks"].append(record)
        print(f'{task["id"]} full={manifest["full_tokens"]} '
              f'sieve={record["sieve_tokens"]} files={len(record["sieve_files"])}')
    (BENCH / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print("wrote", BENCH / "manifest.json")


if __name__ == "__main__":
    main()
