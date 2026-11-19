"""Sieve MCP server.

OpenCode starts this process over stdio from the project directory. The first
tool call indexes the working directory and the index is reused for a short TTL
or until a refresh is requested. Tools keep every original so a compressed
result can be expanded again.
"""
import os
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from mcp.server.mcpserver import MCPServer

from .. import tokenizer
from ..allocator import allocate
from ..composer import compose
from ..compress import compress_text
from ..config import DEFAULT_BUDGET, DEFAULT_TOP_K
from ..index import index_repo
from ..memory import Memory
from ..models import RepositoryIndex
from ..read import read_file
from ..retrieval import hybrid_retrieve
from ..store import STORE, cache_root, event_stats, log_event

INDEX_TTL_SECONDS = 30.0

INSTRUCTIONS = """Sieve decides which repository context you should read.
Call the index tool once for the project. Before opening a file, call the read
tool with the path and, when known, the symbol name. For noisy output such as
logs, test results, JSON or CSV, call the compress tool. Both keep the original,
and the original tool returns it by ref. Prefer the files returned by the query
tool. Do not read files outside that set unless the context is insufficient.
Use the memory tool to record decisions and failures. The query tool includes
recent turns in its memory layer."""

server = MCPServer("sieve", version="0.5.0", instructions=INSTRUCTIONS)
_memory = Memory(path=os.getenv("SIEVE_MEMORY_DIR", str(cache_root() / "memory")))


@dataclass
class _State:
    index: RepositoryIndex | None = None
    repo: str | None = None
    indexed_at: float = 0.0
    vectors: object | None = None
    vectors_repo: str | None = None


_state = _State()
_state_lock = threading.Lock()


def _is_fresh(root: str) -> bool:
    return (_state.index is not None and _state.repo == root
            and time.time() - _state.indexed_at < INDEX_TTL_SECONDS)


def _ensure(repo: str | None = None, refresh: bool = False) -> tuple[str, RepositoryIndex]:
    target = repo or _state.repo or "."
    root = str(Path(target).resolve())
    if not refresh and _is_fresh(root):
        assert _state.index is not None
        return root, _state.index
    with _state_lock:
        if refresh or not _is_fresh(root):
            _state.index = index_repo(root)
            _state.repo = root
            _state.indexed_at = time.time()
    assert _state.index is not None
    return root, _state.index


@server.tool(name="index")
def sieve_index(repo: str = ".", refresh: bool = False) -> dict:
    """Index a repository and return file, symbol and edge counts."""
    try:
        root, index = _ensure(repo, refresh)
    except Exception as exc:
        return {"error": str(exc)}
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
                top_k: int = DEFAULT_TOP_K, learned: bool = False,
                vectors: bool = False) -> dict:
    """Return the smallest sufficient context for a task, under a token budget."""
    try:
        root, index = _ensure()
    except Exception as exc:
        return {"error": str(exc)}
    allocation = allocate(task, budget, index["total_tokens"], learned=learned)
    vector_index = None
    if vectors:
        try:
            from ..embeddings import VectorIndex
            if _state.vectors is None or _state.vectors_repo != root:
                _state.vectors = VectorIndex().build(index)
                _state.vectors_repo = root
            vector_index = _state.vectors
        except Exception as exc:
            return {"error": f"vectors unavailable: {exc}"}
    ranked, meta = hybrid_retrieve(task, index, top_k=top_k, vectors=vector_index)
    prompt, layers = compose(task, index, ranked, allocation, budget,
                             memory_turns=_memory.recent(4))
    files = [chunk["file"] for _, chunk in ranked]
    _memory.log(task, files, note=f"query: {task[:120]}")
    log_event("query", index["total_tokens"], layers["total"], kind="query")
    return {
        "repo": root,
        "prompt": prompt,
        "layers": layers,
        "alloc": allocation,
        "files": files,
        "method": meta["method"],
    }


@server.tool(name="read")
def sieve_read(file: str, symbol: str = "", budget: int = 1200) -> dict:
    """Return a file map and the requested symbol code, under a token budget."""
    try:
        root, index = _ensure()
        result = read_file(root, file, index, symbol or None, budget)
    except Exception as exc:
        return {"error": str(exc)}
    log_event("read", result["tokens_before"], result["tokens_after"],
              kind=result["kind"], ref=result["ref"])
    return result


@server.tool(name="compress")
def sieve_compress(text: str, kind: str = "auto", budget: int = 800) -> dict:
    """Compress noisy tool output to a token budget. The original stays available."""
    result = compress_text(text, budget, kind)
    log_event("compress", result["tokens_before"], result["tokens_after"],
              kind=result["kind"], ref=result["ref"])
    return result


@server.tool(name="original")
def sieve_original(ref: str, start_line: int | None = None,
                   end_line: int | None = None) -> dict:
    """Return the original text behind a ref, optionally as a line range."""
    try:
        text = STORE.get(ref, start_line, end_line)
    except (ValueError, KeyError) as exc:
        return {"error": str(exc), "ref": ref}
    return {"ref": ref, "text": text, "tokens": tokenizer.count(text)}


@server.tool(name="symbol")
def sieve_symbol(name: str) -> list[dict]:
    """Return definitions of a symbol from the current index."""
    try:
        _, index = _ensure()
    except Exception as exc:
        return [{"error": str(exc)}]
    return [symbol for symbol in index["symbols"] if symbol["symbol"] == name]


@server.tool(name="stats")
def sieve_stats() -> dict:
    """Return token savings recorded for read, compress and query calls."""
    return event_stats()


@server.tool(name="memory")
def sieve_memory(note: str = "") -> dict:
    """Return recent turns and notes. Pass a note to record a decision or failure."""
    if note.strip():
        _memory.log(note, [], note=note)
    return {"notes": _memory.notes(), "recent": _memory.recent(5)}


def main() -> None:
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
