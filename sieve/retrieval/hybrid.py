"""Hybrid ranking: BM25 plus the code-structure boosts."""
from ..models import RepositoryIndex
from .bm25 import K1, B, bm25, build_stats, tokenize

TEST_MARKERS = (".test.", ".spec.", "/test_", "test_", ".stories.")


def _is_test(path: str) -> bool:
    return any(marker in path for marker in TEST_MARKERS)


def hybrid_retrieve(
    query: str,
    index: RepositoryIndex,
    top_k: int = 5,
    use_symbols: bool = True,
    use_graph: bool = True,
) -> tuple[list[tuple[float, dict]], dict]:
    """Rank file chunks. Returns [(score, chunk, why)], file-level only."""
    file_chunks = [chunk for chunk in index["chunks"] if chunk["kind"] == "file"]
    stats = build_stats(file_chunks)
    scores = bm25(query, file_chunks, stats)
    query_tokens = set(tokenize(query))

    exact_by_file: dict[str, set[str]] = {}
    part_by_file: dict[str, set[str]] = {}
    imports_by_file: dict[str, set[str]] = {}
    for symbol in index["symbols"]:
        file = symbol["file"]
        exact_by_file.setdefault(file, set()).add(symbol["symbol"].lower())
        part_by_file.setdefault(file, set()).update(tokenize(symbol["symbol"]))
    for entry in index["files"]:
        imports_by_file[entry["file"]] = {
            imported.lower().split(".")[0] for imported in entry["imports"]}

    for i, chunk in enumerate(file_chunks):
        file = chunk["file"]
        if use_symbols and query_tokens & exact_by_file.get(file, set()):
            scores[i] += 5.0
        elif query_tokens & part_by_file.get(file, set()):
            scores[i] += 2.0
        if query_tokens & imports_by_file.get(file, set()):
            scores[i] += 2.0

    # Tests describe runtime code but are not part of the runtime flow.
    for i, chunk in enumerate(file_chunks):
        if _is_test(chunk["file"]):
            scores[i] *= 0.3

    order = sorted(range(len(file_chunks)), key=lambda i: -scores[i])
    if use_graph:
        top_files = [file_chunks[i]["file"] for i in order[:3]]
        callees = {edge["callee"].lower()
                   for edge in index["edges"] if edge["file"] in top_files}
        boosted = {
            file for file, names in part_by_file.items()
            if names & callees and file not in top_files
        }
        for i, chunk in enumerate(file_chunks):
            if chunk["file"] in boosted:
                scores[i] += 1.5
        order = sorted(range(len(file_chunks)), key=lambda i: -scores[i])

    ranked = [(scores[i], file_chunks[i]) for i in order[:top_k]]
    method = f"bm25(k1={K1},b={B})+symbol{'+graph' if use_graph else ''}"
    return ranked, {"method": method, "top_k": top_k}
