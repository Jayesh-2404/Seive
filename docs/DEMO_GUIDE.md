# Demo script (5 min, terminal only)

1. `python tools/build_large_repo.py` — "18 files, 1052 tokens, 37 symbols."
2. `python run_eval.py 600` — point to table: full 1068/recall 1.0, trunc 600/recall 0.0, sieve 518/recall 0.83.
   Say: "Same budget as truncation, keeps 83% of needed files."
3. Open `traces_eval/B1-sieve.json` — show files, tokens per layer, prompt_hash.
   Say: "Every decision traced, not black box."
4. Open `traces_eval/B1-trunc.json` vs `B1-sieve.json` — "Truncation loses auth.py; Sieve keeps it via symbol bonus."
5. A/B: show `docs/DEMO_AB.md` table. Full context 51,194 tokens, Sieve 5,642, same answer key, 86.5% fewer input tokens.
6. Close: "Bugs reproduce (all False). The A/B pilot is one run per arm. Bypass rule handles tiny repos."

Backup if offline: print `results_eval.csv` + one trace JSON + `docs/AB_ANSWER_run-a.md` and `run-b.md`.
