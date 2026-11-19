"""Python parser. Stdlib ast gives accurate symbols, imports and call edges."""
import ast
import hashlib
import re

from .. import tokenizer
from ..config import FILE_CHUNK_CHARS, FUNC_CHUNK_CHARS
from ..models import ParsedFile

IMPORT_RE = re.compile(r"^(?:import|from)\s+(\S+)", re.M)

class CallVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, int]] = []
        self._func_stack = ["<module>"]

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._func_stack.append(node.name)
        self.generic_visit(node)
        self._func_stack.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Call(self, node: ast.Call) -> None:
        name = None
        if isinstance(node.func, ast.Name):
            name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            name = node.func.attr
        if name:
            self.calls.append((self._func_stack[-1], name, node.lineno))
        self.generic_visit(node)

def parse_python(rel: str, src: str) -> ParsedFile:
    tree = ast.parse(src)
    funcs: list[dict] = []
    classes: list[dict] = []
    edges: list[dict] = []
    visitor = CallVisitor()
    visitor.visit(tree)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            segment = ast.get_source_segment(src, node) or ""
            funcs.append({"name": node.name, "line": node.lineno,
                          "code": segment[:FUNC_CHUNK_CHARS],
                          "tokens": tokenizer.count(segment)})
        elif isinstance(node, ast.ClassDef):
            classes.append({"name": node.name, "line": node.lineno})
    for caller, callee, line in visitor.calls:
        edges.append({"caller": caller, "callee": callee, "file": rel, "line": line})
    imports = IMPORT_RE.findall(src)
    chunks = [{"file": rel, "kind": "file", "name": rel,
               "text": src[:FILE_CHUNK_CHARS],
               "tokens": tokenizer.count(src[:FILE_CHUNK_CHARS])}]
    for func in funcs:
        chunks.append({"file": rel, "kind": "func", "name": func["name"],
                       "text": func["code"], "tokens": func["tokens"]})
    symbols = [{"file": rel, "symbol": f["name"], "line": f["line"],
                "kind": "func", "tokens": f["tokens"]} for f in funcs]
    symbols += [{"file": rel, "symbol": c["name"], "line": c["line"],
                 "kind": "class", "tokens": 10} for c in classes]
    return {
        "file": rel,
        "symbols": symbols,
        "chunks": chunks,
        "imports": imports,
        "edges": edges,
        "tokens": tokenizer.count(src),
        "sha": hashlib.sha256(src.encode()).hexdigest()[:12],
    }
