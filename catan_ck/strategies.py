from __future__ import annotations

import random

from .board import pip_value, random_site
from .constants import CITY_COST, SETTLEMENT_PLUS_ROAD_COST, TERRAIN_TO_COMMODITY, TRACK_TO_COMMODITY
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


def dev_turn_action(player: PlayerState, trade_rate: int, primary_track: str, target_level: int) -> None:
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
    while True:
        built_any = False

        settlement_idxs = player.non_city_settlement_indices()
        if settlement_idxs:
            hand_copy = player.hand.copy()
            if ensure_can_pay_with_trades(hand_copy, CITY_COST, trade_rate):
                player.hand = hand_copy
                pay(player.hand, CITY_COST)
                idx = settlement_idxs[0]
                player.sites[idx].is_city = True
                player.cities_built += 1
                built_any = True

        if built_any:
            continue

        hand_copy = player.hand.copy()
        if ensure_can_pay_with_trades(hand_copy, SETTLEMENT_PLUS_ROAD_COST, trade_rate):
            player.hand = hand_copy
            pay(player.hand, SETTLEMENT_PLUS_ROAD_COST)
            player.sites.append(random_site(rng, is_city=False, typical_samples=typical_samples))
            player.settlements_built += 1
            player.roads_built += 1
            built_any = True

        if not built_any:
            break
