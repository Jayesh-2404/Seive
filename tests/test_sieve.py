import tempfile
import unittest
from pathlib import Path

from sieve import allocator, composer, retrieval
from sieve.index import index_repo

ROOT = Path(__file__).resolve().parents[1]

class IndexerTest(unittest.TestCase):
    def test_ts_and_py_symbols_and_skips(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d)
            (repo / "a.ts").write_text(
                "export function buildWorkItems() {}\nexport const queueView = 1;\n")
            (repo / "b.py").write_text("def check_auth(token):\n    return token\n")
            (repo / "node_modules").mkdir()
            (repo / "node_modules" / "x.ts").write_text("export function vendored() {}\n")
            (repo / "package-lock.json").write_text("{}")
            index = index_repo(repo)
            names = {s["symbol"] for s in index["symbols"]}
            self.assertIn("buildWorkItems", names)
            self.assertIn("queueView", names)
            self.assertIn("check_auth", names)
            self.assertNotIn("vendored", names)
            self.assertEqual(len(index["files"]), 2)

    def test_python_repo_still_indexes(self):
        index = index_repo(ROOT / "sample_repo_large")
        self.assertEqual(len(index["files"]), 18)
        self.assertGreater(len(index["symbols"]), 20)

class RetrievalTest(unittest.TestCase):
    def test_camel_case_and_snake_case_split(self):
        tokens = retrieval.tokenize("buildWorkItems check_auth")
        for expected in ("work", "items", "check", "auth"):
            self.assertIn(expected, tokens)

class ComposerTest(unittest.TestCase):
    def test_ceiling_is_hard(self):
        index = index_repo(ROOT / "sample_repo_large")
        query = "Fix KeyError in check_auth when token is missing"
        for budget in (600, 400, 200):
            alloc = allocator.allocate(query, budget, index["total_tokens"])
            ranked, _ = retrieval.hybrid_retrieve(query, index, top_k=5)
            prompt, layers = composer.compose(query, index, ranked, alloc, budget)
            self.assertLessEqual(layers["total"], budget, f"budget {budget} exceeded")
            self.assertEqual(layers["total"], composer.tokenizer.count(prompt))

    def test_bypass_returns_full_mode(self):
        index = index_repo(ROOT / "sample_repo_large")
        alloc = allocator.allocate("anything", 4000, index["total_tokens"])
        ranked, _ = retrieval.hybrid_retrieve("anything", index, top_k=5)
        prompt, layers = composer.compose("anything", index, ranked, alloc, 4000)
        self.assertTrue(alloc["bypass"])
        self.assertEqual(layers["mode"], "full_bypass")

if __name__ == "__main__":
    unittest.main()
