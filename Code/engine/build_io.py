"""Parse and validate build files into immutable world snapshots.

This module performs Python-only staging. It never mutates a live world or
creates Pygame objects, so callers can run it on a worker and apply the returned
snapshot atomically on the main thread.
"""

from __future__ import annotations

from dataclasses import dataclass
import gzip
import json
import os
from pathlib import Path
import struct
from typing import Optional

from domain.blocks import (
    BlockProperties,
    DoorHalf,
    DoorHinge,
    Facing,
    SlabPosition,
    StairShape,
)
from domain.dimensions import DIMENSION_END, DIMENSION_NETHER, DIMENSION_OVERWORLD
from engine import scene_cache
from engine.world_snapshot import WorldSnapshot


@dataclass(frozen=True)
class BuildReadPolicy:
    default_bounds: tuple[int, int, int, int] = (12, 12, 12, 0)
    bundled_worlds_dir: Optional[Path] = None
    derived_cache_dir: Optional[Path] = None


@dataclass(frozen=True)
class BuildReadResult:
    snapshot: WorldSnapshot
    skipped_count: int = 0
    cache_hit: bool = False


@dataclass(frozen=True)
class SaveResult:
    path: Path
    block_count: int


def _is_bundled(path: Path, directory: Optional[Path]) -> bool:
    if directory is None:
        return False
    directory = Path(directory)
    try:
        return os.path.commonpath((path.resolve(), directory.resolve())) == str(
            directory.resolve()
        )
    except ValueError:
        return False


