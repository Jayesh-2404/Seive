"""Compose final prompt strictly under token ceiling.

Order (correctness-first): symbols (cut last) -> retrieved top-k ->
summaries (cut first) -> memory (cut second). If bypass, return full dump.
Summaries are extractive one-liners (no LLM in v0) that preserve identifiers:
  'path: defines f,g (N toks) | calls h'
"""
from . import tokenizer

MEMORY_HEADER = "[MEMORY]"

def summarize_file(entry, index):
    syms = [s["symbol"] for s in index["symbols"] if s["file"] == entry["file"]][:8]
    callees = sorted({e["callee"] for e in index["edges"] if e["file"] == entry["file"]})[:6]
    return (f'{entry["file"]}: defines {", ".join(syms) or "-"} '
            f'({entry["tokens"]} toks) | calls {", ".join(callees) or "-"}')

def _assemble(query, alloc, sym_text, sem_parts, sum_text, mem_text, with_conf=True):
    task = alloc["task_type"] + (f" (conf {alloc['confidence']:.2f})" if with_conf else "")
    return (f"QUERY: {query}\nTASK: {task}\n\n"
            f"[SYMBOLS:{tokenizer.count(sym_text)}t]\n{sym_text}\n\n"
            f"[RETRIEVED:{tokenizer.count(chr(10).join(sem_parts))}t]\n{chr(10).join(sem_parts)}\n\n"
            f"[SUMMARIES]\n{sum_text}\n\n{MEMORY_HEADER}\n{mem_text}\n")

def compose(query, index, ranked, alloc, budget, memory_turns=None):
    if alloc.get("bypass"):
        file_chunks = [c for c in index["chunks"] if c["kind"] == "file"]
        prompt = f"QUERY: {query}\nMODE: FULL (repo fits budget)\n\n" + "\n\n".join(
            f"# {c['file']}\n{c['text'][:4000]}" for c in file_chunks)
        return prompt, {"mode": "full_bypass", "total": tokenizer.count(prompt)}
    toks = alloc["tokens"]
    picked_files = [c["file"] for _, c in ranked]
    ordered = [s for s in index["symbols"] if s["file"] in picked_files]
    ordered += [s for s in index["symbols"] if s["file"] not in picked_files]
    sym_lines, sym_used = [], 0
    for s in ordered:
        line = f'{s["file"]}:{s["line"]} {s["symbol"]}({s["kind"]})'
        t = tokenizer.count(line) + 1
        if sym_lines and sym_used + t > toks["symbols"]:
            break
        sym_lines.append(line)
        sym_used += t
    sym_text = "\n".join(sym_lines)
    sem_parts, used = [], 0
    for score, c in ranked:
        t = tokenizer.count(c["text"][:2000])
        if sem_parts and used + t > toks["semantic"]:
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
    prompt = _assemble(query, alloc, sym_text, sem_parts, sum_text, mem_text)
    # Ceiling is hard. Drop memory, then summaries, then the tail of retrieved
    # files, then the tail of symbols. Symbols stay longest by design.
    while tokenizer.count(prompt) > budget:
        if mem_text:
            mem_text = ""
        elif sum_text:
            sum_text = ""
        elif len(sem_parts) > 1:
            sem_parts.pop()
        elif len(sym_lines) > 1:
            sym_lines.pop()
            sym_text = "\n".join(sym_lines)
        else:
            break
        prompt = _assemble(query, alloc, sym_text, sem_parts, sum_text, mem_text,
                           with_conf=False)
    layers = {"symbols": tokenizer.count(sym_text),
              "semantic": tokenizer.count(chr(10).join(sem_parts)),
              "summary": tokenizer.count(sum_text), "memory": tokenizer.count(mem_text),
              "total": tokenizer.count(prompt)}
    return prompt, layers
