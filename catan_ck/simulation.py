from __future__ import annotations

import random
import statistics
from collections import Counter
from typing import Dict, List, Optional, Tuple

from .board import random_site
from .constants import DICE_BAG, RESOURCES
from .models import PlayerState, TrialResult
from .strategies import (
    choose_primary_track_by_commodity_expectation,
    dev_turn_action,
    unit_turn_action,
)
from .trading import discard_half


def _make_players(
    rng: random.Random,
    num_players: int,
    typical_samples: int,
    starting_hand: str,
) -> List[PlayerState]:
    players: List[PlayerState] = []
    for _ in range(num_players):
        city_site = random_site(rng, is_city=True, typical_samples=typical_samples)
        settlement_site = random_site(rng, is_city=False, typical_samples=typical_samples)
        player = PlayerState(sites=[city_site, settlement_site])
        if starting_hand == "ck_city":
            player.hand.update(city_site.setup_resources_from_city_placement())
        elif starting_hand != "none":
            raise ValueError(f"unknown starting_hand={starting_hand}")
        players.append(player)
    return players


def _metrics_from_players(players: List[PlayerState]) -> Dict[str, object]:
    resource_totals = {r: 0 for r in RESOURCES}
    for player in players:
        for resource in RESOURCES:
            resource_totals[resource] += player.resources_gained_by_type.get(resource, 0)

    return {
        "bank_trades_made": sum(player.bank_trades_made for player in players),
        "resources_gained_total": sum(player.resources_gained_total for player in players),
        "resources_gained_by_type": resource_totals,
        "commodities_gained_from_hexes": sum(player.commodities_gained_from_hexes for player in players),
        "cards_lost_to_sevens": sum(player.cards_lost_to_sevens for player in players),
        "cities_built": sum(player.cities_built for player in players),
        "settlements_built": sum(player.settlements_built for player in players),
        "roads_built": sum(player.roads_built for player in players),
    }


def simulate_development_until_target(
    rng: random.Random,
    num_players: int,
    trade_rate: int,
    target_level: int,
    max_turns: int,
    typical_samples: int,
    starting_hand: str,
    dice_seq: List[int],
    random_seven_discards: bool,
) -> Tuple[int, bool, List[str], Dict[str, object]]:
    players = _make_players(rng, num_players, typical_samples, starting_hand)
    primaries = [choose_primary_track_by_commodity_expectation(p) for p in players]

    for turn in range(1, max_turns + 1):
        roll = dice_seq[turn - 1]
        if roll == 7:
            discard_mode = "random" if random_seven_discards else "bias_resources"
            for player in players:
                if sum(player.hand.values()) > 7:
                    player.cards_lost_to_sevens += discard_half(player.hand, mode=discard_mode, rng=rng)
        else:
            for player in players:
                player.collect(roll)

        active = (turn - 1) % num_players
        dev_turn_action(players[active], trade_rate, primaries[active], target_level)

        if any(player.dev_levels[primaries[i]] >= target_level for i, player in enumerate(players)):
            return turn, True, primaries, _metrics_from_players(players)

    return max_turns, False, primaries, _metrics_from_players(players)


def simulate_units_for_turns(
    rng: random.Random,
    num_players: int,
    trade_rate: int,
    turns: int,
    typical_samples: int,
    starting_hand: str,
    dice_seq: List[int],
    random_seven_discards: bool,
) -> TrialResult:
    players = _make_players(rng, num_players, typical_samples, starting_hand)

    for turn in range(1, turns + 1):
        roll = dice_seq[turn - 1]
        if roll == 7:
            discard_mode = "random" if random_seven_discards else "bias_resources"
            for player in players:
                if sum(player.hand.values()) > 7:
                    player.cards_lost_to_sevens += discard_half(player.hand, mode=discard_mode, rng=rng)
        else:
            for player in players:
                player.collect(roll)

        active = (turn - 1) % num_players
        unit_turn_action(players[active], trade_rate=trade_rate, rng=rng, typical_samples=typical_samples)

    units_by_player = [p.settlements_built + p.cities_built for p in players]
    metrics = _metrics_from_players(players)
    return TrialResult(
        stop_turn=turns,
        reached=True,
        units_total=sum(units_by_player),
        units_by_player=units_by_player,
        cities_by_player=[p.cities_built for p in players],
        settlements_by_player=[p.settlements_built for p in players],
        roads_by_player=[p.roads_built for p in players],
        bank_trades_made=metrics["bank_trades_made"],
        resources_gained_total=metrics["resources_gained_total"],
        resources_gained_by_type=metrics["resources_gained_by_type"],
        commodities_gained_from_hexes=metrics["commodities_gained_from_hexes"],
        cards_lost_to_sevens=metrics["cards_lost_to_sevens"],
    )


