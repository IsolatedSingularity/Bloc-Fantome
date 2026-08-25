"""Replace the End City showcase's rectangular support pad with natural terrain."""

from __future__ import annotations

import gzip
import json
from collections import Counter
from pathlib import Path


WORLD_PATH = Path(__file__).resolve().parents[1] / "worlds" / "end_city_1161.json.gz"
PAD_LEFT, PAD_RIGHT = 99, 155
PAD_TOP, PAD_BOTTOM = 105, 150


def _column_tops(blocks):
    tops = {}
    for block in blocks:
        if block["type"] != "END_STONE":
            continue
        column = block["x"], block["y"]
        tops[column] = max(tops.get(column, -1), block["z"])
    return tops


def _coons_height(x, y, tops):
    """Interpolate the untouched four-sided terrain boundary into the pad."""
    left_x, right_x = PAD_LEFT - 1, PAD_RIGHT + 1
    top_y, bottom_y = PAD_TOP - 1, PAD_BOTTOM + 1
    u = (x - left_x) / (right_x - left_x)
    v = (y - top_y) / (bottom_y - top_y)
    top = tops[(x, top_y)]
    bottom = tops[(x, bottom_y)]
    left = tops[(left_x, y)]
    right = tops[(right_x, y)]
    top_left = tops[(left_x, top_y)]
    top_right = tops[(right_x, top_y)]
    bottom_left = tops[(left_x, bottom_y)]
    bottom_right = tops[(right_x, bottom_y)]
    edge_blend = (1 - v) * top + v * bottom + (1 - u) * left + u * right
    corner_blend = (
        (1 - u) * (1 - v) * top_left
        + u * (1 - v) * top_right
        + (1 - u) * v * bottom_left
        + u * v * bottom_right
    )
    # A tiny deterministic undulation avoids quantized interpolation bands.
    ripple = (((x * 17 + y * 29) % 7) - 3) * 0.14
    return max(2, round(edge_blend - corner_blend + ripple))


def main() -> None:
    scene = json.loads(gzip.decompress(WORLD_PATH.read_bytes()).decode("utf-8"))
    structure = [block for block in scene["blocks"] if block.get("role") == "structure"]
    terrain = [block for block in scene["blocks"] if block.get("role") != "structure"]
    tops = _column_tops(terrain)

    structure_base = {}
    for block in structure:
        column = block["x"], block["y"]
        structure_base[column] = min(structure_base.get(column, 999), block["z"])
    ground_contacts = {
        column for column, base in structure_base.items() if base == 19
    }

    rebuilt = []
    for block in terrain:
        inside_pad = (
            PAD_LEFT <= block["x"] <= PAD_RIGHT
            and PAD_TOP <= block["y"] <= PAD_BOTTOM
        )
        if not inside_pad:
            rebuilt.append(block)

    generated = []
    heights = {}
    for x in range(PAD_LEFT, PAD_RIGHT + 1):
        for y in range(PAD_TOP, PAD_BOTTOM + 1):
            column = x, y
            top = _coons_height(x, y, tops)
            if column in ground_contacts:
                top = 18
            base = structure_base.get(column)
            if base is not None:
                top = min(top, base - 1)
            heights[column] = top
            thickness = 7 + ((x * 11 + y * 5) % 3)
            bottom = max(0, top - thickness)
            for z in range(bottom, top + 1):
                generated.append({
                    "x": x, "y": y, "z": z,
                    "type": "END_STONE", "role": "terrain",
                })

    for column, base in structure_base.items():
        if column in heights and heights[column] >= base:
            raise RuntimeError(f"terrain intersects structure at {column}")
    if any(heights[column] != 18 for column in ground_contacts if column in heights):
        raise RuntimeError("a ground-contact structure column lost exact support")
    if len(set(heights.values())) < 5:
        raise RuntimeError("replacement terrain is still visually flat")

    scene["blocks"] = rebuilt + generated + structure
    scene["scene"]["terrain_note"] = (
        "natural boundary-interpolated End island with exact ground-contact support"
    )
    payload = json.dumps(scene, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    WORLD_PATH.write_bytes(gzip.compress(payload, compresslevel=9, mtime=0))
    distribution = Counter(heights.values())
    print(
        f"reshaped {len(heights)} columns; height range "
        f"{min(heights.values())}..{max(heights.values())}; {dict(sorted(distribution.items()))}"
    )


if __name__ == "__main__":
    main()
