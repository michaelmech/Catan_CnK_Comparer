from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import random
from typing import List, Optional, Tuple

from .constants import NUMBER_TOKENS, TERRAIN_TILES, TERRAIN_TO_COMMODITY, TERRAIN_TO_RESOURCE

Hex = Tuple[str, Optional[int]]


def pip_value(n: int) -> int:
    return {2: 1, 12: 1, 3: 2, 11: 2, 4: 3, 10: 3, 5: 4, 9: 4, 6: 5, 8: 5}.get(n, 0)


@dataclass
class Site:
    hexes: List[Hex]
    is_city: bool

    def produce(self, roll: int) -> Counter:
        out: Counter = Counter()
        if roll == 7:
            return out
        for terrain, num in self.hexes:
            if num is None or num != roll or terrain == "desert":
                continue
            base = TERRAIN_TO_RESOURCE[terrain]
            if base is None:
                continue
            if not self.is_city:
                out[base] += 1
                continue
            if terrain in ("forest", "pasture", "mountains"):
                out[base] += 1
                out[TERRAIN_TO_COMMODITY[terrain]] += 1
            else:
                out[base] += 2
        return out

    def setup_resources_from_city_placement(self) -> Counter:
        if not self.is_city:
            return Counter()
        out: Counter = Counter()
        for terrain, _ in self.hexes:
            base = TERRAIN_TO_RESOURCE[terrain]
            if base is None:
                continue
            out[base] += 1
        return out


def random_hex(rng: random.Random, avoid_desert: bool) -> Hex:
    terrain = rng.choice(TERRAIN_TILES)
    if avoid_desert and terrain == "desert":
        while terrain == "desert":
            terrain = rng.choice(TERRAIN_TILES)
    if terrain == "desert":
        return terrain, None
    return terrain, rng.choice(NUMBER_TOKENS)


def random_site(
    rng: random.Random,
    is_city: bool,
    typical_samples: int = 50,
    avoid_desert: bool = True,
) -> Site:
    best: Optional[Site] = None
    best_score = -1

    for _ in range(max(1, typical_samples)):
        hexes = [random_hex(rng, avoid_desert=avoid_desert) for _ in range(3)]
        score = sum(pip_value(num) for _, num in hexes if num is not None)
        if score > best_score:
            best_score = score
            best = Site(hexes=hexes, is_city=is_city)

    assert best is not None
    return best
