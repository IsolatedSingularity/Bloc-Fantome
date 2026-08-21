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
        "bastion_treasure_1161",
        "Treasure Bastion",
        "Java 1.16.1 | Nether",
        "Full jigsaw assembly in a large editable Nether habitat.",
        "bastion_treasure_1161.json.gz",
        "Nether",
    ),
    WorldEntry(
        "bastion_bridge_1161",
        "Bridge Bastion",
        "Java 1.16.1 | Nether",
        "Complete bridge assembly spanning a rough Nether shelf.",
        "bastion_bridge_1161.json.gz",
        "Nether",
    ),
    WorldEntry(
        "bastion_hoglin_stable_1161",
        "Hoglin Stable Bastion",
        "Java 1.16.1 | Nether",
        "Complete stable assembly with canonical pool connections.",
        "bastion_hoglin_stable_1161.json.gz",
        "Nether",
    ),
    WorldEntry(
        "bastion_housing_units_1161",
        "Housing Units Bastion",
        "Java 1.16.1 | Nether",
        "Complete housing assembly in an editable Nether habitat.",
        "bastion_housing_units_1161.json.gz",
        "Nether",
    ),
    WorldEntry(
        "basalt_deltas_1161",
        "Basalt Deltas",
        "Java 1.16.1 | Nether",
        "Standalone basalt-and-blackstone delta habitat with magma columns.",
        "basalt_deltas_1161.json.gz",
        "Nether",
    ),
    WorldEntry(
        "end_city_1161",
        "End City",
        "Java 1.16.1 | The End",
        "Source-shaped recursive city on a broad editable End island.",
        "end_city_1161.json.gz",
        "The End",
    ),
    WorldEntry(
        "ancient_city_121",
        "Ancient City",
        "Java 1.21 | Deep Dark",
        "Full canonical jigsaw assembly with a deepslate and sculk habitat.",
        "ancient_city_121.json.gz",
        "Overworld",
    ),
    WorldEntry(
        "trial_chamber_121",
        "Trial Chamber",
        "Java 1.21 | Overworld",
        "Complete source-pool chamber network below representative stone.",
        "trial_chamber_121.json.gz",
        "Overworld",
    ),
    WorldEntry(
        "village_plains_1161",
        "Plains Village",
        "Java 1.16.1 | Overworld",
        "Six-level village assembly on gently rolling plains.",
        "village_plains_1161.json.gz",
        "Overworld",
    ),
    WorldEntry(
        "village_desert_1161",
        "Desert Village",
        "Java 1.16.1 | Overworld",
        "Six-level desert assembly in a broad sand habitat.",
        "village_desert_1161.json.gz",
        "Overworld",
    ),
    WorldEntry(
        "village_savanna_1161",
        "Savanna Village",
        "Java 1.16.1 | Overworld",
        "Six-level acacia settlement on representative savanna terrain.",
        "village_savanna_1161.json.gz",
        "Overworld",
    ),
    WorldEntry(
        "village_taiga_1161",
        "Taiga Village",
        "Java 1.16.1 | Overworld",
        "Six-level spruce settlement on a cool rolling habitat.",
        "village_taiga_1161.json.gz",
        "Overworld",
    ),
    WorldEntry(
        "village_snowy_1161",
        "Snowy Village",
        "Java 1.16.1 | Overworld",
        "Six-level snowy settlement with an editable snowfield.",
        "village_snowy_1161.json.gz",
        "Overworld",
    ),
)


def world_catalog(worlds_dir: str) -> List[WorldEntry]:
    """Return only scenes present in the source tree or frozen bundle."""
    return [entry for entry in WORLD_ENTRIES if os.path.isfile(os.path.join(worlds_dir, entry.filename))]
