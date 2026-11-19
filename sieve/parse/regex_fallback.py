"""Regex fallback for languages with no installed grammar.

This is deliberately coarse. It exists so an unknown repo still yields files,
symbols and imports instead of an empty index.
"""
import hashlib
import re

from .. import tokenizer
from ..config import FILE_CHUNK_CHARS
from ..models import ParsedFile

QUOTED_RE = re.compile(r"""["']([^"']+)["']""")
C_INCLUDE_RE = re.compile(r"#include\s+[<\"]([^>\"]+)[>\"]")
KEYWORD_IMPORT_RE = re.compile(
    r"^\s*(?:import|from|use|package)\s+([\w.@/:\-]+)", re.M)
CALL_RE = re.compile(r"\b([A-Za-z_$][\w$]*)\s*\(")
CALL_SKIP = {
    "if", "for", "while", "switch", "catch", "return", "function", "typeof",
    "new", "await", "async", "super", "import", "export", "constructor",
}

FAMILY_PATTERNS: dict[str, list[tuple[str, re.Pattern]]] = {
    "js": [
        ("func", re.compile(r"^(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)", re.M)),
        ("class", re.compile(r"^(?:export\s+)?(?:abstract\s+)?class\s+([A-Za-z_$][\w$]*)", re.M)),
        ("type", re.compile(r"^(?:export\s+)?(?:interface|type|enum)\s+([A-Za-z_$][\w$]*)", re.M)),
        ("const", re.compile(r"^(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)", re.M)),
    ],
    "c": [
        ("class", re.compile(r"^\s*(?:class|struct|enum|union)\s+([A-Za-z_]\w*)", re.M)),
        ("func", re.compile(r"^[A-Za-z_][\w:<>,*&\s\[\]]*\s+([A-Za-z_]\w*)\s*\([^;{}]*\)\s*(?:const\s*)?\{", re.M)),
    ],
    "go": [
        ("func", re.compile(r"^func\s+(?:\([^)]*\)\s*)?([A-Za-z_]\w*)", re.M)),
        ("type", re.compile(r"^type\s+([A-Za-z_]\w*)", re.M)),
    ],
    "java": [
        ("class", re.compile(r"^(?:public\s+|private\s+|protected\s+|static\s+|final\s+|abstract\s+)*(?:class|interface|enum|record)\s+([A-Za-z_]\w*)", re.M)),
        ("func", re.compile(r"^\s*(?:public\s+|private\s+|protected\s+|static\s+|final\s+|abstract\s+|synchronized\s+)+[\w<>\[\],.]+\s+([A-Za-z_]\w*)\s*\([^;]*\)\s*\{", re.M)),
    ],
    "rust": [
        ("func", re.compile(r"^\s*(?:pub\s+)?(?:async\s+)?fn\s+([A-Za-z_]\w*)", re.M)),
        ("class", re.compile(r"^\s*(?:pub\s+)?(?:struct|enum|trait)\s+([A-Za-z_]\w*)", re.M)),
    ],
    "text": [
        ("func", re.compile(r"^(?:def|class|function|func|fn)\s+([A-Za-z_]\w*)", re.M)),
    ],
}
FAMILY_BY_LANG = {
    "typescript": "js", "tsx": "js", "javascript": "js",
    "c": "c", "cpp": "c",
    "go": "go",
    "java": "java", "kotlin": "java", "c_sharp": "java", "scala": "java",
    "rust": "rust",
}

def _family(language: str | None) -> str:
    return FAMILY_BY_LANG.get(language or "", "text")

def parse_with_regex(rel: str, src: str, language: str | None) -> ParsedFile:
    symbols = []
    seen: set[str] = set()
    for kind, pattern in FAMILY_PATTERNS[_family(language)]:
        for match in pattern.finditer(src):
            name = match.group(1)
            if name in seen or name in CALL_SKIP:
                continue
            seen.add(name)
            symbols.append({"file": rel, "symbol": name,
                            "line": src.count("\n", 0, match.start()) + 1,
                            "kind": kind, "tokens": 1})
    imports = C_INCLUDE_RE.findall(src)
    imports += QUOTED_RE.findall(src)
    imports += KEYWORD_IMPORT_RE.findall(src)
    imports = [m for m in dict.fromkeys(imports) if m]
    edges = []
    for match in CALL_RE.finditer(src):
        name = match.group(1)
        if name in CALL_SKIP:
            continue
        edges.append({"caller": "<module>", "callee": name, "file": rel,
                      "line": src.count("\n", 0, match.start()) + 1})
    chunks = [{"file": rel, "kind": "file", "name": rel,
               "text": src[:FILE_CHUNK_CHARS],
               "tokens": tokenizer.count(src[:FILE_CHUNK_CHARS])}]
    return {
        "file": rel,
        "symbols": symbols,
        "chunks": chunks,
        "imports": imports,
        "edges": edges,
        "tokens": tokenizer.count(src),
        "sha": hashlib.sha256(src.encode()).hexdigest()[:12],
    }
