"""Command line interface: index, query, read, compress, original, stats, mcp."""
import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .allocator import allocate
from .composer import compose
from .compress import compress_text
from .config import DEFAULT_BUDGET, DEFAULT_TOP_K
from .index import index_repo
from .read import read_file
from .retrieval import hybrid_retrieve
from .store import STORE, event_stats, log_event


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
    query_parser.add_argument("--json", action="store_true")

    read_parser = subparsers.add_parser("read", help="read a file or one symbol")
    read_parser.add_argument("file")
    read_parser.add_argument("--repo", default=".")
    read_parser.add_argument("--symbol", default="")
    read_parser.add_argument("--budget", type=int, default=1200)
    read_parser.add_argument("--json", action="store_true")

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
    subparsers.add_parser("mcp", help="run the MCP server over stdio")

    args = parser.parse_args(argv)

    if args.command == "mcp":
        from .server.mcp import main as run_server
        run_server()
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

    allocation = allocate(args.task, args.budget, index["total_tokens"])
    ranked, meta = hybrid_retrieve(args.task, index, top_k=args.top_k)
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
