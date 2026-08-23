"""Compatibility exports for stable runtime, projection, and state values.

New code should import from ``runtime_paths``, ``domain.dimensions``,
``engine.block_state``, or ``engine.renderer`` directly.
"""

from domain.dimensions import DIMENSION_END, DIMENSION_NETHER, DIMENSION_OVERWORLD
from domain.blocks import (
    BlockProperties,
    DoorHalf,
    DoorHinge,
    Facing,
    SlabPosition,
    StairShape,
)
from engine.renderer import ProjectionMetrics
from runtime_paths import *  # noqa: F403 - intentional compatibility surface


WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800
TITLE = "Bloc Fantôme"
PANEL_WIDTH = 260
ICON_SIZE = 72
ICON_MARGIN = 10
ICONS_PER_ROW = 3
BG_TILE_SIZE = 64
GRID_WIDTH = 12
GRID_DEPTH = 12
GRID_HEIGHT = 12
TILE_WIDTH = ProjectionMetrics().tile_width
TILE_HEIGHT = ProjectionMetrics().tile_height
BLOCK_HEIGHT = ProjectionMetrics().block_height
WATER_FLOW_DELAY = 250
LAVA_FLOW_DELAY = 1500
