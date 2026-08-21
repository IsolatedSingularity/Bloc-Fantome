"""Read a bounded, editable slice from a Minecraft Java Anvil world.

The importer intentionally uses only the Python standard library. It decodes
modern palette-based chunk sections from official Java ``.mca`` region files
and returns canonical block names and states. World generation remains Java's
job; Bloc Fantome imports the resulting block data without pretending to be a
seed-compatible generator.
"""

from __future__ import annotations

from dataclasses import dataclass
import gzip
import io
import math
from pathlib import Path
import re
import struct
from typing import Dict, Iterator, List, Mapping, Optional, Tuple
import zlib


class AnvilError(ValueError):
    pass


class _NBTReader:
    def __init__(self, data: bytes) -> None:
        self.stream = io.BytesIO(data)

    def _read(self, size: int) -> bytes:
        data = self.stream.read(size)
        if len(data) != size:
            raise AnvilError("truncated NBT payload")
        return data

    def byte(self) -> int:
        return struct.unpack(">b", self._read(1))[0]

    def ubyte(self) -> int:
        return self._read(1)[0]

    def short(self) -> int:
        return struct.unpack(">h", self._read(2))[0]

    def int(self) -> int:
        return struct.unpack(">i", self._read(4))[0]

    def long(self) -> int:
        return struct.unpack(">q", self._read(8))[0]

    def string(self) -> str:
        size = struct.unpack(">H", self._read(2))[0]
        return self._read(size).decode("utf-8", errors="replace")

    def payload(self, tag: int):
        if tag == 1:
            return self.byte()
        if tag == 2:
            return self.short()
        if tag == 3:
            return self.int()
        if tag == 4:
            return self.long()
        if tag == 5:
            return struct.unpack(">f", self._read(4))[0]
        if tag == 6:
            return struct.unpack(">d", self._read(8))[0]
        if tag == 7:
            return self._read(self.int())
        if tag == 8:
            return self.string()
        if tag == 9:
            child = self.ubyte()
            length = self.int()
            if length < 0:
                raise AnvilError("negative NBT list length")
            return [self.payload(child) for _ in range(length)]
        if tag == 10:
            result = {}
            while True:
                child = self.ubyte()
                if child == 0:
                    return result
                name = self.string()
                result[name] = self.payload(child)
        if tag == 11:
            length = self.int()
            return [self.int() for _ in range(length)]
        if tag == 12:
            length = self.int()
            return [self.long() for _ in range(length)]
        raise AnvilError(f"unsupported NBT tag {tag}")

    def root(self) -> Mapping[str, object]:
        tag = self.ubyte()
        if tag != 10:
            raise AnvilError("chunk NBT root is not a compound")
        self.string()
        value = self.payload(tag)
        if not isinstance(value, dict):
            raise AnvilError("invalid chunk NBT root")
        return value


@dataclass(frozen=True)
class JavaBlock:
    x: int
    y: int
    z: int
    name: str
    properties: Mapping[str, str]


def _decompress_chunk(payload: bytes, compression: int) -> bytes:
    if compression == 1:
        return gzip.decompress(payload)
    if compression == 2:
        return zlib.decompress(payload)
    if compression == 3:
        return payload
    raise AnvilError(f"unsupported Anvil compression type {compression}")


def _region_coords(path: Path) -> Tuple[int, int]:
    match = re.fullmatch(r"r\.(-?\d+)\.(-?\d+)\.mca", path.name)
    if not match:
        raise AnvilError(f"invalid region filename: {path.name}")
    return int(match.group(1)), int(match.group(2))


def _read_region_chunk(path: Path, chunk_x: int, chunk_z: int) -> Optional[Mapping[str, object]]:
    region_x, region_z = _region_coords(path)
    local_x = chunk_x - region_x * 32
    local_z = chunk_z - region_z * 32
    if not (0 <= local_x < 32 and 0 <= local_z < 32):
        return None
    with path.open("rb") as handle:
        handle.seek((local_x + local_z * 32) * 4)
        location = handle.read(4)
        if len(location) != 4:
            raise AnvilError(f"truncated region header: {path}")
        sector = int.from_bytes(location[:3], "big")
        if sector == 0:
            return None
        handle.seek(sector * 4096)
        raw_length = handle.read(4)
        if len(raw_length) != 4:
            raise AnvilError(f"truncated chunk header: {path}")
        length = int.from_bytes(raw_length, "big")
        if length < 1 or length > 255 * 4096:
            raise AnvilError(f"invalid chunk length in {path}")
        compression = handle.read(1)
        payload = handle.read(length - 1)
        if len(compression) != 1 or len(payload) != length - 1:
            raise AnvilError(f"truncated chunk payload: {path}")
    compression_type = compression[0]
    if compression_type & 0x80:
        external_path = path.with_name(f"c.{chunk_x}.{chunk_z}.mcc")
        if not external_path.is_file():
            raise AnvilError(f"external chunk payload is missing: {external_path}")
        payload = external_path.read_bytes()
        compression_type &= 0x7F
    return _NBTReader(_decompress_chunk(payload, compression_type)).root()


