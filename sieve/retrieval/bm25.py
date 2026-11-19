"""BM25 scoring and token normalization. No structure boosts here."""
import collections
import math
import re
from typing import TypedDict

TOKEN_RE = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*")
CAMEL_RE = re.compile(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|\d+")
K1, B = 1.2, 0.75


class Bm25Stats(TypedDict):
    tfs: list[collections.Counter]
    df: collections.Counter
    lens: list[int]
    avgdl: float
    N: int


def tokenize(text: str) -> list[str]:
    """Split snake_case and camelCase so buildWorkItems matches work."""
    out: list[str] = []
    for raw in TOKEN_RE.findall(text):
        for part in raw.split("_"):
            if not part:
                continue
            out.append(part.lower())
            if any(char.isupper() for char in part[1:]):
                out.extend(match.lower() for match in CAMEL_RE.findall(part))
    return out


def build_stats(chunks: list[dict]) -> Bm25Stats:
    """Precompute doc lengths, avgdl, doc frequencies. File-level chunks only."""
    doc_tokens = [tokenize((chunk["file"] + " ") * 3 + chunk["text"][:3000])
                  for chunk in chunks]
    lengths = [len(tokens) for tokens in doc_tokens]
    vocabulary = collections.Counter()
    term_freqs = []
    for tokens in doc_tokens:
        freq = collections.Counter(tokens)
        term_freqs.append(freq)
        for term in set(freq):
            vocabulary[term] += 1
    return {
        "tfs": term_freqs,
        "df": vocabulary,
        "lens": lengths,
        "avgdl": sum(lengths) / max(1, len(lengths)),
        "N": len(chunks),
    }


def bm25(query: str, chunks: list[dict], stats: Bm25Stats) -> list[float]:
    query_tokens = tokenize(query)
    count = stats["N"]
    scores = []
    for i in range(count):
        score = 0.0
        length = stats["lens"][i] or 1
        for term in query_tokens:
            freq = stats["tfs"][i].get(term, 0)
            if not freq:
                continue
            doc_freq = stats["df"].get(term, 0)
            idf = math.log(1 + (count - doc_freq + 0.5) / (doc_freq + 0.5))
            score += idf * (freq * (K1 + 1)) / (
                freq + K1 * (1 - B + B * length / stats["avgdl"]))
        scores.append(score)
    return scores
