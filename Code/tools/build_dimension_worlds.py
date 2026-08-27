"""Build the source-backed Nether fortress and deep-ocean gallery worlds."""

from __future__ import annotations

import gzip
import json
import math
from pathlib import Path


CODE_ROOT = Path(__file__).resolve().parents[1]
WORLDS_ROOT = CODE_ROOT / "worlds"
TEMPLATE_BUNDLE = CODE_ROOT / "world_map_templates.json.gz"


class SceneBuilder:
    def __init__(self, dimension: str):
        self.dimension = dimension
        self.blocks: dict[tuple[int, int, int], dict] = {}

    def put(self, x: int, y: int, z: int, block: str, *, role="terrain", state=None):
        if not (0 <= x < 256 and 0 <= y < 256 and 0 <= z < 256):
            return
        self.blocks[(x, y, z)] = {
            "x": x,
            "y": y,
            "z": z,
            "type": block,
            "minecraft": f"minecraft:{block.lower()}",
            "state": state or {},
            "role": role,
        }

    def shell(self, origin, size, block, *, role="structure"):
        ox, oy, oz = origin
        width, depth, height = size
        for x in range(width):
            for y in range(depth):
                for z in range(height):
                    if x in (0, width - 1) or y in (0, depth - 1) or z in (0, height - 1):
                        self.put(ox + x, oy + y, oz + z, block, role=role)

    def payload(self, scene: dict) -> dict:
        return {
            "version": 5,
            "dimension": self.dimension,
            "bounds": {"width": 256, "depth": 256, "height": 256, "min_y": 0},
            "scene": scene,
            "blocks": [self.blocks[position] for position in sorted(self.blocks)],
        }


def _surface_height(x: int, y: int, base: int, amplitude: float = 3.0) -> int:
    return base + round(
        amplitude * 0.48 * math.sin(x * 0.071)
        + amplitude * 0.34 * math.cos(y * 0.083)
        + amplitude * 0.18 * math.sin((x + y) * 0.137)
    )


def _fortress(builder: SceneBuilder) -> None:
    """A source-proportioned long bridge with crossings and castle pieces."""
    deck_z = 34
    for x in range(24, 232):
        for y in range(119, 126):
            builder.put(x, y, deck_z, "NETHER_BRICKS", role="structure")
            if y in (119, 125):
                builder.put(x, y, deck_z + 1, "NETHER_BRICKS", role="structure")
        if x % 24 == 0:
            for y in (121, 123):
                floor = _surface_height(x, y, 21)
                for z in range(floor, deck_z):
                    builder.put(x, y, z, "NETHER_BRICKS", role="structure")

    for cx in (62, 128, 194):
        for x in range(cx - 8, cx + 9):
            for y in range(101, 144):
                builder.put(x, y, deck_z, "NETHER_BRICKS", role="structure")
                edge = x in (cx - 8, cx + 8) or y in (101, 143)
                if edge:
                    for z in range(deck_z + 1, deck_z + 8):
                        if z not in (deck_z + 3, deck_z + 4) or (x + y) % 5:
                            builder.put(x, y, z, "NETHER_BRICKS", role="structure")
        for x in range(cx - 9, cx + 10):
            for y in range(100, 145):
                if x in (cx - 9, cx + 9) or y in (100, 144):
                    builder.put(x, y, deck_z + 8, "NETHER_BRICKS", role="structure")

    # Central lava-well room and blaze approach, both characteristic fortress beats.
    builder.shell((117, 110, deck_z + 1), (23, 23, 13), "NETHER_BRICKS")
    for x in range(125, 132):
        for y in range(118, 125):
            builder.put(x, y, deck_z + 1, "NETHER_BRICKS", role="structure")
    builder.put(128, 121, deck_z + 2, "LAVA", role="structure")
    for x in range(207, 224):
        for y in range(113, 132):
            if x in (207, 223) or y in (113, 131):
                builder.put(x, y, deck_z + 2, "NETHER_BRICKS", role="structure")


