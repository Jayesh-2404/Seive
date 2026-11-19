"""FastAPI adapter over the same engine.

The MCP server is the agent path. This HTTP service is for scripts, dashboards
and a future hosted deployment. It uses the same index, retrieval, composer,
compressor and store.
"""
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from . import __version__, tokenizer
from .allocator import allocate
from .composer import compose
from .compress import compress_text
from .index import index_repo
from .read import read_file
from .retrieval import hybrid_retrieve
from .store import STORE, event_stats, log_event

app = FastAPI(title="Sieve", version=__version__)
_INDEX: dict = {"root": "", "index": None}
_VECTORS: dict = {}


def _get(repo: str):
    root = str(Path(repo).resolve())
    if _INDEX["index"] is None or _INDEX["root"] != root:
        try:
            _INDEX["index"] = index_repo(root)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        _INDEX["root"] = root
    return root, _INDEX["index"]


class IndexRequest(BaseModel):
    repo: str = "."


class QueryRequest(BaseModel):
    task: str
    repo: str = "."
    budget: int = 8000
    top_k: int = 8
    learned: bool = False
    vectors: bool = False


class ReadRequest(BaseModel):
    file: str
    repo: str = "."
    symbol: str | None = None
    budget: int = 1200


class CompressRequest(BaseModel):
    text: str
    kind: str = "auto"
    budget: int = 800


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": __version__}


@app.post("/index")
def index(request: IndexRequest) -> dict:
    root, index_data = _get(request.repo)
    return {
        "repo": root,
        "files": len(index_data["files"]),
        "symbols": len(index_data["symbols"]),
        "edges": len(index_data["edges"]),
        "total_tokens": index_data["total_tokens"],
        "skipped": index_data["skipped"],
    }


@app.post("/query")
def query(request: QueryRequest) -> dict:
    root, index_data = _get(request.repo)
    allocation = allocate(request.task, request.budget, index_data["total_tokens"],
                          learned=request.learned)
    vector_index = None
    if request.vectors:
        try:
            if root not in _VECTORS:
                from .embeddings import VectorIndex
                _VECTORS[root] = VectorIndex().build(index_data)
            vector_index = _VECTORS[root]
        except Exception as exc:
            raise HTTPException(status_code=400,
                                detail=f"vectors unavailable: {exc}") from exc
    ranked, meta = hybrid_retrieve(request.task, index_data,
                                    top_k=request.top_k, vectors=vector_index)
    prompt, layers = compose(request.task, index_data, ranked, allocation,
                             request.budget)
    log_event("query", index_data["total_tokens"], layers["total"], kind="query")
    return {
        "repo": root,
        "prompt": prompt,
        "layers": layers,
        "alloc": allocation,
        "files": [chunk["file"] for _, chunk in ranked],
        "method": meta["method"],
    }


@app.post("/read")
def read(request: ReadRequest) -> dict:
    root, index_data = _get(request.repo)
    try:
        result = read_file(root, request.file, index_data, request.symbol,
                           request.budget)
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    log_event("read", result["tokens_before"], result["tokens_after"],
              kind=result["kind"], ref=result["ref"])
    return result


@app.post("/compress")
def compress(request: CompressRequest) -> dict:
    result = compress_text(request.text, request.budget, request.kind)
    log_event("compress", result["tokens_before"], result["tokens_after"],
              kind=result["kind"], ref=result["ref"])
    return result


@app.get("/stats")
def stats() -> dict:
    return event_stats()


@app.get("/original/{ref}")
def original(ref: str, start: int | None = None, end: int | None = None) -> dict:
    try:
        text = STORE.get(ref, start, end)
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ref": ref, "text": text, "tokens": tokenizer.count(text)}


def run() -> None:
    import uvicorn
    uvicorn.run("sieve.http_server:app", host="127.0.0.1", port=8000)


if __name__ == "__main__":
    run()
