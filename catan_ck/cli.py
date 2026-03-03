from __future__ import annotations

import argparse

from .simulation import run_experiment


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--players", type=int, default=3, choices=(3, 4))
    parser.add_argument("--trade-rate", type=int, default=3, dest="trade_rate")
    parser.add_argument("--target-level", type=int, default=3, dest="target_level")
    parser.add_argument("--trials", type=int, default=2000)
    parser.add_argument("--max-turns", type=int, default=300, dest="max_turns")
    parser.add_argument("--typical-samples", type=int, default=50, dest="typical_samples")
    parser.add_argument("--starting-hand", type=str, default="ck_city", choices=("ck_city", "none"))
    parser.add_argument("--seed", type=int, default=None)
    args, _unknown = parser.parse_known_args()
    return args


def main() -> None:
    args = parse_args()
    if args.trade_rate < 2:
        raise SystemExit("--trade-rate must be >= 2")
    if args.target_level < 1:
        raise SystemExit("--target-level must be >= 1")

    run_experiment(
        trials=args.trials,
        players=args.players,
        trade_rate=args.trade_rate,
        target_level=args.target_level,
        max_turns=args.max_turns,
        typical_samples=args.typical_samples,
        starting_hand=args.starting_hand,
        seed=args.seed,
    )
