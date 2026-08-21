"""Safe persistent staging cache for bundled editable world scenes."""

from __future__ import annotations

import hashlib
import json
import os
import struct
from typing import Iterable

from engine.block_state import (
    BlockProperties,
    DoorHalf,
    DoorHinge,
    Facing,
    SlabPosition,
    StairShape,
)


MAGIC = b"BFC2"
HEADER = struct.Struct("<4s32sI")
RECORD = struct.Struct("<hhhHBBBBBBB")
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
        metadata = json.loads(handle.read(metadata_size).decode("utf-8"))
        count_data = handle.read(4)
        if len(count_data) != 4:
            raise ValueError("Truncated world cache")
        count = struct.unpack("<I", count_data)[0]
        payload = handle.read()
    if len(payload) != count * RECORD.size:
        raise ValueError("Invalid world cache record count")

    staged = []
    structure_positions = set()
    for values in RECORD.iter_unpack(payload):
        x, y, z, type_value, flags, facing, slab, stair, door_half, hinge, liquid = values
        props = None
        if flags & 1:
            props = BlockProperties(
                facing=Facing(facing),
                isOpen=bool(flags & 32),
                slabPosition=SlabPosition(slab),
                stairShape=STAIR_SHAPES[stair],
                doorHalf=DoorHalf.UPPER if door_half else DoorHalf.LOWER,
                doorHinge=DoorHinge.RIGHT if hinge else DoorHinge.LEFT,
            )
        liquid_state = None
        if flags & 4:
            liquid_state = (max(1, min(8, liquid)), bool(flags & 8), bool(flags & 16))
        staged.append((x, y, z, block_type(type_value), props, liquid_state))
        if flags & 2:
            structure_positions.add((x, y, z))
    scene = dict(metadata.get("scene", {}))
    scene["_structure_positions"] = structure_positions
    bounds = tuple(metadata["bounds"])
    return metadata["dimension"], bounds, scene, staged, 0


def write(path: str, digest: bytes, dimension: str, bounds, scene,
          staged: Iterable, structure_positions) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    staged = tuple(staged)
    metadata = json.dumps(
        {"dimension": dimension, "bounds": list(bounds), "scene": dict(scene)},
        separators=(",", ":"),
    ).encode("utf-8")
    temp_path = path + ".tmp"
    with open(temp_path, "wb") as handle:
        handle.write(HEADER.pack(MAGIC, digest, len(metadata)))
        handle.write(metadata)
        handle.write(struct.pack("<I", len(staged)))
        for x, y, z, block, props, liquid_state in staged:
            flags = 2 if (x, y, z) in structure_positions else 0
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
            ))
    os.replace(temp_path, path)


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
