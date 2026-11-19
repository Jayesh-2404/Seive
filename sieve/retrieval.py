"""BM25 retrieval (from scratch, no sklearn) + symbol bonus + call-graph expansion.

Algorithm:
  score(d,q) = sum_IDF * TF saturation (k1=1.2, b=0.75)   [Robertson & Sparck Jones]
           + 5.0 if query token exactly matches a symbol defined in d
           + 2.0 if query token matches an import of d
  Then 1-hop call-graph boost: files that define a callee called by a top-3
  file get +1.5. This is the code-structure awareness (vs plain RAG).
"""
import re, math, collections

TOKEN_RE = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*")
CAMEL_RE = re.compile(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|\d+")
K1, B = 1.2, 0.75
TEST_MARKERS = (".test.", ".spec.", "/test_", "test_", ".stories.")

def tokenize(text: str):
    out = []
    for raw in TOKEN_RE.findall(text):
        # split snake_case and camelCase so 'buildWorkItems' matches 'work'
        for part in raw.split("_"):
            if not part:
                continue
            out.append(part.lower())
            if any(c.isupper() for c in part[1:]):
                out.extend(m.lower() for m in CAMEL_RE.findall(part))
    return out

def _is_test(path: str):
    return any(m in path for m in TEST_MARKERS)

def build_stats(chunks):
    """Precompute doc lengths, avgdl, doc frequencies. chunks: file-level only."""
    doc_toks = [tokenize((c["file"] + " ") * 3 + c["text"][:3000]) for c in chunks]
    lens = [len(t) for t in doc_toks]
    avgdl = sum(lens) / max(1, len(lens))
    df = collections.Counter()
    tfs = []
    for toks in doc_toks:
        tf = collections.Counter(toks)
        tfs.append(tf)
        for t in set(tf):
            df[t] += 1
    return {"tfs": tfs, "df": df, "lens": lens, "avgdl": avgdl, "N": len(chunks)}

def bm25(query, chunks, stats):
    qt = tokenize(query)
    N = stats["N"]
    scores = []
    for i in range(N):
        s = 0.0
        dl = stats["lens"][i] or 1
        for t in qt:
            tf = stats["tfs"][i].get(t, 0)
            if not tf:
                continue
            idf = math.log(1 + (N - stats["df"].get(t, 0) + 0.5) / (stats["df"].get(t, 0) + 0.5))
            s += idf * (tf * (K1 + 1)) / (tf + K1 * (1 - B + B * dl / stats["avgdl"]))
        scores.append(s)
    return scores

def hybrid_retrieve(query, index, top_k=5, use_symbols=True, use_graph=True):
    """Returns ranked [(score, chunk, why)]. File-level chunks only."""
    file_chunks = [c for c in index["chunks"] if c["kind"] == "file"]
    stats = build_stats(file_chunks)
    scores = bm25(query, file_chunks, stats)
    qt = set(tokenize(query))
    exact_by_file, part_by_file, imps_by_file = {}, {}, {}
    for s in index["symbols"]:
        exact_by_file.setdefault(s["file"], set()).add(s["symbol"].lower())
        part_by_file.setdefault(s["file"], set()).update(tokenize(s["symbol"]))
    for f in index["files"]:
        imps_by_file[f["file"]] = set(i.lower().split(".")[0] for i in f["imports"])
    for i, c in enumerate(file_chunks):
        f = c["file"]
        if use_symbols and qt & exact_by_file.get(f, set()):
            scores[i] += 5.0
        elif qt & part_by_file.get(f, set()):
            scores[i] += 2.0
        if qt & imps_by_file.get(f, set()):
            scores[i] += 2.0
    # Tests describe runtime code but are not part of the runtime flow.
    for i, c in enumerate(file_chunks):
        if _is_test(c["file"]):
            scores[i] *= 0.3
    order = sorted(range(len(file_chunks)), key=lambda i: -scores[i])
    # call-graph 1-hop: callees of top-3 get boost, then re-sort ranks 4+
    if use_graph:
        top_files = [file_chunks[i]["file"] for i in order[:3]]
        callees = set()
        for e in index["edges"]:
            if e["file"] in top_files:
                callees.add(e["callee"].lower())
        boosted = set()
        for f, syms in part_by_file.items():
            if syms & callees and f not in top_files:
                boosted.add(f)
        for i, c in enumerate(file_chunks):
            if c["file"] in boosted:
                scores[i] += 1.5
        order = sorted(range(len(file_chunks)), key=lambda i: -scores[i])
    ranked = [(scores[i], file_chunks[i]) for i in order[:top_k]]
    return ranked, {"method": f"bm25(k1={K1},b={B})+symbol{'+graph' if use_graph else ''}",
                    "top_k": top_k}
