"""Compose the final prompt under a hard token ceiling.

The cut order protects correctness. Memory drops first, then summaries, then
the tail of retrieved files, then the tail of symbols. Symbol names are the
last thing removed because they are the map an agent needs to ask a better
question.
"""
from . import tokenizer
from .config import MEMORY_TURNS, SUMMARY_FILES
from .models import Allocation, Layers, RepositoryIndex
from .summarize import summarize_file as summarize_entry

MEMORY_HEADER = "[MEMORY]"


def summarize_file(entry: dict, index: RepositoryIndex) -> str:
    return summarize_entry(entry, index)


def _assemble(query: str, alloc: Allocation, sym_text: str, sem_parts: list[str],
              sum_text: str, mem_text: str, with_conf: bool = True) -> str:
    task = alloc["task_type"] + (
        f" (conf {alloc['confidence']:.2f})" if with_conf else "")
    return (f"QUERY: {query}\nTASK: {task}\n\n"
            f"[SYMBOLS:{tokenizer.count(sym_text)}t]\n{sym_text}\n\n"
            f"[RETRIEVED:{tokenizer.count(chr(10).join(sem_parts))}t]\n"
            f"{chr(10).join(sem_parts)}\n\n"
            f"[SUMMARIES]\n{sum_text}\n\n{MEMORY_HEADER}\n{mem_text}\n")


def compose(query: str, index: RepositoryIndex, ranked: list[tuple[float, dict]],
            alloc: Allocation, budget: int,
            memory_turns: list[dict] | None = None) -> tuple[str, Layers]:
    if alloc.get("bypass"):
        file_chunks = [chunk for chunk in index["chunks"] if chunk["kind"] == "file"]
        prompt = f"QUERY: {query}\nMODE: FULL (repo fits budget)\n\n" + "\n\n".join(
            f'# {chunk["file"]}\n{chunk["text"][:4000]}' for chunk in file_chunks)
        return prompt, {"mode": "full_bypass", "total": tokenizer.count(prompt)}

    tokens = alloc["tokens"]
    picked_files = [chunk["file"] for _, chunk in ranked]
    ordered = [symbol for symbol in index["symbols"] if symbol["file"] in picked_files]
    ordered += [symbol for symbol in index["symbols"] if symbol["file"] not in picked_files]

    symbol_lines: list[str] = []
    symbols_used = 0
    for symbol in ordered:
        line = f'{symbol["file"]}:{symbol["line"]} {symbol["symbol"]}({symbol["kind"]})'
        cost = tokenizer.count(line) + 1
        if symbol_lines and symbols_used + cost > tokens["symbols"]:
            break
        symbol_lines.append(line)
        symbols_used += cost
    symbol_text = "\n".join(symbol_lines)

    semantic_parts: list[str] = []
    semantic_used = 0
    for score, chunk in ranked:
        cost = tokenizer.count(chunk["text"][:2000])
        if semantic_parts and semantic_used + cost > tokens["semantic"]:
            break
        semantic_parts.append(
            f'# {chunk["file"]} [score={score:.2f}]\n{chunk["text"][:2000]}')
        semantic_used += cost

    rest = [entry for entry in index["files"]
            if entry["file"] not in picked_files][:SUMMARY_FILES]
    summary_text = "\n".join(summarize_file(entry, index) for entry in rest)
    summary_text = tokenizer.truncate(summary_text, tokens["summary"])

    memory_text = ""
    if memory_turns:
        memory_text = "\n".join(
            f"- {turn['q'][:120]} -> {turn['note'][:160]}"
            for turn in memory_turns[-MEMORY_TURNS:])
        memory_text = tokenizer.truncate(memory_text, tokens["memory"])

    prompt = _assemble(query, alloc, symbol_text, semantic_parts,
                       summary_text, memory_text)
    while tokenizer.count(prompt) > budget:
        if memory_text:
            memory_text = ""
        elif summary_text:
            summary_text = ""
        elif len(semantic_parts) > 1:
            semantic_parts.pop()
        elif len(symbol_lines) > 1:
            symbol_lines.pop()
            symbol_text = "\n".join(symbol_lines)
        else:
            break
        prompt = _assemble(query, alloc, symbol_text, semantic_parts,
                           summary_text, memory_text, with_conf=False)

    # The first chunk always enters whole, so a budget below one chunk would
    # otherwise be exceeded. Ceiling wins here; the layer counts may then sum
    # higher than total for that degenerate case.
    if tokenizer.count(prompt) > budget:
        prompt = tokenizer.truncate(prompt, max(0, budget))

    layers: Layers = {
        "symbols": tokenizer.count(symbol_text),
        "semantic": tokenizer.count(chr(10).join(semantic_parts)),
        "summary": tokenizer.count(summary_text),
        "memory": tokenizer.count(memory_text),
        "total": tokenizer.count(prompt),
    }
    return prompt, layers
