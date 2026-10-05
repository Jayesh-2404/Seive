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
K1, B = 1.2, 0.75

def tokenize(text: str):
    toks = TOKEN_RE.findall(text.lower())
    out = []
    for t in toks:  # split snake_case so 'check_auth' matches 'auth'
        out.append(t)
        if "_" in t:
            out.extend(x for x in t.split("_") if x)
    return out

def build_stats(chunks):
    """Precompute doc lengths, avgdl, doc frequencies. chunks: file-level only."""
    doc_toks = [tokenize(c["file"] + " " + c["text"][:3000]) for c in chunks]
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
    syms_by_file, imps_by_file = {}, {}
    for s in index["symbols"]:
        syms_by_file.setdefault(s["file"], set()).add(s["symbol"].lower())
    for f in index["files"]:
        imps_by_file[f["file"]] = set(i.lower().split(".")[0] for i in f["imports"])
    for i, c in enumerate(file_chunks):
        if use_symbols and (qt & syms_by_file.get(c["file"], set())):
            scores[i] += 5.0
        if qt & imps_by_file.get(c["file"], set()):
            scores[i] += 2.0
    order = sorted(range(len(file_chunks)), key=lambda i: -scores[i])
    # call-graph 1-hop: callees of top-3 get boost, then re-sort ranks 4+
    if use_graph:
        top_files = [file_chunks[i]["file"] for i in order[:3]]
        callees = set()
        for e in index["edges"]:
            if e["file"] in top_files:
                callees.add(e["callee"].lower())
        boosted = set()
        for f, syms in syms_by_file.items():
            if syms & callees and f not in top_files:
                boosted.add(f)
        for i, c in enumerate(file_chunks):
            if c["file"] in boosted:
                scores[i] += 1.5
        order = sorted(range(len(file_chunks)), key=lambda i: -scores[i])
    ranked = [(scores[i], file_chunks[i]) for i in order[:top_k]]
    return ranked, {"method": f"bm25(k1={K1},b={B})+symbol{'+graph' if use_graph else ''}",
                    "top_k": top_k}
