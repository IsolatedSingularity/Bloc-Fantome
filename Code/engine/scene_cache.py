"""Safe persistent staging cache for bundled editable world scenes."""

from __future__ import annotations

import hashlib
import json
import os
import struct
import tempfile
from typing import Iterable

from engine.block_state import (
    BlockProperties,
    DoorHalf,
    DoorHinge,
    Facing,
    SlabPosition,
    StairShape,
)


MAGIC = b"BFC8"
HEADER = struct.Struct("<4s32sI")
RECORD = struct.Struct("<hhhHHBBBBBBBBBBii")
STAIR_SHAPES = tuple(StairShape)


def source_digest(path: str) -> bytes:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.digest()


def cache_path(cache_dir: str, source_path: str, digest: bytes) -> str:
    basename = os.path.basename(source_path).removesuffix(".json.gz")
    return os.path.join(cache_dir, f"{basename}-{digest.hex()[:16]}.bfc")


def load(path: str, expected_digest: bytes, block_type):
    with open(path, "rb") as handle:
        magic, digest, metadata_size = HEADER.unpack(handle.read(HEADER.size))
        if magic != MAGIC or digest != expected_digest or metadata_size > 1024 * 1024:
            raise ValueError("Stale or invalid world cache")
        metadata_bytes = handle.read(metadata_size)
        metadata = json.loads(metadata_bytes.decode("utf-8"))
        count_data = handle.read(4)
        if len(count_data) != 4:
            raise ValueError("Truncated world cache")
        count = struct.unpack("<I", count_data)[0]
        payload = handle.read()
    if len(payload) < 32:
        raise ValueError("Missing world cache checksum")
    payload, checksum = payload[:-32], payload[-32:]
    actual = hashlib.sha256(metadata_bytes)
    actual.update(count_data)
    actual.update(payload)
    if actual.digest() != checksum:
        raise ValueError("Damaged world cache payload")
    if len(payload) != count * RECORD.size:
        raise ValueError("Invalid world cache record count")

    staged = []
    block_types_by_value = {member.value: member for member in block_type}
    structure_positions = set()
    exterior_glass_positions = set()
    structure_surfaces_by_view = {rotation: set() for rotation in range(4)}
    surface_positions = set()
    view_surface_positions_by_view = {rotation: set() for rotation in range(4)}
    for values in RECORD.iter_unpack(payload):
        x, y, z, type_value, flags, facing, slab, stair, door_half, hinge, liquid, oxidation, power, delay, state_flags, capture_index, palette = values
        props = None
        if flags & 1:
            props = BlockProperties(
                facing=Facing(facing),
                isOpen=bool(flags & 32),
                slabPosition=SlabPosition(slab),
                stairShape=STAIR_SHAPES[stair],
                doorHalf=DoorHalf.UPPER if door_half else DoorHalf.LOWER,
                doorHinge=DoorHinge.RIGHT if hinge else DoorHinge.LEFT,
                oxidationStage=oxidation, redstonePower=power, repeaterDelay=delay,
                powered=bool(state_flags & 1), repeaterLocked=bool(state_flags & 2),
                pistonExtended=bool(state_flags & 4), sticky=bool(state_flags & 8),
                comparatorSubtract=bool(state_flags & 16),
                sourceCapture=metadata["captures"][capture_index], sourcePalette=palette,
            )
        liquid_state = None
        if flags & 4:
            liquid_state = (max(1, min(8, liquid)), bool(flags & 8), bool(flags & 16))
        try:
            parsed_block_type = block_types_by_value[type_value]
        except KeyError as error:
            raise ValueError("Invalid block type in world cache") from error
        staged.append((x, y, z, parsed_block_type, props, liquid_state))
        if flags & 2:
            structure_positions.add((x, y, z))
        if flags & 64:
            exterior_glass_positions.add((x, y, z))
        for rotation in range(4):
            if flags & (128 << rotation):
                structure_surfaces_by_view[rotation].add((x, y, z))
        if flags & 2048:
            surface_positions.add((x, y, z))
        for rotation in range(4):
            if flags & (4096 << rotation):
                view_surface_positions_by_view[rotation].add((x, y, z))
    scene = dict(metadata.get("scene", {}))
    scene["_structure_positions"] = structure_positions
    scene["_exterior_glass_positions"] = exterior_glass_positions
    scene["_structure_surfaces_by_view"] = structure_surfaces_by_view
    scene["_surface_positions"] = surface_positions
    scene["_view_surface_positions_by_view"] = view_surface_positions_by_view
    bounds = tuple(metadata["bounds"])
    if len(bounds) != 4:
        raise ValueError("Invalid world cache bounds")
    width, depth, height, min_y = bounds
    if not (1 <= width <= 512 and 1 <= depth <= 512 and 1 <= height <= 512):
        raise ValueError("Invalid world cache dimensions")
    if any(
        not (0 <= x < width and 0 <= y < depth and min_y <= z < min_y + height)
        for x, y, z, *_ in staged
    ):
        raise ValueError("World cache record is outside declared bounds")
    return metadata["dimension"], bounds, scene, staged, metadata.get("skipped_count", 0)


