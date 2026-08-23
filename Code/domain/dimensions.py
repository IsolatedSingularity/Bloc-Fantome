"""Dimension identifiers and immutable weather presentation data."""

DIMENSION_OVERWORLD = "overworld"
DIMENSION_NETHER = "nether"
DIMENSION_END = "end"

DIMENSION_WEATHER = {
    DIMENSION_OVERWORLD: {
        "rain": {
            "name": "Rain", "style": "rain", "texture": "lapis_block.png",
            "colors": ((70, 100, 140, 220),), "speed": (15, 25),
            "length": (10, 20), "angle": (0.08, 0.15),
            "darkness": 130, "overlay": (20, 30, 50),
        },
        "snow": {
            "name": "Snow", "style": "snow", "texture": "snow.png",
            "colors": ((255, 255, 255, 200),), "speed": (1.5, 3.5),
            "size": (2, 4), "darkness": 80, "overlay": (40, 50, 70),
        },
    },
    DIMENSION_NETHER: {
        "rain": {
            "name": "Ember Fall", "style": "embers", "texture": "netherrack.png",
            "colors": ((255, 120, 20, 230), (255, 75, 10, 210), (255, 175, 45, 190)),
            "speed": (4, 9), "length": (3, 7), "angle": (-0.12, 0.12),
            "darkness": 35, "overlay": (90, 25, 5),
            "particles": 88,
        },
        "snow": {
            "name": "Soul Drift", "style": "souls", "texture": "soul_sand.png",
            "colors": ((80, 190, 255, 175), (55, 145, 225, 155), (115, 220, 255, 135)),
            "speed": (0.6, 1.5), "size": (3, 6),
            "darkness": 30, "overlay": (10, 45, 65),
        },
    },
    DIMENSION_END: {
        "rain": {
            "name": "Void Rain", "style": "void", "texture": "end_stone.png",
            "colors": ((135, 55, 200, 185), (90, 30, 155, 160), (180, 80, 230, 200)),
            "speed": (5, 11), "length": (5, 11), "angle": (0.18, 0.32),
            "darkness": 45, "overlay": (35, 10, 55),
            "particles": 92,
        },
        "snow": {
            "name": "End Shards", "style": "shards", "texture": "purpur_block.png",
            "colors": ((245, 225, 255, 255), (205, 175, 255, 245), (255, 245, 255, 255)),
            "speed": (1.0, 2.4), "size": (4, 8),
            "particles": 84, "darkness": 28, "overlay": (35, 20, 55),
            "screenwide": True,
        },
    },
}