def _section_palette(section: Mapping[str, object]):
    states = section.get("block_states")
    if isinstance(states, dict):
        return states.get("palette"), states.get("data")
    return section.get("Palette"), section.get("BlockStates")


def _palette_indices(palette_size: int, packed: object) -> Iterator[int]:
    if palette_size <= 1 or not isinstance(packed, list) or not packed:
        yield from (0 for _ in range(4096))
        return
    bits = max(4, math.ceil(math.log2(palette_size)))
    values_per_long = 64 // bits
    mask = (1 << bits) - 1
    for index in range(4096):
        packed_index = index // values_per_long
        if packed_index >= len(packed):
            yield 0
            continue
        value = int(packed[packed_index]) & 0xFFFFFFFFFFFFFFFF
        yield (value >> ((index % values_per_long) * bits)) & mask


def _iter_chunk_blocks(root: Mapping[str, object], chunk_x: int, chunk_z: int) -> Iterator[JavaBlock]:
    level = root.get("Level") if isinstance(root.get("Level"), dict) else root
    sections = level.get("sections", level.get("Sections", []))
    if not isinstance(sections, list):
        return
    for section in sections:
        if not isinstance(section, dict) or "Y" not in section:
            continue
        palette, packed = _section_palette(section)
        if not isinstance(palette, list) or not palette:
            continue
        section_y = int(section["Y"])
        for index, palette_index in enumerate(_palette_indices(len(palette), packed)):
            if palette_index >= len(palette):
                continue
            state = palette[palette_index]
            if not isinstance(state, dict):
                continue
            name = str(state.get("Name", "minecraft:air"))
            if name in ("minecraft:air", "minecraft:cave_air", "minecraft:void_air"):
                continue
            local_x = index & 15
            local_z = (index >> 4) & 15
            local_y = (index >> 8) & 15
            properties = state.get("Properties", {})
            if not isinstance(properties, dict):
                properties = {}
            yield JavaBlock(
                chunk_x * 16 + local_x,
                section_y * 16 + local_y,
                chunk_z * 16 + local_z,
                name,
                {str(key): str(value) for key, value in properties.items()},
            )


def dimension_region_dir(world: Path, dimension: str) -> Path:
    candidates = {
        "overworld": (world / "region",),
        "nether": (world / "DIM-1" / "region",),
        "end": (world / "DIM1" / "region",),
    }.get(dimension.lower())
    if candidates is None:
        raise AnvilError(f"unknown dimension {dimension}")
    region = candidates[0]
    if not region.is_dir():
        raise AnvilError(f"{dimension} region folder not found in {world}")
    return region


def import_slice(
    world_path: str,
    dimension: str,
    center_chunk_x: int = 0,
    center_chunk_z: int = 0,
    radius: int = 4,
) -> Tuple[List[JavaBlock], Tuple[int, int, int, int], Mapping[str, object]]:
    """Import a square chunk slice and normalize its X/Z origin for the editor."""
    radius = max(0, min(7, int(radius)))
    region_dir = dimension_region_dir(Path(world_path), dimension)
    min_chunk_x = center_chunk_x - radius
    min_chunk_z = center_chunk_z - radius
    side = radius * 2 + 1
    blocks: List[JavaBlock] = []
    data_versions = set()
    for chunk_z in range(min_chunk_z, center_chunk_z + radius + 1):
        for chunk_x in range(min_chunk_x, center_chunk_x + radius + 1):
            region_path = region_dir / f"r.{chunk_x // 32}.{chunk_z // 32}.mca"
            if not region_path.is_file():
                continue
            root = _read_region_chunk(region_path, chunk_x, chunk_z)
            if root:
                if isinstance(root.get("DataVersion"), int):
                    data_versions.add(int(root["DataVersion"]))
                blocks.extend(_iter_chunk_blocks(root, chunk_x, chunk_z))
    if not blocks:
        raise AnvilError("no generated chunks were found around those chunk coordinates")

    origin_x = min_chunk_x * 16
    origin_z = min_chunk_z * 16
    normalized = [
        JavaBlock(block.x - origin_x, block.y, block.z - origin_z, block.name, block.properties)
        for block in blocks
    ]
    if dimension.lower() == "overworld":
        min_y, height = (-64, 384) if min(block.y for block in normalized) < 0 else (0, 256)
    else:
        min_y, height = 0, 256
    bounds = (side * 16, side * 16, height, min_y)
    metadata = {
        "kind": "java_chunk_import",
        "provider": "Minecraft Java Anvil region data",
        "version": (
            f"Java DataVersion {min(data_versions)}"
            if len(data_versions) == 1
            else f"Java DataVersion {min(data_versions)}-{max(data_versions)}"
            if data_versions
            else "palette block states"
        ),
        "accuracy": "official generated chunk blocks; unsupported editor models use documented material fallbacks",
        "source_center_chunk": [center_chunk_x, center_chunk_z],
        "render_radius_chunks": radius,
    }
    return normalized, bounds, metadata
