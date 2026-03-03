from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List

from .board import Site
from .constants import COMMODITIES, RESOURCES, TRACKS


@dataclass
class PlayerState:
    sites: List[Site]
    hand: Counter = field(default_factory=Counter)
    dev_levels: Dict[str, int] = field(default_factory=lambda: {t: 0 for t in TRACKS})
    settlements_built: int = 0
    cities_built: int = 0
    roads_built: int = 0
    has_knight: bool = False
    bank_trades_made: int = 0
    resources_gained_total: int = 0
    resources_gained_by_type: Dict[str, int] = field(default_factory=lambda: {r: 0 for r in RESOURCES})
    commodities_gained_from_hexes: int = 0
    cards_lost_to_sevens: int = 0

    def collect(self, roll: int) -> None:
        for s in self.sites:
            produced = s.produce(roll)
            self.hand.update(produced)
            for r in RESOURCES:
                gained = produced.get(r, 0)
                self.resources_gained_by_type[r] += gained
                self.resources_gained_total += gained
            self.commodities_gained_from_hexes += sum(produced.get(c, 0) for c in COMMODITIES)

    def non_city_settlement_indices(self) -> List[int]:
        return [i for i, s in enumerate(self.sites) if not s.is_city]


@dataclass
class TrialResult:
    stop_turn: int
    reached: bool
    units_total: int
    units_by_player: List[int]
    cities_by_player: List[int]
    settlements_by_player: List[int]
    roads_by_player: List[int]
    bank_trades_made: int
    resources_gained_total: int
    resources_gained_by_type: Dict[str, int]
    commodities_gained_from_hexes: int
    cards_lost_to_sevens: int
