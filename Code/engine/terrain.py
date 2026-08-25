"""Deterministic, source-informed terrain slices for the editor.

This intentionally models a readable vertical slice/habitat rather than
claiming chunk-for-chunk parity. Exact generated chunks belong to the Java
world importer; the UI records this provider boundary in scene metadata.
"""

from math import cos, floor, pi, sin, sqrt
from typing import Iterator, Tuple


Cell = Tuple[int, int, int, str]


def _hash2(x: int, y: int, seed: int) -> float:
    value = (x * 0x1F123BB5) ^ (y * 0x5F356495) ^ seed
    value = (value ^ (value >> 15)) * 0x2C1B3C6D
    value = (value ^ (value >> 12)) * 0x297A2D39
    value ^= value >> 15
    return (value & 0xFFFFFFFF) / 0xFFFFFFFF


def _smooth(value: float) -> float:
    return value * value * (3.0 - 2.0 * value)


def _value_noise(x: float, y: float, seed: int) -> float:
    x0, y0 = floor(x), floor(y)
    tx, ty = _smooth(x - x0), _smooth(y - y0)
    a = _hash2(x0, y0, seed)
    b = _hash2(x0 + 1, y0, seed)
    c = _hash2(x0, y0 + 1, seed)
    d = _hash2(x0 + 1, y0 + 1, seed)
    top = a + (b - a) * tx
    bottom = c + (d - c) * tx
    return (top + (bottom - top) * ty) * 2.0 - 1.0


def _octaves(x: float, y: float, seed: int) -> float:
    value = 0.0
    amplitude = 1.0
    total = 0.0
    frequency = 0.018
    for octave in range(5):
        value += _value_noise(x * frequency, y * frequency, seed + octave * 1013) * amplitude
        total += amplitude
        amplitude *= 0.5
        frequency *= 2.0
    return value / total


def local_height_offset(x: int, y: int, seed: int, maximum: int = 3) -> int:
    """Return a smooth, compact elevation for sculpting an existing flat pad."""
    maximum = max(0, int(maximum))
    if maximum == 0:
        return 0
    broad = _value_noise(x * 0.18, y * 0.18, seed)
    detail = _value_noise(x * 0.41, y * 0.41, seed ^ 0x51C07)
    normalized = max(0.0, min(1.0, 0.5 + broad * 0.38 + detail * 0.12))
    return max(0, min(maximum, round(normalized * maximum)))


def _column(x: int, y: int, top: int, surface: str, filler: str, base: str,
            min_y: int) -> Iterator[Cell]:
    bottom = max(min_y, top - 5)
    for z in range(bottom, top + 1):
        block = surface if z == top else filler if z >= top - 3 else base
        yield x, y, z, block


def terrain_cells(dimension: str, width: int, depth: int, seed: int,
                  min_y: int = 0) -> Iterator[Cell]:
    """Yield sparse terrain cells for one editable canvas."""
    center_x = (width - 1) / 2.0
    center_y = (depth - 1) / 2.0
    for x in range(width):
        for y in range(depth):
            broad = _octaves(x, y, seed)
            detail = _octaves(x * 2.7, y * 2.7, seed ^ 0x5A17)
            climate = _value_noise(x * 0.009, y * 0.009, seed ^ 0xC11A7E)

            if dimension == "overworld":
                river = abs(sin((x + broad * 18.0) * 0.045) + cos((y - broad * 13.0) * 0.038))
                top = round(64 + broad * 15 + detail * 4)
                if river < 0.18:
                    top = min(top, 59 + round(detail * 2))
                if climate > 0.45:
                    surface, filler = "SAND", "SAND"
                elif climate < -0.55:
                    surface, filler = "SNOW", "DIRT"
                else:
                    surface, filler = "GRASS", "DIRT"
                yield from _column(x, y, top, surface, filler, "STONE", min_y)
                if top < 63:
                    for z in range(top + 1, 64):
                        yield x, y, z, "WATER"

            elif dimension == "nether":
                top = round(31 + broad * 10 + detail * 3)
                if climate > 0.45:
                    surface, filler = "CRIMSON_NYLIUM", "NETHERRACK"
                elif climate > 0.05:
                    surface, filler = "WARPED_NYLIUM", "NETHERRACK"
                elif climate < -0.48:
                    surface, filler = "SOUL_SAND", "SOUL_SOIL"
                else:
                    surface, filler = "BASALT", "BLACKSTONE"
                yield from _column(x, y, top, surface, filler, "NETHERRACK", min_y)
                if _hash2(x, y, seed ^ 0x1A7A) > 0.992:
                    yield x, y, top + 1, "MAGMA_BLOCK"

            else:
                dx, dy = x - center_x, y - center_y
                radius = sqrt(dx * dx + dy * dy)
                island = 78.0 + broad * 19.0
                if radius > island:
                    continue
                edge = max(0.0, (island - radius) / 18.0)
                top = round(56 + detail * 4 + min(1.0, edge) * 3)
                thickness = max(2, round(3 + min(1.0, edge) * 5))
                for z in range(max(min_y, top - thickness), top + 1):
                    yield x, y, z, "END_STONE"
