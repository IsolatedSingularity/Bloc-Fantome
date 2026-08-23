"""Sparse Java 1.16.1-style redstone simulation for editable builds.

The simulator deliberately owns behavior, while canonical serializable state
stays in :mod:`domain.blocks`.  Networks are recalculated only when the world
changes or a scheduled component tick is due; no per-frame world scan occurs.
"""

from __future__ import annotations

from collections import deque
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
        self._torch_history: Dict[Position, deque[int]] = {}
        self._torch_cooldown: Dict[Position, int] = {}
        self._game_tick = 0

    @property
    def powered_dust(self) -> Iterable[Position]:
        block_type = self.block_type
        for pos in self.world.blockTypePositions.get(block_type.REDSTONE_DUST, ()):
            props = self.world.getBlockProperties(*pos)
            if props and props.redstonePower > 0:
                yield pos

    def mark_dirty(self) -> None:
        self._seen_revision = -1

    def update(self, dt_ms: int) -> bool:
        """Advance scheduled component ticks and return whether state changed."""
        changed = False
        self._accumulator += max(0, int(dt_ms))
        if self.world.revision != self._seen_revision:
            changed |= self.recalculate()
        while self._accumulator >= self.TICK_MS:
            self._accumulator -= self.TICK_MS
            self._game_tick += 1
            changed |= self._tick_components()
        return changed

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
        if block in (bt.LEVER, bt.REDSTONE_TORCH, bt.REDSTONE_WALL_TORCH):
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
            if props.powered != desired:
                props.powered = desired
                props.redstonePower = 15 if desired else 0
                self._set_props(pos, props)
                changed = True
        return changed

    def _tick_components(self) -> bool:
        changed = False
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
        if self._direct_power(pos) > 0:
            return True
        # Java's quasi-connectivity check: power around the block above.
        above = (pos[0], pos[1], pos[2] + 1)
        return self._direct_power(above) > 0

    def _movable(self, block, props: Optional[BlockProperties]) -> bool:
        bt = self.block_type
        return block not in {
            bt.AIR, bt.BEDROCK, bt.OBSIDIAN, bt.CRYING_OBSIDIAN,
            bt.RESPAWN_ANCHOR, bt.PISTON_HEAD,
        } and not (block in (bt.PISTON, bt.STICKY_PISTON) and props and props.pistonExtended)

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
            if len(chain) >= 12 or not self._movable(block, cell_props):
                return False
            chain.append(cursor)
            cursor = _add(cursor, direction)
            if not self.world.isInBounds(*cursor):
                return False
        with self.world.bulkUpdate():
            for source in reversed(chain):
                self._move_cell(source, _add(source, direction))
            head = BlockProperties(
                facing=props.facing, pistonExtended=True,
                sticky=self.world.getBlock(*pos) == self.block_type.STICKY_PISTON,
            )
            self.world.setBlock(*front, self.block_type.PISTON_HEAD)
            self.world.setBlockProperties(*front, head)
            props.pistonExtended = True
            self.world.setBlockProperties(*pos, props)
        if self.sound:
            self.sound("piston_out", pos)
        return True

    def _retract(self, pos: Position, props: BlockProperties) -> bool:
        direction = _facing_offset(props.facing)
        front = _add(pos, direction)
        pull = _add(front, direction)
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
                    self._move_cell(pull, front)
            props.pistonExtended = False
            self.world.setBlockProperties(*pos, props)
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

