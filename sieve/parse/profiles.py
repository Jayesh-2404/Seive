"""Extension to language mapping. One table, no language names in the pipeline."""
from pathlib import Path

LANG_BY_EXT = {
    ".py": "python", ".pyi": "python",
    ".ts": "typescript", ".mts": "typescript", ".cts": "typescript",
    ".tsx": "tsx",
    ".js": "javascript", ".jsx": "javascript", ".mjs": "javascript", ".cjs": "javascript",
    ".c": "c", ".h": "c",
    ".cc": "cpp", ".cpp": "cpp", ".cxx": "cpp", ".hpp": "cpp", ".hh": "cpp", ".hxx": "cpp",
    ".go": "go",
    ".java": "java",
    ".rs": "rust",
    ".rb": "ruby",
    ".php": "php",
    ".cs": "c_sharp",
    ".kt": "kotlin",
    ".swift": "swift",
    ".scala": "scala",
}
TEXT_EXTS = {
    ".md", ".txt", ".rst", ".sql", ".sh", ".bash", ".ps1",
    ".html", ".css", ".scss", ".vue", ".svelte",
}

def language_for(path: Path) -> str | None:
    return LANG_BY_EXT.get(path.suffix.lower())

def is_code(path: Path) -> bool:
    return path.suffix.lower() in LANG_BY_EXT

def is_text(path: Path) -> bool:
    return path.suffix.lower() in TEXT_EXTS
