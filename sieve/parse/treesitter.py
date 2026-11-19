"""Tree-sitter parser for non-Python languages.

Parses with the language grammar and walks the tree for named declarations.
Import paths come from a small regex because every target language writes them
as either a quoted path or a dotted module. Call edges are not extracted; the
graph boost stays a Python-only refinement.
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

SYMBOL_NODES = {
    "function_definition": "func", "function_declaration": "func",
    "function_item": "func", "function_signature": "func",
    "method_definition": "method", "method_declaration": "method",
    "constructor_declaration": "method",
    "class_specifier": "class", "class_definition": "class",
    "class_declaration": "class", "struct_specifier": "class",
    "struct_item": "class", "interface_declaration": "class",
    "trait_item": "class", "object_declaration": "class",
    "enum_specifier": "type", "enum_item": "type",
    "enum_declaration": "type", "type_definition": "type",
    "type_declaration": "type", "type_alias_declaration": "type",
    "namespace_definition": "module",
}
NAME_NODES = {
    "identifier", "field_identifier", "type_identifier",
    "property_identifier", "namespace_identifier",
}
TOP_LEVEL = {"program", "module", "translation_unit", "source_file", "export_statement"}
DECLARATORS = {
    "variable_declarator": "const", "const_spec": "const", "var_spec": "const",
    "const_item": "const", "static_item": "const",
}


def ts_available(language: str) -> bool:
    try:
        from tree_sitter_language_pack import has_language
        return bool(has_language(language))
    except Exception:
        return False


def _descend(node) -> object | None:
    if node.type in NAME_NODES:
        return node
    for field in ("declarator", "name"):
        child = node.child_by_field_name(field)
        if child is not None:
            found = _descend(child)
            if found is not None:
                return found
    for child in node.children:
        if child.type in NAME_NODES:
            return child
    return None


def _find_name(node) -> object | None:
    for field in ("name", "declarator"):
        child = node.child_by_field_name(field)
        if child is not None:
            found = _descend(child)
            if found is not None:
                return found
    for child in node.children:
        if child.type in NAME_NODES:
            return child
        found = _descend(child)
        if found is not None:
            return found
    return None


def _walk(node, source: bytes, found: list[tuple[str, str, int]],
          parent: str = "", grandparent: str = "") -> None:
    kind = SYMBOL_NODES.get(node.type)
    if kind:
        name_node = _find_name(node)
        if name_node is not None:
            name = source[name_node.start_byte:name_node.end_byte].decode(
                "utf-8", "ignore").strip()
            if name:
                found.append((name, kind, node.start_point.row + 1))
    decl_kind = DECLARATORS.get(node.type)
    if decl_kind and (parent in TOP_LEVEL or grandparent in TOP_LEVEL):
        name_node = _find_name(node)
        if name_node is not None:
            name = source[name_node.start_byte:name_node.end_byte].decode(
                "utf-8", "ignore").strip()
            if name:
                found.append((name, decl_kind, node.start_point.row + 1))
    for child in node.children:
        _walk(child, source, found, node.type, parent)


def _imports(source: str) -> list[str]:
    paths = C_INCLUDE_RE.findall(source)
    paths += QUOTED_RE.findall(source)
    paths += KEYWORD_IMPORT_RE.findall(source)
    return [path for path in dict.fromkeys(paths) if path]


def parse_tree_sitter(rel: str, src: str, language: str) -> ParsedFile:
    from tree_sitter_language_pack import get_parser

    source = src.encode("utf-8", "ignore")
    tree = get_parser(language).parse(source)
    raw: list[tuple[str, str, int]] = []
    _walk(tree.root_node, source, raw)

    symbols = []
    seen: set[str] = set()
    for name, kind, line in raw:
        if name in seen:
            continue
        seen.add(name)
        symbols.append({"file": rel, "symbol": name, "line": line,
                        "kind": kind, "tokens": 1})

    chunks = [{"file": rel, "kind": "file", "name": rel,
               "text": src[:FILE_CHUNK_CHARS],
               "tokens": tokenizer.count(src[:FILE_CHUNK_CHARS])}]
    return {
        "file": rel,
        "symbols": symbols,
        "chunks": chunks,
        "imports": _imports(src),
        "edges": [],
        "tokens": tokenizer.count(src),
        "sha": hashlib.sha256(src.encode()).hexdigest()[:12],
    }