def build_nether() -> dict:
    builder = SceneBuilder("nether")
    for x in range(256):
        for y in range(256):
            top = _surface_height(x, y, 21, 5.0)
            if x < 116 and y < 116:
                surface, under = "WARPED_NYLIUM", "NETHERRACK"
            elif x >= 140 and y < 116:
                surface, under = "CRIMSON_NYLIUM", "NETHERRACK"
            elif x < 116 and y >= 140:
                surface = "SOUL_SAND" if (x + y) % 5 else "SOUL_SOIL"
                under = "SOUL_SOIL"
            elif x >= 140 and y >= 140:
                surface = "BASALT" if (x * 3 + y) % 5 else "BLACKSTONE"
                under = "BLACKSTONE"
            else:
                surface = under = "NETHERRACK"
            for z in range(max(0, top - 3), top):
                builder.put(x, y, z, under)
            builder.put(x, y, top, surface)
            if 126 <= x <= 133 and (y % 19) < 13:
                builder.put(x, y, top, "LAVA")

    for x, y, stem, cap in (
        (34, 36, "WARPED_STEM", "WARPED_WART_BLOCK"),
        (72, 84, "WARPED_STEM", "WARPED_WART_BLOCK"),
        (164, 43, "CRIMSON_STEM", "NETHER_WART_BLOCK"),
        (210, 82, "CRIMSON_STEM", "NETHER_WART_BLOCK"),
    ):
        top = _surface_height(x, y, 21, 5.0)
        for z in range(top + 1, top + 9):
            builder.put(x, y, z, stem)
        for dx in range(-3, 4):
            for dy in range(-3, 4):
                if abs(dx) + abs(dy) <= 4:
                    builder.put(x + dx, y + dy, top + 9, cap)
        builder.put(x + 1, y, top + 8, "SHROOMLIGHT")

    for x, y, height in ((162, 183, 14), (190, 215, 20), (225, 168, 11)):
        top = _surface_height(x, y, 21, 5.0)
        for z in range(top + 1, top + height):
            builder.put(x, y, z, "BASALT")
    for x in range(24, 103, 17):
        y = 192 + (x * 7) % 37
        top = _surface_height(x, y, 21, 5.0)
        for z in range(top + 1, top + 8):
            builder.put(x, y, z, "BONE_BLOCK")

    _fortress(builder)
    return builder.payload({
        "kind": "world",
        "id": "nether_fortress_biomes_1161",
        "name": "Nether Fortress Biome Expanse",
        "provider": "Java 1.16.1 local source corpus",
        "version": "1.16.1",
        "seed": 11610126,
        "source": "NetherFortressGenerator.java and Nether surface-builder sources",
        "accuracy": "source-proportioned fortress showcase across representative 1.16.1 biome regions",
        "structure_blocks": sum(block["role"] == "structure" for block in builder.blocks.values()),
        "default_terrain_view": "all",
        "exterior_shell_view": "original",
        "biome_regions": ["warped_forest", "crimson_forest", "soul_sand_valley", "basalt_deltas", "nether_wastes"],
    })


def _load_templates() -> dict:
    with gzip.open(TEMPLATE_BUNDLE, "rt", encoding="utf-8") as handle:
        return json.load(handle)["templates"]


def _place_template(builder: SceneBuilder, template: dict, origin, rotation=0):
    ox, oy, oz = origin
    width, _height, depth = map(int, template["source_size"])
    facing = ("north", "east", "south", "west")
    for sx, sy, sz, block, state in template["blocks"]:
        if rotation % 4 == 1:
            rx, ry = depth - 1 - sy, sx
        elif rotation % 4 == 2:
            rx, ry = width - 1 - sx, depth - 1 - sy
        elif rotation % 4 == 3:
            rx, ry = sy, width - 1 - sx
        else:
            rx, ry = sx, sy
        state = dict(state)
        if state.get("facing") in facing:
            state["facing"] = facing[(facing.index(state["facing"]) + rotation) % 4]
        builder.put(ox + rx, oy + ry, oz + sz, block, role="structure", state=state)