def _properties(block_type, state_data, definitions):
    if not isinstance(state_data, dict) or not state_data:
        return None
    definition = definitions.get(block_type)
    if not definition or not (
        definition.isDoor
        or definition.isStair
        or definition.isSlab
        or definition.modelKind
        or block_type.name == "OXIDIZING_COPPER"
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
    properties.oxidationStage = max(
        0, min(3, int(state_data.get("oxidationStage", 0)))
    )
    return properties


def _neighbor_positions(position):
    x, y, z = position
    return (
        (x + 1, y, z),
        (x - 1, y, z),
        (x, y + 1, z),
        (x, y - 1, z),
        (x, y, z + 1),
        (x, y, z - 1),
    )


def _is_opaque_cube(definition) -> bool:
    return bool(
        definition
        and not definition.transparent
        and not definition.isLiquid
        and not definition.isThin
        and not definition.isSlab
        and not definition.isStair
        and not definition.isPortal
        and not definition.modelKind
    )


def _structure_surfaces(blocks, structure_positions, definitions, exterior_shell):
    result = {rotation: set() for rotation in range(4)}
    if not structure_positions:
        return result
    if exterior_shell:
        visible = {
            position
            for position in structure_positions
            if any(neighbor not in structure_positions for neighbor in _neighbor_positions(position))
        }
        return {rotation: visible for rotation in range(4)}
    side_directions = (
        ((0, 1), (1, 0)),
        ((1, 0), (0, -1)),
        ((0, -1), (-1, 0)),
        ((-1, 0), (0, 1)),
    )
    for x, y, z in structure_positions:
        position = (x, y, z)
        if not _is_opaque_cube(definitions.get(blocks[position])):
            for visible in result.values():
                visible.add(position)
            continue
        for rotation, directions in enumerate(side_directions):
            neighbors = ((x, y, z + 1),) + tuple(
                (x + dx, y + dy, z) for dx, dy in directions
            )
            if any(neighbor not in structure_positions for neighbor in neighbors):
                result[rotation].add(position)
    return result


def _view_surface_positions(blocks, surface_positions, definitions):
    """Precompute the exact conservative terrain cells visible in each view."""
    result = {rotation: set() for rotation in range(4)}
    side_directions = (
        ((0, 1), (1, 0)),
        ((1, 0), (0, -1)),
        ((0, -1), (-1, 0)),
        ((-1, 0), (0, 1)),
    )

    def opaque(position):
        return _is_opaque_cube(definitions.get(blocks.get(position)))

    for x, y, z in surface_positions:
        position = (x, y, z)
        if not opaque(position) or not opaque((x, y, z + 1)):
            for visible in result.values():
                visible.add(position)
            continue
        exposed = {
            (1, 0): not opaque((x + 1, y, z)),
            (-1, 0): not opaque((x - 1, y, z)),
            (0, 1): not opaque((x, y + 1, z)),
            (0, -1): not opaque((x, y - 1, z)),
        }
        for rotation, directions in enumerate(side_directions):
            if any(exposed[direction] for direction in directions):
                result[rotation].add(position)
    return result


def _depth_key(rotation, position):
    x, y, z = position
    if rotation == 0:
        return x + y + z
    if rotation == 1:
        return -y + x + z
    if rotation == 2:
        return -x - y + z
    return y - x + z


def _draw_orders(blocks, structure_positions, structure_surfaces, view_surfaces):
    """Build immutable painter orders on the staging worker, never on rotation."""
    terrain_top = {}
    for x, y, z in blocks:
        column = (x, y)
        if z > terrain_top.get(column, -10_000):
            terrain_top[column] = z
    terrain_top_positions = {
        (x, y, z)
        for (x, y), z in terrain_top.items()
        if (x, y, z) not in structure_positions
    }

    modes = {"all": {}, "transparent": {}, "hidden": {}}
    for rotation in range(4):
        mode_positions = {
            "all": view_surfaces.get(rotation, ()),
            "transparent": terrain_top_positions | set(structure_surfaces.get(rotation, ())),
            "hidden": structure_surfaces.get(rotation, ()),
        }
        for mode, positions in mode_positions.items():
            ordered = sorted(
                positions,
                key=lambda position: (
                    _depth_key(rotation, position),
                    position[2],
                    position[0],
                    position[1],
                ),
            )
            modes[mode][rotation] = tuple(
                (_depth_key(rotation, position), *position, blocks[position])
                for position in ordered
            )
    return modes


def _exterior_glass(blocks, structure_positions, block_type, enabled):
    if not enabled or not structure_positions:
        return set()
    masonry = {
        block_type.TUFF_BRICKS,
        block_type.POLISHED_TUFF,
        block_type.CHISELED_TUFF,
        block_type.CHISELED_TUFF_BRICKS,
        block_type.STONE,
        block_type.COBBLED_DEEPSLATE,
    }
    silhouettes = [dict(), dict(), dict()]
    for position in structure_positions:
        for axis in range(3):
            line = tuple(position[index] for index in range(3) if index != axis)
            coordinate = position[axis]
            limits = silhouettes[axis].get(line)
            if limits is None:
                silhouettes[axis][line] = [coordinate, coordinate]
            else:
                limits[0] = min(limits[0], coordinate)
                limits[1] = max(limits[1], coordinate)
    return {
        position
        for position in structure_positions
        if blocks.get(position) in masonry
        and any(
            position[axis]
            in silhouettes[axis][
                tuple(position[index] for index in range(3) if index != axis)
            ]
            for axis in range(3)
        )
    }


def _snapshot_from_staged(
    dimension, bounds, scene, staged, skipped_count, cache_hit, definitions
):
    width, depth, height, min_y = bounds
    blocks = {}
    properties = {}
    liquid_levels = {}
    liquid_sources = set()
    liquid_falling = set()
    for x, y, z, block_type, block_properties, liquid_state in staged:
        position = (x, y, z)
        blocks[position] = block_type
        if block_properties is not None:
            properties[position] = block_properties
        if liquid_state is not None:
            level, source, falling = liquid_state
            liquid_levels[position] = level
            if source:
                liquid_sources.add(position)
            if falling:
                liquid_falling.add(position)
    surface_positions = set(scene.get("_surface_positions", ()))
    structure_positions = set(scene.get("_structure_positions", ()))
    structure_surfaces = scene.get("_structure_surfaces_by_view", {})
    view_surfaces = scene.get("_view_surface_positions_by_view", {})
    if not all(rotation in view_surfaces for rotation in range(4)):
        view_surfaces = _view_surface_positions(blocks, surface_positions, definitions)
    snapshot = WorldSnapshot(
        width=width,
        depth=depth,
        height=height,
        min_y=min_y,
        dimension=dimension,
        blocks=blocks,
        properties=properties,
        liquid_levels=liquid_levels,
        liquid_sources=liquid_sources,
        liquid_falling=liquid_falling,
        scene_metadata=scene,
        structure_positions=structure_positions,
        exterior_glass_positions=set(scene.get("_exterior_glass_positions", ())),
        structure_surfaces_by_view=structure_surfaces,
        surface_positions=surface_positions,
        view_surface_positions_by_view=view_surfaces,
        draw_orders_by_mode=_draw_orders(
            blocks, structure_positions, structure_surfaces, view_surfaces
        ),
    )
    return BuildReadResult(snapshot, skipped_count, cache_hit)


def read_build(path, block_catalog, cache_policy: BuildReadPolicy) -> BuildReadResult:
    """Read one gzip/plain build without changing application or world state."""
    path = Path(path)
    block_type = block_catalog.block_type
    definitions = block_catalog.definitions
    cache_digest = None
    cache_path = None
    if _is_bundled(path, cache_policy.bundled_worlds_dir) and cache_policy.derived_cache_dir:
        cache_digest = scene_cache.source_digest(str(path))
        cache_path = scene_cache.cache_path(
            str(cache_policy.derived_cache_dir), str(path), cache_digest
        )
        try:
            cached = scene_cache.load(cache_path, cache_digest, block_type)
            dimension, bounds, scene, staged, skipped_count = cached
            print(f"World cache hit: {path.name}")
            return _snapshot_from_staged(
                dimension, bounds, dict(scene), staged, skipped_count, True, definitions
            )
        except (OSError, ValueError, KeyError, IndexError, struct.error):
            pass

    try:
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            save_data = json.load(handle)
    except (gzip.BadGzipFile, OSError):
        with path.open("r", encoding="utf-8") as handle:
            save_data = json.load(handle)
    if not isinstance(save_data, dict) or not isinstance(save_data.get("blocks"), list):
        raise ValueError("Invalid build file format")

    save_version = int(save_data.get("version", 1))
    dimension = save_data.get("dimension", DIMENSION_OVERWORLD)
    if dimension not in (DIMENSION_OVERWORLD, DIMENSION_NETHER, DIMENSION_END):
        raise ValueError(f"Unknown dimension: {dimension}")
    bounds_data = save_data.get("bounds") if save_version >= 5 else None
    if bounds_data is None:
        bounds = cache_policy.default_bounds
    else:
        if not isinstance(bounds_data, dict):
            raise ValueError("Invalid build bounds")
        default_width, default_depth, default_height, _ = cache_policy.default_bounds
        bounds = (
            int(bounds_data.get("width", default_width)),
            int(bounds_data.get("depth", default_depth)),
            int(bounds_data.get("height", default_height)),
            int(bounds_data.get("min_y", 0)),
        )
        width, depth, height, min_y = bounds
        if not (1 <= width <= 256 and 1 <= depth <= 256 and 1 <= height <= 512):
            raise ValueError("Build bounds exceed the supported 256 x 256 x 512 canvas")
        if min_y < -128 or min_y + height > 512:
            raise ValueError("Build vertical bounds are unsupported")

    width, depth, height, min_y = bounds
    max_y = min_y + height
    scene = save_data.get("scene", {})
    if not isinstance(scene, dict):
        scene = {}
    scene = dict(scene)
    staged = []
    structure_positions = set()
    skipped_count = 0
    for block_data in save_data["blocks"]:
        try:
            if not all(key in block_data for key in ("x", "y", "z", "type")):
                raise ValueError("missing block field")
            parsed_type = block_type[block_data["type"]]
            x = int(block_data["x"])
            y = int(block_data["y"])
            z = int(block_data["z"])
            if not (0 <= x < width and 0 <= y < depth and min_y <= z < max_y):
                raise ValueError("block outside build bounds")
            state_data = block_data.get("state", {})
            if not isinstance(state_data, dict):
                state_data = {}
            state_data = dict(state_data)
            for key in (
                "facing", "isOpen", "slabPosition", "stairShape", "doorHalf", "doorHinge",
                "oxidationStage",
            ):
                if key in block_data:
                    state_data[key] = block_data[key]
            block_properties = _properties(parsed_type, state_data, definitions)
            liquid_state = None
            if parsed_type in (block_catalog.water, block_catalog.lava):
                liquid_state = (
                    max(1, min(8, int(block_data.get("liquidLevel", 8)))),
                    bool(block_data.get("liquidSource", True)),
                    bool(block_data.get("liquidFalling", False)),
                )
            staged.append((x, y, z, parsed_type, block_properties, liquid_state))
            if block_data.get("role") == "structure":
                structure_positions.add((x, y, z))
        except (KeyError, TypeError, ValueError):
            skipped_count += 1

    if save_version < 4:
        occupied = {(x, y, z) for x, y, z, *_ in staged}
        migrated = []
        for index, (x, y, z, parsed_type, properties, liquid_state) in enumerate(staged):
            definition = definitions.get(parsed_type)
            if not (definition and definition.isDoor):
                continue
            properties = properties or BlockProperties()
            properties.doorHalf = DoorHalf.LOWER
            staged[index] = (x, y, z, parsed_type, properties, liquid_state)
            upper = (x, y, z + 1)
            if z + 1 < max_y and upper not in occupied:
                upper_properties = properties.copy()
                upper_properties.doorHalf = DoorHalf.UPPER
                migrated.append((x, y, z + 1, parsed_type, upper_properties, None))
                occupied.add(upper)
        staged.extend(migrated)

    blocks = {(x, y, z): value for x, y, z, value, _props, _liquid in staged}
    exterior_shell = scene.get("exterior_shell_view") == "glass"
    exterior_glass = _exterior_glass(
        blocks, structure_positions, block_type, exterior_shell
    )
    structure_surfaces = _structure_surfaces(
        blocks, structure_positions, definitions, exterior_shell
    )
    surface_positions = {
        position
        for position in blocks
        if any(neighbor not in blocks for neighbor in _neighbor_positions(position))
    }
    view_surface_positions = _view_surface_positions(
        blocks, surface_positions, definitions
    )
    scene["_structure_positions"] = structure_positions
    scene["_exterior_glass_positions"] = exterior_glass
    scene["_structure_surfaces_by_view"] = structure_surfaces
    scene["_surface_positions"] = surface_positions
    scene["_view_surface_positions_by_view"] = view_surface_positions

    if cache_path is not None and cache_digest is not None:
        try:
            scene_cache.write(
                cache_path,
                cache_digest,
                dimension,
                bounds,
                scene,
                staged,
                structure_positions,
                exterior_glass,
                structure_surfaces,
                surface_positions,
                view_surface_positions,
            )
            scene_cache.prune(str(cache_policy.derived_cache_dir))
        except (OSError, ValueError, struct.error) as error:
            print(f"World cache skipped: {error}")
    return _snapshot_from_staged(
        dimension, bounds, scene, staged, skipped_count, False, definitions
    )


def write_build(path, snapshot: WorldSnapshot, definitions) -> SaveResult:
    """Atomically write a v5 gzip build from a stable world snapshot."""
    path = Path(path)
    temp_path = path.with_name(path.name + ".tmp")
    path.parent.mkdir(parents=True, exist_ok=True)
    blocks = []
    for (x, y, z), block_type in snapshot.blocks.items():
        position = (x, y, z)
        block_data = {"x": x, "y": y, "z": z, "type": block_type.name}
        if position in snapshot.liquid_levels:
            block_data["liquidLevel"] = snapshot.liquid_levels[position]
            block_data["liquidSource"] = position in snapshot.liquid_sources
            block_data["liquidFalling"] = position in snapshot.liquid_falling
        if position in snapshot.structure_positions:
            block_data["role"] = "structure"
        properties = snapshot.properties.get(position)
        if properties is not None:
            definition = definitions.get(block_type)
            if properties.facing:
                block_data["facing"] = properties.facing.name
            if definition and definition.isDoor:
                block_data["isOpen"] = properties.isOpen
                block_data["doorHalf"] = properties.doorHalf.name
                block_data["doorHinge"] = properties.doorHinge.name
            if definition and definition.modelKind == "lantern":
                block_data["isOpen"] = properties.isOpen
            if definition and definition.isStair:
                block_data["stairShape"] = properties.stairShape.name
            if properties.slabPosition:
                block_data["slabPosition"] = properties.slabPosition.name
            if block_type.name == "OXIDIZING_COPPER":
                block_data["oxidationStage"] = max(
                    0, min(3, int(properties.oxidationStage))
                )
        blocks.append(block_data)
    payload = {
        "version": 5,
        "dimension": snapshot.dimension,
        "bounds": {
            "width": snapshot.width,
            "depth": snapshot.depth,
            "height": snapshot.height,
            "min_y": snapshot.min_y,
        },
        "scene": {
            key: value
            for key, value in dict(snapshot.scene_metadata).items()
            if not key.startswith("_")
        },
        "blocks": blocks,
    }
    try:
        with gzip.open(temp_path, "wt", encoding="utf-8") as handle:
            json.dump(payload, handle, separators=(",", ":"))
        os.replace(temp_path, path)
    except Exception:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise
    return SaveResult(path, len(blocks))
