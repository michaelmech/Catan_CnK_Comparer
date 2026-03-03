# Catan_CnK_Comparer

Monte Carlo simulator for a simplified **Catan: Cities & Knights** comparison between:

1. Development-track strategy (commodity-focused city improvements), and
2. Unit/building strategy (cities + settlement/road bundles).

## Project structure

The original brainstorming notebook logic has been split into importable Python modules:

- `catan_ck/constants.py` – game constants and costs
- `catan_ck/board.py` – board/site abstractions and production logic
- `catan_ck/trading.py` – payment, bank-trade, and discard helpers
- `catan_ck/models.py` – dataclasses for player/trial state
- `catan_ck/strategies.py` – per-turn strategy actions
- `catan_ck/simulation.py` – simulation runners and experiment summary output
- `catan_ck/cli.py` – argument parsing and CLI orchestration
- `ck_catan_trade_sim.py` – top-level executable entrypoint

## Run

```bash
python ck_catan_trade_sim.py --players 4 --trade-rate 4 --target-level 4 --trials 5000
```

The notebook (`Catan_CnK_Comparer.ipynb`) is still present for reference, while the runnable logic now lives in `.py` modules.
