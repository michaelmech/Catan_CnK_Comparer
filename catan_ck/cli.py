from __future__ import annotations

import argparse

from .simulation import run_experiment


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--players", type=int, default=3, choices=(3, 4))
    parser.add_argument("--trade-rate", type=int, default=3, dest="trade_rate")
    parser.add_argument("--target-level", type=int, default=3, dest="target_level")
    parser.add_argument("--target-players", type=int, default=1, dest="target_players")
    parser.add_argument("--trials", type=int, default=2000)
    parser.add_argument("--max-turns", type=int, default=300, dest="max_turns")
    parser.add_argument("--typical-samples", type=int, default=50, dest="typical_samples")
    parser.add_argument("--starting-hand", type=str, default="ck_city", choices=("ck_city", "none"))
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--random-seven-discards", dest="random_seven_discards", action="store_true")
    parser.add_argument("--no-random-seven-discards", dest="random_seven_discards", action="store_false")
    parser.add_argument("--barbarian", dest="barbarian_enabled", action="store_true")
    parser.add_argument("--no-barbarian", dest="barbarian_enabled", action="store_false")
    parser.add_argument("--aqueduct", dest="aqueduct_enabled", action="store_true")
    parser.add_argument("--no-aqueduct", dest="aqueduct_enabled", action="store_false")
    parser.add_argument("--force-aqueduct-route", dest="force_aqueduct_route", action="store_true")
    parser.add_argument("--no-force-aqueduct-route", dest="force_aqueduct_route", action="store_false")
    parser.add_argument("--aqueduct-rounds", type=int, default=0, dest="aqueduct_rounds")
    parser.add_argument("--victory-points-target", type=int, default=None, dest="victory_points_target")
    parser.set_defaults(random_seven_discards=True, barbarian_enabled=False, aqueduct_enabled=False, force_aqueduct_route=False)
    args, _unknown = parser.parse_known_args()
    return args


def main() -> None:
    args = parse_args()
    if args.trade_rate < 2:
        raise SystemExit("--trade-rate must be >= 2")
    if args.target_level < 1:
        raise SystemExit("--target-level must be >= 1")
    if args.target_players < 1:
        raise SystemExit("--target-players must be >= 1")
    if args.target_players > args.players:
        raise SystemExit("--target-players must be <= --players")
    if args.aqueduct_rounds < 0:
        raise SystemExit("--aqueduct-rounds must be >= 0")
    if args.victory_points_target is not None and args.victory_points_target < 1:
        raise SystemExit("--victory-points-target must be >= 1")

    run_experiment(
        trials=args.trials,
        players=args.players,
        trade_rate=args.trade_rate,
        target_level=args.target_level,
        target_players=args.target_players,
        max_turns=args.max_turns,
        typical_samples=args.typical_samples,
        starting_hand=args.starting_hand,
        seed=args.seed,
        random_seven_discards=args.random_seven_discards,
        barbarian_enabled=args.barbarian_enabled,
        aqueduct_enabled=args.aqueduct_enabled,
        aqueduct_rounds=args.aqueduct_rounds,
        force_aqueduct_route=args.force_aqueduct_route,
        victory_points_target=args.victory_points_target,
    )
