"""Compose cursor-placeable built-in and JSON-backed structure definitions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping, Optional

from domain.blocks import (
    BlockProperties,
    BlockType,
    DoorHalf,
    DoorHinge,
    Facing,
    SlabPosition,
    StairShape,
)
from domain.dimensions import DIMENSION_OVERWORLD


JSON_STRUCTURE_LIBRARY = {
    "bastion_bridge_edge": "Housing Units Bastion Piece",
    "bastion_remnant_no_lava": "Hoglin Stable Bastion Piece",
    "bastion_remnant_with_lava": "Treasure Bastion Lava Basin",
    "end_city_tower": "End City Tower",
    "ruined_portal_accurate": "Ruined Portal",
    "warped_forest_accurate": "Warped Forest",
}


def properties_from_structure_state(
    block_type: BlockType,
    state_data,
    definitions: Mapping,
) -> Optional[BlockProperties]:
    """Translate canonical Java block-state strings for cursor structures."""
    if not isinstance(state_data, dict) or not state_data:
        return None
    definition = definitions.get(block_type)
    if not definition or not (
        definition.isDoor
        or definition.isStair
        or definition.isSlab
        or definition.modelKind
    ):
        return None
    properties = BlockProperties()
    properties.facing = Facing.__members__.get(
        str(state_data.get("facing", "south")).upper(), Facing.SOUTH
    )
    open_value = state_data.get("isOpen", state_data.get("open", False))
    properties.isOpen = open_value is True or str(open_value).casefold() == "true"
    vertical_half = state_data.get(
        "slabPosition",
        state_data.get("half" if definition.isStair else "type", "bottom"),
    )
    properties.slabPosition = SlabPosition.__members__.get(
        str(vertical_half).upper(), SlabPosition.BOTTOM
    )
    properties.stairShape = StairShape.__members__.get(
        str(state_data.get("stairShape", state_data.get("shape", "straight"))).upper(),
        StairShape.STRAIGHT,
    )
    properties.doorHalf = DoorHalf.__members__.get(
        str(state_data.get("doorHalf", state_data.get("half", "lower"))).upper(),
        DoorHalf.LOWER,
    )
    properties.doorHinge = DoorHinge.__members__.get(
        str(state_data.get("doorHinge", state_data.get("hinge", "left"))).upper(),
        DoorHinge.LEFT,
    )
    return properties


def structure_block_parts(block):
    """Return a uniform five-part cursor-structure cell tuple."""
    x, y, z, block_type = block[:4]
    properties = block[4] if len(block) > 4 else None
    return x, y, z, block_type, properties


def load_json_structures(
    structure_directory,
    definitions: Mapping,
    library: Mapping[str, str] = JSON_STRUCTURE_LIBRARY,
) -> dict:
    """Load and normalize curated JSON structures without global mutation."""
    directory = Path(structure_directory)
    loaded = {}
    for structure_key, display_name in library.items():
        filepath = directory / f"{structure_key}.json"
        if not filepath.is_file():
            if directory.exists():
                print(f"Built-in structure unavailable: {filepath}")
            continue
        try:
            with filepath.open("r", encoding="utf-8") as handle:
                save_data = json.load(handle)
            converted = []
            for block in save_data.get("blocks", []):
                block_type = BlockType[block["type"]]
                converted.append((
                    int(block["x"]),
                    int(block["y"]),
                    int(block["z"]),
                    block_type,
                    properties_from_structure_state(
                        block_type, block.get("state", {}), definitions
                    ),
                ))
            if not converted:
                continue

            min_x = min(block[0] for block in converted)
            max_x = max(block[0] for block in converted)
            min_y = min(block[1] for block in converted)
            max_y = max(block[1] for block in converted)
            min_z = min(block[2] for block in converted)
            center_x = (min_x + max_x) // 2
            center_y = (min_y + max_y) // 2
            loaded[structure_key] = {
                "name": display_name,
                "blocks": [
                    (x - center_x, y - center_y, z - min_z, block_type, properties)
                    for x, y, z, block_type, properties in converted
                ],
                "dimension": save_data.get("dimension", DIMENSION_OVERWORLD),
                "source_file": str(filepath),
            }
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
            print(f"Could not load built-in structure '{structure_key}': {error}")
    return loaded


def compose_structure_registry(
    builtin_structures: Mapping,
    *,
    structure_directory,
    definitions: Mapping,
    library: Mapping[str, str] = JSON_STRUCTURE_LIBRARY,
) -> dict:
    """Return a new ordered registry containing built-ins then JSON entries."""
    registry = dict(builtin_structures)
    registry.update(load_json_structures(structure_directory, definitions, library))
    return registry
