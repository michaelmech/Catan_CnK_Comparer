from __future__ import annotations

import random
import statistics
from collections import Counter
from typing import Dict, List, Optional, Tuple

from .board import random_site
from .constants import CITY_COST, DICE_BAG, RESOURCES, SETTLEMENT_PLUS_ROAD_COST
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


def _victory_points(player: PlayerState) -> int:
    board_points = sum(2 if site.is_city else 1 for site in player.sites)
    dev_points = sum(2 for lvl in player.dev_levels.values() if lvl >= 4)
    return board_points + dev_points


def _pick_aqueduct_resource_for_units(player: PlayerState) -> str:
    city_gap_by_resource = {c: max(0, n - player.hand.get(c, 0)) for c, n in CITY_COST.items()}
    settlement_gap_by_resource = {c: max(0, n - player.hand.get(c, 0)) for c, n in SETTLEMENT_PLUS_ROAD_COST.items()}

    city_gap = sum(city_gap_by_resource.values())
    settlement_gap = sum(settlement_gap_by_resource.values())
    preferred_cost = SETTLEMENT_PLUS_ROAD_COST if settlement_gap < city_gap else CITY_COST
    preferred_gaps = settlement_gap_by_resource if settlement_gap < city_gap else city_gap_by_resource

    best_resource = RESOURCES[0]
    best_score = -10**9
    for resource in RESOURCES:
        score = 0
        if preferred_gaps.get(resource, 0) > 0:
            score += 2
        if preferred_cost.get(resource, 0) > 0:
            score += 1
        score += preferred_gaps.get(resource, 0)

        if score > best_score:
            best_score = score
            best_resource = resource

    return best_resource


def _collect_for_turn(
    players: List[PlayerState],
    roll: int,
    aqueduct_enabled: bool,
) -> None:
    for player in players:
        if roll == 7:
            continue

        before_total = player.resources_gained_total
        player.collect(roll)

        if not aqueduct_enabled:
            continue
        if player.dev_levels.get("science", 0) < 3:
            continue
        if player.resources_gained_total != before_total:
            continue

        chosen = _pick_aqueduct_resource_for_units(player)
        player.hand[chosen] += 1
        player.resources_gained_total += 1
        player.resources_gained_by_type[chosen] += 1


def _resolve_barbarian_attack(players: List[PlayerState]) -> None:
    for player in players:
        defended = False
        if player.has_knight:
            if player.knight_active:
                defended = True
            elif player.hand.get("grain", 0) >= 1:
                player.hand["grain"] -= 1
                if player.hand["grain"] <= 0:
                    del player.hand["grain"]
                player.knight_active = True
                defended = True

        if not defended:
            player.lose_one_city()

    for player in players:
        if player.has_knight:
            player.knight_active = False


def simulate_development_until_target(
    rng: random.Random,
    num_players: int,
    trade_rate: int,
    target_level: int,
    target_players: int,
    max_turns: int,
    typical_samples: int,
    starting_hand: str,
    dice_seq: List[int],
    random_seven_discards: bool,
    barbarian_enabled: bool,
    aqueduct_enabled: bool = False,
    force_aqueduct_route: bool = False,
    victory_points_target: Optional[int] = None,
) -> Tuple[int, bool, List[str], Dict[str, object]]:
    players = _make_players(rng, num_players, typical_samples, starting_hand)
    primaries = ["science" for _ in players] if force_aqueduct_route else [choose_primary_track_by_commodity_expectation(p) for p in players]
    building_units = [False for _ in players]
    reached_target = False
    barbarian_progress = 0

    for turn in range(1, max_turns + 1):
        roll = dice_seq[turn - 1]
        if roll == 7:
            discard_mode = "random" if random_seven_discards else "bias_resources"
            for player in players:
                if sum(player.hand.values()) > 7:
                    player.cards_lost_to_sevens += discard_half(player.hand, mode=discard_mode, rng=rng)
        else:
            _collect_for_turn(players, roll=roll, aqueduct_enabled=aqueduct_enabled)

        if barbarian_enabled:
            barbarian_progress += 1
            if barbarian_progress >= 7:
                _resolve_barbarian_attack(players)
                barbarian_progress = 0

        active = (turn - 1) % num_players
        if building_units[active]:
            unit_turn_action(players[active], trade_rate=trade_rate, rng=rng, typical_samples=typical_samples)
        else:
            dev_goal = 3 if aqueduct_enabled else target_level
            dev_turn_action(players[active], trade_rate, primaries[active], dev_goal)
            if aqueduct_enabled and players[active].dev_levels.get("science", 0) >= 3:
                building_units[active] = True

        n_players_reached_target = sum(
            1 for i, player in enumerate(players) if player.dev_levels[primaries[i]] >= target_level
        )
        if n_players_reached_target >= target_players:
            reached_target = True
            if not aqueduct_enabled and victory_points_target is None:
                return turn, True, primaries, _metrics_from_players(players)

        if victory_points_target is not None and any(_victory_points(player) >= victory_points_target for player in players):
            return turn, True, primaries, _metrics_from_players(players)

    return max_turns, reached_target if victory_points_target is None else False, primaries, _metrics_from_players(players)


