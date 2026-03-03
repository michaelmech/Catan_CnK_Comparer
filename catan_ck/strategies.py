from __future__ import annotations

import random

from .board import pip_value, random_site
from .constants import CITY_COST, KNIGHT_COST, SETTLEMENT_PLUS_ROAD_COST, TERRAIN_TO_COMMODITY, TRACK_TO_COMMODITY
from .models import PlayerState
from .trading import ensure_can_pay_with_trades, pay


def choose_primary_track_by_commodity_expectation(player: PlayerState) -> str:
    exp = {"cloth": 0, "coin": 0, "paper": 0}
    for site in player.sites:
        if not site.is_city:
            continue
        for terrain, num in site.hexes:
            if num is None:
                continue
            if terrain in ("forest", "pasture", "mountains"):
                exp[TERRAIN_TO_COMMODITY[terrain]] += pip_value(num)

    commodity_to_track = {v: k for k, v in TRACK_TO_COMMODITY.items()}
    best_comm = max(exp.items(), key=lambda kv: kv[1])[0]
    return commodity_to_track[best_comm]


def _build_required_knight(player: PlayerState, trade_rate: int) -> bool:
    if player.has_knight:
        return True

    hand_copy = player.hand.copy()
    if not ensure_can_pay_with_trades(hand_copy, KNIGHT_COST, trade_rate):
        return False

    player.hand = hand_copy
    pay(player.hand, KNIGHT_COST)
    player.has_knight = True
    return True


def dev_turn_action(player: PlayerState, trade_rate: int, primary_track: str, target_level: int) -> None:
    if not _build_required_knight(player, trade_rate):
        return

    commodity = TRACK_TO_COMMODITY[primary_track]

    while player.dev_levels[primary_track] < target_level:
        next_level = player.dev_levels[primary_track] + 1
        cost = {commodity: next_level}

        hand_copy = player.hand.copy()
        if not ensure_can_pay_with_trades(hand_copy, cost, trade_rate):
            break

        player.hand = hand_copy
        pay(player.hand, cost)
        player.dev_levels[primary_track] = next_level


def unit_turn_action(player: PlayerState, trade_rate: int, rng: random.Random, typical_samples: int) -> None:
    if not _build_required_knight(player, trade_rate):
        return

    while True:
        built_any = False

        settlement_idxs = player.non_city_settlement_indices()
        city_gap = sum(max(0, n - player.hand.get(c, 0)) for c, n in CITY_COST.items())
        settlement_gap = sum(max(0, n - player.hand.get(c, 0)) for c, n in SETTLEMENT_PLUS_ROAD_COST.items())

        preferred = "settlement" if settlement_gap < city_gap else "city"
        build_order = (preferred, "city" if preferred == "settlement" else "settlement")

        for build_kind in build_order:
            if build_kind == "city":
                if not settlement_idxs:
                    continue
                hand_copy = player.hand.copy()
                if not ensure_can_pay_with_trades(hand_copy, CITY_COST, trade_rate):
                    continue
                player.hand = hand_copy
                pay(player.hand, CITY_COST)
                idx = settlement_idxs[0]
                player.sites[idx].is_city = True
                player.cities_built += 1
                built_any = True
                break

            hand_copy = player.hand.copy()
            if not ensure_can_pay_with_trades(hand_copy, SETTLEMENT_PLUS_ROAD_COST, trade_rate):
                continue
            player.hand = hand_copy
            pay(player.hand, SETTLEMENT_PLUS_ROAD_COST)
            player.sites.append(random_site(rng, is_city=False, typical_samples=typical_samples))
            player.settlements_built += 1
            player.roads_built += 1
            built_any = True
            break

        if not built_any:
            break
