"""Compose final prompt strictly under token ceiling.

Order (correctness-first): symbols (never cut) -> retrieved top-k ->
summaries (cut first) -> memory (cut second). If bypass, return full dump.
Summaries are extractive one-liners (no LLM in v0) that preserve identifiers:
  'path: defines f,g (N toks) | calls h'
"""
from . import tokenizer

def summarize_file(entry, index):
    syms = [s["symbol"] for s in index["symbols"] if s["file"] == entry["file"]][:8]
    callees = sorted({e["callee"] for e in index["edges"] if e["file"] == entry["file"]})[:6]
    return (f'{entry["file"]}: defines {", ".join(syms) or "-"} '
            f'({entry["tokens"]} toks) | calls {", ".join(callees) or "-"}')

def compose(query, index, ranked, alloc, budget, memory_turns=None):
    if alloc.get("bypass"):
        texts = [c["text"] for c in index["chunks"] if c["kind"] == "file"]
        prompt = f"QUERY: {query}\nMODE: FULL (repo fits budget)\n\n" + "\n\n".join(
            f"# {c['file']}\n{c['text'][:4000]}" for c in
            [c for c in index["chunks"] if c["kind"] == "file"])
        return prompt, {"mode": "full_bypass", "total": tokenizer.count(prompt)}
    toks = alloc["tokens"]
    sym_lines = [f'{s["file"]}:{s["line"]} {s["symbol"]}({s["kind"]})'
                 for s in index["symbols"][:100]]
    sym_text = "\n".join(sym_lines)
    picked_files = [c["file"] for _, c in ranked]
    sem_parts, used = [], 0
    for score, c in ranked:
        t = tokenizer.count(c["text"][:2000])
        if used + t > toks["semantic"] and sem_parts:
            break
        sem_parts.append(f'# {c["file"]} [score={score:.2f}]\n{c["text"][:2000]}')
        used += t
    rest = [f for f in index["files"] if f["file"] not in picked_files][:12]
    sum_text = "\n".join(summarize_file(f, index) for f in rest)
    sum_text = tokenizer.truncate(sum_text, toks["summary"])
    mem_text = ""
    if memory_turns:
        mem_text = "\n".join(f"- {m['q'][:120]} -> {m['note'][:160]}"
                             for m in memory_turns[-2:])
        mem_text = tokenizer.truncate(mem_text, toks["memory"])
    prompt = (f"QUERY: {query}\nTASK: {alloc['task_type']} (conf {alloc['confidence']:.2f})\n\n"
              f"[SYMBOLS:{tokenizer.count(sym_text)}t]\n{sym_text}\n\n"
              f"[RETRIEVED:{tokenizer.count(chr(10).join(sem_parts))}t]\n{chr(10).join(sem_parts)}\n\n"
              f"[SUMMARIES]\n{sum_text}\n\n[MEMORY]\n{mem_text}\n")
    # enforce ceiling: cut summaries, then memory, never symbols first
    while tokenizer.count(prompt) > budget and (sum_text or mem_text):
        if sum_text:
            sum_text = sum_text[:int(len(sum_text) * 0.7)]
        elif mem_text:
            mem_text = mem_text[:int(len(mem_text) * 0.7)]
        prompt = (f"QUERY: {query}\nTASK: {alloc['task_type']}\n\n[SYMBOLS]\n{sym_text}\n\n"
                  f"[RETRIEVED]\n{chr(10).join(sem_parts)}\n\n[SUMMARIES]\n{sum_text}\n\n[MEMORY]\n{mem_text}\n")
    layers = {"symbols": tokenizer.count(sym_text),
              "semantic": tokenizer.count(chr(10).join(sem_parts)),
              "summary": tokenizer.count(sum_text), "memory": tokenizer.count(mem_text),
              "total": tokenizer.count(prompt)}
    return prompt, layers
