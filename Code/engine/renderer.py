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

from typing import Dict, List, Optional, Tuple

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
        self._tileW = float(TILE_WIDTH)
        self._tileH = float(TILE_HEIGHT)
        self._blockH = float(BLOCK_HEIGHT)
        self._tileWHalf = TILE_WIDTH / 2.0
        self._tileHHalf = TILE_HEIGHT / 2.0
    
    def setZoom(self, zoomLevel: float):
        """Set zoom without quantizing the projection at overview scales."""
        self.zoomLevel = max(0.01, float(zoomLevel))
        # Keeping these as floats matters below 25%. Integer dimensions made
        # the half-height become zero and caused blocks to jump or collapse.
        self._tileW = TILE_WIDTH * self.zoomLevel
        self._tileH = TILE_HEIGHT * self.zoomLevel
        self._blockH = BLOCK_HEIGHT * self.zoomLevel
        self._tileWHalf = self._tileW / 2.0
        self._tileHHalf = self._tileH / 2.0
    
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
        return (round(screenX), round(screenY))
    
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
    
    def setOffset(self, offsetX: float, offsetY: float):
        """Update the screen offset"""
        self.offsetX = offsetX
        self.offsetY = offsetY
    
    def getScaledBlockHeight(self) -> float:
        """Get the current zoom-scaled block height"""
        return self._blockH
    
    def getScaledTileWidth(self) -> float:
        """Get the current zoom-scaled tile width"""
        return self._tileW
    
    def getScaledTileHeight(self) -> float:
        """Get the current zoom-scaled tile height"""
        return self._tileH

    def depthKey(self, x: int, y: int, z: int) -> int:
        """Return the exact painter-order key used by rendering and picking."""
        if self.viewRotation == 0:
            return x + y + z
        if self.viewRotation == 1:
            return -y + x + z
        if self.viewRotation == 2:
            return -x - y + z
        return y - x + z

    def getBlockFacePolygons(self, x: int, y: int, z: int) -> Dict[str, List[Tuple[int, int]]]:
        """Return zoom-correct polygons for the three visible cube faces."""
        screenX, screenY = self.worldToScreen(x, y, z)
        halfW = self._tileW / 2.0
        halfH = self._tileH / 2.0
        tileH = self._tileH
        blockH = self._blockH
        point = lambda px, py: (round(px), round(py))
        return {
            "top": [
                point(screenX, screenY),
                point(screenX + halfW, screenY + halfH),
                point(screenX, screenY + tileH),
                point(screenX - halfW, screenY + halfH),
            ],
            "left": [
                point(screenX - halfW, screenY + halfH),
                point(screenX, screenY + tileH),
                point(screenX, screenY + tileH + blockH),
                point(screenX - halfW, screenY + halfH + blockH),
            ],
            "right": [
                point(screenX, screenY + tileH),
                point(screenX + halfW, screenY + halfH),
                point(screenX + halfW, screenY + halfH + blockH),
                point(screenX, screenY + tileH + blockH),
            ],
        }

    @staticmethod
    def _pointInConvexPolygon(point: Tuple[int, int], polygon: List[Tuple[int, int]], tolerance: int = 1) -> bool:
        """Return True for points inside or on the edge of a convex polygon."""
        px, py = point
        sign = 0
        for index, (x1, y1) in enumerate(polygon):
            x2, y2 = polygon[(index + 1) % len(polygon)]
            cross = (x2 - x1) * (py - y1) - (y2 - y1) * (px - x1)
            if abs(cross) <= tolerance:
                continue
            currentSign = 1 if cross > 0 else -1
            if sign and currentSign != sign:
                return False
            sign = currentSign
        return True

    def detectBlockFace(self, mouseX: int, mouseY: int, x: int, y: int, z: int) -> Optional[str]:
        """Pick a visible face using the same scaled geometry as rendering."""
        polygons = self.getBlockFacePolygons(x, y, z)
        tolerance = 0 if self.zoomLevel < 0.2 else max(1, int(self.zoomLevel * 2))
        # Top wins shared edges, matching the visible top surface.
        for face in ("top", "left", "right"):
            if self._pointInConvexPolygon((mouseX, mouseY), polygons[face], tolerance):
                return face
        return None
