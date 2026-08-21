"""
Engine module for Bloc Fantome.

Contains core systems:
- Undo management
- World voxel grid
- Isometric renderer
- Performance optimizations
"""

from .undo import UndoManager, Command, PlaceBlockCommand, RemoveBlockCommand, BatchCommand
from .renderer import IsometricRenderer, ProjectionMetrics, set_tile_dimensions
from .world import World
from .performance import (
    DirtyRegionTracker,
    ChunkStorage,
    SpriteCache,
    TextureAtlas,
    LazyTextureLoader,
    RenderBatcher,
    PerformanceMonitor
)

__all__ = [
    # Undo system
    'UndoManager',
    'Command',
    'PlaceBlockCommand',
    'RemoveBlockCommand',
    'BatchCommand',
    # Renderer
    'IsometricRenderer',
    'ProjectionMetrics',
    'set_tile_dimensions',
    # World
    'World',
    # Performance
    'DirtyRegionTracker',
    'ChunkStorage',
    'SpriteCache',
    'TextureAtlas',
    'LazyTextureLoader',
    'RenderBatcher',
    'PerformanceMonitor',
]
