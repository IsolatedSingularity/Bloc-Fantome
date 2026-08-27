"""Derive compact World Map pieces from the local Java 1.16.1 NBT corpus.

The private Game Reference remains outside release artifacts. This tool emits
only the selected, editor-supported block/state records needed by the map.
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path
import sys


CODE_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = CODE_ROOT.parent
sys.path.insert(0, str(CODE_ROOT))

from domain.blocks import BlockType  # noqa: E402
from engine.anvil import _NBTReader  # noqa: E402


REFERENCE_ROOT = PROJECT_ROOT / "Game Reference" / "06_structure_templates_raw"
OUTPUT = CODE_ROOT / "world_map_templates.json.gz"
TEMPLATES = {
    "plains_house": "village/plains/houses/plains_small_house_1.nbt",
    "plains_farm": "village/plains/houses/plains_large_farm_1.nbt",
    "plains_center": "village/plains/town_centers/plains_meeting_point_1.nbt",
    "bastion_bridge": "bastion/bridge/bridge_pieces/bridge.nbt",
    "bastion_gate": "bastion/bridge/starting_pieces/entrance_face.nbt",
    "end_base": "end_city/base_floor.nbt",
    "end_tower_base": "end_city/tower_base.nbt",
    "end_tower_piece": "end_city/tower_piece.nbt",
    "end_tower_top": "end_city/tower_top.nbt",
    "end_bridge": "end_city/bridge_piece.nbt",
    "end_ship": "end_city/ship.nbt",
    "ocean_ruin_warm": "underwater_ruin/big_warm_5.nbt",
    "ocean_ruin_warm_small": "underwater_ruin/warm_6.nbt",
    "ocean_ruin_cold": "underwater_ruin/big_mossy_8.nbt",
    "ocean_ruin_cold_small": "underwater_ruin/mossy_4.nbt",
    "ocean_shipwreck": "shipwreck/with_mast.nbt",
}


ALIASES = {
    "CAVE_AIR": None,
    "VOID_AIR": None,
    "GRASS_BLOCK": "GRASS",
    "GRASS_PATH": "DIRT_PATH",
    "OAK_WOOD": "OAK_LOG",
    "STRIPPED_OAK_WOOD": "STRIPPED_OAK_LOG",
    "NETHER_BRICK": "NETHER_BRICKS",
    "RED_NETHER_BRICKS": "NETHER_BRICKS",
    "END_STONE_BRICK": "END_STONE_BRICKS",
    "SMOOTH_STONE_SLAB": "STONE_SLAB",
    "POLISHED_BLACKSTONE_BRICK_WALL": "POLISHED_BLACKSTONE_BRICKS",
    "POLISHED_BLACKSTONE_WALL": "BLACKSTONE",
    "BLACKSTONE_WALL": "BLACKSTONE",
    "PURPUR_WALL": "PURPUR_BLOCK",
    "CUT_SANDSTONE": "SANDSTONE",
    "CHISELED_SANDSTONE": "SANDSTONE",
    "MOSSY_COBBLESTONE_WALL": "MOSSY_COBBLESTONE",
}


def resolve(name: str) -> str | None:
    key = name.split(":", 1)[-1].upper()
    if key in ("AIR", "STRUCTURE_BLOCK", "JIGSAW", "STRUCTURE_VOID"):
        return None
    if key in BlockType.__members__:
        return key
    alias = ALIASES.get(key)
    if alias is not None or key in ALIASES:
        return alias
    material_aliases = {
        "POLISHED_BLACKSTONE_BRICK": "POLISHED_BLACKSTONE_BRICKS",
        "END_STONE_BRICK": "END_STONE_BRICKS",
        "STONE_BRICK": "STONE_BRICKS",
        "MOSSY_STONE_BRICK": "MOSSY_STONE_BRICKS",
        "PURPUR": "PURPUR_BLOCK",
        "OAK": "OAK_PLANKS",
        "BLACKSTONE": "BLACKSTONE",
    }
    for suffix in ("_STAIRS", "_SLAB", "_WALL", "_FENCE", "_FENCE_GATE"):
        if key.endswith(suffix):
            material = material_aliases.get(key[:-len(suffix)], key[:-len(suffix)])
            return material if material in BlockType.__members__ else None
    return None


def decode(relative_path: str) -> dict:
    path = REFERENCE_ROOT / relative_path
    root = _NBTReader(gzip.decompress(path.read_bytes())).root()
    # Structure blocks may store either one palette or a list of equivalent
    # palettes.  The bundled shipwrecks use the latter; the first palette is
    # the deterministic canonical variant used by vanilla's template loader.
    palette = root.get("palette")
    if palette is None:
        palettes = root.get("palettes", [])
        if not palettes:
            raise ValueError(f"Structure has no palette: {relative_path}")
        palette = palettes[0]
    records = []
    skipped = set()
    for block in root["blocks"]:
        state = palette[int(block["state"])]
        canonical = str(state.get("Name", "minecraft:air"))
        resolved = resolve(canonical)
        if resolved is None:
            if canonical not in (
                "minecraft:air", "minecraft:cave_air", "minecraft:void_air",
                "minecraft:structure_block", "minecraft:jigsaw",
                "minecraft:structure_void",
            ):
                skipped.add(canonical)
            continue
        source_x, source_y, source_z = map(int, block["pos"])
        properties = state.get("Properties", {})
        records.append([
            source_x,
            source_z,
            source_y,
            resolved,
            {str(key): str(value) for key, value in properties.items()},
        ])
    return {
        "source": relative_path.replace("\\", "/"),
        "source_size": list(map(int, root["size"])),
        "blocks": records,
        "skipped": sorted(skipped),
    }


def main() -> int:
    payload = {
        "format": 1,
        "minecraft_version": "Java 1.16.1",
        "provenance": "canonical structure-template NBT from Game Reference",
        "templates": {name: decode(path) for name, path in TEMPLATES.items()},
    }
    encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as archive:
            archive.write(encoded)
    for name, template in payload["templates"].items():
        print(
            f"{name}: {len(template['blocks'])} supported blocks; "
            f"{len(template['skipped'])} unsupported names"
        )
    print(f"Wrote {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
