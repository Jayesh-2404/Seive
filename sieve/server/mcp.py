"""Sieve MCP server.

OpenCode starts this process over stdio from the project directory. The first
tool call indexes the working directory and the index is reused until a
refresh or a different repo is requested.
"""
from dataclasses import dataclass
from pathlib import Path

from mcp.server.mcpserver import MCPServer

from ..allocator import allocate
from ..composer import compose
from ..config import DEFAULT_BUDGET, DEFAULT_TOP_K
from ..index import index_repo
from ..models import RepositoryIndex
from ..retrieval import hybrid_retrieve

INSTRUCTIONS = """Sieve decides which repository context you should read.
Call the Sieve index tool once for the project, then the query tool before
opening files. Pass the user's task wording to the query tool. Prefer the files
it returns. If the answer needs more, query again with a narrower task or call
the symbol tool. Do not read files outside the returned set unless the returned
context is clearly insufficient."""

server = MCPServer("sieve", version="0.5.0", instructions=INSTRUCTIONS)


@dataclass
class _State:
    index: RepositoryIndex | None = None
    repo: str | None = None


_state = _State()


def _ensure(repo: str | None = None, refresh: bool = False) -> tuple[str, RepositoryIndex]:
    target = repo or _state.repo or "."
    root = str(Path(target).resolve())
    if refresh or _state.index is None or _state.repo != root:
        _state.index = index_repo(root)
        _state.repo = root
    return root, _state.index


@server.tool(name="index")
def sieve_index(repo: str = ".", refresh: bool = False) -> dict:
    """Index a repository and return file, symbol and edge counts."""
    root, index = _ensure(repo, refresh)
    return {
        "repo": root,
        "files": len(index["files"]),
        "symbols": len(index["symbols"]),
        "edges": len(index["edges"]),
        "total_tokens": index["total_tokens"],
        "skipped": index["skipped"],
    }


@server.tool(name="query")
def sieve_query(task: str, budget: int = DEFAULT_BUDGET,
                top_k: int = DEFAULT_TOP_K) -> dict:
    """Return the smallest sufficient context for a task, under a token budget."""
    root, index = _ensure()
    allocation = allocate(task, budget, index["total_tokens"])
    ranked, meta = hybrid_retrieve(task, index, top_k=top_k)
    prompt, layers = compose(task, index, ranked, allocation, budget)
    return {
        "repo": root,
        "prompt": prompt,
        "layers": layers,
        "alloc": allocation,
        "files": [chunk["file"] for _, chunk in ranked],
        "method": meta["method"],
    }


@server.tool(name="symbol")
def sieve_symbol(name: str) -> list[dict]:
    """Return definitions of a symbol from the current index."""
    _, index = _ensure()
    return [symbol for symbol in index["symbols"] if symbol["symbol"] == name]


def main() -> None:
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
