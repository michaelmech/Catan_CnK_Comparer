from __future__ import annotations

from collections import Counter
import random
from typing import Dict, Optional, Tuple

from .constants import ALL_CARDS, COMMODITIES, RESOURCES

Cost = Dict[str, int]


def can_pay(hand: Counter, cost: Cost) -> bool:
    return all(hand[c] >= n for c, n in cost.items())


def pay(hand: Counter, cost: Cost) -> None:
    for c, n in cost.items():
        hand[c] -= n
        if hand[c] <= 0:
            del hand[c]


def _pick_trade_source(hand: Counter, trade_rate: int, cost: Cost, target_card: str) -> Optional[str]:
    best_src = None
    best_surplus = -10**9
    best_count = -1

    for src, cnt in hand.items():
        if src == target_card or cnt < trade_rate:
            continue
        required = cost.get(src, 0)
        surplus = cnt - required
        if surplus > best_surplus or (surplus == best_surplus and cnt > best_count):
            best_surplus = surplus
            best_count = cnt
            best_src = src

    return best_src


def ensure_can_pay_with_trades(hand: Counter, cost: Cost, trade_rate: int) -> Tuple[bool, int]:
    trades_made = 0
    if can_pay(hand, cost):
        return True, trades_made

    for card, need in cost.items():
        while hand.get(card, 0) < need:
            src = _pick_trade_source(hand, trade_rate, cost, target_card=card)
            if src is None:
                return False, trades_made
            hand[src] -= trade_rate
            if hand[src] <= 0:
                del hand[src]
            hand[card] += 1
            trades_made += 1

    return can_pay(hand, cost), trades_made


def discard_half(hand: Counter, mode: str, rng: random.Random) -> int:
    total = sum(hand.values())
    k = total // 2
    if k <= 0:
        return 0

    discarded = 0

    def weighted_pick(card_types: Tuple[str, ...]) -> Optional[str]:
        weights = [hand.get(c, 0) for c in card_types]
        s = sum(weights)
        if s <= 0:
            return None
        r = rng.randrange(s)
        acc = 0
        for c, w in zip(card_types, weights):
            acc += w
            if r < acc:
                return c
        return None

    if mode == "bias_resources":
        for _ in range(k):
            if sum(hand.get(c, 0) for c in RESOURCES) > 0:
                card = weighted_pick(RESOURCES)
            else:
                card = weighted_pick(COMMODITIES)
            if card is None:
                break
            hand[card] -= 1
            if hand[card] <= 0:
                del hand[card]
            discarded += 1
        return discarded

    for _ in range(k):
        card = weighted_pick(ALL_CARDS)
        if card is None:
            break
        hand[card] -= 1
        if hand[card] <= 0:
            del hand[card]
        discarded += 1

    return discarded
