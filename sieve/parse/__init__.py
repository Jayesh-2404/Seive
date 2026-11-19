"""Parse dispatch. Python uses ast, supported languages use tree-sitter,
everything else falls back to regex so a repo is never empty.
"""
from pathlib import Path

from ..models import ParsedFile
from .profiles import language_for
from .python_ast import parse_python
from .regex_fallback import parse_with_regex
from .treesitter import parse_tree_sitter, ts_available

__all__ = ["parse_file", "parse_python", "parse_with_regex", "parse_tree_sitter",
           "ts_available", "language_for"]

def parse_file(path: Path, root: Path) -> ParsedFile:
    # Normalize line endings so token counts do not depend on the checkout.
    source = path.read_text(encoding="utf-8", errors="ignore")
    source = source.replace("\r\n", "\n").replace("\r", "\n")
    rel = path.relative_to(root).as_posix()
    language = language_for(path)
    if language == "python":
        return parse_python(rel, source)
    if language and ts_available(language):
        try:
            return parse_tree_sitter(rel, source, language)
        except Exception:
            pass
    return parse_with_regex(rel, source, language)
