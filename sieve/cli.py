"""Command line interface: index, query, mcp."""
import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .allocator import allocate
from .composer import compose
from .config import DEFAULT_BUDGET, DEFAULT_TOP_K
from .index import index_repo
from .retrieval import hybrid_retrieve


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

    subparsers.add_parser("mcp", help="run the MCP server over stdio")

    args = parser.parse_args(argv)
    if args.command == "mcp":
        from .server.mcp import main as run_server
        run_server()
        return 0

    index = index_repo(Path(args.repo))
    if args.command == "index":
        print(json.dumps({
            "repo": str(Path(args.repo).resolve()),
            "files": len(index["files"]),
            "symbols": len(index["symbols"]),
            "edges": len(index["edges"]),
            "total_tokens": index["total_tokens"],
            "skipped": index["skipped"],
        }, indent=2))
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
