"""Immutable data staged off-thread before replacing a live world.

Snapshots contain Python data only. They intentionally exclude Pygame surfaces,
UI state, and undo history so decoding and validation may run in a worker.
"""

from dataclasses import dataclass, field
from typing import Any, Mapping


Position = tuple[int, int, int]


@dataclass(frozen=True)
class WorldSnapshot:
    """Validated build state ready for one atomic live-world replacement."""

    width: int
    depth: int
    height: int
    min_y: int = 0
    dimension: str = "overworld"
    blocks: Mapping[Position, Any] = field(default_factory=dict)
    properties: Mapping[Position, Any] = field(default_factory=dict)
    liquid_levels: Mapping[Position, int] = field(default_factory=dict)
    liquid_sources: frozenset[Position] = frozenset()
    liquid_falling: frozenset[Position] = frozenset()
    scene_metadata: Mapping[str, Any] = field(default_factory=dict)
    structure_positions: frozenset[Position] = frozenset()
    exterior_glass_positions: frozenset[Position] = frozenset()
    structure_surfaces_by_view: Mapping[int, frozenset[Position]] = field(default_factory=dict)
    surface_positions: frozenset[Position] = frozenset()
    view_surface_positions_by_view: Mapping[int, frozenset[Position]] = field(default_factory=dict)
    draw_orders_by_mode: Mapping[str, Mapping[int, tuple]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.width < 1 or self.depth < 1 or self.height < 1:
            raise ValueError("world dimensions must be positive")
        # Staging owns these containers until ``World.replace`` consumes them.
        # Avoid copying 100k+ cell maps on the main thread.
