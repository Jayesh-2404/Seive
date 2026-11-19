"""MCP stdio server stub: exposes Sieve as tools any agent can call.

Tools:
  index(repo)            -> files, symbols, total_tokens
  query(q, budget=600)   -> prompt, layers, files, trace
  get_symbol(name)       -> definitions
Protocol: JSON-RPC per line on stdin/stdout (MCP-compatible subset).
Full MCP SDK wiring is Milestone-2; this stub proves the contract today.
"""
import json, sys
from pathlib import Path
sys.path.insert(0, ".")
from sieve import indexer, retrieval, allocator, composer

INDEX = {"index": None, "repo": None}

def handle(req):
    m, p = req.get("method"), req.get("params", {})
    if m == "index":
        idx = indexer.index_repo(Path(p["repo"]))
        INDEX["index"], INDEX["repo"] = idx, p["repo"]
        return {"files": len(idx["files"]), "symbols": len(idx["symbols"]),
                "edges": len(idx["edges"]), "total_tokens": idx["total_tokens"]}
    if m == "query":
        idx = INDEX["index"]
        if idx is None:
            return {"error": "call index first"}
        budget = int(p.get("budget", 600))
        alloc = allocator.allocate(p["q"], budget, idx["total_tokens"])
        ranked, meta = retrieval.hybrid_retrieve(p["q"], idx, top_k=int(p.get("top_k", 8)))
        prompt, layers = composer.compose(p["q"], idx, ranked, alloc, budget)
        return {"prompt": prompt, "layers": layers, "alloc": alloc,
                "files": [c["file"] for _, c in ranked], "method": meta["method"]}
    if m == "get_symbol":
        idx = INDEX["index"]
        return [s for s in idx["symbols"] if s["symbol"] == p["name"]] if idx else []
    return {"error": f"unknown method {m}"}

if __name__ == "__main__":
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            print(json.dumps({"id": req.get("id"), "result": handle(req)}), flush=True)
        except Exception as e:
            print(json.dumps({"error": str(e)}), flush=True)