def write(path: str, digest: bytes, dimension: str, bounds, scene,
          staged: Iterable, structure_positions,
          exterior_glass_positions=(), structure_surfaces_by_view=None,
          surface_positions=(), view_surface_positions_by_view=None, skipped_count=0) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    staged = tuple(staged)
    serialized_scene = {
        key: value for key, value in scene.items() if not key.startswith("_")
    }
    captures = sorted({props.sourceCapture for *_, props, liquid in staged if props is not None})
    capture_indices = {name: index for index, name in enumerate(captures)}
    metadata = json.dumps(
        {"dimension": dimension, "bounds": list(bounds), "scene": serialized_scene,
         "captures": captures, "skipped_count": skipped_count},
        separators=(",", ":"),
    ).encode("utf-8")
    fd, temp_path = tempfile.mkstemp(prefix=os.path.basename(path) + ".", suffix=".tmp",
                                     dir=os.path.dirname(path))
    os.close(fd)
    structure_surfaces_by_view = structure_surfaces_by_view or {}
    view_surface_positions_by_view = view_surface_positions_by_view or {}
    try:
        with open(temp_path, "wb") as handle:
            handle.write(HEADER.pack(MAGIC, digest, len(metadata)))
            handle.write(metadata)
            handle.write(struct.pack("<I", len(staged)))
            for x, y, z, block, props, liquid_state in staged:
                flags = 2 if (x, y, z) in structure_positions else 0
                if (x, y, z) in exterior_glass_positions:
                    flags |= 64
                for rotation in range(4):
                    if (x, y, z) in structure_surfaces_by_view.get(rotation, ()):
                        flags |= 128 << rotation
                if (x, y, z) in surface_positions:
                    flags |= 2048
                for rotation in range(4):
                    if (x, y, z) in view_surface_positions_by_view.get(rotation, ()):
                        flags |= 4096 << rotation
                facing = slab = stair = door_half = hinge = liquid = 0
                if props is not None:
                    flags |= 1
                    if props.isOpen:
                        flags |= 32
                    facing = props.facing.value
                    slab = props.slabPosition.value
                    stair = STAIR_SHAPES.index(props.stairShape)
                    door_half = 1 if props.doorHalf == DoorHalf.UPPER else 0
                    hinge = 1 if props.doorHinge == DoorHinge.RIGHT else 0
                if liquid_state is not None:
                    flags |= 4
                    liquid, source, falling = liquid_state
                    if source:
                        flags |= 8
                    if falling:
                        flags |= 16
                handle.write(RECORD.pack(
                    x, y, z, block.value, flags, facing, slab, stair,
                    door_half, hinge, liquid,
                    props.oxidationStage if props else 0,
                    props.redstonePower if props else 0,
                    props.repeaterDelay if props else 1,
                    (int(props.powered) | int(props.repeaterLocked) << 1 |
                     int(props.pistonExtended) << 2 | int(props.sticky) << 3 |
                     int(props.comparatorSubtract) << 4) if props else 0,
                    capture_indices[props.sourceCapture] if props else -1,
                    props.sourcePalette if props else -1,
                ))
        with open(temp_path, "rb") as stream:
            stream.seek(HEADER.size)
            checksum = hashlib.file_digest(stream, "sha256").digest()
        with open(temp_path, "ab") as stream:
            stream.write(checksum)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_path, path)
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def prune(cache_dir: str, maximum_bytes: int = 1024 * 1024 * 1024) -> None:
    if not os.path.isdir(cache_dir):
        return
    entries = []
    for name in os.listdir(cache_dir):
        if not name.endswith(".bfc"):
            continue
        path = os.path.join(cache_dir, name)
        try:
            stat = os.stat(path)
            entries.append((stat.st_atime, stat.st_size, path))
        except OSError:
            continue
    total = sum(size for _, size, _ in entries)
    for _, size, path in sorted(entries):
        if total <= maximum_bytes:
            break
        try:
            os.remove(path)
            total -= size
        except OSError:
            pass