def _monument(builder: SceneBuilder, origin):
    ox, oy, base_z = origin
    tiers = (
        (0, 0, 58, 58, 5, "PRISMARINE_BRICKS"),
        (6, 6, 46, 46, 5, "PRISMARINE"),
        (13, 13, 32, 32, 6, "PRISMARINE_BRICKS"),
        (20, 20, 18, 18, 12, "DARK_PRISMARINE"),
    )
    level_z = base_z
    for dx, dy, width, depth, height, block in tiers:
        builder.shell((ox + dx, oy + dy, level_z), (width, depth, height), block)
        level_z += height - 1
    for side_x in (ox - 11, ox + 58):
        builder.shell((side_x, oy + 13, base_z + 3), (11, 32, 12), "PRISMARINE_BRICKS")
    for x in range(ox + 4, ox + 55, 7):
        for y in (oy, oy + 57):
            builder.put(x, y, base_z + 3, "SEA_LANTERN", role="structure")
    for y in range(oy + 4, oy + 55, 7):
        for x in (ox, ox + 57):
            builder.put(x, y, base_z + 3, "SEA_LANTERN", role="structure")
    for x in range(ox + 25, ox + 33):
        for z in range(base_z + 1, base_z + 7):
            builder.blocks.pop((x, oy, z), None)


def build_ocean() -> dict:
    builder = SceneBuilder("overworld")
    floor_heights = {}
    for x in range(256):
        for y in range(256):
            top = _surface_height(x, y, 13, 4.5)
            floor_heights[(x, y)] = top
            material = "GRAVEL" if (x * 5 + y * 3) % 13 < 4 else "SAND"
            for z in range(max(0, top - 3), top):
                builder.put(x, y, z, "STONE")
            builder.put(x, y, top, material)

    _monument(builder, (93, 83, 16))
    templates = _load_templates()
    _place_template(builder, templates["ocean_ruin_warm"], (28, 178, 16), rotation=1)
    _place_template(builder, templates["ocean_ruin_cold"], (192, 39, 16), rotation=2)
    _place_template(builder, templates["ocean_shipwreck"], (177, 181, 16), rotation=3)

    for x, y in ((35, 44), (56, 201), (78, 166), (168, 57), (214, 142), (229, 213)):
        top = floor_heights[(x, y)]
        for z in range(top + 1, top + 7 + (x + y) % 5):
            builder.put(x, y, z, "WATER")

    guardians = [
        {"type": "guardian", "position": [84, 102, 36], "scale": 1.1},
        {"type": "guardian", "position": [154, 119, 39], "scale": 0.95},
        {"type": "guardian", "position": [125, 157, 43], "scale": 1.0},
        {"type": "elder_guardian", "position": [122, 111, 33], "scale": 1.25},
    ]
    return builder.payload({
        "kind": "world",
        "id": "ocean_monument_1161",
        "name": "Deep Ocean Monument",
        "provider": "Java 1.16.1 local source and NBT corpus",
        "version": "1.16.1",
        "seed": 11610713,
        "source": "OceanMonumentGenerator.java plus canonical ocean-ruin and shipwreck NBT",
        "accuracy": "source-proportioned monument habitat with exact bundled ruin and shipwreck templates",
        "structure_blocks": sum(block["role"] == "structure" for block in builder.blocks.values()),
        "default_terrain_view": "all",
        "exterior_shell_view": "original",
        "underwater": True,
        "waterline": 52,
        "decorations": guardians,
    })


def _write(filename: str, payload: dict) -> None:
    path = WORLDS_ROOT / filename
    encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    with path.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as archive:
            archive.write(encoded)
    print(f"{filename}: {len(payload['blocks'])} blocks, {len(encoded)} bytes JSON")


def main() -> int:
    _write("nether_fortress_biomes_1161.json.gz", build_nether())
    _write("ocean_monument_1161.json.gz", build_ocean())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
