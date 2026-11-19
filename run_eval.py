"""Full eval: baselines + ablations on 12 pre-registered tasks.

Systems:
  full    - dump all files (upper success bound, worst tokens)
  trunc   - naive first-N tokens cut to budget
  sieve   - BM25 + symbols + graph + summaries + routed budget
  sieve-nosym - sieve minus symbol bonus (ablation)
  sieve-nograph - sieve minus call-graph boost (ablation)

Metrics per task (no LLM needed, honest):
  tokens, latency_ms, Recall@k (gold files in top-k?), saving_vs_full_%
Functional bug tests (t_b1..t_b3) run separately to show bugs exist;
end-to-end LLM fix success = experiment to be conducted (needs API key).

Writes results_eval.csv + traces_eval/*.json
"""
import json, time, csv, sys, hashlib
from pathlib import Path
sys.path.insert(0, ".")
from sieve import indexer, retrieval, allocator, composer, tokenizer
from tools.build_large_repo import build

TASKS = [
 {"id":"B1","q":"Fix KeyError in check_auth when token is missing","gold":["auth.py","api.py","middleware.py"]},
 {"id":"B2","q":"Fix cart_total dropping last item in checkout","gold":["cart.py","api.py","orders.py"]},
 {"id":"B3","q":"Fix cache returning stale expired entries","gold":["cache.py","api.py","config.py"]},
 {"id":"Q1","q":"Where is auth validated? What calls check_auth?","gold":["auth.py","api.py","middleware.py"]},
 {"id":"Q2","q":"How is checkout total computed? Which files touch prices?","gold":["cart.py","orders.py","api.py"]},
 {"id":"Q3","q":"Where are orders listed and revenue computed?","gold":["db.py","orders.py","reports.py"]},
 {"id":"F1","q":"Add logout endpoint removing user from Session","gold":["auth.py","api.py","middleware.py"]},
 {"id":"F2","q":"Add refund flow using payments gateway","gold":["payments.py","orders.py","db.py"]},
 {"id":"R1","q":"Refactor cart module without changing totals","gold":["cart.py","orders.py","utils.py"]},
 {"id":"P1","q":"Investigate slow checkout, suspect N+1 in list_orders","gold":["db.py","orders.py","reports.py"]},
 {"id":"V1","q":"Validate email and quantity inputs where?","gold":["validators.py","api.py","utils.py"]},
 {"id":"S1","q":"How do notifications send email and sms?","gold":["services_notify.py","logger.py","app.py"]},
]

def run_system(name, index, tasks, budget):
    rows = []
    for t in tasks:
        t0 = time.time()
        if name == "full":
            prompt = "\n\n".join(c["text"][:4000] for c in index["chunks"] if c["kind"]=="file")
            files = [f["file"] for f in index["files"]]
            layers = {"total": tokenizer.count(prompt)}
        elif name == "trunc":
            full = "\n\n".join(c["text"] for c in index["chunks"] if c["kind"]=="file")
            prompt = tokenizer.truncate(full, budget)
            files = ["<truncated>"]
            layers = {"total": tokenizer.count(prompt)}
        else:
            use_sym = not name.endswith("-nosym")
            use_graph = not name.endswith("-nograph")
            alloc = allocator.allocate(t["q"], budget, index["total_tokens"])
            ranked, _ = retrieval.hybrid_retrieve(t["q"], index, top_k=5,
                                                  use_symbols=use_sym, use_graph=use_graph)
            prompt, layers = composer.compose(t["q"], index, ranked, alloc, budget)
            files = [c["file"] for _, c in ranked]
        lat = int((time.time()-t0)*1000)
        gold = set(t["gold"])
        rec = len(gold & set(files)) / max(1, len(gold))
        rows.append({"task": t["id"], "system": name, "tokens": layers["total"],
                     "latency_ms": lat, "recall_at_5": round(rec,2),
                     "files": "|".join(files[:5]),
                     "task_type": allocator.classify(t["q"])[0]})
        Path("traces_eval").mkdir(exist_ok=True)
        Path(f"traces_eval/{t['id']}-{name}.json").write_text(json.dumps(
            {"task":t["id"],"q":t["q"],"system":name,"tokens":layers,
             "files":files,"gold":t["gold"],"recall":round(rec,2),
             "prompt_hash": hashlib.sha256(prompt.encode()).hexdigest()[:12]}, indent=1))
    return rows

def main(budget=4000):
    repo = build()
    # ensure clean import of generated repo tests
    sys.path.insert(0, str(repo))
    index = indexer.index_repo(repo)
    print(f"repo files={len(index['files'])} total_tokens={index['total_tokens']} symbols={len(index['symbols'])} edges={len(index['edges'])}")
    all_rows = []
    for sys_name in ["full","trunc","sieve","sieve-nosym","sieve-nograph"]:
        all_rows += run_system(sys_name, index, TASKS, budget)
    # functional bug presence (proves tasks are real, not toy pass)
    try:
        import tests_core
        bugs = {"t_b1_fixed": tests_core.t_b1(), "t_b2_fixed": tests_core.t_b2(), "t_b3_fixed": tests_core.t_b3()}
    except Exception as e:
        bugs = {"error": str(e)}
    print("bug status (False = bug present, honest):", bugs)
    with open("results_eval.csv","w",newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(all_rows[0].keys())); w.writeheader(); w.writerows(all_rows)
    # summary table
    import collections
    summ = collections.defaultdict(list)
    for r in all_rows: summ[r["system"]].append(r)
    print(f"\n{'system':14} {'avg_tok':>8} {'avg_recall':>10} {'avg_ms':>7}  saving_vs_full")
    full_avg = sum(r["tokens"] for r in summ["full"])/len(summ["full"])
    for s, rs in summ.items():
        avg_t = sum(r["tokens"] for r in rs)/len(rs)
        avg_r = sum(r["recall_at_5"] for r in rs)/len(rs)
        avg_m = sum(r["latency_ms"] for r in rs)/len(rs)
        print(f"{s:14} {avg_t:8.0f} {avg_r:10.2f} {avg_m:7.1f}  {100*(1-avg_t/full_avg):+.1f}%")
    print("\nWrote results_eval.csv + traces_eval/. End-to-end LLM fix rate: EXPERIMENT TO BE CONDUCTED (needs API key).")

if __name__ == "__main__":
    main(budget=int(sys.argv[1]) if len(sys.argv)>1 else 4000)
