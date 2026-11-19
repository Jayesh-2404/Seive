"""Repository indexer.

Python files are parsed with stdlib ast. JavaScript and TypeScript files use
regex symbol extraction so retrieval, allocation and composition work on
non-Python repos. Call edges are kept only when the callee is a defined symbol.
"""
import ast, re, hashlib
from pathlib import Path
from . import tokenizer

IMPORT_RE = re.compile(r"^(?:import|from)\s+(\S+)", re.M)
JS_IMPORT_RE = re.compile(r"""(?:from\s+["']([^"']+)["']|require\(\s*["']([^"']+)["']\s*\))""")
JS_CALL_RE = re.compile(r"\b([A-Za-z_$][\w$]*)\s*\(")
JS_CALL_SKIP = {
    "if", "for", "while", "switch", "catch", "return", "function", "typeof",
    "new", "await", "async", "super", "import", "export", "constructor",
}
# Anchored at line start so loop-local and block-local declarations stay out.
JS_SYMBOL_RES = [
    ("func", re.compile(r"^(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)", re.M)),
    ("class", re.compile(r"^(?:export\s+)?(?:abstract\s+)?class\s+([A-Za-z_$][\w$]*)", re.M)),
    ("type", re.compile(r"^(?:export\s+)?(?:interface|type|enum)\s+([A-Za-z_$][\w$]*)", re.M)),
    ("const", re.compile(r"^(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)", re.M)),
]
CODE_EXTS = {".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".mts", ".cjs"}
SKIP_PARTS = {"__pycache__", ".git", "node_modules", ".next", "dist", "build", "out", "vendor", ".venv"}
SKIP_FILES = {"package-lock.json", "yarn.lock", "pnpm-lock.yaml"}

class CallVisitor(ast.NodeVisitor):
    def __init__(self):
        self.calls = []
        self._func_stack = ["<module>"]
    def visit_FunctionDef(self, node):
        self._func_stack.append(node.name)
        self.generic_visit(node)
        self._func_stack.pop()
    visit_AsyncFunctionDef = visit_FunctionDef
    def visit_Call(self, node):
        name = None
        if isinstance(node.func, ast.Name):
            name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            name = node.func.attr
        if name:
            self.calls.append((self._func_stack[-1], name, node.lineno))
        self.generic_visit(node)

def _line_at(src, idx):
    return src.count("\n", 0, idx) + 1

def _rel(path, repo):
    return str(path.relative_to(repo)).replace("\\", "/")

def _parse_python(path, repo):
    rel = _rel(path, repo)
    src = path.read_text(encoding="utf-8", errors="ignore")
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        return {"file": rel, "error": str(e), "symbols": [], "chunks": [],
                "imports": [], "edges": [], "tokens": tokenizer.count(src),
                "sha": hashlib.sha256(src.encode()).hexdigest()[:12]}
    funcs, classes, edges = [], [], []
    v = CallVisitor(); v.visit(tree)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            try:
                seg = ast.get_source_segment(src, node) or ""
            except Exception:
                seg = ""
            funcs.append({"name": node.name, "line": node.lineno,
                          "code": seg[:2500], "tokens": tokenizer.count(seg),
                          "args": [a.arg for a in node.args.args]})
        elif isinstance(node, ast.ClassDef):
            classes.append({"name": node.name, "line": node.lineno})
    for caller, callee, line in v.calls:
        edges.append({"caller": caller, "callee": callee, "file": rel, "line": line})
    imports = IMPORT_RE.findall(src)
    chunks = [{"file": rel, "kind": "file", "name": rel,
               "text": src[:8000], "tokens": tokenizer.count(src[:8000])}]
    for f in funcs:
        chunks.append({"file": rel, "kind": "func", "name": f["name"],
                       "text": f["code"][:2500], "tokens": f["tokens"]})
    symbols = [{"file": rel, "symbol": f["name"], "line": f["line"],
                "kind": "func", "tokens": f["tokens"]} for f in funcs]
    symbols += [{"file": rel, "symbol": c["name"], "line": c["line"],
                 "kind": "class", "tokens": 10} for c in classes]
    return {"file": rel, "symbols": symbols, "chunks": chunks, "imports": imports,
            "edges": edges, "tokens": tokenizer.count(src),
            "sha": hashlib.sha256(src.encode()).hexdigest()[:12], "funcs": funcs}

def _parse_generic(path, repo):
    rel = _rel(path, repo)
    src = path.read_text(encoding="utf-8", errors="ignore")
    symbols, edges, seen = [], [], set()
    for kind, pat in JS_SYMBOL_RES:
        for m in pat.finditer(src):
            name = m.group(1)
            if name in seen or name in JS_CALL_SKIP:
                continue
            seen.add(name)
            symbols.append({"file": rel, "symbol": name, "line": _line_at(src, m.start()),
                            "kind": kind, "tokens": 1})
    for m in JS_CALL_RE.finditer(src):
        name = m.group(1)
        if name in JS_CALL_SKIP:
            continue
        edges.append({"caller": "<module>", "callee": name, "file": rel,
                      "line": _line_at(src, m.start())})
    imports = [a or b for a, b in JS_IMPORT_RE.findall(src)]
    chunks = [{"file": rel, "kind": "file", "name": rel,
               "text": src[:8000], "tokens": tokenizer.count(src[:8000])}]
    return {"file": rel, "symbols": symbols, "chunks": chunks, "imports": imports,
            "edges": edges, "tokens": tokenizer.count(src),
            "sha": hashlib.sha256(src.encode()).hexdigest()[:12], "funcs": []}

def parse_file(path, repo):
    path = Path(path)
    return _parse_python(path, repo) if path.suffix == ".py" else _parse_generic(path, repo)

def index_repo(repo: Path):
    repo = Path(repo)
    files, symbols, chunks, edges = [], [], [], []
    for path in sorted(repo.rglob("*")):
        if not path.is_file() or path.suffix not in CODE_EXTS:
            continue
        if any(part in SKIP_PARTS for part in path.parts) or path.name in SKIP_FILES:
            continue
        r = parse_file(path, repo)
        if r.get("error"):
            continue
        files.append({"file": r["file"], "tokens": r["tokens"], "sha": r["sha"],
                      "imports": r["imports"]})
        symbols.extend(r["symbols"])
        chunks.extend(r["chunks"])
        edges.extend(r["edges"])
    defined = {s["symbol"] for s in symbols}
    edges = [e for e in edges if e["callee"] in defined and e["callee"] != e["caller"]]
    def_index = {}
    for s in symbols:
        def_index.setdefault(s["symbol"], []).append(s["file"])
    return {"files": files, "symbols": symbols, "chunks": chunks,
            "edges": edges, "def_index": def_index,
            "total_tokens": sum(f["tokens"] for f in files)}
