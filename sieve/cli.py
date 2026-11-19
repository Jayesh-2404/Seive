"""Command line interface: index, query, read, compress, original, stats, memory, mcp."""
import argparse
import json
import os
import sys
from pathlib import Path

from . import __version__
from .allocator import allocate
from .composer import compose
from .compress import compress_text
from .config import DEFAULT_BUDGET, DEFAULT_TOP_K
from .index import index_repo
from .memory import Memory
from .read import read_file
from .retrieval import hybrid_retrieve
from .store import STORE, cache_root, event_stats, log_event
from .summarize import default_provider, summarize_file


def _read_input(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8", errors="ignore")


def _relative(root: Path, file: str) -> str:
    path = Path(file)
    if path.is_absolute():
        return path.resolve().relative_to(root).as_posix()
    return path.as_posix()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="sieve", description="Compress repository context for coding agents")
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    index_parser = subparsers.add_parser("index", help="index a repository")
    index_parser.add_argument("repo", nargs="?", default=".")

    query_parser = subparsers.add_parser("query", help="compose a context prompt")
    query_parser.add_argument("task")
    query_parser.add_argument("--repo", default=".")
    query_parser.add_argument("--budget", type=int, default=DEFAULT_BUDGET)
    query_parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    query_parser.add_argument("--learned", action="store_true")
    query_parser.add_argument("--vectors", action="store_true")
    query_parser.add_argument("--json", action="store_true")

    read_parser = subparsers.add_parser("read", help="read a file or one symbol")
    read_parser.add_argument("file")
    read_parser.add_argument("--repo", default=".")
    read_parser.add_argument("--symbol", default="")
    read_parser.add_argument("--budget", type=int, default=1200)
    read_parser.add_argument("--json", action="store_true")

    summarize_parser = subparsers.add_parser("summarize", help="summarize one file")
    summarize_parser.add_argument("file")
    summarize_parser.add_argument("--repo", default=".")
    summarize_parser.add_argument("--max-tokens", type=int, default=120)
    summarize_parser.add_argument("--json", action="store_true")

    compress_parser = subparsers.add_parser("compress", help="compress tool output")
    compress_parser.add_argument("path", nargs="?", default="-")
    compress_parser.add_argument("--kind", default="auto")
    compress_parser.add_argument("--budget", type=int, default=800)
    compress_parser.add_argument("--json", action="store_true")

    original_parser = subparsers.add_parser("original", help="recover original text")
    original_parser.add_argument("ref")
    original_parser.add_argument("--start", type=int, default=None)
    original_parser.add_argument("--end", type=int, default=None)

    subparsers.add_parser("stats", help="show recorded token savings")

    init_parser = subparsers.add_parser("init", help="install the MCP server and commands")
    init_parser.add_argument("--dry-run", action="store_true")
    init_parser.add_argument("--force", action="store_true")

    memory_parser = subparsers.add_parser("memory", help="show or record memory")
    memory_parser.add_argument("--note", default="")
    memory_parser.add_argument("--limit", type=int, default=5)

    subparsers.add_parser("mcp", help="run the MCP server over stdio")

    args = parser.parse_args(argv)

    if args.command == "mcp":
        from .server.mcp import main as run_server
        run_server()
        return 0

    if args.command == "init":
        from .install import init
        print(json.dumps(init(dry_run=args.dry_run, force=args.force), indent=2))
        return 0

    if args.command == "memory":
        memory = Memory(path=os.getenv("SIEVE_MEMORY_DIR",
                                       str(cache_root() / "memory")))
        if args.note:
            memory.log(args.note, [], note=args.note)
        print(json.dumps({"notes": memory.notes(),
                          "recent": memory.recent(args.limit)}, indent=2))
        return 0

    if args.command == "compress":
        result = compress_text(_read_input(args.path), args.budget, args.kind)
        log_event("compress", result["tokens_before"], result["tokens_after"],
                  kind=result["kind"], ref=result["ref"])
        print(json.dumps(result, indent=2) if args.json else result["text"])
        return 0

    if args.command == "original":
        try:
            print(STORE.get(args.ref, args.start, args.end))
        except (ValueError, KeyError) as exc:
            print(json.dumps({"error": str(exc), "ref": args.ref}))
            return 1
        return 0

    if args.command == "stats":
        print(json.dumps(event_stats(), indent=2))
        return 0

    root = Path(args.repo).resolve()
    index = index_repo(root)

    if args.command == "index":
        print(json.dumps({
            "repo": str(root),
            "files": len(index["files"]),
            "symbols": len(index["symbols"]),
            "edges": len(index["edges"]),
            "total_tokens": index["total_tokens"],
            "skipped": index["skipped"],
        }, indent=2))
        return 0

    if args.command == "read":
        try:
            rel = _relative(root, args.file)
            result = read_file(root, rel, index, args.symbol or None, args.budget)
        except (ValueError, FileNotFoundError) as exc:
            print(json.dumps({"error": str(exc)}))
            return 1
        log_event("read", result["tokens_before"], result["tokens_after"],
                  kind=result["kind"], ref=result["ref"])
        print(json.dumps(result, indent=2) if args.json else result["text"])
        return 0

    if args.command == "summarize":
        try:
            rel = _relative(root, args.file)
        except ValueError as exc:
            print(json.dumps({"error": str(exc)}))
            return 1
        entry = next((item for item in index["files"] if item["file"] == rel), None)
        if entry is None:
            print(json.dumps({"error": f"{rel} is not in the index"}))
            return 1
        summary = summarize_file(entry, index, max_tokens=args.max_tokens)
        payload = {"file": rel, "summary": summary,
                   "provider": bool(default_provider())}
        print(json.dumps(payload, indent=2) if args.json else summary)
        return 0

    allocation = allocate(args.task, args.budget, index["total_tokens"],
                          learned=args.learned)
    vector_index = None
    if args.vectors:
        try:
            from .embeddings import VectorIndex
            vector_index = VectorIndex().build(index)
        except Exception as exc:
            print(f"vectors unavailable: {exc}", file=sys.stderr)
    ranked, meta = hybrid_retrieve(args.task, index, top_k=args.top_k,
                                    vectors=vector_index)
    prompt, layers = compose(args.task, index, ranked, allocation, args.budget)
    if args.json:
        print(json.dumps({
            "prompt": prompt,
            "layers": layers,
            "alloc": allocation,
            "files": [chunk["file"] for _, chunk in ranked],
            "method": meta["method"],
        }, indent=2))
    else:
        print(prompt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
