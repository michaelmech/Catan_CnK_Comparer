from __future__ import annotations

import random
import statistics
from typing import List, Optional, Tuple

from .board import random_site
from .constants import DICE_BAG
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
) -> Tuple[int, bool, List[str]]:
    players = _make_players(rng, num_players, typical_samples, starting_hand)
    primaries = [choose_primary_track_by_commodity_expectation(p) for p in players]

    for turn in range(1, max_turns + 1):
        roll = dice_seq[turn - 1]
        if roll == 7:
            discard_mode = "random" if random_seven_discards else "bias_resources"
            for player in players:
                if sum(player.hand.values()) > 7:
                    discard_half(player.hand, mode=discard_mode, rng=rng)
        else:
            for player in players:
                player.collect(roll)

        active = (turn - 1) % num_players
        dev_turn_action(players[active], trade_rate, primaries[active], target_level)

        if any(player.dev_levels[primaries[i]] >= target_level for i, player in enumerate(players)):
            return turn, True, primaries

    return max_turns, False, primaries


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
                    discard_half(player.hand, mode=discard_mode, rng=rng)
        else:
            for player in players:
                player.collect(roll)

        active = (turn - 1) % num_players
        unit_turn_action(players[active], trade_rate=trade_rate, rng=rng, typical_samples=typical_samples)

    units_by_player = [p.settlements_built + p.cities_built for p in players]
    return TrialResult(
        stop_turn=turns,
        reached=True,
        units_total=sum(units_by_player),
        units_by_player=units_by_player,
        cities_by_player=[p.cities_built for p in players],
        settlements_by_player=[p.settlements_built for p in players],
        roads_by_player=[p.roads_built for p in players],
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

    for _ in range(trials):
        dice_seq = [rng.choice(DICE_BAG) for _ in range(max_turns)]

        stop_turn, reached, _primaries = simulate_development_until_target(
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

        stop_turns.append(stop_turn)
        reached_flags.append(reached)
        units_totals.append(unit_res.units_total)

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