def simulate_units_for_turns(
    rng: random.Random,
    num_players: int,
    trade_rate: int,
    turns: int,
    typical_samples: int,
    starting_hand: str,
    dice_seq: List[int],
    random_seven_discards: bool,
    barbarian_enabled: bool,
    aqueduct_enabled: bool = False,
    victory_points_target: Optional[int] = None,
) -> TrialResult:
    players = _make_players(rng, num_players, typical_samples, starting_hand)

    barbarian_progress = 0

    for turn in range(1, turns + 1):
        roll = dice_seq[turn - 1]
        if roll == 7:
            discard_mode = "random" if random_seven_discards else "bias_resources"
            for player in players:
                if sum(player.hand.values()) > 7:
                    player.cards_lost_to_sevens += discard_half(player.hand, mode=discard_mode, rng=rng)
        else:
            _collect_for_turn(players, roll=roll, aqueduct_enabled=aqueduct_enabled)

        if barbarian_enabled:
            barbarian_progress += 1
            if barbarian_progress >= 7:
                _resolve_barbarian_attack(players)
                barbarian_progress = 0

        active = (turn - 1) % num_players
        unit_turn_action(players[active], trade_rate=trade_rate, rng=rng, typical_samples=typical_samples)

        if victory_points_target is not None and any(_victory_points(player) >= victory_points_target for player in players):
            units_by_player = [p.settlements_built + p.cities_built for p in players]
            metrics = _metrics_from_players(players)
            return TrialResult(
                stop_turn=turn,
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
    target_players: int,
    max_turns: int,
    typical_samples: int,
    starting_hand: str,
    seed: Optional[int] = None,
    random_seven_discards: bool = True,
    barbarian_enabled: bool = False,
    aqueduct_enabled: bool = False,
    aqueduct_rounds: int = 0,
    force_aqueduct_route: bool = False,
    victory_points_target: Optional[int] = None,
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
        dice_seq = [rng.choice(DICE_BAG) for _ in range(max_turns + aqueduct_rounds * players)]

        stop_turn, reached, _primaries, dev_metrics = simulate_development_until_target(
            rng=rng,
            num_players=players,
            trade_rate=trade_rate,
            target_level=target_level,
            target_players=target_players,
            max_turns=max_turns,
            typical_samples=typical_samples,
            starting_hand=starting_hand,
            dice_seq=dice_seq,
            random_seven_discards=random_seven_discards,
            barbarian_enabled=barbarian_enabled,
            aqueduct_enabled=aqueduct_enabled,
            force_aqueduct_route=force_aqueduct_route,
            victory_points_target=victory_points_target,
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
            barbarian_enabled=barbarian_enabled,
            aqueduct_enabled=aqueduct_enabled,
            victory_points_target=victory_points_target,
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
    print(
        f"players={players}  trade_rate={trade_rate}:1  target_level={target_level}  "
        f"target_players={target_players}  trials={trials}"
    )
    print(f"starting_hand={starting_hand}  typical_samples={typical_samples}  max_turns={max_turns}")
    print(f"random_seven_discards={random_seven_discards}")
    print(f"barbarian_enabled={barbarian_enabled}")
    print(f"aqueduct_enabled={aqueduct_enabled}  force_aqueduct_route={force_aqueduct_route}  aqueduct_rounds={aqueduct_rounds}")
    print(f"victory_points_target={victory_points_target}")
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
