# Demo script (5 min, terminal only)

1. `pip install -e .` then `python tools/build_large_repo.py`. Say "18 files, 1127 tokens, 37 symbols."
2. `python run_eval.py 600`. Point at the table. Full 1127 at recall 1.0, truncation 600 at recall 0.0, Sieve 548 at recall 0.83.
   Say "Same budget as truncation, keeps 83 percent of the needed files."
3. Open `traces_eval/B1-sieve.json`. Show files, tokens per layer, tokenizer and prompt hash.
   Say "Every decision is traced, not a black box."
4. Compare `traces_eval/B1-trunc.json` with `B1-sieve.json`. Truncation loses auth.py. Sieve keeps it.
5. A/B: show the table in `docs/DEMO_AB.md`. Full context 49,412 tokens and 52,508 input tokens. Sieve 5,516 and 6,926. Same 6 of 6 answer key. 86.8 percent fewer input tokens.
6. MCP: `opencode mcp list` shows `sieve connected`. The recorded session shows one `sieve_index` call and three `sieve_query` calls with no filesystem access, and the same correct chain.
7. Close with the limits. One run per arm, one model, one repository. Bugs reproduce. The allocator is rule-based. Non-Python call graphs are not extracted.

Backup if offline: print `results_eval.csv`, one trace JSON, `docs/AB_ANSWER_run-a.md` and `docs/AB_ANSWER_run-b.md`.