def run_experiment(
    trials: int,
    players: int,
    trade_rate: int,
    target_level: int,
    max_turns: int,
    typical_samples: int,
    starting_hand: str,
    seed: Optional[int] = None,
    random_seven_discards: bool = True,
) -> None:
    rng = random.Random(seed)

    stop_turns: List[int] = []
    reached_flags: List[bool] = []
    units_totals: List[int] = []
    dev_bank_trades: List[int] = []
    unit_bank_trades: List[int] = []
    dev_resources_total: List[int] = []
    unit_resources_total: List[int] = []
    dev_commodities_total: List[int] = []
    unit_commodities_total: List[int] = []
    dev_cards_lost_sevens: List[int] = []
    unit_cards_lost_sevens: List[int] = []
    dev_cities_built: List[int] = []
    unit_cities_built: List[int] = []
    dev_settlements_built: List[int] = []
    unit_settlements_built: List[int] = []
    dev_roads_built: List[int] = []
    unit_roads_built: List[int] = []
    dev_resource_by_type = {r: [] for r in RESOURCES}
    unit_resource_by_type = {r: [] for r in RESOURCES}
    roll_counts: Counter = Counter()

    for _ in range(trials):
        dice_seq = [rng.choice(DICE_BAG) for _ in range(max_turns)]

        stop_turn, reached, _primaries, dev_metrics = simulate_development_until_target(
            rng=rng,
            num_players=players,
            trade_rate=trade_rate,
            target_level=target_level,
            max_turns=max_turns,
            typical_samples=typical_samples,
            starting_hand=starting_hand,
            dice_seq=dice_seq,
            random_seven_discards=random_seven_discards,
        )

        unit_res = simulate_units_for_turns(
            rng=rng,
            num_players=players,
            trade_rate=trade_rate,
            turns=stop_turn,
            typical_samples=typical_samples,
            starting_hand=starting_hand,
            dice_seq=dice_seq,
            random_seven_discards=random_seven_discards,
        )

        roll_counts.update(dice_seq[:stop_turn])

        stop_turns.append(stop_turn)
        reached_flags.append(reached)
        units_totals.append(unit_res.units_total)

        dev_bank_trades.append(dev_metrics["bank_trades_made"])
        unit_bank_trades.append(unit_res.bank_trades_made)
        dev_resources_total.append(dev_metrics["resources_gained_total"])
        unit_resources_total.append(unit_res.resources_gained_total)
        dev_commodities_total.append(dev_metrics["commodities_gained_from_hexes"])
        unit_commodities_total.append(unit_res.commodities_gained_from_hexes)
        dev_cards_lost_sevens.append(dev_metrics["cards_lost_to_sevens"])
        unit_cards_lost_sevens.append(unit_res.cards_lost_to_sevens)
        dev_cities_built.append(dev_metrics["cities_built"])
        unit_cities_built.append(sum(unit_res.cities_by_player))
        dev_settlements_built.append(dev_metrics["settlements_built"])
        unit_settlements_built.append(sum(unit_res.settlements_by_player))
        dev_roads_built.append(dev_metrics["roads_built"])
        unit_roads_built.append(sum(unit_res.roads_by_player))

        for resource in RESOURCES:
            dev_resource_by_type[resource].append(dev_metrics["resources_gained_by_type"][resource])
            unit_resource_by_type[resource].append(unit_res.resources_gained_by_type[resource])

    reached_rate = sum(1 for x in reached_flags if x) / len(reached_flags)

    def _pct(xs: List[int], p: float) -> float:
        xs2 = sorted(xs)
        if not xs2:
            return float("nan")
        k = max(0, min(len(xs2) - 1, int(round(p * (len(xs2) - 1)))))
        return float(xs2[k])

    mean_stop = statistics.mean(stop_turns)
    med_stop = statistics.median(stop_turns)
    p25_stop = _pct(stop_turns, 0.25)
    p75_stop = _pct(stop_turns, 0.75)

    mean_rounds = mean_stop / players
    med_rounds = med_stop / players

    mean_units = statistics.mean(units_totals)
    med_units = statistics.median(units_totals)

    print("\n=== Cities & Knights rough trade sim ===")
    print(f"players={players}  trade_rate={trade_rate}:1  target_level={target_level}  trials={trials}")
    print(f"starting_hand={starting_hand}  typical_samples={typical_samples}  max_turns={max_turns}")
    print(f"random_seven_discards={random_seven_discards}")
    if seed is not None:
        print(f"seed={seed}")

    print("\n--- Development side (time to reach target) ---")
    print(f"reached within max_turns: {reached_rate*100:.1f}%")
    print(f"stop_turns (player-turns): mean={mean_stop:.2f}  median={med_stop:.2f}  p25={p25_stop:.0f}  p75={p75_stop:.0f}")
    print(f"stop_rounds (full rounds): mean={mean_rounds:.2f}  median={med_rounds:.2f}")

    print("\n--- Unit/building side (units built by that time) ---")
    print(f"units_total: mean={mean_units:.2f}  median={med_units:.2f}")

    print("\n--- Additional metrics (means across trials) ---")
    print(f"bank_trades_made: dev={statistics.mean(dev_bank_trades):.2f}  unit={statistics.mean(unit_bank_trades):.2f}")
    print(f"n_resources_gotten_total: dev={statistics.mean(dev_resources_total):.2f}  unit={statistics.mean(unit_resources_total):.2f}")
    print(f"n_commodities_generated_from_hexes: dev={statistics.mean(dev_commodities_total):.2f}  unit={statistics.mean(unit_commodities_total):.2f}")
    print(f"total_cards_lost_from_7s: dev={statistics.mean(dev_cards_lost_sevens):.2f}  unit={statistics.mean(unit_cards_lost_sevens):.2f}")
    print(
        "build_counts: "
        f"dev(cities={statistics.mean(dev_cities_built):.2f}, settlements={statistics.mean(dev_settlements_built):.2f}, roads={statistics.mean(dev_roads_built):.2f})  "
        f"unit(cities={statistics.mean(unit_cities_built):.2f}, settlements={statistics.mean(unit_settlements_built):.2f}, roads={statistics.mean(unit_roads_built):.2f})"
    )

    by_resource_dev = "  ".join(f"{r}={statistics.mean(dev_resource_by_type[r]):.2f}" for r in RESOURCES)
    by_resource_unit = "  ".join(f"{r}={statistics.mean(unit_resource_by_type[r]):.2f}" for r in RESOURCES)
    print(f"n_resources_by_type_dev: {by_resource_dev}")
    print(f"n_resources_by_type_unit: {by_resource_unit}")

    roll_line = "  ".join(f"{n}:{roll_counts.get(n, 0)}" for n in range(2, 13))
    print(f"roll_counts: {roll_line}")
