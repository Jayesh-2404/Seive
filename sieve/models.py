"""Typed shapes shared by index, retrieval, composition and the server.

These are the JSON-facing records. They stay plain dicts so a trace can be
written without a serializer, but every producer and consumer is annotated.
"""
from typing import TypedDict


class Symbol(TypedDict):
    file: str
    symbol: str
    line: int
    kind: str
    tokens: int


class Chunk(TypedDict):
    file: str
    kind: str
    name: str
    text: str
    tokens: int


class Edge(TypedDict):
    caller: str
    callee: str
    file: str
    line: int


class FileEntry(TypedDict):
    file: str
    tokens: int
    sha: str
    imports: list[str]


class ParsedFile(TypedDict):
    file: str
    symbols: list[Symbol]
    chunks: list[Chunk]
    imports: list[str]
    edges: list[Edge]
    tokens: int
    sha: str


class RepositoryIndex(TypedDict):
    files: list[FileEntry]
    symbols: list[Symbol]
    chunks: list[Chunk]
    edges: list[Edge]
    def_index: dict[str, list[str]]
    total_tokens: int
    skipped: dict[str, int]


class Allocation(TypedDict, total=False):
    task_type: str
    confidence: float
    bypass: bool
    reason: str
    split: dict[str, float]
    tokens: dict[str, int]


class Layers(TypedDict, total=False):
    symbols: int
    semantic: int
    summary: int
    memory: int
    total: int
    mode: str
