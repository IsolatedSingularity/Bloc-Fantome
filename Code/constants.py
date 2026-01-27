"""
Constants Module for Bloc Fantôme

This module centralizes all constant values, enums, and block definitions
used throughout the application. Import from here for consistent access.

Usage:
    from constants import (
        WINDOW_WIDTH, WINDOW_HEIGHT, PANEL_WIDTH,
        BlockType, BlockDefinition, BLOCK_DEFINITIONS,
        DIMENSION_OVERWORLD, DIMENSION_NETHER, DIMENSION_END
    )
"""

import os
import sys
import math
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

# ============================================================================
# WINDOW AND DISPLAY
# ============================================================================

WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800
TITLE = "Bloc Fantome"

# Panel settings
PANEL_WIDTH = 260
ICON_SIZE = 72
ICON_MARGIN = 10
ICONS_PER_ROW = 3

# Background tile size
BG_TILE_SIZE = 64

# ============================================================================
# GRID SETTINGS
# ============================================================================

GRID_WIDTH = 12
GRID_DEPTH = 12
GRID_HEIGHT = 12

# ============================================================================
# ISOMETRIC PROJECTION
# ============================================================================

TILE_WIDTH = 64
TILE_HEIGHT = 32
BLOCK_HEIGHT = 38  # Slightly taller for better visual appearance

# ============================================================================
# TIMING CONSTANTS
# ============================================================================

# Splash screen (frames at 60 FPS)
SPLASH_DISPLAY_FRAMES = 90
SPLASH_FADE_FRAMES = 60
SPLASH_ICON_SIZE = 256

# Sound settings
SOUND_VOLUME_DEFAULT = 0.6
SOUND_VOLUME_AMBIENT = 0.5
SOUND_VOLUME_UI = 0.4
SOUND_VOLUME_DOOR = 0.7
SOUND_MAX_VARIANTS = 10

# Animation settings (milliseconds)
PORTAL_FRAME_DELAY = 50
FIRE_FRAME_DELAY = 80
CHEST_FRAME_DELAY = 40
OXIDATION_INTERVAL = 10000

# Weather settings
RAIN_DROP_COUNT_BASE = 150
RAIN_INTENSITY_MIN = 0.5
RAIN_INTENSITY_MAX = 1.5
THUNDER_MIN_DELAY = 8000
THUNDER_MAX_DELAY = 25000

# Liquid flow (milliseconds)
WATER_FLOW_DELAY = 400
LAVA_FLOW_DELAY = 2400

# ============================================================================
# COLORS
# ============================================================================

BG_COLOR = (30, 30, 35)
GRID_COLOR = (60, 60, 70)
PANEL_COLOR = (40, 40, 50)
PANEL_BORDER = (80, 80, 100)
TEXT_COLOR = (220, 220, 220)
HIGHLIGHT_COLOR = (100, 200, 100)
SELECTED_COLOR = (255, 215, 0)

# Tint colors
GRASS_TINT = (124, 189, 107)
LEAVES_TINT = (106, 173, 90)
WATER_TINT = (63, 118, 228)
LAVA_TINT = (207, 92, 15)

# ============================================================================
# DIMENSIONS
# ============================================================================

DIMENSION_OVERWORLD = "overworld"
DIMENSION_NETHER = "nether"
DIMENSION_END = "end"

# ============================================================================
# PATHS
# ============================================================================

