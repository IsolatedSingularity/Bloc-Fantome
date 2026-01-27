"""
Isometric Renderer Module for Bloc Fantome

This module handles conversion between 3D world coordinates and 2D screen
coordinates using 2:1 dimetric (pseudo-isometric) projection.

Features:
- World to screen coordinate conversion
- Screen to world coordinate conversion  
- 4 view rotations (0°, 90°, 180°, 270°)
- Zoom support
"""

from typing import Tuple

# Default tile dimensions - can be overridden
TILE_WIDTH = 64
TILE_HEIGHT = 32
BLOCK_HEIGHT = 38


def set_tile_dimensions(tile_width: int, tile_height: int, block_height: int):
    """Set the tile dimensions used for projection."""
    global TILE_WIDTH, TILE_HEIGHT, BLOCK_HEIGHT
    TILE_WIDTH = tile_width
    TILE_HEIGHT = tile_height
    BLOCK_HEIGHT = block_height


class IsometricRenderer:
    """
    Handles conversion between 3D world coordinates and 2D screen coordinates
    using 2:1 dimetric (pseudo-isometric) projection.
    
    Supports 4 view rotations:
    - 0: Default view (45°)
    - 1: Rotated 90° clockwise (135°)
    - 2: Rotated 180° (225°)
    - 3: Rotated 270° clockwise (315°)
    """
    
    def __init__(self, offsetX: int, offsetY: int):
        """
        Initialize the renderer.
        
        Args:
            offsetX: Screen X offset for centering
            offsetY: Screen Y offset for centering
        """
        self.offsetX = offsetX
        self.offsetY = offsetY
        self.zoomLevel = 1.0
        self.viewRotation = 0  # 0, 1, 2, 3 for 4 isometric views
        # Cached zoom-scaled tile dimensions
        self._tileW = TILE_WIDTH
        self._tileH = TILE_HEIGHT
        self._blockH = BLOCK_HEIGHT
        self._tileWHalf = TILE_WIDTH // 2
        self._tileHHalf = TILE_HEIGHT // 2
    
    def setZoom(self, zoomLevel: float):
        """Set the zoom level (0.5 to 2.0)"""
        self.zoomLevel = zoomLevel
        # Update cached dimensions
        self._tileW = int(TILE_WIDTH * zoomLevel)
        self._tileH = int(TILE_HEIGHT * zoomLevel)
        self._blockH = int(BLOCK_HEIGHT * zoomLevel)
        self._tileWHalf = self._tileW // 2
        self._tileHHalf = self._tileH // 2
    
    def rotateView(self, direction: int = 1):
        """
        Rotate the view by 90 degrees.
        
        Args:
            direction: 1 for clockwise, -1 for counter-clockwise
        """
        self.viewRotation = (self.viewRotation + direction) % 4
    
    def setViewRotation(self, rotation: int):
        """Set the view rotation directly (0-3)"""
        self.viewRotation = rotation % 4
    
    def _rotateCoords(self, x: int, y: int) -> Tuple[int, int]:
        """
        Rotate world X,Y coordinates based on current view rotation.
        
        Returns rotated (x, y) coordinates.
        """
        if self.viewRotation == 0:
            return (x, y)
        elif self.viewRotation == 1:
            return (-y, x)
        elif self.viewRotation == 2:
            return (-x, -y)
        elif self.viewRotation == 3:
            return (y, -x)
        return (x, y)
    
    def _unrotateCoords(self, x: int, y: int) -> Tuple[int, int]:
        """
        Inverse rotation to convert screen-derived coords back to world coords.
        
        Returns unrotated (x, y) coordinates.
        """
        if self.viewRotation == 0:
            return (x, y)
        elif self.viewRotation == 1:
            return (y, -x)
        elif self.viewRotation == 2:
            return (-x, -y)
        elif self.viewRotation == 3:
            return (-y, x)
        return (x, y)
    
    def worldToScreen(self, x: int, y: int, z: int) -> Tuple[int, int]:
        """
        Convert 3D world coordinates to 2D screen coordinates.
        
        Args:
            x, y, z: World coordinates
            
        Returns:
            Tuple of (screenX, screenY)
        """
        # Apply view rotation to X,Y coordinates
        rx, ry = self._rotateCoords(x, y)
        
        # Use cached zoom-scaled dimensions for performance
        screenX = (rx - ry) * self._tileWHalf + self.offsetX
        screenY = (rx + ry) * self._tileHHalf - z * self._blockH + self.offsetY
        return (screenX, screenY)
    
    def screenToWorld(self, screenX: int, screenY: int, targetZ: int = 0) -> Tuple[int, int]:
        """
        Convert 2D screen coordinates to 3D world coordinates at a given Z level.
        
        Args:
            screenX, screenY: Screen coordinates
            targetZ: Z level to project onto
            
        Returns:
            Tuple of (worldX, worldY)
        """
        # Use cached zoom-scaled dimensions for performance
        tileW = self._tileW
        tileH = self._tileH
        blockH = self._blockH
        
        # Adjust for offset and Z level
        adjustedX = screenX - self.offsetX
        adjustedY = screenY - self.offsetY + targetZ * blockH
        
        # Inverse of the projection formulas (gives rotated coords)
        rotatedX = (adjustedX / (tileW / 2) + adjustedY / (tileH / 2)) / 2
        rotatedY = (adjustedY / (tileH / 2) - adjustedX / (tileW / 2)) / 2
        
        # Unrotate to get actual world coordinates
        worldX, worldY = self._unrotateCoords(round(rotatedX), round(rotatedY))
        
        return (worldX, worldY)
    
    def setOffset(self, offsetX: int, offsetY: int):
        """Update the screen offset"""
        self.offsetX = offsetX
        self.offsetY = offsetY
    
    def getScaledBlockHeight(self) -> int:
        """Get the current zoom-scaled block height"""
        return self._blockH
    
    def getScaledTileWidth(self) -> int:
        """Get the current zoom-scaled tile width"""
        return self._tileW
    
    def getScaledTileHeight(self) -> int:
        """Get the current zoom-scaled tile height"""
        return self._tileH
