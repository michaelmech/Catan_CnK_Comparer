from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List

from .board import Site
from .constants import TRACKS


@dataclass
class PlayerState:
    sites: List[Site]
    hand: Counter = field(default_factory=Counter)
    dev_levels: Dict[str, int] = field(default_factory=lambda: {t: 0 for t in TRACKS})
    settlements_built: int = 0
    cities_built: int = 0
    roads_built: int = 0
    has_knight: bool = False

    def collect(self, roll: int) -> None:
        for s in self.sites:
            self.hand.update(s.produce(roll))

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
