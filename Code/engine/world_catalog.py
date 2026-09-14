"""Curated, version-labelled editable world scenes."""

from dataclasses import dataclass
import os
from typing import List


@dataclass(frozen=True)
class WorldEntry:
    scene_id: str
    name: str
    subtitle: str
    description: str
    filename: str
    category: str


WORLD_ENTRIES = (
    WorldEntry(
        "nether_fortress_biomes_1161",
        "Nether Fortress",
        "Java 1.16.1 | Nether",
        "The road ends at a locked gate. On the far side, the fire has no echo.",
        "nether_fortress_biomes_1161.json.gz",
        "Nether",
    ),
    WorldEntry(
        "bastion_treasure_1161",
        "Treasure Bastion",
        "Java 1.16.1 | Nether",
        "The vault stands open. Even the ash keeps its distance.",
        "bastion_treasure_1161.json.gz",
        "Nether",
    ),
    WorldEntry(
        "bastion_bridge_1161",
        "Bridge Bastion",
        "Java 1.16.1 | Nether",
        "The bridge survived its builders. Something still patrols the far bank.",
        "bastion_bridge_1161.json.gz",
        "Nether",
    ),
    WorldEntry(
        "bastion_hoglin_stable_1161",
        "Hoglin Stable Bastion",
        "Java 1.16.1 | Nether",
        "The pens are broken. The feeding bells still hang.",
        "bastion_hoglin_stable_1161.json.gz",
        "Nether",
    ),
    WorldEntry(
        "bastion_housing_units_1161",
        "Housing Units Bastion",
        "Java 1.16.1 | Nether",
        "No hearth burns here. Gold still changes hands.",
        "bastion_housing_units_1161.json.gz",
        "Nether",
    ),
    WorldEntry(
        "basalt_deltas_1161",
        "Basalt Deltas",
        "Java 1.16.1 | Nether",
        "Nothing rests long enough to leave a footprint.",
        "basalt_deltas_1161.json.gz",
        "Nether",
    ),
    WorldEntry(
        "end_city_1161",
        "End City",
        "Java 1.16.1 | The End",
        "Doors without roads. Towers without shadows. No sign of the people who left.",
        "end_city_1161.json.gz",
        "The End",
    ),
    WorldEntry(
        "ocean_monument_1161",
        "Deep Ocean",
        "Java 1.16.1 | Overworld",
        "The sea buried the entrance. It never put out the lights.",
        "ocean_monument_1161.json.gz",
        "Overworld",
    ),
    WorldEntry(
        "ancient_city_121",
        "Ancient City",
        "Java 1.21 | Deep Dark",
        "The streets are empty. Beneath them, something has learned to listen.",
        "ancient_city_121.json.gz",
        "Overworld",
    ),
    WorldEntry(
        "trial_chamber_121",
        "Trial Chamber",
        "Java 1.21 | Overworld",
        "They sealed every door from inside. The lamps have not gone out.",
        "trial_chamber_121.json.gz",
        "Overworld",
    ),
    WorldEntry(
        "village_plains_1161",
        "Plains World",
        "Java 1.16.1 | Overworld",
        "The fields end where the sand begins. An older doorway waits beyond them.",
        "village_plains_1161.json.gz",
        "Overworld",
    ),
    WorldEntry(
        "village_desert_1161",
        "Desert World",
        "Java 1.16.1 | Overworld",
        "The village draws from one well. Beyond it, the pyramid keeps its own counsel.",
        "village_desert_1161.json.gz",
        "Overworld",
    ),
    WorldEntry(
        "village_savanna_1161",
        "Savanna World",
        "Java 1.16.1 | Overworld",
        "Smoke above the roofs. Silence at the temple. One path joins them.",
        "village_savanna_1161.json.gz",
        "Overworld",
    ),
    WorldEntry(
        "village_taiga_1161",
        "Taiga World",
        "Java 1.16.1 | Overworld",
        "The village bell carries to the outpost. Nobody there answers.",
        "village_taiga_1161.json.gz",
        "Overworld",
    ),
    WorldEntry(
        "village_snowy_1161",
        "Snowbound World",
        "Java 1.16.1 | Overworld",
        "The paths vanish every night. Every morning, someone clears them.",
        "village_snowy_1161.json.gz",
        "Overworld",
    ),
)


def world_catalog(worlds_dir: str) -> List[WorldEntry]:
    """Return only scenes present in the source tree or frozen bundle."""
    return [entry for entry in WORLD_ENTRIES if os.path.isfile(os.path.join(worlds_dir, entry.filename))]
