"""Sparse Java 1.16.1-style redstone simulation for editable builds.

The simulator deliberately owns behavior, while canonical serializable state
stays in :mod:`domain.blocks`.  Networks are recalculated only when the world
changes or a scheduled component tick is due; no per-frame world scan occurs.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, Optional, Tuple

from engine.block_state import BlockProperties, Facing


Position = Tuple[int, int, int]
HORIZONTAL = ((0, -1, 0), (1, 0, 0), (0, 1, 0), (-1, 0, 0))
NEIGHBORS = HORIZONTAL + ((0, 0, 1), (0, 0, -1))


def _add(a: Position, b: tuple[int, int, int]) -> Position:
    return a[0] + b[0], a[1] + b[1], a[2] + b[2]


def _facing_offset(facing: Facing) -> tuple[int, int, int]:
    dx, dy = facing.offset
    return dx, dy, 0


@dataclass(frozen=True)
class MovingCell:
    """One captured block moving between two cells during a piston animation."""

    block: object
    props: Optional[BlockProperties]
    source: Position
    target: Position


@dataclass
class PistonMotion:
    """Short, time-based visual motion layered over the committed world state."""

    piston: Position
    extending: bool
    cells: tuple[MovingCell, ...]
    final_targets: frozenset[Position]
    elapsed_ms: float = 0.0
    duration_ms: float = 100.0

    @property
    def progress(self) -> float:
        return min(1.0, self.elapsed_ms / self.duration_ms)


class RedstoneSimulator:
    """Bounded redstone updates plus horizontal piston movement."""

    TICK_MS = 50

    def __init__(self, world, definitions, *, sound: Optional[Callable[[str, Position], None]] = None):
        self.world = world
        self.definitions = definitions
        self.block_type = world.catalog.block_type
        self.sound = sound
        self._seen_revision = -1
        self._accumulator = 0
        self._repeater_updates: Dict[Position, tuple[bool, int]] = {}
        self._lamp_off_updates: Dict[Position, int] = {}
        self._button_updates: Dict[Position, int] = {}
        self._torch_history: Dict[Position, deque[int]] = {}
        self._torch_cooldown: Dict[Position, int] = {}
        self._game_tick = 0
        self.active_motions: list[PistonMotion] = []

    @property
    def powered_dust(self) -> Iterable[Position]:
        block_type = self.block_type
        for pos in self.world.blockTypePositions.get(block_type.REDSTONE_DUST, ()):
            props = self.world.getBlockProperties(*pos)
            if props and props.redstonePower > 0:
                yield pos

    @property
    def powered_components(self) -> Iterable[Position]:
        """Powered circuitry eligible for restrained visual sparks."""
        bt = self.block_type
        for block in (bt.REDSTONE_DUST, bt.REDSTONE_TORCH,
                      bt.REDSTONE_WALL_TORCH, bt.REPEATER, bt.STONE_BUTTON):
            for pos in self.world.blockTypePositions.get(block, ()):
                props = self.world.getBlockProperties(*pos)
                if props and props.powered:
                    yield pos

    def mark_dirty(self) -> None:
        self._seen_revision = -1

    def update(self, dt_ms: int) -> bool:
        """Advance scheduled component ticks and return whether state changed."""
        changed = False
        elapsed = max(0, int(dt_ms))
        self._advance_motions(elapsed)
        self._accumulator += elapsed
        if self.world.revision != self._seen_revision:
            changed |= self.recalculate()
        while self._accumulator >= self.TICK_MS:
            self._accumulator -= self.TICK_MS
            self._game_tick += 1
            changed |= self._tick_components()
        return changed

    def _advance_motions(self, dt_ms: int) -> None:
        if not self.active_motions or dt_ms <= 0:
            return
        for motion in self.active_motions:
            motion.elapsed_ms += dt_ms
        self.active_motions[:] = [
            motion for motion in self.active_motions if motion.progress < 1.0
        ]

    def prune_stale_motions(self) -> None:
        """Discard visual transients whose piston vanished with a world reset."""
        bt = self.block_type
        self.active_motions[:] = [
            motion for motion in self.active_motions
            if self.world.getBlock(*motion.piston) in (bt.PISTON, bt.STICKY_PISTON)
        ]

    @property
    def moving_final_targets(self) -> frozenset[Position]:
        targets = set()
        for motion in self.active_motions:
            targets.update(motion.final_targets)
        return frozenset(targets)

    def recalculate(self) -> bool:
        """Resolve torches, wires, repeaters, lamps and piston inputs."""
        changed = False
        changed |= self._update_torches()
        changed |= self._update_dust()
        self._schedule_repeaters()
        changed |= self._update_lamps()
        self._seen_revision = self.world.revision
        return changed

    def _props(self, pos: Position) -> BlockProperties:
        props = self.world.getBlockProperties(*pos)
        if props is None:
            props = BlockProperties()
            self.world.setBlockProperties(*pos, props)
        return props

    def _set_props(self, pos: Position, props: BlockProperties) -> None:
        self.world.setBlockProperties(*pos, props)

    def _is_solid(self, pos: Position) -> bool:
        block = self.world.getBlock(*pos)
        bt = self.block_type
        if block == bt.AIR or block in (bt.WATER, bt.LAVA):
            return False
        definition = self.definitions.get(block)
        return bool(
            definition
            and not definition.transparent
            and not definition.isDoor
            and not definition.isSlab
            and not definition.isStair
            and not definition.modelKind
        )

    def _output_toward(self, source: Position, target: Position, *, dust: bool = True) -> int:
        bt = self.block_type
        block = self.world.getBlock(*source)
        if block == bt.REDSTONE_BLOCK:
            return 15
        props = self.world.getBlockProperties(*source) or BlockProperties()
        if block in (
            bt.LEVER, bt.STONE_BUTTON, bt.REDSTONE_TORCH, bt.REDSTONE_WALL_TORCH
        ):
            return 15 if props.powered else 0
        if block == bt.REPEATER and props.powered:
            return 15 if _add(source, _facing_offset(props.facing)) == target else 0
        if dust and block == bt.REDSTONE_DUST:
            return max(0, min(15, int(props.redstonePower)))
        return 0

    def _strong_powered_solid(self, solid: Position, target: Position) -> int:
        """Power emitted by a solid block receiving a strong input."""
        level = 0
        for delta in NEIGHBORS:
            source = _add(solid, delta)
            if source == target:
                continue
            level = max(level, self._output_toward(source, solid, dust=False))
        return level

    def _direct_power(self, pos: Position, *, dust: bool = True) -> int:
        level = 0
        for delta in NEIGHBORS:
            source = _add(pos, delta)
            level = max(level, self._output_toward(source, pos, dust=dust))
            if self._is_solid(source):
                level = max(level, self._strong_powered_solid(source, pos))
        return level

    def _wire_neighbors(self, pos: Position) -> Iterable[Position]:
        bt = self.block_type
        x, y, z = pos
        above_open = not self._is_solid((x, y, z + 1))
        for dx, dy, _ in HORIZONTAL:
            side = (x + dx, y + dy, z)
            if self.world.getBlock(*side) == bt.REDSTONE_DUST:
                yield side
            if self._is_solid(side) and above_open:
                upper = (side[0], side[1], z + 1)
                if self.world.getBlock(*upper) == bt.REDSTONE_DUST:
                    yield upper
            elif not self._is_solid(side):
                lower = (side[0], side[1], z - 1)
                if self.world.getBlock(*lower) == bt.REDSTONE_DUST:
                    yield lower

    def wire_connection_mask(self, pos: Position) -> int:
        """Return N/E/S/W visual connectivity as a four-bit mask."""
        if self.world.getBlock(*pos) != self.block_type.REDSTONE_DUST:
            return 0
        bt = self.block_type
        x, y, z = pos
        mask = 0
        for bit, (dx, dy, _) in enumerate(HORIZONTAL):
            side = (x + dx, y + dy, z)
            candidates = (side, (side[0], side[1], z + 1), (side[0], side[1], z - 1))
            direction = Facing(bit)
            if any(self._wire_connects_to(candidate, direction) for candidate in candidates):
                mask |= 1 << bit
        return mask

    def _wire_connects_to(self, pos: Position, direction: Facing) -> bool:
        """Match Java wire's can-connect rule without connecting to consumers."""
        bt = self.block_type
        block = self.world.getBlock(*pos)
        if block == bt.REDSTONE_DUST:
            return True
        if block == bt.REPEATER:
            props = self.world.getBlockProperties(*pos) or BlockProperties()
            return props.facing in (direction, direction.opposite())
        return block in {
            bt.REDSTONE_BLOCK, bt.REDSTONE_TORCH, bt.REDSTONE_WALL_TORCH,
            bt.LEVER, bt.STONE_BUTTON,
        }

    def press_button(self, pos: Position) -> bool:
        """Press a stone button for the source-backed twenty game ticks."""
        if self.world.getBlock(*pos) != self.block_type.STONE_BUTTON:
            return False
        props = self._props(pos)
        props.powered = True
        props.redstonePower = 15
        self._set_props(pos, props)
        self._button_updates[pos] = 20
        self.mark_dirty()
        return True

    def _update_dust(self) -> bool:
        bt = self.block_type
        positions = list(self.world.blockTypePositions.get(bt.REDSTONE_DUST, ()))
        if not positions:
            return False
        levels = {pos: 0 for pos in positions}
        queue = deque()
        for pos in positions:
            direct = self._direct_power(pos, dust=False)
            if direct:
                levels[pos] = direct
                queue.append(pos)
        while queue:
            pos = queue.popleft()
            next_level = levels[pos] - 1
            if next_level <= 0:
                continue
            for neighbor in self._wire_neighbors(pos):
                if next_level > levels.get(neighbor, 0):
                    levels[neighbor] = next_level
                    queue.append(neighbor)
        changed = False
        for pos, level in levels.items():
            props = self._props(pos)
            if props.redstonePower != level or props.powered != (level > 0):
                props.redstonePower = level
                props.powered = level > 0
                self._set_props(pos, props)
                changed = True
        return changed

    def _torch_support(self, pos: Position, props: BlockProperties) -> Position:
        if self.world.getBlock(*pos) == self.block_type.REDSTONE_WALL_TORCH:
            dx, dy, _ = _facing_offset(props.facing)
            return pos[0] - dx, pos[1] - dy, pos[2]
        return pos[0], pos[1], pos[2] - 1

    def _update_torches(self) -> bool:
        bt = self.block_type
        changed = False
        positions = set(self.world.blockTypePositions.get(bt.REDSTONE_TORCH, ()))
        positions.update(self.world.blockTypePositions.get(bt.REDSTONE_WALL_TORCH, ()))
        for pos in positions:
            props = self._props(pos)
            support = self._torch_support(pos, props)
            desired = self._direct_power(support) == 0
            cooldown = self._torch_cooldown.get(pos, 0)
            if cooldown > self._game_tick:
                desired = False
            if props.powered != desired:
                history = self._torch_history.setdefault(pos, deque())
                history.append(self._game_tick)
                while history and self._game_tick - history[0] > 60:
                    history.popleft()
                if len(history) >= 8:
                    self._torch_cooldown[pos] = self._game_tick + 160
                    desired = False
                    history.clear()
                props.powered = desired
                props.redstonePower = 15 if desired else 0
                self._set_props(pos, props)
                changed = True
        return changed

    def _repeater_input(self, pos: Position, props: BlockProperties) -> int:
        dx, dy, _ = _facing_offset(props.facing)
        back = (pos[0] - dx, pos[1] - dy, pos[2])
        return max(
            self._output_toward(back, pos),
            self._strong_powered_solid(back, pos) if self._is_solid(back) else 0,
        )

    def _repeater_locked(self, pos: Position, props: BlockProperties) -> bool:
        for side_facing in (props.facing.clockwise(), props.facing.counterclockwise()):
            side = _add(pos, _facing_offset(side_facing))
            side_props = self.world.getBlockProperties(*side) or BlockProperties()
            if self.world.getBlock(*side) == self.block_type.REPEATER:
                if side_props.powered and _add(side, _facing_offset(side_props.facing)) == pos:
                    return True
        return False

    def _schedule_repeaters(self) -> None:
        bt = self.block_type
        for pos in self.world.blockTypePositions.get(bt.REPEATER, ()):
            props = self._props(pos)
            locked = self._repeater_locked(pos, props)
            if props.repeaterLocked != locked:
                props.repeaterLocked = locked
                self._set_props(pos, props)
            if locked:
                self._repeater_updates.pop(pos, None)
                continue
            desired = self._repeater_input(pos, props) > 0
            if desired == props.powered:
                self._repeater_updates.pop(pos, None)
            else:
                current = self._repeater_updates.get(pos)
                if current is None or current[0] != desired:
                    self._repeater_updates[pos] = (desired, max(1, props.repeaterDelay) * 2)

    def _update_lamps(self) -> bool:
        bt = self.block_type
        changed = False
        for pos in self.world.blockTypePositions.get(bt.REDSTONE_LAMP, ()):
            props = self._props(pos)
            desired = self._direct_power(pos) > 0
            if desired:
                self._lamp_off_updates.pop(pos, None)
                if not props.powered:
                    props.powered = True
                    props.redstonePower = 15
                    self._set_props(pos, props)
                    changed = True
            elif props.powered:
                # Java lamps remain lit for four game ticks after losing input.
                self._lamp_off_updates.setdefault(pos, 4)
            else:
                self._lamp_off_updates.pop(pos, None)
        return changed

    def _tick_lamp_off_updates(self) -> bool:
        changed = False
        for pos, ticks in list(self._lamp_off_updates.items()):
            if self.world.getBlock(*pos) != self.block_type.REDSTONE_LAMP:
                self._lamp_off_updates.pop(pos, None)
                continue
            if self._direct_power(pos) > 0:
                self._lamp_off_updates.pop(pos, None)
                continue
            ticks -= 1
            if ticks > 0:
                self._lamp_off_updates[pos] = ticks
                continue
            self._lamp_off_updates.pop(pos, None)
            props = self._props(pos)
            if props.powered:
                props.powered = False
                props.redstonePower = 0
                self._set_props(pos, props)
                changed = True
        return changed

    def _tick_components(self) -> bool:
        changed = False
        changed |= self._tick_lamp_off_updates()
        for pos, ticks in list(self._button_updates.items()):
            ticks -= 1
            if ticks > 0:
                self._button_updates[pos] = ticks
                continue
            self._button_updates.pop(pos, None)
            if self.world.getBlock(*pos) != self.block_type.STONE_BUTTON:
                continue
            props = self._props(pos)
            if props.powered:
                props.powered = False
                props.redstonePower = 0
                self._set_props(pos, props)
                changed = True
        for pos, (desired, ticks) in list(self._repeater_updates.items()):
            ticks -= 1
            if ticks > 0:
                self._repeater_updates[pos] = (desired, ticks)
                continue
            self._repeater_updates.pop(pos, None)
            if self.world.getBlock(*pos) != self.block_type.REPEATER:
                continue
            props = self._props(pos)
            if not props.repeaterLocked and props.powered != desired:
                props.powered = desired
                props.redstonePower = 15 if desired else 0
                self._set_props(pos, props)
                changed = True
        if changed:
            self._update_dust()
            self._schedule_repeaters()
            self._update_lamps()
        changed |= self._update_torches()
        changed |= self._update_pistons()
        self._seen_revision = self.world.revision
        return changed

    def _piston_powered(self, pos: Position) -> bool:
        # Intentional project rule: direct/strong power only, never quasi-connectivity.
        return self._direct_power(pos) > 0

    def _piston_behavior(self, block, props: Optional[BlockProperties]) -> str:
        bt = self.block_type
        if block == bt.AIR:
            return "air"
        definition = self.definitions.get(block)
        if block in {
            bt.REDSTONE_DUST, bt.REDSTONE_TORCH, bt.REDSTONE_WALL_TORCH,
            bt.LEVER, bt.STONE_BUTTON, bt.REPEATER,
            bt.WATER, bt.LAVA, bt.FIRE, bt.SOUL_FIRE,
        } or (definition and (
            definition.isDoor
            or definition.modelKind in {
                "torch", "ladder", "plant", "banner", "candle", "lantern"
            }
        )):
            return "break"
        if block in {
            bt.BEDROCK, bt.OBSIDIAN, bt.CRYING_OBSIDIAN,
            bt.RESPAWN_ANCHOR, bt.REINFORCED_DEEPSLATE, bt.PISTON_HEAD,
            bt.END_PORTAL_FRAME, bt.END_PORTAL, bt.END_GATEWAY,
            bt.CHEST, bt.TRAPPED_CHEST, bt.CHRISTMAS_CHEST,
            bt.COPPER_CHEST, bt.COPPER_CHEST_EXPOSED,
            bt.COPPER_CHEST_WEATHERED, bt.COPPER_CHEST_OXIDIZED,
            bt.ENDER_CHEST, bt.FURNACE, bt.ENCHANTING_TABLE,
            bt.MOB_SPAWNER, bt.TRIAL_SPAWNER,
        } or (block in (bt.PISTON, bt.STICKY_PISTON) and props and props.pistonExtended):
            return "block"
        return "move"

    def _movable(self, block, props: Optional[BlockProperties]) -> bool:
        return self._piston_behavior(block, props) == "move"

    def _capture_cell(self, source: Position, target: Position) -> MovingCell:
        props = self.world.getBlockProperties(*source)
        return MovingCell(
            self.world.getBlock(*source), props.copy() if props is not None else None,
            source, target,
        )

    def _break_cell(self, pos: Position) -> None:
        """Remove a fragile cell and its paired door half, if present."""
        block = self.world.getBlock(*pos)
        definition = self.definitions.get(block)
        self.world.setBlock(*pos, self.block_type.AIR)
        if not (definition and definition.isDoor):
            return
        for dz in (-1, 1):
            paired = pos[0], pos[1], pos[2] + dz
            if self.world.isInBounds(*paired) and self.world.getBlock(*paired) == block:
                self.world.setBlock(*paired, self.block_type.AIR)

    def _start_motion(
        self, pos: Position, extending: bool, cells: list[MovingCell],
        final_targets: Iterable[Position],
    ) -> None:
        self.active_motions[:] = [
            motion for motion in self.active_motions if motion.piston != pos
        ]
        self.active_motions.append(PistonMotion(
            piston=pos,
            extending=extending,
            cells=tuple(cells),
            final_targets=frozenset(final_targets),
        ))

    def _move_cell(self, source: Position, target: Position) -> None:
        block = self.world.getBlock(*source)
        props = self.world.getBlockProperties(*source)
        level = self.world.getLiquidLevel(*source)
        source_liquid = source in self.world.liquidSources
        falling = source in self.world.liquidFalling
        self.world.setBlock(*target, block)
        if props is not None:
            self.world.setBlockProperties(*target, props.copy())
        if level:
            self.world.liquidLevels[target] = level
            if source_liquid:
                self.world.liquidSources.add(target)
            if falling:
                self.world.liquidFalling.add(target)
        self.world.setBlock(*source, self.block_type.AIR)

    def _extend(self, pos: Position, props: BlockProperties) -> bool:
        direction = _facing_offset(props.facing)
        front = _add(pos, direction)
        if not self.world.isInBounds(*front):
            return False
        chain = []
        cursor = front
        while self.world.getBlock(*cursor) != self.block_type.AIR:
            block = self.world.getBlock(*cursor)
            cell_props = self.world.getBlockProperties(*cursor)
            behavior = self._piston_behavior(block, cell_props)
            if behavior == "break":
                self._break_cell(cursor)
                break
            if len(chain) >= 12 or behavior != "move":
                return False
            chain.append(cursor)
            cursor = _add(cursor, direction)
            if not self.world.isInBounds(*cursor):
                return False
        moving = [self._capture_cell(source, _add(source, direction)) for source in chain]
        head_props = BlockProperties(
            facing=props.facing, pistonExtended=True,
            sticky=self.world.getBlock(*pos) == self.block_type.STICKY_PISTON,
        )
        moving.append(MovingCell(self.block_type.PISTON_HEAD, head_props.copy(), pos, front))
        final_targets = [_add(source, direction) for source in chain]
        final_targets.append(front)
        with self.world.bulkUpdate():
            for source in reversed(chain):
                self._move_cell(source, _add(source, direction))
            self.world.setBlock(*front, self.block_type.PISTON_HEAD)
            self.world.setBlockProperties(*front, head_props)
            props.pistonExtended = True
            self.world.setBlockProperties(*pos, props)
        self._start_motion(pos, True, moving, final_targets)
        if self.sound:
            self.sound("piston_out", pos)
        return True

    def _retract(self, pos: Position, props: BlockProperties) -> bool:
        direction = _facing_offset(props.facing)
        front = _add(pos, direction)
        pull = _add(front, direction)
        head_props = BlockProperties(
            facing=props.facing, pistonExtended=True,
            sticky=self.world.getBlock(*pos) == self.block_type.STICKY_PISTON,
        )
        moving = [MovingCell(self.block_type.PISTON_HEAD, head_props, front, pos)]
        final_targets = []
        with self.world.bulkUpdate():
            if self.world.getBlock(*front) == self.block_type.PISTON_HEAD:
                self.world.setBlock(*front, self.block_type.AIR)
            if (
                self.world.getBlock(*pos) == self.block_type.STICKY_PISTON
                and self.world.isInBounds(*pull)
            ):
                block = self.world.getBlock(*pull)
                cell_props = self.world.getBlockProperties(*pull)
                if block != self.block_type.AIR and self._movable(block, cell_props):
                    moving.append(self._capture_cell(pull, front))
                    final_targets.append(front)
                    self._move_cell(pull, front)
            props.pistonExtended = False
            self.world.setBlockProperties(*pos, props)
        self._start_motion(pos, False, moving, final_targets)
        if self.sound:
            self.sound("piston_in", pos)
        return True

    def _update_pistons(self) -> bool:
        bt = self.block_type
        changed = False
        positions = set(self.world.blockTypePositions.get(bt.PISTON, ()))
        positions.update(self.world.blockTypePositions.get(bt.STICKY_PISTON, ()))
        for pos in sorted(positions):
            if self.world.getBlock(*pos) not in (bt.PISTON, bt.STICKY_PISTON):
                continue
            props = self._props(pos)
            desired = self._piston_powered(pos)
            if desired and not props.pistonExtended:
                changed |= self._extend(pos, props)
            elif not desired and props.pistonExtended:
                changed |= self._retract(pos, props)
        return changed
