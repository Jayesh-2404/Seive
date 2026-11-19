"""Summary layer with an optional external model.

The default is the extractive one-liner, so no model is called and the measured
results do not move. Set SIEVE_SUMMARY_CMD to a command that reads a prompt on
stdin and writes text on stdout, for example `ollama run qwen2.5-coder`. The
summary is rejected and the extractive line is used when a backticked identifier
does not exist in the source or the symbol list.
"""
import os
import re
import shlex
import subprocess

from . import tokenizer
from .config import SUMMARY_CALLEES
from .models import RepositoryIndex

SUMMARY_TEMPLATE = """Summarize this file for a coding agent.
Keep every function, class and identifier name exactly. Do not invent names.
Use backticks around identifiers. Maximum {max_tokens} tokens.
File: {file}
Symbols: {symbols}
Code:
{code}
"""
BACKTICK_RE = re.compile(r"`([^`]+)`")
_CACHE: dict[tuple[str, str], str] = {}


def extractive_summary(entry: dict, index: RepositoryIndex) -> str:
    names = [symbol["symbol"] for symbol in index["symbols"]
             if symbol["file"] == entry["file"]][:8]
    callees = sorted({edge["callee"] for edge in index["edges"]
                      if edge["file"] == entry["file"]})[:SUMMARY_CALLEES]
    return (f'{entry["file"]}: defines {", ".join(names) or "-"} '
            f'({entry["tokens"]} toks) | calls {", ".join(callees) or "-"}')


def validate_summary(summary: str, source: str, symbols: list[str]) -> bool:
    haystack = source + "\n" + "\n".join(symbols)
    for raw in BACKTICK_RE.findall(summary):
        name = raw.strip().strip("()")
        if name and name not in haystack:
            return False
    return True


class CommandProvider:
    def __init__(self, command: list[str]) -> None:
        self.command = command

    def __call__(self, prompt: str) -> str:
        result = subprocess.run(self.command, input=prompt, capture_output=True,
                                text=True, encoding="utf-8", errors="replace",
                                timeout=120)
        if result.returncode != 0:
            raise RuntimeError(result.stderr[-200:])
        return result.stdout.strip()


def default_provider():
    command = os.getenv("SIEVE_SUMMARY_CMD", "").strip()
    return CommandProvider(shlex.split(command)) if command else None


def summarize_file(entry: dict, index: RepositoryIndex, provider=None,
                   max_tokens: int = 120, use_cache: bool = True) -> str:
    fallback = extractive_summary(entry, index)
    provider = provider or default_provider()
    if provider is None:
        return fallback
    key = (entry["file"], entry["sha"])
    if use_cache and key in _CACHE:
        return _CACHE[key]
    chunk = next((item for item in index["chunks"]
                  if item["file"] == entry["file"] and item["kind"] == "file"), None)
    if chunk is None:
        return fallback
    symbols = [symbol["symbol"] for symbol in index["symbols"]
               if symbol["file"] == entry["file"]]
    prompt = SUMMARY_TEMPLATE.format(max_tokens=max_tokens, file=entry["file"],
                                     symbols=", ".join(symbols[:40]),
                                     code=chunk["text"][:6000])
    try:
        summary = provider(prompt).strip()
    except Exception:
        return fallback
    if not summary or not validate_summary(summary, chunk["text"], symbols):
        return fallback
    summary = tokenizer.truncate(summary, max_tokens)
    if use_cache:
        _CACHE[key] = summary
    return summary
