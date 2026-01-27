"""
Performance Module for Bite Sized Minecraft

This module provides performance optimizations including:
- Dirty region tracking (only re-render changed areas)
- Chunk-based world storage for large builds
- LRU cache management for sprites
- Sprite atlas generation and lookup
- Lazy texture loading with demand-based caching

Usage:
    from engine.performance import DirtyRegionTracker, ChunkStorage, SpriteCache
"""

from collections import OrderedDict
from typing import Dict, Set, Tuple, Optional, List, Any
import pygame
import math


class DirtyRegionTracker:
    """
    Tracks which regions of the world have changed and need re-rendering.
    
    Instead of redrawing the entire world every frame, only regions marked
    as "dirty" (changed) are redrawn. This significantly improves performance
    for large builds where most blocks don't change frame-to-frame.
    
    Regions are cube-shaped chunks of configurable size.
    """
    
    def __init__(self, chunk_size: int = 8):
        """
        Initialize the dirty region tracker.
        
        Args:
            chunk_size: Size of each chunk region in blocks (default 8x8x8)
        """
        self.chunk_size = chunk_size
        self.dirty_chunks: Set[Tuple[int, int, int]] = set()
        self.full_redraw_needed = True  # Start with full redraw
    
    def mark_dirty(self, x: int, y: int, z: int) -> None:
        """
        Mark a block position as dirty, requiring its chunk to be redrawn.
        
        Args:
            x, y, z: World coordinates of the changed block
        """
        chunk_x = x // self.chunk_size
        chunk_y = y // self.chunk_size
        chunk_z = z // self.chunk_size
        self.dirty_chunks.add((chunk_x, chunk_y, chunk_z))
    
    def mark_region_dirty(self, x1: int, y1: int, z1: int, 
                          x2: int, y2: int, z2: int) -> None:
        """
        Mark a rectangular region as dirty.
        
        Args:
            x1, y1, z1: Start corner
            x2, y2, z2: End corner
        """
        # Ensure proper ordering
        x1, x2 = min(x1, x2), max(x1, x2)
        y1, y2 = min(y1, y2), max(y1, y2)
        z1, z2 = min(z1, z2), max(z1, z2)
        
        # Mark all chunks in the region
        for x in range(x1 // self.chunk_size, x2 // self.chunk_size + 1):
            for y in range(y1 // self.chunk_size, y2 // self.chunk_size + 1):
                for z in range(z1 // self.chunk_size, z2 // self.chunk_size + 1):
                    self.dirty_chunks.add((x, y, z))
    
    def request_full_redraw(self) -> None:
        """Request a full world redraw (e.g., after view rotation or zoom)."""
        self.full_redraw_needed = True
    
    def needs_redraw(self) -> bool:
        """Check if any redraw is needed."""
        return self.full_redraw_needed or len(self.dirty_chunks) > 0
    
    def is_chunk_dirty(self, chunk_x: int, chunk_y: int, chunk_z: int) -> bool:
        """Check if a specific chunk needs redraw."""
        return self.full_redraw_needed or (chunk_x, chunk_y, chunk_z) in self.dirty_chunks
    
    def is_block_in_dirty_chunk(self, x: int, y: int, z: int) -> bool:
        """Check if a block's chunk is dirty."""
        chunk_x = x // self.chunk_size
        chunk_y = y // self.chunk_size
        chunk_z = z // self.chunk_size
        return self.is_chunk_dirty(chunk_x, chunk_y, chunk_z)
    
    def clear_dirty(self) -> None:
        """Clear all dirty flags after rendering."""
        self.dirty_chunks.clear()
        self.full_redraw_needed = False
    
    def get_dirty_chunks(self) -> Set[Tuple[int, int, int]]:
        """Get the set of dirty chunk coordinates."""
        return self.dirty_chunks.copy()


class ChunkStorage:
    """
    Chunk-based world storage for efficient large build handling.
    
    Divides the world into fixed-size chunks, allowing:
    - Efficient spatial queries (get blocks in a region)
    - Memory-efficient storage of sparse worlds
    - Faster iteration when rendering
    
    Each chunk is a dictionary mapping local coordinates to block data.
    """
    
    def __init__(self, chunk_size: int = 8):
        """
        Initialize chunk storage.
        
        Args:
            chunk_size: Size of each chunk in blocks (default 8x8x8)
        """
        self.chunk_size = chunk_size
        self.chunks: Dict[Tuple[int, int, int], Dict[Tuple[int, int, int], Any]] = {}
    
    def _get_chunk_key(self, x: int, y: int, z: int) -> Tuple[int, int, int]:
        """Get the chunk key for a world position."""
        return (x // self.chunk_size, y // self.chunk_size, z // self.chunk_size)
    
    def _get_local_coords(self, x: int, y: int, z: int) -> Tuple[int, int, int]:
        """Get local coordinates within a chunk."""
        return (x % self.chunk_size, y % self.chunk_size, z % self.chunk_size)
    
    def set_block(self, x: int, y: int, z: int, block_data: Any) -> None:
        """
        Set block data at a position.
        
        Args:
            x, y, z: World coordinates
            block_data: Data to store (typically BlockType or (BlockType, props))
        """
        chunk_key = self._get_chunk_key(x, y, z)
        local_coords = self._get_local_coords(x, y, z)
        
        if block_data is None:
            # Remove block
            if chunk_key in self.chunks:
                self.chunks[chunk_key].pop(local_coords, None)
                # Clean up empty chunks
                if not self.chunks[chunk_key]:
                    del self.chunks[chunk_key]
        else:
            # Add/update block
            if chunk_key not in self.chunks:
                self.chunks[chunk_key] = {}
            self.chunks[chunk_key][local_coords] = block_data
    
    def get_block(self, x: int, y: int, z: int) -> Optional[Any]:
        """
        Get block data at a position.
        
        Args:
            x, y, z: World coordinates
            
        Returns:
            Block data or None if no block at position
        """
        chunk_key = self._get_chunk_key(x, y, z)
        if chunk_key not in self.chunks:
            return None
        local_coords = self._get_local_coords(x, y, z)
        return self.chunks[chunk_key].get(local_coords)
    
    def get_blocks_in_chunk(self, chunk_x: int, chunk_y: int, chunk_z: int) -> Dict[Tuple[int, int, int], Any]:
        """
        Get all blocks in a specific chunk with world coordinates.
        
        Args:
            chunk_x, chunk_y, chunk_z: Chunk coordinates
            
        Returns:
            Dictionary mapping world coords to block data
        """
        chunk_key = (chunk_x, chunk_y, chunk_z)
        if chunk_key not in self.chunks:
            return {}
        
        result = {}
        base_x = chunk_x * self.chunk_size
        base_y = chunk_y * self.chunk_size
        base_z = chunk_z * self.chunk_size
        
        for (lx, ly, lz), data in self.chunks[chunk_key].items():
            world_x = base_x + lx
            world_y = base_y + ly
            world_z = base_z + lz
            result[(world_x, world_y, world_z)] = data
        
        return result
    
    def get_all_blocks(self) -> Dict[Tuple[int, int, int], Any]:
        """
        Get all blocks as a flat dictionary (for compatibility).
        
        Returns:
            Dictionary mapping world coords to block data
        """
        result = {}
        for (cx, cy, cz), chunk_data in self.chunks.items():
            base_x = cx * self.chunk_size
            base_y = cy * self.chunk_size
            base_z = cz * self.chunk_size
            for (lx, ly, lz), data in chunk_data.items():
                result[(base_x + lx, base_y + ly, base_z + lz)] = data
        return result
    
    def get_occupied_chunks(self) -> List[Tuple[int, int, int]]:
        """Get list of all chunks that contain blocks."""
        return list(self.chunks.keys())
    
    def get_block_count(self) -> int:
        """Get total number of blocks stored."""
        return sum(len(chunk) for chunk in self.chunks.values())
    
    def clear(self) -> None:
        """Remove all blocks."""
        self.chunks.clear()


class SpriteCache:
    """
    LRU (Least Recently Used) cache for rendered sprites.
    
    Caches transformed/lit sprites to avoid redundant processing.
    Uses OrderedDict to track access order and evict least-used entries.
    """
    
    def __init__(self, max_size: int = 500):
        """
        Initialize sprite cache.
        
        Args:
            max_size: Maximum number of sprites to cache
        """
        self.max_size = max_size
        self.cache: OrderedDict[Any, pygame.Surface] = OrderedDict()
        self.hits = 0
        self.misses = 0
    
    def get(self, key: Any) -> Optional[pygame.Surface]:
        """
        Get a cached sprite.
        
        Args:
            key: Cache key (typically (blockType, lightLevel, ao, rotation) tuple)
            
        Returns:
            Cached sprite or None if not found
        """
        if key in self.cache:
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            self.hits += 1
            return self.cache[key]
        self.misses += 1
        return None
    
    def set(self, key: Any, sprite: pygame.Surface) -> None:
        """
        Store a sprite in cache.
        
        Args:
            key: Cache key
            sprite: Sprite to cache
        """
        if key in self.cache:
            # Update existing and move to end
            self.cache[key] = sprite
            self.cache.move_to_end(key)
        else:
            # Add new entry
            self.cache[key] = sprite
            # Evict oldest if over capacity
            while len(self.cache) > self.max_size:
                self.cache.popitem(last=False)  # Remove oldest (first)
    
    def invalidate(self, key: Any) -> None:
        """Remove a specific entry from cache."""
        self.cache.pop(key, None)
    
    def invalidate_by_prefix(self, prefix: Any) -> None:
        """
        Remove all entries whose key starts with the given prefix.
        Useful for invalidating all variants of a block type.
        
        Args:
            prefix: Key prefix (e.g., BlockType value)
        """
        keys_to_remove = [k for k in self.cache if k[0] == prefix]
        for key in keys_to_remove:
            del self.cache[key]
    
    def clear(self) -> None:
        """Clear the entire cache."""
        self.cache.clear()
        self.hits = 0
        self.misses = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self.hits + self.misses
        hit_rate = self.hits / total if total > 0 else 0
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate
        }


class TextureAtlas:
    """
    Combines multiple textures into a single large texture (atlas).
    
    Benefits:
    - Reduces draw calls (one blit per frame instead of many)
    - Better cache locality for GPU
    - Efficient batch rendering
    """
    
    def __init__(self, tile_size: int = 16, padding: int = 1):
        """
        Initialize texture atlas.
        
        Args:
            tile_size: Size of each tile (default 16x16)
            padding: Pixels between tiles to prevent bleeding
        """
        self.tile_size = tile_size
        self.padding = padding
        self.atlas_surface: Optional[pygame.Surface] = None
        self.tile_positions: Dict[str, Tuple[int, int]] = {}  # name -> (x, y) in atlas
        self.atlas_size = 0
    
    def build(self, textures: Dict[str, pygame.Surface]) -> pygame.Surface:
        """
        Build atlas from a dictionary of textures.
        
        Args:
            textures: Dictionary mapping texture name to Surface
            
        Returns:
            The combined atlas surface
        """
        if not textures:
            return pygame.Surface((1, 1))
        
        # Calculate atlas size (square, power of 2)
        num_textures = len(textures)
        tiles_per_row = math.ceil(math.sqrt(num_textures))
        total_tile_size = self.tile_size + self.padding * 2
        atlas_size = tiles_per_row * total_tile_size
        
        # Round up to power of 2 for GPU efficiency
        atlas_size = 2 ** math.ceil(math.log2(atlas_size))
        self.atlas_size = atlas_size
        
        # Create atlas surface with alpha
        self.atlas_surface = pygame.Surface((atlas_size, atlas_size), pygame.SRCALPHA)
        self.atlas_surface.fill((0, 0, 0, 0))  # Transparent
        
        # Place textures
        self.tile_positions.clear()
        current_x = self.padding
        current_y = self.padding
        row_height = 0
        
        for name, texture in textures.items():
            # Scale texture to tile_size if needed
            if texture.get_size() != (self.tile_size, self.tile_size):
                texture = pygame.transform.scale(texture, (self.tile_size, self.tile_size))
            
            # Check if we need to wrap to next row
            if current_x + self.tile_size + self.padding > atlas_size:
                current_x = self.padding
                current_y += row_height + self.padding * 2
                row_height = 0
            
            # Blit texture to atlas
            self.atlas_surface.blit(texture, (current_x, current_y))
            self.tile_positions[name] = (current_x, current_y)
            
            row_height = max(row_height, self.tile_size)
            current_x += self.tile_size + self.padding * 2
        
        return self.atlas_surface
    
    def get_tile_rect(self, name: str) -> Optional[pygame.Rect]:
        """
        Get the rectangle for a tile in the atlas.
        
        Args:
            name: Texture name
            
        Returns:
            pygame.Rect for the tile, or None if not found
        """
        if name not in self.tile_positions:
            return None
        x, y = self.tile_positions[name]
        return pygame.Rect(x, y, self.tile_size, self.tile_size)
    
    def get_tile(self, name: str) -> Optional[pygame.Surface]:
        """
        Extract a tile from the atlas as a subsurface.
        
        Args:
            name: Texture name
            
        Returns:
            Subsurface of the tile, or None if not found
        """
        rect = self.get_tile_rect(name)
        if rect is None or self.atlas_surface is None:
            return None
        return self.atlas_surface.subsurface(rect)


class LazyTextureLoader:
    """
    Lazy texture loader that only loads textures when first requested.
    
    Useful for large texture sets where not all textures may be used
    in a single session.
    """
    
    def __init__(self, texture_dir: str):
        """
        Initialize lazy loader.
        
        Args:
            texture_dir: Base directory for textures
        """
        import os
        self.texture_dir = texture_dir
        self.loaded_textures: Dict[str, pygame.Surface] = {}
        self.failed_textures: Set[str] = set()  # Track failed loads to avoid retrying
    
    def get(self, name: str) -> Optional[pygame.Surface]:
        """
        Get a texture, loading it if not already loaded.
        
        Args:
            name: Texture filename
            
        Returns:
            Loaded texture or None if load failed
        """
        import os
        
        # Return cached if available
        if name in self.loaded_textures:
            return self.loaded_textures[name]
        
        # Don't retry failed loads
        if name in self.failed_textures:
            return None
        
        # Try to load
        path = os.path.join(self.texture_dir, name)
        try:
            texture = pygame.image.load(path).convert_alpha()
            self.loaded_textures[name] = texture
            return texture
        except Exception as e:
            self.failed_textures.add(name)
            return None
    
    def preload(self, names: List[str]) -> None:
        """
        Preload multiple textures.
        
        Args:
            names: List of texture filenames to preload
        """
        for name in names:
            self.get(name)
    
    def unload(self, name: str) -> None:
        """
        Unload a texture to free memory.
        
        Args:
            name: Texture filename to unload
        """
        self.loaded_textures.pop(name, None)
    
    def get_loaded_count(self) -> int:
        """Get number of currently loaded textures."""
        return len(self.loaded_textures)


class RenderBatcher:
    """
    Batches multiple sprite draw calls for more efficient rendering.
    
    Instead of individual blit calls, collects sprites and draws them
    in a single batch operation when possible.
    """
    
    def __init__(self):
        """Initialize the render batcher."""
        self.batch: List[Tuple[pygame.Surface, Tuple[int, int], int]] = []
        # Each entry: (sprite, position, z_order)
    
    def add(self, sprite: pygame.Surface, position: Tuple[int, int], z_order: int = 0) -> None:
        """
        Add a sprite to the current batch.
        
        Args:
            sprite: Surface to draw
            position: (x, y) position
            z_order: Draw order (lower = drawn first/behind)
        """
        self.batch.append((sprite, position, z_order))
    
    def flush(self, target: pygame.Surface) -> int:
        """
        Draw all batched sprites to target surface.
        
        Args:
            target: Surface to draw to
            
        Returns:
            Number of sprites drawn
        """
        if not self.batch:
            return 0
        
        # Sort by z_order
        self.batch.sort(key=lambda x: x[2])
        
        # Draw all sprites
        count = 0
        for sprite, position, _ in self.batch:
            target.blit(sprite, position)
            count += 1
        
        # Clear batch
        self.batch.clear()
        return count
    
    def clear(self) -> None:
        """Clear the batch without drawing."""
        self.batch.clear()


# Performance monitoring utilities
class PerformanceMonitor:
    """
    Simple performance monitoring for tracking frame times and bottlenecks.
    """
    
    def __init__(self, window_size: int = 60):
        """
        Initialize monitor.
        
        Args:
            window_size: Number of frames to average over
        """
        self.window_size = window_size
        self.frame_times: List[float] = []
        self.section_times: Dict[str, List[float]] = {}
        self._section_start: Dict[str, float] = {}
    
    def frame_start(self) -> None:
        """Call at the start of each frame."""
        import time
        self._frame_start = time.perf_counter()
    
    def frame_end(self) -> None:
        """Call at the end of each frame."""
        import time
        elapsed = time.perf_counter() - self._frame_start
        self.frame_times.append(elapsed * 1000)  # Convert to ms
        if len(self.frame_times) > self.window_size:
            self.frame_times.pop(0)
    
    def section_start(self, name: str) -> None:
        """Start timing a named section."""
        import time
        self._section_start[name] = time.perf_counter()
    
    def section_end(self, name: str) -> None:
        """End timing a named section."""
        import time
        if name not in self._section_start:
            return
        elapsed = time.perf_counter() - self._section_start[name]
        
        if name not in self.section_times:
            self.section_times[name] = []
        self.section_times[name].append(elapsed * 1000)
        if len(self.section_times[name]) > self.window_size:
            self.section_times[name].pop(0)
    
    def get_fps(self) -> float:
        """Get average FPS over the window."""
        if not self.frame_times:
            return 0
        avg_ms = sum(self.frame_times) / len(self.frame_times)
        return 1000 / avg_ms if avg_ms > 0 else 0
    
    def get_frame_time(self) -> float:
        """Get average frame time in ms."""
        if not self.frame_times:
            return 0
        return sum(self.frame_times) / len(self.frame_times)
    
    def get_section_time(self, name: str) -> float:
        """Get average time for a named section in ms."""
        if name not in self.section_times or not self.section_times[name]:
            return 0
        return sum(self.section_times[name]) / len(self.section_times[name])
    
    def get_report(self) -> Dict[str, Any]:
        """Get a full performance report."""
        report = {
            "fps": self.get_fps(),
            "frame_time_ms": self.get_frame_time(),
            "sections": {}
        }
        for name in self.section_times:
            report["sections"][name] = self.get_section_time(name)
        return report
