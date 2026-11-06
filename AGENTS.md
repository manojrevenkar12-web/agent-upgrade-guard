# Working on agent-upgrade-guard

## Fast feedback

```bash
pip install -e ".[dev]"
ruff check . && ruff format --check .
pytest -q                 # about 1 s
guard bench               # dev workspace, about 3 s
guard report --fast       # regenerate reports without the budget sweep
cd web && npm run typecheck && npm run build
```

## Invariants

- **The guard never sees the truth.** Only `guard/sim/` and `guard/evaluate.py` (and `report.py`
  and `cli.py`, which call it) may import `guard.sim`. `tests/test_isolation.py` enforces this.
- **Every verdict has a reason.** A check that fails returns evidence a person can read, and every
  obligation keeps the sentence it came from.
- **A candidate is held back only by statistics.** A single failed check is not a regression. Do not
  add shortcuts that block on one answer.
- **Doubtful checks go to a person.** If the current model fails a check most of the time, the agent
  goes to review; it never passes silently.
- **Settings live in config.** Alpha, effect size, hard rules, budget and thresholds belong in
  `config/guard.json`, and workspaces in `config/bench.json`. Code holds no tuned numbers.
- **Reports are generated.** `reports/` and `web/public/data.json` come from `guard report`. Never
  edit them by hand.
- **The frontend follows house rules.** Feature folders under `web/src/features`. Colours, faces
  and sizes come only from `web/src/shared/theme.ts`. Every view has loading, error and empty states.

## The held-out rule

`eval/heldout/` holds workspaces pinned by sha256 before their only run.

- Never re-pin to make a changed generator pass.
- Never change code because of a held-out result and then report that set's numbers again.
- The first run is the result; `--again` writes a separate later run.
- Changing the reader or the checks needs a new held-out set, written before the change is tested
  on it.

Phrasings in `guard/sim/bench.py` under `heldout` and `heldout2` must not appear in tests.