def _get_base_dir() -> str:
    """Get the base directory for assets."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = _get_base_dir()

if getattr(sys, 'frozen', False):
    ASSETS_DIR = os.path.join(BASE_DIR, "Assets")
else:
    ASSETS_DIR = os.path.join(BASE_DIR, "..", "Assets")

TEXTURES_DIR = os.path.join(ASSETS_DIR, "Texture Hub", "blocks")
ENTITY_DIR = os.path.join(ASSETS_DIR, "Texture Hub", "entity")
ITEMS_DIR = os.path.join(ASSETS_DIR, "Texture Hub", "items")
GUI_DIR = os.path.join(ASSETS_DIR, "Texture Hub", "gui")
COLORMAP_DIR = os.path.join(ASSETS_DIR, "Texture Hub", "colormap")
SOUNDS_DIR = os.path.join(ASSETS_DIR, "Sound Hub")
MUSIC_DIR = os.path.join(SOUNDS_DIR, "music", "menu")
MUSIC_DIR_NETHER = os.path.join(SOUNDS_DIR, "music", "game", "nether")
MUSIC_DIR_END = os.path.join(SOUNDS_DIR, "music", "game", "end")
ICONS_DIR = os.path.join(ASSETS_DIR, "Icons")
FONTS_DIR = os.path.join(ASSETS_DIR, "Fonts")
SAVES_DIR = os.path.join(BASE_DIR, "saves")
CUSTOM_MUSIC_DIR = os.path.join(SAVES_DIR, "custom_music")
APP_CONFIG_FILE = os.path.join(BASE_DIR, ".app_config.json")

# ============================================================================
# ENUMS
# ============================================================================

class Facing(Enum):
    """Cardinal directions for block facing"""
    NORTH = 0  # -Y direction
    EAST = 1   # +X direction
    SOUTH = 2  # +Y direction
    WEST = 3   # -X direction


class SlabPosition(Enum):
    """Position of slab within block space"""
    BOTTOM = 0
    TOP = 1


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class BlockDefinition:
    """Definition for a block type including texture names"""
    name: str
    textureTop: str
    textureSide: str
    textureBottom: str
    tintTop: bool = False
    tintSide: bool = False
    textureFront: str = None
    transparent: bool = False
    isThin: bool = False
    isDoor: bool = False
    isLiquid: bool = False
    isStair: bool = False
    isSlab: bool = False
    isPortal: bool = False
    lightLevel: int = 0
    lightColor: Tuple[int, int, int] = (255, 200, 150)


@dataclass
class BlockProperties:
    """Properties for special blocks (doors, slabs, stairs)"""
    facing: Facing = Facing.SOUTH
    isOpen: bool = False
    slabPosition: SlabPosition = SlabPosition.BOTTOM
    
    def copy(self) -> 'BlockProperties':
        return BlockProperties(
            facing=self.facing,
            isOpen=self.isOpen,
            slabPosition=self.slabPosition
        )


@dataclass
class SoundDefinition:
    """Definition for block sounds"""
    placeSound: str
    breakSound: str


# ============================================================================
# BLOCK TYPE ENUM
# Note: Full definition is in minecraftBuilder.py for now
# This is a forward reference for imports
# ============================================================================

# BlockType enum is defined in minecraftBuilder.py due to its size (~250 values)
# Import it from there:
# from minecraftBuilder import BlockType, BLOCK_DEFINITIONS, BLOCK_SOUNDS

# ============================================================================
# 3D RENDERER UTILITIES
# ============================================================================

class Renderer3D:
    """
    3D box renderer with fixed isometric camera.
    Provides consistent projection for all block shapes.
    """
    
    # Isometric angles (2:1 dimetric)
    ANGLE_X = math.atan(0.5)  # ~26.57 degrees
    ANGLE_Y = math.pi / 4     # 45 degrees
    
    # Pre-computed rotation components
    COS_X = math.cos(ANGLE_X)
    SIN_X = math.sin(ANGLE_X)
    COS_Y = math.cos(ANGLE_Y)
    SIN_Y = math.sin(ANGLE_Y)
    
    # Scale
    SCALE = TILE_WIDTH / 16
    
    @classmethod
    def project(cls, x: float, y: float, z: float) -> Tuple[float, float]:
        """Project 3D point to 2D screen coordinates."""
        # Y rotation
        rx = x * cls.COS_Y - z * cls.SIN_Y
        rz = x * cls.SIN_Y + z * cls.COS_Y
        ry = y
        
        # X rotation
        fy = ry * cls.COS_X - rz * cls.SIN_X
        
        # Project
        screenX = rx * cls.SCALE
        screenY = -fy * cls.SCALE
        
        return screenX, screenY


# ============================================================================
# CATEGORY DEFINITIONS (for panel organization)
# ============================================================================

# Block category order and visibility
BLOCK_CATEGORIES = [
    "Natural",
    "Wood",
    "Stone",
    "Ores",
    "Nether",
    "End",
    "Decorative",
    "Glass",
    "Concrete",
    "Terracotta",
    "Wool",
    "Redstone",
    "Light",
    "Interactive",
    "Liquid",
    "Special"
]

# Default collapsed state for categories
DEFAULT_COLLAPSED = {
    "Natural": False,
    "Wood": False,
    "Stone": True,
    "Ores": True,
    "Nether": True,
    "End": True,
    "Decorative": True,
    "Glass": True,
    "Concrete": True,
    "Terracotta": True,
    "Wool": True,
    "Redstone": True,
    "Light": True,
    "Interactive": True,
    "Liquid": True,
    "Special": True
}
