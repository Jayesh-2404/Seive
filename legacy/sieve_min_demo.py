"""
Sieve 30-35% vertical slice — minimal working prototype.
Input -> Index (AST symbols) -> Retrieve (lexical+TF-IDF) -> Budget (rule) -> Compose -> Log trace -> Eval

No DB, no network, no GPU. Stdlib only (+ optional tiktoken).
Run: python sieve_min_demo.py --repo ./sample_repo --budget 4000
Demo creates ./sample_repo if missing, indexes it, runs 3 sample tasks,
compares FULL-DUMP vs NAIVE-TRUNC vs SIEVE, writes traces/*.jsonl + results.csv
"""
import ast, argparse, json, os, re, time, uuid, hashlib, collections, math, csv, sys
from pathlib import Path

def count_tokens(text: str) -> int:
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        return max(1, len(text) // 4)  # ~4 chars/token fallback, label as approx

def parse_py_file(path: Path):
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception as e:
        return [], [], str(e)
    funcs, classes = [], []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            try: src = ast.get_source_segment(path.read_text(encoding="utf-8", errors="ignore"), node) or ""
            except Exception: src = ""
            funcs.append({"name": node.name, "lineno": node.lineno, "code": src[:2000]})
        elif isinstance(node, ast.ClassDef):
            funcs.append({"name": node.name, "lineno": node.lineno, "code": f"class {node.name}"})
            classes.append(node.name)
    imports = re.findall(r"^(?:import|from)\s+(\S+)", path.read_text(encoding="utf-8", errors="ignore"), re.M)
    return funcs, imports, None

def index_repo(repo: Path):
    symbols, chunks = [], []
    for py in sorted(repo.rglob("*.py")):
        if ".venv" in str(py) or "__pycache__" in str(py): continue
        funcs, imports, err = parse_py_file(py)
        rel = str(py.relative_to(repo))
        text = py.read_text(encoding="utf-8", errors="ignore")
        toks = count_tokens(text)
        for f in funcs:
            symbols.append({"file": rel, "symbol": f["name"], "line": f["lineno"], "tokens": count_tokens(f["code"])})
        chunks.append({"file": rel, "tokens": toks, "text": text[:6000], "symbols": [f["name"] for f in funcs]})
    return symbols, chunks

TOKEN_RE = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*")
def tf_idf_scores(query, docs):
    qt = TOKEN_RE.findall(query.lower())
    N = len(docs)
    df = collections.Counter()
    doc_tfs = []
    for d in docs:
        toks = TOKEN_RE.findall((d["file"] + " " + " ".join(d["symbols"]) + " " + d["text"][:2000]).lower())
        tf = collections.Counter(toks)
        doc_tfs.append(tf)
        for t in set(tf): df[t] += 1
    scores = []
    for tf in doc_tfs:
        s = sum(tf.get(t, 0) * math.log((N + 1) / (df.get(t, 1))) for t in qt)
        scores.append(s)
    # exact symbol bonus (hybrid: lexical exact + semantic-ish TF-IDF)
    for i, d in enumerate(docs):
        if any(q in d["symbols"] for q in qt): scores[i] += 5.0
    return scores

TASK_TYPES = {
    "bug_fix": {"symbols": 0.45, "semantic": 0.35, "summary": 0.10, "memory": 0.10},
    "feature": {"symbols": 0.30, "semantic": 0.50, "summary": 0.10, "memory": 0.10},
    " perf":   {"symbols": 0.15, "semantic": 0.35, "summary": 0.40, "memory": 0.10},
    "question": {"symbols": 0.25, "semantic": 0.35, "summary": 0.30, "memory": 0.10},
}
def classify_task(q: str) -> str:
    ql = q.lower()
    if any(w in ql for w in ["fix", "bug", "error", "exception", "traceback"]): return "bug_fix"
    if any(w in ql for w in ["add", "implement", "feature", "create"]): return "feature"
    if any(w in ql for w in ["slow", "perf", "optim", "latency"]): return " perf".strip()
    return "question"

def compose(symbols, chunks, query, budget: int):
    t0 = time.time()
    trace_id = uuid.uuid4().hex[:8]
    task_type = classify_task(query)
    split = TASK_TYPES[task_type]
    scores = tf_idf_scores(query, chunks)
    ranked = sorted(zip(scores, chunks), key=lambda x: -x[0])
    # Layer budgets
    b_sym = int(budget * split["symbols"]); b_sem = int(budget * split["semantic"])
    b_sum = int(budget * split["summary"]); b_mem = budget - b_sym - b_sem - b_sum
    # L1 symbols: cheap, always resident
    sym_text = "\n".join(f'{s["file"]}:{s["line"]} {s["symbol"]}' for s in symbols[:80])
    sym_toks = count_tokens(sym_text)
    # L2 semantic: top-k chunks until b_sem fills
    picked, used = [], 0
    for score, c in ranked:
        t = min(c["tokens"], count_tokens(c["text"]))
        if used + t > b_sem and picked: break
        picked.append((score, c)); used += t
        if len(picked) >= 5: break
    sem_text = "\n\n".join(f'# {c["file"]}\n{c["text"][:1500]}' for _, c in picked)
    # L3 summary: one-line per non-picked file (extractive, no LLM — honest baseline)
    rest = [c for c in chunks if c not in [p[1] for p in picked]][:10]
    sum_text = "\n".join(f'{c["file"]}: defines {", ".join(c["symbols"][:6])} ({c["tokens"]} toks)' for c in rest)
    sum_text = sum_text[:b_sum * 4]
    total = sym_toks + count_tokens(sem_text) + count_tokens(sum_text)
    prompt = f"QUERY: {query}\nTASK_TYPE: {task_type}\n\n[SYMBOLS]\n{sym_text}\n\n[RETRIEVED]\n{sem_text}\n\n[SUMMARIES]\n{sum_text}\n"
    # enforce ceiling (raw-working-context rule simplified: truncate summaries first, then semantic)
    while count_tokens(prompt) > budget and sum_text:
        sum_text = sum_text[:int(len(sum_text) * 0.8)]
        prompt = f"QUERY: {query}\nTASK_TYPE: {task_type}\n\n[SYMBOLS]\n{sym_text}\n\n[RETRIEVED]\n{sem_text}\n\n[SUMMARIES]\n{sum_text}\n"
    trace = {
        "trace_id": trace_id, "query": query, "task_type": task_type,
        "budget": budget, "split": split,
        "retrieval": [{"file": c["file"], "score": round(float(s), 2)} for s, c in picked],
        "tokens": {"symbols": sym_toks, "semantic": count_tokens(sem_text),
                   "summary": count_tokens(sum_text), "total": count_tokens(prompt)},
        "latency_ms": int((time.time() - t0) * 1000),
        "prompt_hash": hashlib.sha256(prompt.encode()).hexdigest()[:12],
    }
    return prompt, trace

def ensure_sample_repo(repo: Path):
    repo.mkdir(parents=True, exist_ok=True)
    (repo / "auth.py").write_text('''"""Auth middleware sample."""\nimport hashlib\ndef hash_pw(pw: str) -> str:\n    return hashlib.sha256(pw.encode()).hexdigest()\n\ndef check_auth(token: str, store: dict) -> bool:\n    # BUG: KeyError when token missing\n    return store[token] == "active"\n\nclass Session:\n    def __init__(self): self.data = {}\n    def login(self, user): self.data[user] = "active"\n''')
    (repo / "api.py").write_text('''"""API layer."""\nfrom auth import check_auth, Session\ndef handle_request(token, store):\n    if check_auth(token, store): return {"ok": True}\n    return {"ok": False, "error": "unauthorized"}\n\ndef add(a, b): return a + b\n''')
    (repo / "db.py").write_text('''"""DB helpers."""\ndef get_user(uid, conn):\n    cur = conn.cursor()\n    cur.execute("SELECT * FROM users WHERE id=?", (uid,))\n    return cur.fetchone()\n''')

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="./sample_repo")
    ap.add_argument("--budget", type=int, default=4000)
    args = ap.parse_args()
    repo = Path(args.repo); ensure_sample_repo(repo)
    symbols, chunks = index_repo(repo)
    full_text = "\n\n".join(c["text"] for c in chunks)
    full_toks = count_tokens(full_text)
    tasks = [
        "Fix KeyError in check_auth when token is missing",
        "Where is auth validated? What calls check_auth?",
        "Add logout that removes user from Session",
    ]
    Path("traces").mkdir(exist_ok=True)
    rows = []
    for q in tasks:
        prompt, trace = compose(symbols, chunks, q, args.budget)
        # baselines
        trunc = full_text[:args.budget * 4]
        row = {"task": q[:50], "full_tokens": full_toks,
               "trunc_tokens": count_tokens(trunc), "sieve_tokens": trace["tokens"]["total"],
               "saving_vs_full_pct": round(100 * (1 - trace["tokens"]["total"] / max(1, full_toks)), 1),
               "trace_id": trace["trace_id"], "task_type": trace["task_type"],
               "latency_ms": trace["latency_ms"]}
        rows.append(row)
        Path(f'traces/{trace["trace_id"]}.json').write_text(json.dumps({**trace, "prompt_preview": prompt[:2000]}, indent=1))
        print(f'[{trace["task_type"]}] sieve={trace["tokens"]["total"]} toks vs full={full_toks} (save {row["saving_vs_full_pct"]}%) latency={trace["latency_ms"]}ms')
    with open("results.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print(f"\nWrote {len(rows)} traces/ to traces/ + results.csv")
    print("NOTE: success% not claimed here — needs model calls + hidden tests (see experiments/experiment_plan.md E02).")

if __name__ == "__main__":
    main()
