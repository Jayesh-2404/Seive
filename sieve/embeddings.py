"""Local dense retrieval with fastembed.

This is the semantic layer for a single machine. The model runs on CPU with
ONNX, so there is no service and no API key. The `VectorIndex` interface is
small enough to swap for pgvector later.
"""
from __future__ import annotations

import numpy as np

from .models import RepositoryIndex

DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"
_MODELS: dict = {}


def _model(name: str):
    if name not in _MODELS:
        from fastembed import TextEmbedding
        _MODELS[name] = TextEmbedding(model_name=name)
    return _MODELS[name]


class VectorIndex:
    def __init__(self, model_name: str = DEFAULT_MODEL) -> None:
        self.model_name = model_name
        self.files: list[str] = []
        self.chunks: list[dict] = []
        self.matrix: np.ndarray | None = None

    def build(self, index: RepositoryIndex) -> VectorIndex:
        self.chunks = [chunk for chunk in index["chunks"] if chunk["kind"] == "file"]
        if not self.chunks:
            self.files = []
            self.matrix = np.zeros((0, 1), dtype=np.float32)
            return self
        texts = [f'{chunk["file"]}\n{chunk["text"][:2000]}' for chunk in self.chunks]
        vectors = list(_model(self.model_name).embed(texts))
        matrix = np.asarray(vectors, dtype=np.float32)
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        self.matrix = matrix / np.clip(norms, 1e-9, None)
        self.files = [chunk["file"] for chunk in self.chunks]
        return self

    def scores(self, query: str) -> list[float]:
        if self.matrix is None or not self.files:
            return []
        query_vector = np.asarray(
            next(iter(_model(self.model_name).embed([query]))), dtype=np.float32)
        query_vector = query_vector / max(float(np.linalg.norm(query_vector)), 1e-9)
        return (self.matrix @ query_vector).tolist()

    def search(self, query: str, top_k: int = 5) -> list[tuple[float, dict]]:
        scores = self.scores(query)
        order = sorted(range(len(scores)), key=lambda i: -scores[i])[:top_k]
        return [(scores[i], self.chunks[i]) for i in order]

    @property
    def dim(self) -> int:
        return 0 if self.matrix is None or self.matrix.size == 0 else int(self.matrix.shape[1])
