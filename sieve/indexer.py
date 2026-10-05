"""AST indexer: functions, classes, imports, call-graph edges. Stdlib ast only."""
import ast, re, hashlib
from pathlib import Path
from . import tokenizer

IMPORT_RE = re.compile(r"^(?:import|from)\s+(\S+)", re.M)

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

def parse_file(path: Path, repo: Path):
    rel = str(path.relative_to(repo))
    src = path.read_text(encoding="utf-8", errors="ignore")
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        return {"file": rel, "error": str(e), "symbols": [], "chunks": [],
                "imports": [], "edges": [], "tokens": tokenizer.count(src), "sha": hashlib.sha256(src.encode()).hexdigest()[:12]}
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
    # chunk = whole file + per-function chunks
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

def index_repo(repo: Path):
    repo = Path(repo)
    files, symbols, chunks, edges = [], [], [], []
    for py in sorted(repo.rglob("*.py")):
        if "__pycache__" in str(py) or ".venv" in str(py):
            continue
        r = parse_file(py, repo)
        if r.get("error"):
            continue
        files.append({"file": r["file"], "tokens": r["tokens"], "sha": r["sha"],
                      "imports": r["imports"]})
        symbols.extend(r["symbols"])
        chunks.extend(r["chunks"])
        edges.extend(r["edges"])
    # callee -> files that define it (for 1-hop expansion)
    def_index = {}
    for s in symbols:
        def_index.setdefault(s["symbol"], []).append(s["file"])
    return {"files": files, "symbols": symbols, "chunks": chunks,
            "edges": edges, "def_index": def_index,
            "total_tokens": sum(f["tokens"] for f in files)}
