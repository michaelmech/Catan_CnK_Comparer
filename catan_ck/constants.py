from __future__ import annotations

RESOURCES = ("lumber", "brick", "grain", "wool", "ore")
COMMODITIES = ("paper", "cloth", "coin")
ALL_CARDS = RESOURCES + COMMODITIES

TRACKS = ("trade", "politics", "science")
TRACK_TO_COMMODITY = {
    "trade": "cloth",
    "politics": "coin",
    "science": "paper",
}

TERRAINS = ("forest", "hills", "fields", "pasture", "mountains", "desert")
TERRAIN_TO_RESOURCE = {
    "forest": "lumber",
    "hills": "brick",
    "fields": "grain",
    "pasture": "wool",
    "mountains": "ore",
    "desert": None,
}
TERRAIN_TO_COMMODITY = {
    "forest": "paper",
    "pasture": "cloth",
    "mountains": "coin",
}

NUMBER_TOKENS = [2, 3, 3, 4, 4, 5, 5, 6, 6, 8, 8, 9, 9, 10, 10, 11, 11, 12]

TERRAIN_TILES = [
    "forest",
    "forest",
    "forest",
    "forest",
    "pasture",
    "pasture",
    "pasture",
    "pasture",
    "fields",
    "fields",
    "fields",
    "fields",
    "hills",
    "hills",
    "hills",
    "mountains",
    "mountains",
    "mountains",
    "desert",
]

DICE_WEIGHTS = {2: 1, 3: 2, 4: 3, 5: 4, 6: 5, 7: 6, 8: 5, 9: 4, 10: 3, 11: 2, 12: 1}
DICE_BAG = [v for v, w in DICE_WEIGHTS.items() for _ in range(w)]


CITY_COST = {"grain": 2, "ore": 3}
SETTLEMENT_COST = {"brick": 1, "lumber": 1, "grain": 1, "wool": 1}
ROAD_COST = {"brick": 1, "lumber": 1}
SETTLEMENT_PLUS_ROAD_COST = {
    "brick": SETTLEMENT_COST["brick"] + ROAD_COST["brick"],
    "lumber": SETTLEMENT_COST["lumber"] + ROAD_COST["lumber"],
    "grain": SETTLEMENT_COST["grain"],
    "wool": SETTLEMENT_COST["wool"],
}
