# Semantic layer: local dense retrieval

The engine now has a real dense retrieval path. It runs on CPU with `fastembed`
and ONNX, so there is no service and no API key.

## What it does

- Model: `BAAI/bge-small-en-v1.5`, 384 dimensions.
- `sieve/embeddings.py` embeds each file chunk and keeps a normalized matrix.
- `hybrid_retrieve` adds `8.0 * cosine` to the BM25 and structure score.
- The index is built per repository and held in memory. The model downloads once
  to the fastembed cache.

## Measured result: no gain on this task set

The 12-task eval is lexical. Dense retrieval did not improve it.

| System | Avg tokens | Recall@5 | Avg ms |
|---|---|---|---|
| sieve | 548 | 0.83 | 11.8 |
| sieve-vec | 553 | 0.83 | 38.6 |

That is an honest negative result. The vector path finds the same files, uses a
few more tokens, and costs about three times the latency. It is available, but
it is not the default. The likely place for a gain is a paraphrase task set where
the query shares no words with the file, and that test does not exist yet.

## How to use it

```sh
sieve query "how does sign out remove the session" --vectors --json
```

- MCP: `sieve_query(task, vectors=true)`.
- HTTP: `{"task": "...", "vectors": true}`.
- Eval: `python run_eval.py 600` includes the `sieve-vec` row when the model is
  available. Set `SIEVE_SKIP_EMBEDDINGS=1` to skip it.

## Limits

- No pgvector. The index is local and in memory, and it rebuilds when the
  process starts. The `VectorIndex` interface is small enough to swap for
  pgvector or another store.
- No RRF. The fusion is a weighted dense boost on top of BM25 and the structure
  boosts.
- No paraphrase benchmark yet. Without one, the semantic layer is unproven.
- The first run downloads the model. CI sets `SIEVE_SKIP_EMBEDDINGS=1` so it does
  not fetch the model.
