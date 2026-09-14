"""Immutable data staged off-thread before replacing a live world.

Snapshots contain Python data only. They intentionally exclude Pygame surfaces,
UI state, and undo history so decoding and validation may run in a worker.
"""

from dataclasses import dataclass, field
from typing import Any, Mapping


Position = tuple[int, int, int]


def release_world_state(state):
    """Drop old indexes on the loading worker, yielding between containers.

    Only release references: snapshots or undo records may still own their data.
    """
    import time
    while state:
        state.popitem()
        time.sleep(0)


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
    _prepared: Any = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.width < 1 or self.depth < 1 or self.height < 1:
            raise ValueError("world dimensions must be positive")
        # Staging owns these containers until ``World.replace`` consumes them.
        # Avoid copying 100k+ cell maps on the main thread.


def prepare_snapshot(snapshot, catalog, *, reusable=True):
    """Build an independently owned replacement on the loading worker.

    The one-use holder transfers indexes as well as cells. The original snapshot
    remains reusable, so editing a tour page cannot change a later visit.
    """
    from dataclasses import replace
    from engine.world import World

    owned = snapshot
    if reusable:
        owned = replace(snapshot, _prepared=None, blocks=dict(snapshot.blocks),
            properties={p: value.copy() for p, value in snapshot.properties.items()},
            surface_positions=frozenset(snapshot.surface_positions),
            structure_positions=frozenset(snapshot.structure_positions),
            structure_surfaces_by_view={r: frozenset(v) for r, v in snapshot.structure_surfaces_by_view.items()},
            view_surface_positions_by_view={r: frozenset(v) for r, v in snapshot.view_surface_positions_by_view.items()},
            draw_orders_by_mode={mode: dict(views) for mode, views in snapshot.draw_orders_by_mode.items()})
    prepared = World(owned.width, owned.depth, owned.height, catalog=catalog)
    prepared.replace(owned)
    for rotation in range(4):
        prepared.prepareViewSurfaceChunks(rotation)
    if not prepared.drawOrdersByMode or snapshot.scene_metadata.get('water_cutaway'):
        from engine.build_io import _draw_orders
        visible_blocks = prepared.blocks
        if snapshot.scene_metadata.get('water_cutaway'):
            visible_blocks = {p: b for p, b in prepared.blocks.items() if b.name not in ('WATER', 'BUBBLE_COLUMN')}
        prepared.drawOrdersByMode = _draw_orders(visible_blocks,prepared.sceneStructurePositions,
            prepared.sceneStructureSurfacesByView,prepared.viewSurfacePositionsByView)
        prepared.drawOrdersRevision = prepared.revision
    if snapshot.scene_metadata.get('water_cutaway'):
        for views in prepared.drawOrdersByMode.values():
            for rotation,order in views.items():
                views[rotation]=tuple(item for item in order if item[4].name not in ('WATER','BUBBLE_COLUMN'))
    return replace(snapshot, _prepared=[prepared])
