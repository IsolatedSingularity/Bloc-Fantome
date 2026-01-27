"""
Engine module for Bloc Fantome.

Contains core systems:
- Undo management
- World voxel grid
- Isometric renderer
- Performance optimizations
"""

from .undo import UndoManager, Command, PlaceBlockCommand, RemoveBlockCommand, BatchCommand
from .renderer import IsometricRenderer, set_tile_dimensions
from .world import World, init_world_module
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
    'set_tile_dimensions',
    # World
    'World',
    'init_world_module',
    # Performance
    'DirtyRegionTracker',
    'ChunkStorage',
    'SpriteCache',
    'TextureAtlas',
    'LazyTextureLoader',
    'RenderBatcher',
    'PerformanceMonitor',
]
