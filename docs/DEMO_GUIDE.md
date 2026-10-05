# Demo script (5 min, terminal only)

1. `python tools/build_large_repo.py` — "18 files, 1127 tokens, 37 symbols."
2. `python run_eval.py 600` — point to table: full 1127/recall 1.0, trunc 600/recall 0.0, sieve 607/recall 0.86.
   Say: "Same budget as truncation, keeps 86% of needed files."
3. Open `traces_eval/B1-sieve.json` — show files, tokens per layer, prompt_hash.
   Say: "Every decision traced, not black box."
4. Open `traces_eval/B1-trunc.json` vs `B1-sieve.json` — "Truncation loses auth.py; Sieve keeps it via symbol bonus."
5. Close: "Bugs reproduce (all False). LLM fix rate is next, harness hook already in run_eval.py. Bypass rule handles tiny repos."

Backup if offline: print `results_eval.csv` + one trace JSON.
