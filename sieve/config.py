"""Tunable defaults. One place for numbers the engine depends on."""
from pathlib import Path

VERSION = "0.5.0"
DEFAULT_BUDGET = 8000
DEFAULT_TOP_K = 8
DEFAULT_QUERY_BUDGET = 600

MAX_FILE_BYTES = 400_000
MAX_LINE_CHARS = 5_000
SNIFF_BYTES = 8_000
FILE_CHUNK_CHARS = 8_000
FUNC_CHUNK_CHARS = 2_500
SYMBOL_PREVIEW = 8
SUMMARY_FILES = 12
SUMMARY_CALLEES = 6
MEMORY_TURNS = 2

SKIP_DIRS = {
    "__pycache__", ".git", "node_modules", ".next", "dist", "build", "out",
    "vendor", ".venv", "venv", "target", "coverage", ".turbo", ".cache",
}
SKIP_FILES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock",
    "Cargo.lock", "go.sum", "composer.lock",
}

INDEX_ROOT = Path(__file__).resolve().parent
