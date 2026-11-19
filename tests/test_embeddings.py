import os
from pathlib import Path

import pytest

from sieve.embeddings import VectorIndex
from sieve.index import index_repo

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(os.getenv("SIEVE_SKIP_EMBEDDINGS") == "1",
                    reason="embedding model is not downloaded in this run")
def test_vector_index_builds_and_searches() -> None:
    index = index_repo(ROOT / "sample_repo_large")
    vectors = VectorIndex().build(index)
    assert vectors.dim > 0
    assert len(vectors.files) == len(index["files"])
    results = vectors.search("auth token check", top_k=3)
    assert results
    assert any("auth" in chunk["file"] for _, chunk in results)
