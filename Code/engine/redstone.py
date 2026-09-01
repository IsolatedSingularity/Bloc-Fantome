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
        # None means a full topology pass is required; an empty/set value means
        # edits can be restricted to dust components touching those cells.
        self._dirty_positions: Optional[set[Position]] = None
        self._pistons_dirty = True

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
                      bt.REDSTONE_WALL_TORCH, bt.REPEATER, bt.LEVER,
                      bt.STONE_BUTTON):
            for pos in self.world.blockTypePositions.get(block, ()):
                props = self.world.getBlockProperties(*pos)
                if props and props.powered:
                    yield pos

    def mark_dirty(self, *positions: Position) -> None:
        """Mark a full network or only components affected by edited cells."""
        self._seen_revision = -1
        self._pistons_dirty = True
        if not positions:
            self._dirty_positions = None
        elif self._dirty_positions is not None:
            self._dirty_positions.update(positions)

    def update(self, dt_ms: int) -> bool:
        """Advance scheduled component ticks and return whether state changed."""
        changed = False
        elapsed = max(0, int(dt_ms))
        self._advance_motions(elapsed)
        self._accumulator += elapsed
        if self.world.revision != self._seen_revision:
            if self._dirty_positions == set():
                self._dirty_positions = None
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
        # A revision not accompanied by positions may have come from loading,
        # undo, or a bulk mutation; fall back to a complete safe pass.
        dirty = self._dirty_positions
        changed = False
        torch_changes: set[Position] = set()
        changed |= self._update_torches(torch_changes)
        if dirty is not None:
            dirty = set(dirty) | torch_changes
        changed |= self._update_dust(dirty)
        changed |= self._schedule_repeaters()
        changed |= self._update_lamps()
        self._seen_revision = self.world.revision
        self._dirty_positions = set()
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
        # Piston bases are full solid blocks even though they use a custom
        # modelKind for rendering. Treating every modelKind as non-solid made
        # dust fail to climb beside a piston and prevented strong power from
        # crossing a piston body.
        if block in (bt.PISTON, bt.STICKY_PISTON, bt.PISTON_HEAD):
            return True
        # Slime and honey use a translucent-looking texture in the editor,
        # but they are still full solid blocks to redstone.  Vanilla allows
        # dust to sit on them and wires to climb beside them; visual
        # transparency must not change that support/collision rule.
        if block in (bt.SLIME_BLOCK, bt.HONEY_BLOCK):
            return True
        definition = self.definitions.get(block)
        return bool(
            definition
            and not definition.transparent
            and not definition.isDoor
            and not definition.isSlab
            and not definition.isStair
            and not definition.modelKind
        )

    def _output_toward(
        self,
        source: Position,
        target: Position,
        *,
        dust: bool = True,
        strong: bool = False,
    ) -> int:
        """Return one block's weak or strong power toward a neighbor.

        ``World.getEmittedRedstonePower`` first asks the source for weak power
        in the direction from the receiving cell back to that source.  Solid
        blocks then add their received *strong* power.  Keeping that distinction
        here prevents a floor lever or torch from incorrectly powering every
        side of a solid block when Java only powers its mounted face.
        """
        bt = self.block_type
        block = self.world.getBlock(*source)
        if block == bt.REDSTONE_BLOCK:
            return 15
        props = self.world.getBlockProperties(*source) or BlockProperties()
        if block in (bt.REDSTONE_TORCH, bt.REDSTONE_WALL_TORCH):
            if strong:
                # RedstoneTorchBlock.getStrongRedstonePower only responds to
                # Direction.DOWN (the receiving block is above the torch).
                return 15 if props.powered and target == (
                    source[0], source[1], source[2] + 1
                ) else 0
            # A redstone torch never powers the block it is mounted on. The
            # old all-directions shortcut counted its own support as input,
            # making an unpowered torch toggle every time topology was dirtied.
            if target == self._torch_support(source, props):
                return 0
            return 15 if props.powered else 0
        if block == bt.LEVER:
            if strong:
                # The Lab places floor levers.  WallMountedBlock.getDirection
                # is UP for that state, so only the supporting cell below gets
                # strong power; weak power remains omnidirectional.
                return 15 if props.powered and target == (
                    source[0], source[1], source[2] - 1
                ) else 0
            return 15 if props.powered else 0
        if block == bt.STONE_BUTTON:
            if strong:
                # The editor's button model is the wall-mounted state.  Its
                # support is opposite FACING, matching WallMountedBlock.
                dx, dy, _ = _facing_offset(props.facing)
                return 15 if props.powered and target == (
                    source[0] - dx, source[1] - dy, source[2]
                ) else 0
            return 15 if props.powered else 0
        if block == bt.REPEATER and props.powered:
            # Java's RepeaterBlock.FACING is the input side. A powered
            # repeater emits through the opposite face; World passes the
            # direction from the receiving cell back toward this source.
            dx, dy, dz = _facing_offset(props.facing)
            return 15 if target == (
                source[0] - dx, source[1] - dy, source[2] - dz
            ) else 0
        if dust and block == bt.REDSTONE_DUST:
            return self._dust_output_toward(source, target, props)
        return 0

    def _dust_output_toward(
        self, source: Position, target: Position, props: BlockProperties
    ) -> int:
        """Return Java wire power for one receiving face.

        RedstoneWireBlock only emits horizontally through a connected arm,
        emits down into the block beneath it, and does not emit upward. The
        previous shortcut returned the wire level to every adjacent block,
        which made an isolated dust mote power lamps and pistons that vanilla
        would leave dark.
        """
        level = max(0, min(15, int(props.redstonePower)))
        if level <= 0:
            return 0
        dx = target[0] - source[0]
        dy = target[1] - source[1]
        dz = target[2] - source[2]
        if dz == -1 and dx == 0 and dy == 0:
            return level
        if dz != 0 or (abs(dx) + abs(dy) != 1):
            return 0
        for bit, (offset_x, offset_y, _offset_z) in enumerate(HORIZONTAL):
            if (dx, dy) == (offset_x, offset_y):
                return level if self.wire_connection_mask(source) & (1 << bit) else 0
        return 0

    def _strong_powered_solid(
        self, solid: Position, target: Position, *, dust: bool = True
    ) -> int:
        """Power emitted by a solid block receiving a strong input."""
        level = 0
        for delta in NEIGHBORS:
            source = _add(solid, delta)
            if source == target:
                continue
            level = max(
                level,
                # Wires implement both weak and strong redstone power in
                # Java. A wire above a solid block must therefore be able to
                # strongly energize that block, which then relays power to
                # components on its other faces.
                self._output_toward(source, solid, dust=dust, strong=True),
            )
        return level

    def _direct_power(self, pos: Position, *, dust: bool = True) -> int:
        level = 0
        for delta in NEIGHBORS:
            source = _add(pos, delta)
            level = max(level, self._emitted_power_toward(source, pos, dust=dust))
        return level

    def _emitted_power_toward(
        self, source: Position, target: Position, *, dust: bool = True
    ) -> int:
        """Return the power a neighboring block emits into one target face.

        ``World.getEmittedRedstonePower`` combines the source's directional
        weak output with the strong power a solid source has received from its
        other neighbors.  Keeping this directional wrapper separate from
        ``_direct_power`` matters for mounted torches: a torch asks whether
        *its support's downward face* is powered, not whether any face of that
        support has a weak signal.
        """
        level = self._output_toward(source, target, dust=dust)
        if self._is_solid(source):
            level = max(
                level,
                self._strong_powered_solid(source, target, dust=dust),
            )
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
        x, y, z = pos
        mask = 0
        above_open = not self._is_solid((x, y, z + 1))
        for bit, (dx, dy, _) in enumerate(HORIZONTAL):
            side = (x + dx, y + dy, z)
            direction = Facing(bit)
            # Mirror RedstoneWireBlock's getRenderConnectionType.  A wire can
            # climb to a component on a solid neighbor only when the current
            # cell's upper space is open; a component one block above an air
            # side (or above a blocked current cell) is not connected.  On an
            # open side, the only stepped connection is the wire/component
            # directly below that neighbor.
            if (
                above_open
                and self._is_solid(side)
                and self._wire_connects_to((side[0], side[1], z + 1), direction)
            ):
                mask |= 1 << bit
            elif self._wire_connects_to(side, direction):
                mask |= 1 << bit
            elif (
                not self._is_solid(side)
                and self._wire_connects_to((side[0], side[1], z - 1), direction)
            ):
                mask |= 1 << bit
        return mask

    def wire_up_connection_mask(self, pos: Position) -> int:
        """Return directions whose wire climbs onto a neighboring solid block."""
        if self.world.getBlock(*pos) != self.block_type.REDSTONE_DUST:
            return 0
        x, y, z = pos
        if self._is_solid((x, y, z + 1)):
            return 0
        mask = 0
        for bit, (dx, dy, _) in enumerate(HORIZONTAL):
            side = (x + dx, y + dy, z)
            upper = (side[0], side[1], z + 1)
            if self._is_solid(side) and self.world.getBlock(*upper) == self.block_type.REDSTONE_DUST:
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
        self.mark_dirty(pos)
        return True

    def _dust_components_touching(self, positions: Iterable[Position]) -> set[Position]:
        """Return complete wire components adjacent to a localized edit."""
        bt = self.block_type
        seeds: set[Position] = set()
        for x, y, z in positions:
            candidates = {(x, y, z)}
            for dx, dy, dz in NEIGHBORS:
                candidates.add((x + dx, y + dy, z + dz))
                if dz == 0:
                    candidates.add((x + dx, y + dy, z + 1))
                    candidates.add((x + dx, y + dy, z - 1))
            seeds.update(
                candidate for candidate in candidates
                if self.world.getBlock(*candidate) == bt.REDSTONE_DUST
            )
        connected: set[Position] = set()
        queue = deque(seeds)
        while queue:
            pos = queue.popleft()
            if pos in connected:
                continue
            connected.add(pos)
            for neighbor in self._wire_neighbors(pos):
                if neighbor not in connected:
                    queue.append(neighbor)
        return connected

    def _update_dust(self, dirty: Optional[Iterable[Position]] = None) -> bool:
        bt = self.block_type
        if dirty is None:
            positions = list(self.world.blockTypePositions.get(bt.REDSTONE_DUST, ()))
        else:
            positions = list(self._dust_components_touching(dirty))
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

    def _update_torches(self, changed_positions: Optional[set[Position]] = None) -> bool:
        bt = self.block_type
        changed = False
        positions = set(self.world.blockTypePositions.get(bt.REDSTONE_TORCH, ()))
        positions.update(self.world.blockTypePositions.get(bt.REDSTONE_WALL_TORCH, ()))
        if not positions:
            return False

        # Torch output is an inverter, so a single arbitrary set iteration can
        # leave a downstream torch one state behind when its support is visited
        # before the upstream torch changes. Revisit the finite torch set until
        # it reaches a fixed point. The bound is deliberately proportional to
        # the network size: acyclic chains settle in at most one pass per link,
        # while a feedback loop still terminates and uses the normal burnout
        # history/cooldown above instead of spinning forever.
        max_passes = max(1, len(positions) * 2)
        for _ in range(max_passes):
            pass_changed = False
            for pos in positions:
                props = self._props(pos)
                support = self._torch_support(pos, props)
                # Java's RedstoneTorchBlock.shouldUnpower checks the support's
                # emitted power in the torch-facing direction.  Asking for a
                # full ``_direct_power(support)`` scan would incorrectly turn
                # off a torch when a weak-only side lever powers a different
                # face of the support block.
                desired = self._emitted_power_toward(support, pos) == 0
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
                    if changed_positions is not None:
                        changed_positions.add(pos)
                    changed = True
                    pass_changed = True
            if not pass_changed:
                break
        return changed

    def _repeater_input(self, pos: Position, props: BlockProperties) -> int:
        dx, dy, dz = _facing_offset(props.facing)
        # RepeaterBlock.getPower reads the cell on its FACING side. The
        # output is on the opposite side (see _output_toward above).
        front = (pos[0] + dx, pos[1] + dy, pos[2] + dz)
        emitted = self._output_toward(front, pos)
        if self._is_solid(front):
            emitted = max(emitted, self._strong_powered_solid(front, pos))
        # AbstractRedstoneGateBlock.getPower has a deliberate wire fallback:
        # after getEmittedRedstonePower it reads RedstoneWireBlock.POWER
        # directly. Keep that source behavior for stepped/loaded reference
        # states whose directional arm is not currently connected.
        if self.world.getBlock(*front) == self.block_type.REDSTONE_DUST:
            front_props = self.world.getBlockProperties(*front)
            if front_props:
                emitted = max(emitted, max(0, min(15, int(front_props.redstonePower))))
        return emitted

    def _repeater_locked(self, pos: Position, props: BlockProperties) -> bool:
        for side_facing in (props.facing.clockwise(), props.facing.counterclockwise()):
            # getMaxInputLevelSides samples pos.offset(sideFacing), then
            # asks that repeater for strong power in sideFacing. A side
            # repeater therefore locks the main gate when its FACING points
            # back to the side cell, i.e. equals sideFacing.
            side = _add(pos, _facing_offset(side_facing))
            side_props = self.world.getBlockProperties(*side) or BlockProperties()
            if self.world.getBlock(*side) == self.block_type.REPEATER:
                if side_props.powered and side_props.facing == side_facing:
                    return True
        return False

    def _schedule_repeaters(self) -> bool:
        changed = False
        bt = self.block_type
        for pos in self.world.blockTypePositions.get(bt.REPEATER, ()):
            props = self._props(pos)
            locked = self._repeater_locked(pos, props)
            if props.repeaterLocked != locked:
                props.repeaterLocked = locked
                self._set_props(pos, props)
                changed = True
            if locked:
                continue
            desired = self._repeater_input(pos, props) > 0
            # Java keeps an already scheduled gate tick even if the input
            # changes before it fires. That is what extends a pulse shorter
            # than the selected delay instead of swallowing it.
            if desired != props.powered and pos not in self._repeater_updates:
                self._repeater_updates[pos] = (
                    desired, max(1, props.repeaterDelay) * 2
                )
        return changed

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
        # A previous piston event may have edited the world during the last
        # tick. Re-resolve that topology before applying another scheduled
        # repeater/button tick, especially when update() catches up multiple
        # 50 ms ticks in one frame.
        if self.world.revision != self._seen_revision:
            changed |= self.recalculate()
        power_changes: set[Position] = set()
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
                power_changes.add(pos)
                changed = True
        for pos, (scheduled_state, ticks) in list(self._repeater_updates.items()):
            ticks -= 1
            if ticks > 0:
                self._repeater_updates[pos] = (scheduled_state, ticks)
                continue
            self._repeater_updates.pop(pos, None)
            if self.world.getBlock(*pos) != self.block_type.REPEATER:
                continue
            props = self._props(pos)
            if props.repeaterLocked:
                continue
            has_power = self._repeater_input(pos, props) > 0
            if props.powered and not has_power:
                props.powered = False
                props.redstonePower = 0
                self._set_props(pos, props)
                power_changes.add(pos)
                changed = True
            elif not props.powered:
                props.powered = True
                props.redstonePower = 15
                self._set_props(pos, props)
                power_changes.add(pos)
                changed = True
                if not has_power:
                    self._repeater_updates[pos] = (
                        False, max(1, props.repeaterDelay) * 2
                    )
        changed |= self._update_torches(power_changes)
        if power_changes:
            changed |= self._update_dust(power_changes)
            changed |= self._schedule_repeaters()
            # Lamp state is part of the component tick result.  Dropping this
            # return value left callers with a false ``changed`` result even
            # though the lamp had just switched on.
            changed |= self._update_lamps()
        if changed:
            self._pistons_dirty = True
        if self._pistons_dirty:
            piston_changed = self._update_pistons()
            changed |= piston_changed
            if piston_changed:
                # Piston movement can break dust, move a repeater/lamp, or
                # expose a newly powered face. Those world writes happen
                # during this tick; leave a full topology pass queued instead
                # of advancing _seen_revision past the edits and freezing a
                # stale network until the next unrelated user action.
                self._dirty_positions = None
                self._seen_revision = -1
            else:
                self._pistons_dirty = False
                self._seen_revision = self.world.revision
        else:
            self._seen_revision = self.world.revision
        return changed

    def _piston_powered(self, pos: Position) -> bool:
        """Match Java 1.16.1 PistonBlock.shouldExtend, including QC."""
        props = self.world.getBlockProperties(*pos) or BlockProperties()
        face = _facing_offset(props.facing)
        for delta in NEIGHBORS:
            if delta == face:
                continue
            source = _add(pos, delta)
            if self._output_toward(source, pos) > 0:
                return True
            if self._is_solid(source) and self._strong_powered_solid(source, pos) > 0:
                return True
        # Vanilla's second pass checks all power around the block above the
        # piston except the piston beneath it: quasi-connectivity.
        above = (pos[0], pos[1], pos[2] + 1)
        for delta in NEIGHBORS:
            if delta == (0, 0, -1):
                continue
            source = _add(above, delta)
            if self._output_toward(source, above) > 0:
                return True
            if self._is_solid(source) and self._strong_powered_solid(source, above) > 0:
                return True
        return False

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

    def _blocks_stick(self, first, second) -> bool:
        """Return Java's slime/honey adjacency rule for a block pair."""
        bt = self.block_type
        if first == bt.AIR or second == bt.AIR:
            return False
        if {first, second} == {bt.SLIME_BLOCK, bt.HONEY_BLOCK}:
            return False
        return first in (bt.SLIME_BLOCK, bt.HONEY_BLOCK) or second in (
            bt.SLIME_BLOCK, bt.HONEY_BLOCK
        )

    def _plan_piston_move(
        self, start: Position, direction: tuple[int, int, int], piston: Position,
        *, initial_can_break: bool = True,
    ) -> Optional[tuple[list[Position], set[Position]]]:
        """Plan one bounded Java-style push with sticky side branches."""
        moving: set[Position] = set()
        breaking: set[Position] = set()
        backward = (-direction[0], -direction[1], -direction[2])
        movement_axis = 0 if direction[0] else 1 if direction[1] else 2

        def add_cell(
            cell: Position, *, can_break: bool, initial: bool = False,
        ) -> bool:
            if cell == piston:
                return True
            if not self.world.isInBounds(*cell):
                return False
            block = self.world.getBlock(*cell)
            if block == self.block_type.AIR:
                return True
            behavior = self._piston_behavior(
                block, self.world.getBlockProperties(*cell)
            )
            # PistonHandler.tryMove returns success for an immovable branch
            # block: it is not added to the moving list, but it also does not
            # prevent the sticky line from moving.  Only the forward chain
            # (where ``can_break`` is true) treats a BLOCK-behavior cell as a
            # hard obstruction.
            if behavior == "block":
                return False if initial else not can_break
            if behavior == "break":
                if initial and not can_break:
                    return False
                if can_break:
                    breaking.add(cell)
                return True
            if behavior != "move":
                return False
            if cell in moving:
                return True
            if len(moving) >= 12:
                return False
            moving.add(cell)

            # A slime/honey line can pull blocks behind the first encountered
            # block into the moving group. The piston base terminates it.
            behind = _add(cell, backward)
            if behind != piston and self.world.isInBounds(*behind):
                behind_block = self.world.getBlock(*behind)
                if self._blocks_stick(block, behind_block):
                    if not add_cell(behind, can_break=False):
                        return False

            if not add_cell(_add(cell, direction), can_break=True):
                return False

            # PistonHandler checks sticky neighbors perpendicular to motion.
            if block in (self.block_type.SLIME_BLOCK, self.block_type.HONEY_BLOCK):
                for side in NEIGHBORS:
                    if side[movement_axis] != 0:
                        continue
                    neighbor = _add(cell, side)
                    if not self.world.isInBounds(*neighbor):
                        continue
                    neighbor_block = self.world.getBlock(*neighbor)
                    if self._blocks_stick(block, neighbor_block):
                        if not add_cell(neighbor, can_break=False):
                            return False
            return True

        if not add_cell(start, can_break=initial_can_break, initial=True):
            return None
        ordered = sorted(
            moving,
            key=lambda cell: (
                cell[0] * direction[0]
                + cell[1] * direction[1]
                + cell[2] * direction[2]
            ),
            reverse=True,
        )
        return ordered, breaking

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
        plan = self._plan_piston_move(front, direction, pos)
        if plan is None:
            return False
        chain, breaking = plan
        moving = [self._capture_cell(source, _add(source, direction)) for source in chain]
        head_props = BlockProperties(
            facing=props.facing, pistonExtended=True,
            sticky=self.world.getBlock(*pos) == self.block_type.STICKY_PISTON,
        )
        moving.append(MovingCell(self.block_type.PISTON_HEAD, head_props.copy(), pos, front))
        final_targets = [_add(source, direction) for source in chain]
        final_targets.append(front)
        with self.world.bulkUpdate():
            for fragile in breaking:
                self._break_cell(fragile)
            for source in chain:
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
                pull_direction = (-direction[0], -direction[1], -direction[2])
                plan = self._plan_piston_move(
                    pull, pull_direction, pos, initial_can_break=False,
                )
                if plan is not None:
                    chain, breaking = plan
                    for fragile in breaking:
                        self._break_cell(fragile)
                    for source in chain:
                        target = _add(source, pull_direction)
                        moving.append(self._capture_cell(source, target))
                        final_targets.append(target)
                        self._move_cell(source, target)
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
