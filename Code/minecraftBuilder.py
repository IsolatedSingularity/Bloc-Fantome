"""
Bite Sized Minecraft

This module implements an interactive Minecraft-style building simulator using Pygame with
isometric 2.5D rendering. Users can drag and drop blocks from a TMI-style inventory panel
onto a grid-based building area, load premade structures, and hear authentic placement sounds.

The simulator features a 12x12x8 building grid with 2:1 dimetric projection for pixel-perfect
isometric rendering, supporting block placement, removal, and structure loading.

Author: Jeffrey Morais
"""

import pygame
import os
import sys
import math
import json
import urllib.request
import zipfile
import shutil
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum
import random

# Windows-specific: Set AppUserModelID for proper taskbar icon
if sys.platform == 'win32':
    try:
        import ctypes
        myappid = 'bitesizedminecraft.builder.1.0'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass

# Initialize pygame
pygame.init()
pygame.mixer.init()

# ============================================================================
# CONSTANTS AND CONFIGURATION
# ============================================================================

# Window settings
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800
TITLE = "Bite Sized Minecraft"

# Grid settings
GRID_WIDTH = 12
GRID_DEPTH = 12
GRID_HEIGHT = 8

# Isometric projection settings (2:1 dimetric)
# Higher resolution tiles for crisp textures
# Mathematically correct 2:1 would have BLOCK_HEIGHT = TILE_HEIGHT
# But visually, slightly taller sides look more "cube-like" to human perception
TILE_WIDTH = 64
TILE_HEIGHT = 32
BLOCK_HEIGHT = 38  # Slightly taller than mathematical 32 for better visual cube appearance


# ============================================================================
# 3D RENDERER - Consistent projection for ALL block shapes
# ============================================================================

class Renderer3D:
    """
    A proper 3D box renderer with fixed isometric camera.
    All blocks (regular, doors, stairs, slabs) use this same projection.
    No more special-case isometric math!
    """
    
    # Isometric angles (classic 2:1 dimetric)
    ANGLE_X = math.atan(0.5)  # ~26.57 degrees - pitch
    ANGLE_Y = math.pi / 4     # 45 degrees - yaw
    
    # Pre-compute rotation matrix components
    COS_X = math.cos(ANGLE_X)
    SIN_X = math.sin(ANGLE_X)
    COS_Y = math.cos(ANGLE_Y)
    SIN_Y = math.sin(ANGLE_Y)
    
    # Scale factors
    SCALE = TILE_WIDTH / 16  # 4 pixels per voxel unit
    
    @classmethod
    def project(cls, x: float, y: float, z: float) -> Tuple[float, float]:
        """
        Project a 3D point to 2D screen coordinates.
        Input: x (right), y (up), z (toward viewer) in voxel units (0-16)
        Output: screen x, y
        """
        # Apply Y rotation (around vertical axis)
        rx = x * cls.COS_Y - z * cls.SIN_Y
        rz = x * cls.SIN_Y + z * cls.COS_Y
        ry = y
        
        # Apply X rotation (tilt down)
        fy = ry * cls.COS_X - rz * cls.SIN_X
        fz = ry * cls.SIN_X + rz * cls.COS_X
        
        # Project to 2D (orthographic)
        screenX = rx * cls.SCALE
        screenY = -fy * cls.SCALE  # Flip Y for screen coords
        
        return screenX, screenY
    
    @classmethod
    def renderBox(cls, surface: pygame.Surface, 
                  x: float, y: float, z: float,
                  w: float, h: float, d: float,
                  topTex: pygame.Surface = None,
                  sideTex: pygame.Surface = None,
                  frontTex: pygame.Surface = None,
                  centerX: int = None, centerY: int = None) -> None:
        """
        Render a 3D box onto a surface.
        
        Box defined in voxel coordinates (0-16 range like Minecraft):
        - x, y, z: corner position (bottom-back-left)
        - w: width (X axis)
        - h: height (Y axis)  
        - d: depth (Z axis)
        
        centerX/Y: screen position to center the rendering
        """
        if centerX is None:
            centerX = surface.get_width() // 2
        if centerY is None:
            centerY = surface.get_height() // 2
        
        # Define 8 corners of the box
        corners = [
            (x, y, z),          # 0: bottom-back-left
            (x+w, y, z),        # 1: bottom-back-right
            (x+w, y, z+d),      # 2: bottom-front-right
            (x, y, z+d),        # 3: bottom-front-left
            (x, y+h, z),        # 4: top-back-left
            (x+w, y+h, z),      # 5: top-back-right
            (x+w, y+h, z+d),    # 6: top-front-right
            (x, y+h, z+d),      # 7: top-front-left
        ]
        
        # Project all corners to 2D
        projected = []
        for cx, cy, cz in corners:
            px, py = cls.project(cx - 8, cy - 8, cz - 8)  # Center around origin
            projected.append((int(centerX + px), int(centerY + py)))
        
        # Define visible faces (top, left/back, right/front)
        # Each face: list of corner indices, texture, brightness
        faces = [
            # Top face (indices 4,5,6,7)
            ([4, 5, 6, 7], topTex, 1.0),
            # Left face (indices 0,3,7,4) - darker
            ([0, 3, 7, 4], sideTex, 0.7),
            # Right face (indices 1,2,6,5) - medium  
            ([3, 2, 6, 7], frontTex if frontTex else sideTex, 0.85),
        ]
        
        for indices, tex, brightness in faces:
            pts = [projected[i] for i in indices]
            
            # Get average color from texture for base fill
            if tex:
                avgColor = cls._getAverageColor(tex)
                shadedColor = (int(avgColor[0] * brightness),
                              int(avgColor[1] * brightness),
                              int(avgColor[2] * brightness))
            else:
                shadedColor = (int(128 * brightness), int(128 * brightness), int(128 * brightness))
            
            # Fill polygon with base color
            pygame.draw.polygon(surface, shadedColor, pts)
            
            # Apply texture mapping
            if tex:
                cls._textureQuad(surface, pts, tex, brightness)
    
    @classmethod
    def _getAverageColor(cls, texture: pygame.Surface) -> Tuple[int, int, int]:
        """Get average color from texture"""
        try:
            scaled = pygame.transform.scale(texture, (1, 1))
            return scaled.get_at((0, 0))[:3]
        except:
            return (128, 128, 128)
    
    @classmethod
    def _textureQuad(cls, surface: pygame.Surface, pts: List[Tuple[int, int]], 
                     tex: pygame.Surface, brightness: float) -> None:
        """
        Apply texture to a quadrilateral using scanline rendering.
        pts: 4 corner points in order (e.g., top-left, top-right, bottom-right, bottom-left)
        """
        # Scale texture to 16x16
        tex = pygame.transform.scale(tex, (16, 16))
        
        # Find bounding box
        minX = min(p[0] for p in pts)
        maxX = max(p[0] for p in pts)
        minY = min(p[1] for p in pts)
        maxY = max(p[1] for p in pts)
        
        # For each pixel in bounding box, check if inside quad and map texture
        for py in range(minY, maxY + 1):
            for px in range(minX, maxX + 1):
                # Check if point is inside quad using cross product method
                if cls._pointInQuad(px, py, pts):
                    # Calculate UV coordinates using bilinear interpolation
                    u, v = cls._getUV(px, py, pts)
                    texX = max(0, min(15, int(u * 15)))
                    texY = max(0, min(15, int(v * 15)))
                    
                    try:
                        color = tex.get_at((texX, texY))
                        if color.a > 0:
                            r = int(color.r * brightness)
                            g = int(color.g * brightness)
                            b = int(color.b * brightness)
                            surface.set_at((px, py), (r, g, b, 255))
                    except:
                        pass
    
    @classmethod
    def _pointInQuad(cls, x: int, y: int, pts: List[Tuple[int, int]]) -> bool:
        """Check if point is inside quadrilateral using cross products"""
        def cross(o, a, b):
            return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
        
        # Check all edges have consistent winding
        n = len(pts)
        sign = None
        for i in range(n):
            c = cross(pts[i], pts[(i+1) % n], (x, y))
            if c != 0:
                if sign is None:
                    sign = c > 0
                elif (c > 0) != sign:
                    return False
        return True
    
    @classmethod
    def _getUV(cls, px: int, py: int, pts: List[Tuple[int, int]]) -> Tuple[float, float]:
        """
        Calculate UV coordinates for a point inside a quad.
        Uses inverse bilinear interpolation.
        """
        # Simplified UV mapping based on position within bounding box
        # For more accuracy, could use proper inverse bilinear
        minX = min(p[0] for p in pts)
        maxX = max(p[0] for p in pts)
        minY = min(p[1] for p in pts)
        maxY = max(p[1] for p in pts)
        
        # Use position relative to quad center and extents
        if maxX > minX:
            u = (px - minX) / (maxX - minX)
        else:
            u = 0.5
        if maxY > minY:
            v = (py - minY) / (maxY - minY)
        else:
            v = 0.5
        
        return max(0, min(1, u)), max(0, min(1, v))

# Colors (dark theme)
BG_COLOR = (30, 30, 35)
GRID_COLOR = (60, 60, 70)
PANEL_COLOR = (40, 40, 50)
PANEL_BORDER = (80, 80, 100)
TEXT_COLOR = (220, 220, 220)
HIGHLIGHT_COLOR = (100, 200, 100)
SELECTED_COLOR = (255, 215, 0)

# Panel settings
PANEL_WIDTH = 260
ICON_SIZE = 72  # Higher resolution icons for clarity
ICON_MARGIN = 10
ICONS_PER_ROW = 3

# Background tile size (larger for less busy look)
BG_TILE_SIZE = 64

# Asset paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
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

# Dimension constants
DIMENSION_OVERWORLD = "overworld"
DIMENSION_NETHER = "nether"
DIMENSION_END = "end"

# Grass tint color (plains biome - sampled from colormap)
GRASS_TINT = (124, 189, 107)
LEAVES_TINT = (106, 173, 90)  # Slightly different for leaves
WATER_TINT = (63, 118, 228)  # Blue water tint
LAVA_TINT = (207, 92, 15)  # Orange-red lava tint


# ============================================================================
# BLOCK DEFINITIONS
# ============================================================================

class BlockType(Enum):
    """Enumeration of available block types"""
    AIR = 0
    # Natural blocks
    GRASS = 1
    DIRT = 2
    STONE = 3
    COBBLESTONE = 4
    GRAVEL = 5
    SAND = 6
    CLAY = 7
    # Wood types
    OAK_LOG = 10
    OAK_PLANKS = 11
    OAK_LEAVES = 12
    BIRCH_LOG = 13
    BIRCH_PLANKS = 14
    BIRCH_LEAVES = 15
    SPRUCE_LOG = 16
    SPRUCE_PLANKS = 17
    SPRUCE_LEAVES = 18
    DARK_OAK_LOG = 19
    DARK_OAK_PLANKS = 20
    DARK_OAK_LEAVES = 21
    # Ores and minerals
    COAL_ORE = 30
    IRON_ORE = 31
    GOLD_ORE = 32
    DIAMOND_ORE = 33
    COAL_BLOCK = 34
    IRON_BLOCK = 35
    GOLD_BLOCK = 36
    DIAMOND_BLOCK = 37
    # Building blocks
    BRICKS = 40
    STONE_BRICKS = 41
    MOSSY_STONE_BRICKS = 42
    MOSSY_COBBLESTONE = 43
    SANDSTONE = 44
    RED_SANDSTONE = 45
    # Decorative
    GLASS = 50
    BOOKSHELF = 51
    GLOWSTONE = 52
    # Wool colors
    WHITE_WOOL = 60
    RED_WOOL = 61
    BLUE_WOOL = 62
    GREEN_WOOL = 63
    YELLOW_WOOL = 64
    BLACK_WOOL = 65
    # Concrete
    WHITE_CONCRETE = 70
    RED_CONCRETE = 71
    BLUE_CONCRETE = 72
    # Special
    CRAFTING_TABLE = 80
    FURNACE = 81
    TNT = 82
    BEDROCK = 83
    # Doors (thin blocks)
    OAK_DOOR = 90
    IRON_DOOR = 91
    # Liquids
    WATER = 95
    LAVA = 96
    # Stairs (actual stair shape)
    OAK_STAIRS = 100
    COBBLESTONE_STAIRS = 101
    STONE_BRICK_STAIRS = 102
    # Slabs (half blocks)
    OAK_SLAB = 110
    COBBLESTONE_SLAB = 111
    STONE_BRICK_SLAB = 112
    STONE_SLAB = 113
    # Nether/End blocks
    OBSIDIAN = 120
    END_PORTAL_FRAME = 121
    END_STONE = 122
    END_STONE_BRICKS = 123
    NETHER_PORTAL = 124  # Animated portal block
    NETHER_BRICKS = 125
    NETHERRACK = 126
    SOUL_SAND = 127
    GLOWSTONE_BLOCK = 128  # Alias for glowstone in nether structures
    # Plants and Nature
    CACTUS = 130
    PUMPKIN = 131
    JACK_O_LANTERN = 132
    HAY_BLOCK = 133
    MELON = 134
    # Cold blocks
    SNOW = 140
    ICE = 141
    PACKED_ICE = 142
    # Copper blocks (all stages of oxidation)
    COPPER_BLOCK = 150
    EXPOSED_COPPER = 151
    WEATHERED_COPPER = 152
    OXIDIZED_COPPER = 153
    CUT_COPPER = 154
    EXPOSED_CUT_COPPER = 155
    WEATHERED_CUT_COPPER = 156
    OXIDIZED_CUT_COPPER = 157
    # Regular new blocks
    CHEST = 160
    ENDER_CHEST = 161
    BONE_BLOCK = 162
    SCULK = 163  # Sculk block
    # Chest variants (entity textures)
    TRAPPED_CHEST = 165
    CHRISTMAS_CHEST = 166
    COPPER_CHEST = 167
    COPPER_CHEST_EXPOSED = 168
    COPPER_CHEST_WEATHERED = 169
    COPPER_CHEST_OXIDIZED = 170
    # Problematic/Special blocks (animated or complex)
    OXIDIZING_COPPER = 200  # Auto-oxidizes over time
    ENCHANTING_TABLE = 201
    MOB_SPAWNER = 202  # Normal spawner with cage texture
    TRIAL_SPAWNER = 203  # Trial chamber spawner
    SCULK_SENSOR = 204
    END_PORTAL = 205  # Animated starfield
    END_GATEWAY = 206  # Animated starfield
    FIRE = 207  # Animated fire
    SOUL_FIRE = 208  # Animated soul fire


@dataclass
class BlockDefinition:
    """Definition for a block type including texture names"""
    name: str
    textureTop: str
    textureSide: str
    textureBottom: str
    tintTop: bool = False  # Whether to apply grass tint to top
    tintSide: bool = False  # Whether to apply grass/leaf tint to sides
    textureFront: str = None  # Optional front texture (for furnace, etc.)
    transparent: bool = False  # Whether block is transparent (glass)
    isThin: bool = False  # Whether block is a thin block (door)
    isDoor: bool = False  # Whether block is a door (can open/close)
    isLiquid: bool = False  # Whether block is a liquid (water/lava)
    isStair: bool = False  # Whether block is a stair
    isSlab: bool = False  # Whether block is a half-height slab
    isPortal: bool = False  # Whether block is an animated portal


class Facing(Enum):
    """Cardinal directions for block facing"""
    NORTH = 0  # -Y direction (towards top-left in isometric)
    EAST = 1   # +X direction (towards top-right in isometric)
    SOUTH = 2  # +Y direction (towards bottom-right in isometric)
    WEST = 3   # -X direction (towards bottom-left in isometric)


class SlabPosition(Enum):
    """Position of slab within block space"""
    BOTTOM = 0
    TOP = 1


@dataclass
class BlockProperties:
    """
    Properties for special blocks that need additional state.
    Used for doors (open/closed, hinge), slabs (top/bottom), stairs (facing).
    """
    facing: Facing = Facing.SOUTH  # Direction the block faces
    isOpen: bool = False  # For doors: whether door is open
    slabPosition: SlabPosition = SlabPosition.BOTTOM  # For slabs: top or bottom half
    
    def copy(self) -> 'BlockProperties':
        """Create a copy of this properties object"""
        return BlockProperties(
            facing=self.facing,
            isOpen=self.isOpen,
            slabPosition=self.slabPosition
        )
    
    
@dataclass
class SoundDefinition:
    """Definition for block sounds"""
    placeSound: str  # Sound category for placement
    breakSound: str  # Sound category for breaking


# Block definitions with texture file names
BLOCK_DEFINITIONS: Dict[BlockType, BlockDefinition] = {
    # Natural blocks
    BlockType.GRASS: BlockDefinition("Grass", "grass_block_top.png", "grass_block_side.png", "dirt.png", tintTop=True),
    BlockType.DIRT: BlockDefinition("Dirt", "dirt.png", "dirt.png", "dirt.png"),
    BlockType.STONE: BlockDefinition("Stone", "stone.png", "stone.png", "stone.png"),
    BlockType.COBBLESTONE: BlockDefinition("Cobblestone", "cobblestone.png", "cobblestone.png", "cobblestone.png"),
    BlockType.GRAVEL: BlockDefinition("Gravel", "gravel.png", "gravel.png", "gravel.png"),
    BlockType.SAND: BlockDefinition("Sand", "sand.png", "sand.png", "sand.png"),
    BlockType.CLAY: BlockDefinition("Clay", "clay.png", "clay.png", "clay.png"),
    # Wood - Oak
    BlockType.OAK_LOG: BlockDefinition("Oak Log", "oak_log_top.png", "oak_log.png", "oak_log_top.png"),
    BlockType.OAK_PLANKS: BlockDefinition("Oak Planks", "oak_planks.png", "oak_planks.png", "oak_planks.png"),
    BlockType.OAK_LEAVES: BlockDefinition("Oak Leaves", "oak_leaves.png", "oak_leaves.png", "oak_leaves.png", transparent=True, tintTop=True, tintSide=True),
    # Wood - Birch
    BlockType.BIRCH_LOG: BlockDefinition("Birch Log", "birch_log_top.png", "birch_log.png", "birch_log_top.png"),
    BlockType.BIRCH_PLANKS: BlockDefinition("Birch Planks", "birch_planks.png", "birch_planks.png", "birch_planks.png"),
    BlockType.BIRCH_LEAVES: BlockDefinition("Birch Leaves", "birch_leaves.png", "birch_leaves.png", "birch_leaves.png", transparent=True, tintTop=True, tintSide=True),
    # Wood - Spruce
    BlockType.SPRUCE_LOG: BlockDefinition("Spruce Log", "spruce_log_top.png", "spruce_log.png", "spruce_log_top.png"),
    BlockType.SPRUCE_PLANKS: BlockDefinition("Spruce Planks", "spruce_planks.png", "spruce_planks.png", "spruce_planks.png"),
    BlockType.SPRUCE_LEAVES: BlockDefinition("Spruce Leaves", "spruce_leaves.png", "spruce_leaves.png", "spruce_leaves.png", transparent=True),
    # Wood - Dark Oak
    BlockType.DARK_OAK_LOG: BlockDefinition("Dark Oak Log", "dark_oak_log_top.png", "dark_oak_log.png", "dark_oak_log_top.png"),
    BlockType.DARK_OAK_PLANKS: BlockDefinition("Dark Oak Planks", "dark_oak_planks.png", "dark_oak_planks.png", "dark_oak_planks.png"),
    BlockType.DARK_OAK_LEAVES: BlockDefinition("Dark Oak Leaves", "dark_oak_leaves.png", "dark_oak_leaves.png", "dark_oak_leaves.png", transparent=True, tintTop=True, tintSide=True),
    # Ores
    BlockType.COAL_ORE: BlockDefinition("Coal Ore", "coal_ore.png", "coal_ore.png", "coal_ore.png"),
    BlockType.IRON_ORE: BlockDefinition("Iron Ore", "iron_ore.png", "iron_ore.png", "iron_ore.png"),
    BlockType.GOLD_ORE: BlockDefinition("Gold Ore", "gold_ore.png", "gold_ore.png", "gold_ore.png"),
    BlockType.DIAMOND_ORE: BlockDefinition("Diamond Ore", "diamond_ore.png", "diamond_ore.png", "diamond_ore.png"),
    # Mineral blocks
    BlockType.COAL_BLOCK: BlockDefinition("Coal Block", "coal_block.png", "coal_block.png", "coal_block.png"),
    BlockType.IRON_BLOCK: BlockDefinition("Iron Block", "iron_block.png", "iron_block.png", "iron_block.png"),
    BlockType.GOLD_BLOCK: BlockDefinition("Gold Block", "gold_block.png", "gold_block.png", "gold_block.png"),
    BlockType.DIAMOND_BLOCK: BlockDefinition("Diamond Block", "diamond_block.png", "diamond_block.png", "diamond_block.png"),
    # Building blocks
    BlockType.BRICKS: BlockDefinition("Bricks", "bricks.png", "bricks.png", "bricks.png"),
    BlockType.STONE_BRICKS: BlockDefinition("Stone Bricks", "stone_bricks.png", "stone_bricks.png", "stone_bricks.png"),
    BlockType.MOSSY_STONE_BRICKS: BlockDefinition("Mossy Stone Bricks", "mossy_stone_bricks.png", "mossy_stone_bricks.png", "mossy_stone_bricks.png"),
    BlockType.MOSSY_COBBLESTONE: BlockDefinition("Mossy Cobblestone", "mossy_cobblestone.png", "mossy_cobblestone.png", "mossy_cobblestone.png"),
    BlockType.SANDSTONE: BlockDefinition("Sandstone", "sandstone_top.png", "sandstone.png", "sandstone_bottom.png"),
    BlockType.RED_SANDSTONE: BlockDefinition("Red Sandstone", "red_sandstone_top.png", "red_sandstone.png", "red_sandstone_bottom.png"),
    # Decorative
    BlockType.GLASS: BlockDefinition("Glass", "glass.png", "glass.png", "glass.png", transparent=True),
    BlockType.BOOKSHELF: BlockDefinition("Bookshelf", "oak_planks.png", "bookshelf.png", "oak_planks.png"),
    BlockType.GLOWSTONE: BlockDefinition("Glowstone", "glowstone.png", "glowstone.png", "glowstone.png"),
    # Wool
    BlockType.WHITE_WOOL: BlockDefinition("White Wool", "white_wool.png", "white_wool.png", "white_wool.png"),
    BlockType.RED_WOOL: BlockDefinition("Red Wool", "red_wool.png", "red_wool.png", "red_wool.png"),
    BlockType.BLUE_WOOL: BlockDefinition("Blue Wool", "blue_wool.png", "blue_wool.png", "blue_wool.png"),
    BlockType.GREEN_WOOL: BlockDefinition("Green Wool", "green_wool.png", "green_wool.png", "green_wool.png"),
    BlockType.YELLOW_WOOL: BlockDefinition("Yellow Wool", "yellow_wool.png", "yellow_wool.png", "yellow_wool.png"),
    BlockType.BLACK_WOOL: BlockDefinition("Black Wool", "black_wool.png", "black_wool.png", "black_wool.png"),
    # Concrete
    BlockType.WHITE_CONCRETE: BlockDefinition("White Concrete", "white_concrete.png", "white_concrete.png", "white_concrete.png"),
    BlockType.RED_CONCRETE: BlockDefinition("Red Concrete", "red_concrete.png", "red_concrete.png", "red_concrete.png"),
    BlockType.BLUE_CONCRETE: BlockDefinition("Blue Concrete", "blue_concrete.png", "blue_concrete.png", "blue_concrete.png"),
    # Special
    BlockType.CRAFTING_TABLE: BlockDefinition("Crafting Table", "crafting_table_top.png", "crafting_table_side.png", "oak_planks.png", textureFront="crafting_table_front.png"),
    BlockType.FURNACE: BlockDefinition("Furnace", "furnace_top.png", "furnace_side.png", "furnace_side.png", textureFront="furnace_front.png"),
    BlockType.TNT: BlockDefinition("TNT", "tnt_top.png", "tnt_side.png", "tnt_bottom.png"),
    BlockType.BEDROCK: BlockDefinition("Bedrock", "bedrock.png", "bedrock.png", "bedrock.png"),
    # Doors (rendered as thin 2-high blocks) - use door textures
    BlockType.OAK_DOOR: BlockDefinition("Oak Door", "oak_door_top.png", "oak_door_bottom.png", "oak_door_bottom.png", textureFront="oak_door_bottom.png", isThin=True, isDoor=True),
    BlockType.IRON_DOOR: BlockDefinition("Iron Door", "iron_door_top.png", "iron_door_bottom.png", "iron_door_bottom.png", textureFront="iron_door_bottom.png", isThin=True, isDoor=True),
    # Liquids - use flow textures for better appearance
    BlockType.WATER: BlockDefinition("Water", "water_flow.png", "water_flow.png", "water_flow.png", transparent=True, isLiquid=True),
    BlockType.LAVA: BlockDefinition("Lava", "lava_flow.png", "lava_flow.png", "lava_flow.png", isLiquid=True),
    # Stairs (actual stair shape with two steps)
    BlockType.OAK_STAIRS: BlockDefinition("Oak Stairs", "oak_planks.png", "oak_planks.png", "oak_planks.png", isStair=True),
    BlockType.COBBLESTONE_STAIRS: BlockDefinition("Cobble Stairs", "cobblestone.png", "cobblestone.png", "cobblestone.png", isStair=True),
    BlockType.STONE_BRICK_STAIRS: BlockDefinition("Stone Brick Stairs", "stone_bricks.png", "stone_bricks.png", "stone_bricks.png", isStair=True),
    # Slabs (half-height blocks)
    BlockType.OAK_SLAB: BlockDefinition("Oak Slab", "oak_planks.png", "oak_planks.png", "oak_planks.png", isSlab=True),
    BlockType.COBBLESTONE_SLAB: BlockDefinition("Cobble Slab", "cobblestone.png", "cobblestone.png", "cobblestone.png", isSlab=True),
    BlockType.STONE_BRICK_SLAB: BlockDefinition("Stone Brick Slab", "stone_bricks.png", "stone_bricks.png", "stone_bricks.png", isSlab=True),
    BlockType.STONE_SLAB: BlockDefinition("Stone Slab", "smooth_stone_slab_side.png", "smooth_stone_slab_side.png", "smooth_stone_slab_side.png", isSlab=True),
    # Nether/End blocks
    BlockType.OBSIDIAN: BlockDefinition("Obsidian", "obsidian.png", "obsidian.png", "obsidian.png"),
    BlockType.END_PORTAL_FRAME: BlockDefinition("End Portal Frame", "end_portal_frame_top.png", "end_portal_frame_side.png", "end_stone.png"),
    BlockType.END_STONE: BlockDefinition("End Stone", "end_stone.png", "end_stone.png", "end_stone.png"),
    BlockType.END_STONE_BRICKS: BlockDefinition("End Stone Bricks", "end_stone_bricks.png", "end_stone_bricks.png", "end_stone_bricks.png"),
    BlockType.NETHER_PORTAL: BlockDefinition("Nether Portal", "nether_portal.png", "nether_portal.png", "nether_portal.png", transparent=True, isPortal=True),
    BlockType.NETHER_BRICKS: BlockDefinition("Nether Bricks", "nether_bricks.png", "nether_bricks.png", "nether_bricks.png"),
    BlockType.NETHERRACK: BlockDefinition("Netherrack", "netherrack.png", "netherrack.png", "netherrack.png"),
    BlockType.SOUL_SAND: BlockDefinition("Soul Sand", "soul_sand.png", "soul_sand.png", "soul_sand.png"),
    # Plants
    BlockType.CACTUS: BlockDefinition("Cactus", "cactus_top.png", "cactus_side.png", "cactus_bottom.png"),
    BlockType.PUMPKIN: BlockDefinition("Pumpkin", "pumpkin_top.png", "pumpkin_side.png", "pumpkin_top.png"),
    BlockType.JACK_O_LANTERN: BlockDefinition("Jack o'Lantern", "pumpkin_top.png", "pumpkin_side.png", "pumpkin_top.png", textureFront="jack_o_lantern.png"),
    BlockType.HAY_BLOCK: BlockDefinition("Hay Block", "hay_block_top.png", "hay_block_side.png", "hay_block_top.png"),
    BlockType.MELON: BlockDefinition("Melon", "melon_top.png", "melon_side.png", "melon_top.png"),
    # Cold blocks
    BlockType.SNOW: BlockDefinition("Snow Block", "snow.png", "snow.png", "snow.png"),
    BlockType.ICE: BlockDefinition("Ice", "ice.png", "ice.png", "ice.png", transparent=True),
    BlockType.PACKED_ICE: BlockDefinition("Packed Ice", "packed_ice.png", "packed_ice.png", "packed_ice.png"),
    # Copper blocks (all stages)
    BlockType.COPPER_BLOCK: BlockDefinition("Copper Block", "copper_block.png", "copper_block.png", "copper_block.png"),
    BlockType.EXPOSED_COPPER: BlockDefinition("Exposed Copper", "exposed_copper.png", "exposed_copper.png", "exposed_copper.png"),
    BlockType.WEATHERED_COPPER: BlockDefinition("Weathered Copper", "weathered_copper.png", "weathered_copper.png", "weathered_copper.png"),
    BlockType.OXIDIZED_COPPER: BlockDefinition("Oxidized Copper", "oxidized_copper.png", "oxidized_copper.png", "oxidized_copper.png"),
    BlockType.CUT_COPPER: BlockDefinition("Cut Copper", "cut_copper.png", "cut_copper.png", "cut_copper.png"),
    BlockType.EXPOSED_CUT_COPPER: BlockDefinition("Exposed Cut Copper", "exposed_cut_copper.png", "exposed_cut_copper.png", "exposed_cut_copper.png"),
    BlockType.WEATHERED_CUT_COPPER: BlockDefinition("Weathered Cut Copper", "weathered_cut_copper.png", "weathered_cut_copper.png", "weathered_cut_copper.png"),
    BlockType.OXIDIZED_CUT_COPPER: BlockDefinition("Oxidized Cut Copper", "oxidized_cut_copper.png", "oxidized_cut_copper.png", "oxidized_cut_copper.png"),
    # Regular new blocks - Chests will use custom rendering from entity textures
    BlockType.CHEST: BlockDefinition("Chest", "oak_planks.png", "oak_planks.png", "oak_planks.png"),  # Custom chest render
    BlockType.ENDER_CHEST: BlockDefinition("Ender Chest", "obsidian.png", "obsidian.png", "obsidian.png"),  # Custom chest render
    BlockType.BONE_BLOCK: BlockDefinition("Bone Block", "bone_block_top.png", "bone_block_side.png", "bone_block_top.png"),
    BlockType.SCULK: BlockDefinition("Sculk", "sculk.png", "sculk.png", "sculk.png"),  # Regular sculk block
    # Chest variants
    BlockType.TRAPPED_CHEST: BlockDefinition("Trapped Chest", "oak_planks.png", "oak_planks.png", "oak_planks.png"),  # Custom render
    BlockType.CHRISTMAS_CHEST: BlockDefinition("Christmas Chest", "oak_planks.png", "oak_planks.png", "oak_planks.png"),  # Custom render
    BlockType.COPPER_CHEST: BlockDefinition("Copper Chest", "copper_block.png", "copper_block.png", "copper_block.png"),  # Custom render
    BlockType.COPPER_CHEST_EXPOSED: BlockDefinition("Exposed Copper Chest", "exposed_copper.png", "exposed_copper.png", "exposed_copper.png"),  # Custom render
    BlockType.COPPER_CHEST_WEATHERED: BlockDefinition("Weathered Copper Chest", "weathered_copper.png", "weathered_copper.png", "weathered_copper.png"),  # Custom render
    BlockType.COPPER_CHEST_OXIDIZED: BlockDefinition("Oxidized Copper Chest", "oxidized_copper.png", "oxidized_copper.png", "oxidized_copper.png"),  # Custom render
    # Problematic/Special blocks
    BlockType.OXIDIZING_COPPER: BlockDefinition("Oxidizing Copper", "copper_block.png", "copper_block.png", "copper_block.png"),  # Animates through stages
    BlockType.ENCHANTING_TABLE: BlockDefinition("Enchanting Table", "enchanting_table_top.png", "enchanting_table_side.png", "enchanting_table_bottom.png"),
    BlockType.MOB_SPAWNER: BlockDefinition("Mob Spawner", "spawner.png", "spawner.png", "spawner.png", transparent=True),
    BlockType.TRIAL_SPAWNER: BlockDefinition("Trial Spawner", "trial_spawner_top_inactive.png", "trial_spawner_side_inactive.png", "trial_spawner_bottom.png", transparent=True),
    BlockType.SCULK_SENSOR: BlockDefinition("Sculk Sensor", "sculk_sensor_top.png", "sculk_sensor_side.png", "sculk_sensor_bottom.png"),
    BlockType.END_PORTAL: BlockDefinition("End Portal", "black_concrete.png", "black_concrete.png", "black_concrete.png", isPortal=True),  # Animated starfield
    BlockType.END_GATEWAY: BlockDefinition("End Gateway", "black_concrete.png", "black_concrete.png", "black_concrete.png", isPortal=True),  # Animated starfield
    BlockType.FIRE: BlockDefinition("Fire", "fire_0.png", "fire_0.png", "fire_0.png", transparent=True),  # Animated
    BlockType.SOUL_FIRE: BlockDefinition("Soul Fire", "soul_fire_0.png", "soul_fire_0.png", "soul_fire_0.png", transparent=True),  # Animated
}

# Sound definitions for each block type
BLOCK_SOUNDS: Dict[BlockType, SoundDefinition] = {
    # Natural
    BlockType.GRASS: SoundDefinition("grass", "grass"),
    BlockType.DIRT: SoundDefinition("gravel", "gravel"),
    BlockType.STONE: SoundDefinition("stone", "stone"),
    BlockType.COBBLESTONE: SoundDefinition("stone", "stone"),
    BlockType.GRAVEL: SoundDefinition("gravel", "gravel"),
    BlockType.SAND: SoundDefinition("sand", "sand"),
    BlockType.CLAY: SoundDefinition("gravel", "gravel"),
    # Wood
    BlockType.OAK_LOG: SoundDefinition("wood", "wood"),
    BlockType.OAK_PLANKS: SoundDefinition("wood", "wood"),
    BlockType.OAK_LEAVES: SoundDefinition("grass", "grass"),
    BlockType.BIRCH_LOG: SoundDefinition("wood", "wood"),
    BlockType.BIRCH_PLANKS: SoundDefinition("wood", "wood"),
    BlockType.BIRCH_LEAVES: SoundDefinition("grass", "grass"),
    BlockType.SPRUCE_LOG: SoundDefinition("wood", "wood"),
    BlockType.SPRUCE_PLANKS: SoundDefinition("wood", "wood"),
    BlockType.SPRUCE_LEAVES: SoundDefinition("grass", "grass"),
    BlockType.DARK_OAK_LOG: SoundDefinition("wood", "wood"),
    BlockType.DARK_OAK_PLANKS: SoundDefinition("wood", "wood"),
    BlockType.DARK_OAK_LEAVES: SoundDefinition("grass", "grass"),
    # Ores and minerals
    BlockType.COAL_ORE: SoundDefinition("stone", "stone"),
    BlockType.IRON_ORE: SoundDefinition("stone", "stone"),
    BlockType.GOLD_ORE: SoundDefinition("stone", "stone"),
    BlockType.DIAMOND_ORE: SoundDefinition("stone", "stone"),
    BlockType.COAL_BLOCK: SoundDefinition("stone", "stone"),
    BlockType.IRON_BLOCK: SoundDefinition("stone", "stone"),
    BlockType.GOLD_BLOCK: SoundDefinition("stone", "stone"),
    BlockType.DIAMOND_BLOCK: SoundDefinition("stone", "stone"),
    # Building
    BlockType.BRICKS: SoundDefinition("stone", "stone"),
    BlockType.STONE_BRICKS: SoundDefinition("stone", "stone"),
    BlockType.MOSSY_STONE_BRICKS: SoundDefinition("stone", "stone"),
    BlockType.MOSSY_COBBLESTONE: SoundDefinition("stone", "stone"),
    BlockType.SANDSTONE: SoundDefinition("stone", "stone"),
    BlockType.RED_SANDSTONE: SoundDefinition("stone", "stone"),
    # Decorative
    BlockType.GLASS: SoundDefinition("glass", "glass"),
    BlockType.BOOKSHELF: SoundDefinition("wood", "wood"),
    BlockType.GLOWSTONE: SoundDefinition("stone", "stone"),
    # Wool (cloth sound in Minecraft)
    BlockType.WHITE_WOOL: SoundDefinition("cloth", "cloth"),
    BlockType.RED_WOOL: SoundDefinition("cloth", "cloth"),
    BlockType.BLUE_WOOL: SoundDefinition("cloth", "cloth"),
    BlockType.GREEN_WOOL: SoundDefinition("cloth", "cloth"),
    BlockType.YELLOW_WOOL: SoundDefinition("cloth", "cloth"),
    BlockType.BLACK_WOOL: SoundDefinition("cloth", "cloth"),
    # Concrete
    BlockType.WHITE_CONCRETE: SoundDefinition("stone", "stone"),
    BlockType.RED_CONCRETE: SoundDefinition("stone", "stone"),
    BlockType.BLUE_CONCRETE: SoundDefinition("stone", "stone"),
    # Special
    BlockType.CRAFTING_TABLE: SoundDefinition("wood", "wood"),
    BlockType.FURNACE: SoundDefinition("stone", "stone"),
    BlockType.TNT: SoundDefinition("grass", "grass"),
    BlockType.BEDROCK: SoundDefinition("stone", "stone"),
    # Doors
    BlockType.OAK_DOOR: SoundDefinition("wood", "wood"),
    BlockType.IRON_DOOR: SoundDefinition("stone", "stone"),
    # Liquids
    BlockType.WATER: SoundDefinition("water", "water"),
    BlockType.LAVA: SoundDefinition("lava", "lava"),
    # Stairs
    BlockType.OAK_STAIRS: SoundDefinition("wood", "wood"),
    BlockType.COBBLESTONE_STAIRS: SoundDefinition("stone", "stone"),
    BlockType.STONE_BRICK_STAIRS: SoundDefinition("stone", "stone"),
    # Slabs
    BlockType.OAK_SLAB: SoundDefinition("wood", "wood"),
    BlockType.COBBLESTONE_SLAB: SoundDefinition("stone", "stone"),
    BlockType.STONE_BRICK_SLAB: SoundDefinition("stone", "stone"),
    BlockType.STONE_SLAB: SoundDefinition("stone", "stone"),
    # Nether/End blocks
    BlockType.OBSIDIAN: SoundDefinition("stone", "stone"),
    BlockType.END_PORTAL_FRAME: SoundDefinition("stone", "glass"),
    BlockType.END_STONE: SoundDefinition("stone", "stone"),
    BlockType.END_STONE_BRICKS: SoundDefinition("stone", "stone"),
    BlockType.NETHER_PORTAL: SoundDefinition("portal", "glass"),
    BlockType.NETHER_BRICKS: SoundDefinition("nether_bricks", "nether_bricks"),
    BlockType.NETHERRACK: SoundDefinition("netherrack", "netherrack"),
    BlockType.SOUL_SAND: SoundDefinition("sand", "sand"),
    BlockType.CACTUS: SoundDefinition("cloth", "cloth"),
    BlockType.PUMPKIN: SoundDefinition("wood", "wood"),
    BlockType.JACK_O_LANTERN: SoundDefinition("wood", "wood"),
    BlockType.HAY_BLOCK: SoundDefinition("grass", "grass"),
    BlockType.MELON: SoundDefinition("wood", "wood"),
    BlockType.SNOW: SoundDefinition("cloth", "cloth"),
    BlockType.ICE: SoundDefinition("glass", "glass"),
    BlockType.PACKED_ICE: SoundDefinition("glass", "glass"),
    # Copper blocks - all use copper sound
    BlockType.COPPER_BLOCK: SoundDefinition("copper", "copper"),
    BlockType.EXPOSED_COPPER: SoundDefinition("copper", "copper"),
    BlockType.WEATHERED_COPPER: SoundDefinition("copper", "copper"),
    BlockType.OXIDIZED_COPPER: SoundDefinition("copper", "copper"),
    BlockType.CUT_COPPER: SoundDefinition("copper", "copper"),
    BlockType.EXPOSED_CUT_COPPER: SoundDefinition("copper", "copper"),
    BlockType.WEATHERED_CUT_COPPER: SoundDefinition("copper", "copper"),
    BlockType.OXIDIZED_CUT_COPPER: SoundDefinition("copper", "copper"),
    # Regular new blocks
    BlockType.CHEST: SoundDefinition("chest", "wood"),
    BlockType.ENDER_CHEST: SoundDefinition("enderchest", "stone"),
    BlockType.BONE_BLOCK: SoundDefinition("bone_block", "bone_block"),
    BlockType.SCULK: SoundDefinition("sculk", "sculk"),  # Sculk block sound
    # Chest variants
    BlockType.TRAPPED_CHEST: SoundDefinition("chest", "wood"),
    BlockType.CHRISTMAS_CHEST: SoundDefinition("chest", "wood"),
    BlockType.COPPER_CHEST: SoundDefinition("copper_chest", "copper"),
    BlockType.COPPER_CHEST_EXPOSED: SoundDefinition("copper_chest", "copper"),
    BlockType.COPPER_CHEST_WEATHERED: SoundDefinition("copper_chest_weathered", "copper"),
    BlockType.COPPER_CHEST_OXIDIZED: SoundDefinition("copper_chest_oxidized", "copper"),
    # Problematic/Special blocks
    BlockType.OXIDIZING_COPPER: SoundDefinition("copper", "copper"),
    BlockType.ENCHANTING_TABLE: SoundDefinition("enchantment_table", "stone"),
    BlockType.MOB_SPAWNER: SoundDefinition("spawner", "spawner"),
    BlockType.TRIAL_SPAWNER: SoundDefinition("spawner", "spawner"),
    BlockType.SCULK_SENSOR: SoundDefinition("sculk_sensor", "sculk_sensor"),
    BlockType.END_PORTAL: SoundDefinition("end_portal", "glass"),
    BlockType.END_GATEWAY: SoundDefinition("end_portal", "glass"),
    BlockType.FIRE: SoundDefinition("fire", "fire"),
    BlockType.SOUL_FIRE: SoundDefinition("fire", "fire"),
}


# ============================================================================
# BLOCK CATEGORIES (for dropdown UI)
# ============================================================================

# Define categories and which blocks belong to each
BLOCK_CATEGORIES = {
    "Natural": [
        BlockType.GRASS, BlockType.DIRT, BlockType.STONE, BlockType.COBBLESTONE,
        BlockType.GRAVEL, BlockType.SAND, BlockType.CLAY,
        BlockType.SNOW, BlockType.ICE, BlockType.PACKED_ICE
    ],
    "Plants": [
        BlockType.CACTUS, BlockType.PUMPKIN, BlockType.JACK_O_LANTERN,
        BlockType.HAY_BLOCK, BlockType.MELON
    ],
    "Wood": [
        BlockType.OAK_LOG, BlockType.OAK_PLANKS, BlockType.OAK_LEAVES,
        BlockType.BIRCH_LOG, BlockType.BIRCH_PLANKS, BlockType.BIRCH_LEAVES,
        BlockType.SPRUCE_LOG, BlockType.SPRUCE_PLANKS, BlockType.SPRUCE_LEAVES,
        BlockType.DARK_OAK_LOG, BlockType.DARK_OAK_PLANKS, BlockType.DARK_OAK_LEAVES
    ],
    "Ores & Minerals": [
        BlockType.COAL_ORE, BlockType.IRON_ORE, BlockType.GOLD_ORE, BlockType.DIAMOND_ORE,
        BlockType.COAL_BLOCK, BlockType.IRON_BLOCK, BlockType.GOLD_BLOCK, BlockType.DIAMOND_BLOCK
    ],
    "Copper": [
        BlockType.COPPER_BLOCK, BlockType.EXPOSED_COPPER, BlockType.WEATHERED_COPPER, BlockType.OXIDIZED_COPPER,
        BlockType.CUT_COPPER, BlockType.EXPOSED_CUT_COPPER, BlockType.WEATHERED_CUT_COPPER, BlockType.OXIDIZED_CUT_COPPER
    ],
    "Chests": [
        BlockType.CHEST, BlockType.TRAPPED_CHEST, BlockType.ENDER_CHEST, BlockType.CHRISTMAS_CHEST,
        BlockType.COPPER_CHEST, BlockType.COPPER_CHEST_EXPOSED, BlockType.COPPER_CHEST_WEATHERED, BlockType.COPPER_CHEST_OXIDIZED
    ],
    "Building": [
        BlockType.BRICKS, BlockType.STONE_BRICKS, BlockType.MOSSY_STONE_BRICKS,
        BlockType.MOSSY_COBBLESTONE, BlockType.SANDSTONE, BlockType.RED_SANDSTONE,
        BlockType.BONE_BLOCK, BlockType.SCULK
    ],
    "Decorative": [
        BlockType.GLASS, BlockType.BOOKSHELF, BlockType.GLOWSTONE,
        BlockType.WHITE_WOOL, BlockType.RED_WOOL, BlockType.BLUE_WOOL,
        BlockType.GREEN_WOOL, BlockType.YELLOW_WOOL, BlockType.BLACK_WOOL,
        BlockType.WHITE_CONCRETE, BlockType.RED_CONCRETE, BlockType.BLUE_CONCRETE
    ],
    "Special": [
        BlockType.CRAFTING_TABLE, BlockType.FURNACE, BlockType.TNT, BlockType.BEDROCK,
        BlockType.WATER, BlockType.LAVA
    ],
    "Nether/End": [
        BlockType.OBSIDIAN, BlockType.NETHER_PORTAL,
        BlockType.END_PORTAL_FRAME, BlockType.END_STONE, BlockType.END_STONE_BRICKS,
        BlockType.NETHER_BRICKS, BlockType.NETHERRACK, BlockType.SOUL_SAND
    ],
    "Slabs": [
        BlockType.OAK_SLAB, BlockType.COBBLESTONE_SLAB, BlockType.STONE_BRICK_SLAB, BlockType.STONE_SLAB
    ],
    "Problematic": [
        BlockType.OAK_DOOR, BlockType.IRON_DOOR,
        BlockType.OAK_STAIRS, BlockType.COBBLESTONE_STAIRS, BlockType.STONE_BRICK_STAIRS,
        BlockType.OXIDIZING_COPPER, BlockType.ENCHANTING_TABLE, BlockType.MOB_SPAWNER,
        BlockType.TRIAL_SPAWNER, BlockType.SCULK_SENSOR, BlockType.END_PORTAL, BlockType.END_GATEWAY,
        BlockType.FIRE, BlockType.SOUL_FIRE
    ],
}

# Order of categories in the UI
CATEGORY_ORDER = ["Natural", "Plants", "Wood", "Ores & Minerals", "Copper", "Chests", "Building", "Decorative", "Special", "Nether/End", "Slabs", "Problematic"]


# ============================================================================
# PREMADE STRUCTURES
# ============================================================================

# Simple house structure (relative positions and block types)
STRUCTURE_HOUSE = {
    "name": "Simple House",
    "blocks": [
        # Floor (oak planks)
        *[(x, y, 0, BlockType.OAK_PLANKS) for x in range(5) for y in range(5)],
        
        # Walls (cobblestone) - front wall with door gap
        *[(0, y, z, BlockType.COBBLESTONE) for y in range(5) for z in range(1, 4)],
        *[(4, y, z, BlockType.COBBLESTONE) for y in range(5) for z in range(1, 4)],
        *[(x, 0, z, BlockType.COBBLESTONE) for x in range(1, 4) for z in range(1, 4) if not (x == 2 and z < 3)],
        *[(x, 4, z, BlockType.COBBLESTONE) for x in range(1, 4) for z in range(1, 4)],
        
        # Roof (oak planks) - flat for simplicity
        *[(x, y, 4, BlockType.OAK_PLANKS) for x in range(5) for y in range(5)],
    ]
}

# Tree structure
STRUCTURE_TREE = {
    "name": "Oak Tree",
    "blocks": [
        # Trunk (oak log)
        *[(0, 0, z, BlockType.OAK_LOG) for z in range(4)],
        
        # Leaves (oak leaves)
        *[(x, y, 3, BlockType.OAK_LEAVES) for x in range(-1, 2) for y in range(-1, 2)],
        *[(x, y, 4, BlockType.OAK_LEAVES) for x in range(-1, 2) for y in range(-1, 2)],
        *[(0, 0, 5, BlockType.OAK_LEAVES)],
    ]
}

# Villager House Structure (5x5 Plains Village House)
STRUCTURE_VILLAGER_HOUSE = {
    "name": "Villager House",
    "blocks": [
        # Foundation - Layer 1 (5x5 cobblestone floor)
        *[(x, y, 0, BlockType.COBBLESTONE) for x in range(5) for y in range(5)],
        
        # Layer 2 - First wall level (oak logs at corners, oak planks between)
        # Corner pillars
        (0, 0, 1, BlockType.OAK_LOG),
        (4, 0, 1, BlockType.OAK_LOG),
        (0, 4, 1, BlockType.OAK_LOG),
        (4, 4, 1, BlockType.OAK_LOG),
        # Walls - front (y=0) with door gap at x=2
        (1, 0, 1, BlockType.OAK_PLANKS),
        (3, 0, 1, BlockType.OAK_PLANKS),
        # Walls - back (y=4)
        *[(x, 4, 1, BlockType.OAK_PLANKS) for x in range(1, 4)],
        # Walls - left (x=0)
        *[(0, y, 1, BlockType.OAK_PLANKS) for y in range(1, 4)],
        # Walls - right (x=4)
        *[(4, y, 1, BlockType.OAK_PLANKS) for y in range(1, 4)],
        
        # Layer 3 - Second wall level (windows on sides)
        # Corner pillars
        (0, 0, 2, BlockType.OAK_LOG),
        (4, 0, 2, BlockType.OAK_LOG),
        (0, 4, 2, BlockType.OAK_LOG),
        (4, 4, 2, BlockType.OAK_LOG),
        # Front wall with door gap
        (1, 0, 2, BlockType.OAK_PLANKS),
        (3, 0, 2, BlockType.OAK_PLANKS),
        # Back wall
        *[(x, 4, 2, BlockType.OAK_PLANKS) for x in range(1, 4)],
        # Left wall with window (glass at center)
        (0, 1, 2, BlockType.OAK_PLANKS),
        (0, 2, 2, BlockType.GLASS),
        (0, 3, 2, BlockType.OAK_PLANKS),
        # Right wall with window
        (4, 1, 2, BlockType.OAK_PLANKS),
        (4, 2, 2, BlockType.GLASS),
        (4, 3, 2, BlockType.OAK_PLANKS),
        
        # Layer 4 - Third wall level
        # Corner pillars
        (0, 0, 3, BlockType.OAK_LOG),
        (4, 0, 3, BlockType.OAK_LOG),
        (0, 4, 3, BlockType.OAK_LOG),
        (4, 4, 3, BlockType.OAK_LOG),
        # Front wall
        *[(x, 0, 3, BlockType.OAK_PLANKS) for x in range(1, 4)],
        # Back wall
        *[(x, 4, 3, BlockType.OAK_PLANKS) for x in range(1, 4)],
        # Left wall
        *[(0, y, 3, BlockType.OAK_PLANKS) for y in range(1, 4)],
        # Right wall
        *[(4, y, 3, BlockType.OAK_PLANKS) for y in range(1, 4)],
        
        # Layer 5 - Ceiling (flat 5x5 oak planks)
        *[(x, y, 4, BlockType.OAK_PLANKS) for x in range(5) for y in range(5)],
        
        # Layer 6 - Roof edges (oak stairs - using planks as substitute)
        # Left edge stairs
        *[(0, y, 5, BlockType.OAK_STAIRS) for y in range(5)],
        # Right edge stairs
        *[(4, y, 5, BlockType.OAK_STAIRS) for y in range(5)],
        
        # Layer 7 - Roof middle
        *[(1, y, 5, BlockType.OAK_STAIRS) for y in range(5)],
        *[(3, y, 5, BlockType.OAK_STAIRS) for y in range(5)],
        # Peak
        *[(2, y, 5, BlockType.OAK_PLANKS) for y in range(5)],
    ]
}

# Nether Portal Structure (4 wide x 5 tall obsidian frame with portal inside)
STRUCTURE_NETHER_PORTAL = {
    "name": "Nether Portal",
    "blocks": [
        # Bottom obsidian frame (4 blocks wide)
        *[(x, 0, 0, BlockType.OBSIDIAN) for x in range(4)],
        
        # Left pillar (3 blocks high)
        *[(0, 0, z, BlockType.OBSIDIAN) for z in range(1, 4)],
        
        # Right pillar (3 blocks high)
        *[(3, 0, z, BlockType.OBSIDIAN) for z in range(1, 4)],
        
        # Top obsidian frame (4 blocks wide)
        *[(x, 0, 4, BlockType.OBSIDIAN) for x in range(4)],
        
        # Portal blocks inside (2 wide x 3 tall)
        *[(x, 0, z, BlockType.NETHER_PORTAL) for x in range(1, 3) for z in range(1, 4)],
    ]
}

# Spruce Tree Structure (taller, narrow cone shape)
STRUCTURE_SPRUCE_TREE = {
    "name": "Spruce Tree",
    "blocks": [
        # Trunk (6 blocks tall)
        *[(0, 0, z, BlockType.SPRUCE_LOG) for z in range(6)],
        
        # Bottom layer of leaves (wide)
        *[(x, y, 2, BlockType.SPRUCE_LEAVES) for x in range(-2, 3) for y in range(-2, 3) 
          if abs(x) + abs(y) <= 3 and not (x == 0 and y == 0)],
        
        # Middle layer of leaves
        *[(x, y, 3, BlockType.SPRUCE_LEAVES) for x in range(-1, 2) for y in range(-1, 2)],
        *[(x, y, 4, BlockType.SPRUCE_LEAVES) for x in range(-1, 2) for y in range(-1, 2)],
        
        # Top layer of leaves (narrow)
        *[(x, y, 5, BlockType.SPRUCE_LEAVES) for x in range(-1, 2) for y in range(-1, 2) 
          if abs(x) + abs(y) <= 1],
        (0, 0, 6, BlockType.SPRUCE_LEAVES),
    ]
}

# Birch Tree Structure (white bark, similar to oak)
STRUCTURE_BIRCH_TREE = {
    "name": "Birch Tree",
    "blocks": [
        # Trunk (5 blocks tall)
        *[(0, 0, z, BlockType.BIRCH_LOG) for z in range(5)],
        
        # Leaves (round canopy)
        *[(x, y, 3, BlockType.BIRCH_LEAVES) for x in range(-2, 3) for y in range(-2, 3) 
          if abs(x) + abs(y) <= 2],
        *[(x, y, 4, BlockType.BIRCH_LEAVES) for x in range(-1, 2) for y in range(-1, 2)],
        (0, 0, 5, BlockType.BIRCH_LEAVES),
    ]
}

# Dark Oak Tree Structure (thick trunk, 2x2)
STRUCTURE_DARK_OAK_TREE = {
    "name": "Dark Oak Tree",
    "blocks": [
        # Thick trunk (2x2, 5 blocks tall)
        *[(x, y, z, BlockType.DARK_OAK_LOG) for x in range(2) for y in range(2) for z in range(5)],
        
        # Leaves (large canopy)
        *[(x, y, 3, BlockType.DARK_OAK_LEAVES) for x in range(-2, 4) for y in range(-2, 4) 
          if not (0 <= x <= 1 and 0 <= y <= 1)],
        *[(x, y, 4, BlockType.DARK_OAK_LEAVES) for x in range(-2, 4) for y in range(-2, 4) 
          if not (0 <= x <= 1 and 0 <= y <= 1)],
        *[(x, y, 5, BlockType.DARK_OAK_LEAVES) for x in range(-1, 3) for y in range(-1, 3)],
        *[(x, y, 6, BlockType.DARK_OAK_LEAVES) for x in range(2) for y in range(2)],
    ]
}

# Desert Well Structure (sandstone well with water)
STRUCTURE_DESERT_WELL = {
    "name": "Desert Well",
    "blocks": [
        # Base slab layer (sandstone)
        *[(x, y, 0, BlockType.SANDSTONE) for x in range(-2, 3) for y in range(-2, 3) 
          if abs(x) == 2 or abs(y) == 2],
        
        # Water in center
        *[(x, y, 0, BlockType.WATER) for x in range(-1, 2) for y in range(-1, 2)],
        
        # Walls around water
        *[(x, y, 1, BlockType.SANDSTONE) for x in range(-1, 2) for y in range(-1, 2) 
          if abs(x) == 1 or abs(y) == 1],
    ]
}

# Lamp Post Structure (stone base with glowstone top)
STRUCTURE_LAMP_POST = {
    "name": "Lamp Post",
    "blocks": [
        # Stone base
        (0, 0, 0, BlockType.STONE_BRICKS),
        # Pole
        (0, 0, 1, BlockType.COBBLESTONE),
        (0, 0, 2, BlockType.COBBLESTONE),
        (0, 0, 3, BlockType.COBBLESTONE),
        # Glowstone top
        (0, 0, 4, BlockType.GLOWSTONE),
    ]
}

# Fountain Structure (stone brick basin with water)
STRUCTURE_FOUNTAIN = {
    "name": "Fountain",
    "blocks": [
        # Outer ring base
        *[(x, y, 0, BlockType.STONE_BRICKS) for x in range(-2, 3) for y in range(-2, 3)],
        
        # Walls (1 block high)
        *[(x, y, 1, BlockType.STONE_BRICKS) for x in range(-2, 3) for y in range(-2, 3) 
          if abs(x) == 2 or abs(y) == 2],
        
        # Water inside
        *[(x, y, 1, BlockType.WATER) for x in range(-1, 2) for y in range(-1, 2) 
          if not (x == 0 and y == 0)],
        
        # Center pillar
        (0, 0, 1, BlockType.STONE_BRICKS),
        (0, 0, 2, BlockType.STONE_BRICKS),
        
        # Water on top of pillar (fountain spray)
        (0, 0, 3, BlockType.WATER),
    ]
}

# Watch Tower Structure (tall wooden tower with lookout)
STRUCTURE_WATCH_TOWER = {
    "name": "Watch Tower",
    "blocks": [
        # Foundation (3x3 cobblestone)
        *[(x, y, 0, BlockType.COBBLESTONE) for x in range(3) for y in range(3)],
        
        # Corner pillars (oak logs, 6 high)
        *[(0, 0, z, BlockType.OAK_LOG) for z in range(1, 7)],
        *[(2, 0, z, BlockType.OAK_LOG) for z in range(1, 7)],
        *[(0, 2, z, BlockType.OAK_LOG) for z in range(1, 7)],
        *[(2, 2, z, BlockType.OAK_LOG) for z in range(1, 7)],
        
        # Platform floor at z=4
        *[(x, y, 4, BlockType.OAK_PLANKS) for x in range(3) for y in range(3)],
        
        # Railing at z=5
        (1, 0, 5, BlockType.OAK_PLANKS),
        (1, 2, 5, BlockType.OAK_PLANKS),
        (0, 1, 5, BlockType.OAK_PLANKS),
        (2, 1, 5, BlockType.OAK_PLANKS),
        
        # Roof
        *[(x, y, 7, BlockType.OAK_PLANKS) for x in range(3) for y in range(3)],
    ]
}

# Cactus Farm Structure (desert farm with cacti)
STRUCTURE_CACTUS_FARM = {
    "name": "Cactus Farm",
    "blocks": [
        # Sand base
        *[(x, y, 0, BlockType.SAND) for x in range(5) for y in range(5)],
        
        # Cacti in a pattern (they need space between them in real MC)
        *[(0, 0, z, BlockType.CACTUS) for z in range(1, 4)],
        *[(2, 0, z, BlockType.CACTUS) for z in range(1, 3)],
        *[(4, 0, z, BlockType.CACTUS) for z in range(1, 4)],
        *[(0, 2, z, BlockType.CACTUS) for z in range(1, 3)],
        *[(4, 2, z, BlockType.CACTUS) for z in range(1, 3)],
        *[(0, 4, z, BlockType.CACTUS) for z in range(1, 4)],
        *[(2, 4, z, BlockType.CACTUS) for z in range(1, 3)],
        *[(4, 4, z, BlockType.CACTUS) for z in range(1, 4)],
    ]
}

# Pumpkin Patch Structure (farm with pumpkins and hay)
STRUCTURE_PUMPKIN_PATCH = {
    "name": "Pumpkin Patch",
    "blocks": [
        # Dirt base
        *[(x, y, 0, BlockType.DIRT) for x in range(4) for y in range(4)],
        
        # Pumpkins scattered
        (0, 0, 1, BlockType.PUMPKIN),
        (2, 1, 1, BlockType.PUMPKIN),
        (1, 3, 1, BlockType.PUMPKIN),
        (3, 2, 1, BlockType.PUMPKIN),
        
        # Jack o'lantern for decoration
        (3, 0, 1, BlockType.JACK_O_LANTERN),
        
        # Hay bale stack
        (0, 3, 1, BlockType.HAY_BLOCK),
        (0, 3, 2, BlockType.HAY_BLOCK),
    ]
}

# Nether Ruins Structure (ruined nether brick tower)
STRUCTURE_NETHER_RUINS = {
    "name": "Nether Ruins",
    "blocks": [
        # Base floor (netherrack with nether bricks)
        *[(x, y, 0, BlockType.NETHERRACK) for x in range(5) for y in range(5)],
        *[(x, y, 0, BlockType.NETHER_BRICKS) for x in range(1, 4) for y in range(1, 4)],
        
        # Broken walls
        *[(0, y, z, BlockType.NETHER_BRICKS) for y in range(5) for z in range(1, 4)],
        *[(4, y, z, BlockType.NETHER_BRICKS) for y in range(5) for z in range(1, 3)],  # Shorter wall (ruined)
        *[(x, 0, z, BlockType.NETHER_BRICKS) for x in range(1, 4) for z in range(1, 3)],
        *[(x, 4, z, BlockType.NETHER_BRICKS) for x in range(1, 4) for z in range(1, 4)],
        
        # Soul sand patches
        (1, 1, 1, BlockType.SOUL_SAND),
        (3, 3, 1, BlockType.SOUL_SAND),
        
        # Glowstone lighting
        (2, 2, 3, BlockType.GLOWSTONE),
    ]
}

# Igloo Structure (ice dome with interior)
STRUCTURE_IGLOO = {
    "name": "Igloo",
    "blocks": [
        # Snow floor
        *[(x, y, 0, BlockType.SNOW) for x in range(-2, 3) for y in range(-2, 3) 
          if x*x + y*y <= 6],
        
        # Walls - packed ice dome shape
        *[(x, y, 1, BlockType.PACKED_ICE) for x in range(-2, 3) for y in range(-2, 3) 
          if x*x + y*y <= 6 and x*x + y*y > 2 and not (x == 0 and y == -2)],  # Opening at front
        
        # Interior floor
        *[(x, y, 0, BlockType.WHITE_WOOL) for x in range(-1, 2) for y in range(-1, 2)],
        
        # Second layer (smaller)
        *[(x, y, 2, BlockType.PACKED_ICE) for x in range(-1, 2) for y in range(-1, 2) 
          if abs(x) == 1 or abs(y) == 1],
        
        # Roof cap
        (0, 0, 2, BlockType.PACKED_ICE),
    ]
}

# Nether Fortress Bridge Structure (simplified fortress bridge with arches and pillars)
STRUCTURE_NETHER_FORTRESS = {
    "name": "Nether Fortress Bridge",
    "blocks": [
        # Main bridge deck (11 blocks long, 3 wide)
        *[(x, y, 4, BlockType.NETHER_BRICKS) for x in range(11) for y in range(3)],
        
        # Bridge side walls (railings)
        *[(x, 0, 5, BlockType.NETHER_BRICKS) for x in range(11)],
        *[(x, 2, 5, BlockType.NETHER_BRICKS) for x in range(11)],
        
        # Left support pillar (goes down to ground)
        *[(0, y, z, BlockType.NETHER_BRICKS) for y in range(3) for z in range(5)],
        *[(1, y, z, BlockType.NETHER_BRICKS) for y in range(3) for z in range(5)],
        
        # Right support pillar
        *[(9, y, z, BlockType.NETHER_BRICKS) for y in range(3) for z in range(5)],
        *[(10, y, z, BlockType.NETHER_BRICKS) for y in range(3) for z in range(5)],
        
        # Arch under bridge (left side)
        (2, 0, 3, BlockType.NETHER_BRICKS),
        (2, 2, 3, BlockType.NETHER_BRICKS),
        (3, 0, 2, BlockType.NETHER_BRICKS),
        (3, 2, 2, BlockType.NETHER_BRICKS),
        (4, 0, 1, BlockType.NETHER_BRICKS),
        (4, 2, 1, BlockType.NETHER_BRICKS),
        (5, 0, 1, BlockType.NETHER_BRICKS),
        (5, 2, 1, BlockType.NETHER_BRICKS),
        (6, 0, 1, BlockType.NETHER_BRICKS),
        (6, 2, 1, BlockType.NETHER_BRICKS),
        (7, 0, 2, BlockType.NETHER_BRICKS),
        (7, 2, 2, BlockType.NETHER_BRICKS),
        (8, 0, 3, BlockType.NETHER_BRICKS),
        (8, 2, 3, BlockType.NETHER_BRICKS),
        
        # Decorative top corners (like fortress style)
        (0, 0, 6, BlockType.NETHER_BRICKS),
        (0, 2, 6, BlockType.NETHER_BRICKS),
        (10, 0, 6, BlockType.NETHER_BRICKS),
        (10, 2, 6, BlockType.NETHER_BRICKS),
    ]
}

# End Portal Frame Structure (filled portal like nether portal)
STRUCTURE_END_PORTAL = {
    "name": "End Portal",
    "blocks": [
        # Frame ring of end portal frames (3x3 with corners missing)
        # Bottom row
        (1, 0, 0, BlockType.END_PORTAL_FRAME),
        (2, 0, 0, BlockType.END_PORTAL_FRAME),
        (3, 0, 0, BlockType.END_PORTAL_FRAME),
        # Top row
        (1, 4, 0, BlockType.END_PORTAL_FRAME),
        (2, 4, 0, BlockType.END_PORTAL_FRAME),
        (3, 4, 0, BlockType.END_PORTAL_FRAME),
        # Left column
        (0, 1, 0, BlockType.END_PORTAL_FRAME),
        (0, 2, 0, BlockType.END_PORTAL_FRAME),
        (0, 3, 0, BlockType.END_PORTAL_FRAME),
        # Right column
        (4, 1, 0, BlockType.END_PORTAL_FRAME),
        (4, 2, 0, BlockType.END_PORTAL_FRAME),
        (4, 3, 0, BlockType.END_PORTAL_FRAME),
        
        # Portal blocks inside (3x3 grid)
        (1, 1, 0, BlockType.END_PORTAL),
        (2, 1, 0, BlockType.END_PORTAL),
        (3, 1, 0, BlockType.END_PORTAL),
        (1, 2, 0, BlockType.END_PORTAL),
        (2, 2, 0, BlockType.END_PORTAL),
        (3, 2, 0, BlockType.END_PORTAL),
        (1, 3, 0, BlockType.END_PORTAL),
        (2, 3, 0, BlockType.END_PORTAL),
        (3, 3, 0, BlockType.END_PORTAL),
    ]
}

# Nether Fossil Structure (bone block fossil remains)
STRUCTURE_NETHER_FOSSIL = {
    "name": "Nether Fossil",
    "blocks": [
        # A ribcage fossil - creature lying on its side, ribs arcing upward
        # Spine runs along the ground (z=0), ribs curve up and inward
        
        # Central spine (backbone) - along x-axis at ground level
        (0, 1, 0, BlockType.BONE_BLOCK),  # Pelvis/tail end
        (1, 1, 0, BlockType.BONE_BLOCK),
        (2, 1, 0, BlockType.BONE_BLOCK),
        (3, 1, 0, BlockType.BONE_BLOCK),
        (4, 1, 0, BlockType.BONE_BLOCK),
        (5, 1, 0, BlockType.BONE_BLOCK),  # Neck
        
        # RIBS - arcing upward from spine, curving inward at top
        # Each rib pair: base at y=0 and y=2, curving up through z=1,2
        
        # Rib pair 1 (near pelvis)
        (1, 0, 0, BlockType.BONE_BLOCK),  # Left base
        (1, 0, 1, BlockType.BONE_BLOCK),  # Left rising
        (1, 2, 0, BlockType.BONE_BLOCK),  # Right base
        (1, 2, 1, BlockType.BONE_BLOCK),  # Right rising
        
        # Rib pair 2
        (2, 0, 0, BlockType.BONE_BLOCK),
        (2, 0, 1, BlockType.BONE_BLOCK),
        (2, 0, 2, BlockType.BONE_BLOCK),  # Curves inward
        (2, 1, 2, BlockType.BONE_BLOCK),  # Top meeting point
        (2, 2, 0, BlockType.BONE_BLOCK),
        (2, 2, 1, BlockType.BONE_BLOCK),
        (2, 2, 2, BlockType.BONE_BLOCK),
        
        # Rib pair 3 (tallest - mid torso)
        (3, 0, 0, BlockType.BONE_BLOCK),
        (3, 0, 1, BlockType.BONE_BLOCK),
        (3, 0, 2, BlockType.BONE_BLOCK),
        (3, 0, 3, BlockType.BONE_BLOCK),  # Tallest point
        (3, 1, 3, BlockType.BONE_BLOCK),  # Top connector
        (3, 2, 0, BlockType.BONE_BLOCK),
        (3, 2, 1, BlockType.BONE_BLOCK),
        (3, 2, 2, BlockType.BONE_BLOCK),
        (3, 2, 3, BlockType.BONE_BLOCK),
        
        # Rib pair 4 (broken/incomplete for decay)
        (4, 0, 0, BlockType.BONE_BLOCK),
        (4, 0, 1, BlockType.BONE_BLOCK),
        (4, 2, 0, BlockType.BONE_BLOCK),
        (4, 2, 1, BlockType.BONE_BLOCK),
        (4, 2, 2, BlockType.BONE_BLOCK),
        
        # Skull (block cluster at head end)
        (6, 1, 0, BlockType.BONE_BLOCK),  # Skull base
        (6, 0, 0, BlockType.BONE_BLOCK),  # Jaw
        (6, 1, 1, BlockType.BONE_BLOCK),  # Cranium
    ]
}

PREMADE_STRUCTURES = {
    "house": STRUCTURE_HOUSE,
    "tree": STRUCTURE_TREE,
    "villager_house": STRUCTURE_VILLAGER_HOUSE,
    "nether_portal": STRUCTURE_NETHER_PORTAL,
    "spruce_tree": STRUCTURE_SPRUCE_TREE,
    "birch_tree": STRUCTURE_BIRCH_TREE,
    "dark_oak_tree": STRUCTURE_DARK_OAK_TREE,
    "desert_well": STRUCTURE_DESERT_WELL,
    "lamp_post": STRUCTURE_LAMP_POST,
    "fountain": STRUCTURE_FOUNTAIN,
    "watch_tower": STRUCTURE_WATCH_TOWER,
    "cactus_farm": STRUCTURE_CACTUS_FARM,
    "pumpkin_patch": STRUCTURE_PUMPKIN_PATCH,
    "nether_ruins": STRUCTURE_NETHER_RUINS,
    "igloo": STRUCTURE_IGLOO,
    "nether_fortress": STRUCTURE_NETHER_FORTRESS,
    "end_portal": STRUCTURE_END_PORTAL,
    "nether_fossil": STRUCTURE_NETHER_FOSSIL,
}


# ============================================================================
# ASSET MANAGEMENT
# ============================================================================

class AssetManager:
    """
    Manages loading and caching of textures and sounds.
    
    This class handles loading textures from the Texture Hub and sounds from
    the Sound Hub, creating isometric block sprites, and playing sound effects.
    """
    
    def __init__(self):
        """Initialize the asset manager"""
        self.textures: Dict[str, pygame.Surface] = {}
        self.blockSprites: Dict[BlockType, pygame.Surface] = {}
        self.iconSprites: Dict[BlockType, pygame.Surface] = {}
        self.sounds: Dict[str, List[pygame.mixer.Sound]] = {}  # Category -> list of sound variants
        self.clickSound: Optional[pygame.mixer.Sound] = None
        
        # Special block sprite variants
        # Doors: (blockType, facing, isOpen) -> sprite
        self.doorSprites: Dict[Tuple[BlockType, bool], pygame.Surface] = {}
        # Slabs: (blockType, position) -> sprite
        self.slabSprites: Dict[Tuple[BlockType, SlabPosition], pygame.Surface] = {}
        # Stairs: (blockType, facing) -> sprite
        self.stairSprites: Dict[Tuple[BlockType, Facing], pygame.Surface] = {}
        
        # UI textures
        self.buttonNormal: Optional[pygame.Surface] = None
        self.buttonHover: Optional[pygame.Surface] = None
        self.buttonDisabled: Optional[pygame.Surface] = None
        self.slotFrame: Optional[pygame.Surface] = None
        self.backgroundTile: Optional[pygame.Surface] = None
        
        # Animation support for liquids
        self.waterFrames: List[pygame.Surface] = []
        self.lavaFrames: List[pygame.Surface] = []
        self.currentWaterFrame = 0
        self.currentLavaFrame = 0
        self.animationTimer = 0
        self.animationSpeed = 50  # milliseconds per frame
        
        # Animation support for portal
        self.portalFrames: List[pygame.Surface] = []
        self.currentPortalFrame = 0
        self.portalAnimationTimer = 0
        self.portalAnimationSpeed = 100  # milliseconds per frame (slower for portal)
        
        # Animation support for end portal (parallax layered starfield)
        self.endPortalTexture: Optional[pygame.Surface] = None  # Full 256x256 texture
        self.endPortalLayers: List[Dict] = []  # Layer info: offset, speed, tint
        self.endPortalScrollOffset = 0.0
        self.endPortalAnimationTimer = 0
        self.endPortalAnimationSpeed = 30  # milliseconds per update (smooth scrolling)
        
        # Animation support for fire
        self.fireFrames: List[pygame.Surface] = []
        self.soulFireFrames: List[pygame.Surface] = []
        self.currentFireFrame = 0
        self.fireAnimationTimer = 0
        self.fireAnimationSpeed = 60  # milliseconds per frame (fast fire animation)
        
        # Oxidizing copper animation - starts fresh at stage 0
        self.oxidizingCopperTimer = 0
        self.oxidizingCopperSpeed = 3000  # milliseconds between oxidation stages (3 seconds)
        self.oxidizingCopperStage = 0  # 0=copper, 1=exposed, 2=weathered, 3=oxidized
        self.copperStageTextures = ["copper_block.png", "exposed_copper.png", "weathered_copper.png", "oxidized_copper.png"]
        self.oxidizingCopperInitialized = False  # Flag to ensure we start with copper texture
        
        # Spawner particle system
        self.spawnerParticles: List[Dict] = []  # {x, y, z, px, py, vx, vy, life, color}
        self.spawnerParticleTimer = 0
        self.spawnerParticleSpeed = 100  # ms between particle spawns
        
        # Chest textures (loaded from entity folder)
        self.chestTextures: Dict[str, pygame.Surface] = {}
        
        # Portal ambient sound
        self.portalAmbientSound: Optional[pygame.mixer.Sound] = None
        self.portalSoundChannel: Optional[pygame.mixer.Channel] = None
    
    def loadAllAssets(self) -> bool:
        """
        Load all textures and sounds from Texture Hub and Sound Hub.
        
        Returns:
            True if assets loaded successfully, False otherwise
        """
        print("Loading assets...")
        
        # Check if textures exist
        if not self._checkTextures():
            print("ERROR: Textures not found in Texture Hub/blocks/")
            print("Please ensure Minecraft textures are in the Assets/Texture Hub/blocks/ folder")
            return False
        
        # Load textures
        self._loadTextures()
        print(f"  Loaded {len(self.textures)} textures")
        
        # Create isometric block sprites
        self._createBlockSprites()
        print(f"  Created {len(self.blockSprites)} block sprites")
        
        # Create icon sprites for the panel
        self._createIconSprites()
        
        # Load sounds from Sound Hub
        self._loadSounds()
        print(f"  Loaded {len(self.sounds)} sound categories")
        
        # Load UI textures
        self._loadUITextures()
        print("  Loaded UI textures")
        
        # Create background
        self._createBackground()
        print("  Created background")
        
        print("Assets loaded successfully!")
        return True
    
    def _checkTextures(self) -> bool:
        """Check if all required textures exist in Texture Hub"""
        missingTextures = []
        for blockType, blockDef in BLOCK_DEFINITIONS.items():
            for textureName in [blockDef.textureTop, blockDef.textureSide, blockDef.textureBottom]:
                texturePath = os.path.join(TEXTURES_DIR, textureName)
                if not os.path.exists(texturePath):
                    missingTextures.append(textureName)
        
        if missingTextures:
            print(f"Missing textures: {set(missingTextures)}")
            return False
        return True
    
    def _loadTextures(self):
        """Load all texture files into memory"""
        textureFiles = set()
        for blockDef in BLOCK_DEFINITIONS.values():
            textureFiles.add(blockDef.textureTop)
            textureFiles.add(blockDef.textureSide)
            textureFiles.add(blockDef.textureBottom)
            if blockDef.textureFront:
                textureFiles.add(blockDef.textureFront)
        
        for textureName in textureFiles:
            texturePath = os.path.join(TEXTURES_DIR, textureName)
            if os.path.exists(texturePath):
                self.textures[textureName] = pygame.image.load(texturePath).convert_alpha()
        
        # Load animation frames for liquids
        self._loadAnimationFrames()
    
    def _loadAnimationFrames(self):
        """Load animation frames from water_flow.png, lava_flow.png, and nether_portal.png"""
        # Water flow texture is 32x1024 (32 frames of 32x32)
        waterPath = os.path.join(TEXTURES_DIR, "water_flow.png")
        if os.path.exists(waterPath):
            waterSheet = pygame.image.load(waterPath).convert_alpha()
            frameSize = waterSheet.get_width()  # 32
            numFrames = waterSheet.get_height() // frameSize
            for i in range(numFrames):
                frame = waterSheet.subsurface((0, i * frameSize, frameSize, frameSize))
                # Apply water tint
                tintedFrame = self._tintLiquid(frame, WATER_TINT)
                self.waterFrames.append(tintedFrame)
        
        # Lava flow texture is 32x512 (16 frames of 32x32)
        lavaPath = os.path.join(TEXTURES_DIR, "lava_flow.png")
        if os.path.exists(lavaPath):
            lavaSheet = pygame.image.load(lavaPath).convert_alpha()
            frameSize = lavaSheet.get_width()  # 32
            numFrames = lavaSheet.get_height() // frameSize
            for i in range(numFrames):
                frame = lavaSheet.subsurface((0, i * frameSize, frameSize, frameSize))
                # Apply lava tint
                tintedFrame = self._tintLiquid(frame, LAVA_TINT)
                self.lavaFrames.append(tintedFrame)
        
        # Nether portal texture - vertical strip of 16x16 frames
        portalPath = os.path.join(TEXTURES_DIR, "nether_portal.png")
        if os.path.exists(portalPath):
            portalSheet = pygame.image.load(portalPath).convert_alpha()
            frameWidth = portalSheet.get_width()  # 16
            frameHeight = frameWidth  # 16x16 frames
            numFrames = portalSheet.get_height() // frameHeight
            if numFrames > 0:
                for i in range(numFrames):
                    frame = portalSheet.subsurface((0, i * frameHeight, frameWidth, frameHeight))
                    self.portalFrames.append(frame)
                print(f"    Loaded {len(self.portalFrames)} portal animation frames")
        
        # Load portal ambient sound
        portalSoundPath = os.path.join(SOUNDS_DIR, "portal", "portal.ogg")
        if os.path.exists(portalSoundPath):
            try:
                self.portalAmbientSound = pygame.mixer.Sound(portalSoundPath)
                self.portalAmbientSound.set_volume(0.3)
                print("    Loaded portal ambient sound")
            except Exception as e:
                print(f"    Could not load portal sound: {e}")
        
        # Load end portal texture from entity folder (256x256 starfield)
        # Load end portal texture from entity folder (256x256 starfield) for parallax effect
        endPortalPath = os.path.join(ENTITY_DIR, "end_portal.png")
        if os.path.exists(endPortalPath):
            self.endPortalTexture = pygame.image.load(endPortalPath).convert_alpha()
            # Define parallax layers with different speeds and tints
            # Each layer scrolls at different speed for depth effect
            self.endPortalLayers = [
                {"speed": 0.3, "tint": (20, 10, 40), "alpha": 255},      # Bottom layer - dark, slow
                {"speed": 0.6, "tint": (60, 30, 100), "alpha": 200},     # Middle layer - purple, medium
                {"speed": 1.0, "tint": (120, 80, 180), "alpha": 150},    # Upper layer - bright purple, fast
                {"speed": 1.5, "tint": (200, 180, 255), "alpha": 100},   # Top layer - white/pink stars, fastest
            ]
            print(f"    Loaded end portal texture with {len(self.endPortalLayers)} parallax layers")
        
        # Load fire animation frames from fire_0.png (16x512 = 32 frames of 16x16)
        firePath = os.path.join(TEXTURES_DIR, "fire_0.png")
        if os.path.exists(firePath):
            fireSheet = pygame.image.load(firePath).convert_alpha()
            frameWidth = fireSheet.get_width()  # 16
            frameHeight = frameWidth  # 16x16 frames
            numFrames = fireSheet.get_height() // frameHeight
            # Use the frame order from mcmeta (16-31, then 0-15)
            frameOrder = list(range(16, 32)) + list(range(0, 16))
            for idx in frameOrder:
                if idx < numFrames:
                    frame = fireSheet.subsurface((0, idx * frameHeight, frameWidth, frameHeight))
                    self.fireFrames.append(frame)
            print(f"    Loaded {len(self.fireFrames)} fire animation frames")
        
        # Load soul fire animation frames from soul_fire_0.png
        soulFirePath = os.path.join(TEXTURES_DIR, "soul_fire_0.png")
        if os.path.exists(soulFirePath):
            soulFireSheet = pygame.image.load(soulFirePath).convert_alpha()
            frameWidth = soulFireSheet.get_width()  # 16
            frameHeight = frameWidth  # 16x16 frames
            numFrames = soulFireSheet.get_height() // frameHeight
            frameOrder = list(range(16, min(32, numFrames))) + list(range(0, min(16, numFrames)))
            for idx in frameOrder:
                if idx < numFrames:
                    frame = soulFireSheet.subsurface((0, idx * frameHeight, frameWidth, frameHeight))
                    self.soulFireFrames.append(frame)
            print(f"    Loaded {len(self.soulFireFrames)} soul fire animation frames")
        
        # Load chest textures from entity/chest folder and extract faces
        chestDir = os.path.join(ENTITY_DIR, "chest")
        if os.path.exists(chestDir):
            chestFiles = ["normal.png", "ender.png", "trapped.png", "christmas.png",
                         "copper.png", "copper_exposed.png", "copper_weathered.png", "copper_oxidized.png"]
            for chestFile in chestFiles:
                chestPath = os.path.join(chestDir, chestFile)
                if os.path.exists(chestPath):
                    self.chestTextures[chestFile] = pygame.image.load(chestPath).convert_alpha()
            print(f"    Loaded {len(self.chestTextures)} chest textures")
            
            # Extract chest face textures from UV maps
            # Chest UV layout (128x128 texture, coordinates scaled from 64x64 standard):
            # Top: (28, 0) size 14x14 -> scale by 2 for 128x128
            # Front (bottom part): (28, 33) size 14x10
            # Side: (0, 33) size 14x10
            self._extractChestFaces()
    
    def _extractChestFaces(self):
        """Extract top, front, and side textures from chest UV maps"""
        # Mapping of chest texture file to block types
        chestMapping = {
            "normal.png": BlockType.CHEST,
            "ender.png": BlockType.ENDER_CHEST,
            "trapped.png": BlockType.TRAPPED_CHEST,
            "christmas.png": BlockType.CHRISTMAS_CHEST,
            "copper.png": BlockType.COPPER_CHEST,
            "copper_exposed.png": BlockType.COPPER_CHEST_EXPOSED,
            "copper_weathered.png": BlockType.COPPER_CHEST_WEATHERED,
            "copper_oxidized.png": BlockType.COPPER_CHEST_OXIDIZED,
        }
        
        # UV coordinates for 128x128 chest texture (doubled from standard 64x64)
        # These are approximate based on Minecraft's chest model
        scale = 2  # 128/64
        
        # Top lid face: starts at (28, 0), size 14x14 in 64x64 coords
        topX, topY = 28 * scale, 0 * scale
        topW, topH = 14 * scale, 14 * scale
        
        # Front face (bottom chest body): starts at (28, 33), size 14x10
        frontX, frontY = 28 * scale, 33 * scale
        frontW, frontH = 14 * scale, 10 * scale
        
        # Side face: starts at (0, 33), size 14x10
        sideX, sideY = 0 * scale, 33 * scale
        sideW, sideH = 14 * scale, 10 * scale
        
        # Latch/clasp: starts at (1, 1), size 2x4 in 64x64 coords
        latchX, latchY = 1 * scale, 1 * scale
        latchW, latchH = 2 * scale, 4 * scale
        
        for chestFile, blockType in chestMapping.items():
            if chestFile in self.chestTextures:
                tex = self.chestTextures[chestFile]
                texW, texH = tex.get_size()
                
                # Extract faces with bounds checking
                try:
                    # Top face
                    if topX + topW <= texW and topY + topH <= texH:
                        topFace = tex.subsurface((topX, topY, topW, topH))
                        # Scale to 16x16
                        topFace = pygame.transform.scale(topFace, (16, 16))
                    else:
                        topFace = None
                    
                    # Front face (with latch detail)
                    if frontX + frontW <= texW and frontY + frontH <= texH:
                        frontFace = tex.subsurface((frontX, frontY, frontW, frontH))
                        # Scale to 16x16
                        frontFace = pygame.transform.scale(frontFace, (16, 16))
                        
                        # Extract and overlay the latch/clasp on the front face
                        if latchX + latchW <= texW and latchY + latchH <= texH:
                            latchFace = tex.subsurface((latchX, latchY, latchW, latchH))
                            # Scale latch proportionally (about 2x4 pixels -> scale to fit)
                            latchScaled = pygame.transform.scale(latchFace, (2, 4))
                            # Position latch at center-top of front face
                            latchPosX = (16 - 2) // 2  # Center horizontally
                            latchPosY = 0  # Top of front face
                            frontFace.blit(latchScaled, (latchPosX, latchPosY))
                    else:
                        frontFace = None
                    
                    # Side face
                    if sideX + sideW <= texW and sideY + sideH <= texH:
                        sideFace = tex.subsurface((sideX, sideY, sideW, sideH))
                        # Scale to 16x16
                        sideFace = pygame.transform.scale(sideFace, (16, 16))
                    else:
                        sideFace = None
                    
                    # Store extracted faces as regular textures
                    baseName = chestFile.replace(".png", "")
                    if topFace:
                        self.textures[f"chest_{baseName}_top.png"] = topFace
                    if frontFace:
                        self.textures[f"chest_{baseName}_front.png"] = frontFace
                    if sideFace:
                        self.textures[f"chest_{baseName}_side.png"] = sideFace
                        
                except Exception as e:
                    print(f"    Warning: Could not extract faces from {chestFile}: {e}")
    
    def updateAnimation(self, dt: int):
        """Update liquid animation frames based on elapsed time"""
        self.animationTimer += dt
        
        if self.animationTimer >= self.animationSpeed:
            self.animationTimer = 0
            
            # Advance water frame
            if self.waterFrames:
                self.currentWaterFrame = (self.currentWaterFrame + 1) % len(self.waterFrames)
                # Recreate water sprite with new frame (level 8 = source)
                frame = self.waterFrames[self.currentWaterFrame]
                self.blockSprites[BlockType.WATER] = self._createLiquidBlock(
                    frame, frame, frame, isWater=True, level=8
                )
            
            # Advance lava frame (slower than water)
            if self.lavaFrames and self.currentWaterFrame % 2 == 0:
                self.currentLavaFrame = (self.currentLavaFrame + 1) % len(self.lavaFrames)
                # Recreate lava sprite with new frame
                frame = self.lavaFrames[self.currentLavaFrame]
                self.blockSprites[BlockType.LAVA] = self._createLiquidBlock(
                    frame, frame, frame, isWater=False, level=8
                )
        
        # Update portal animation (separate timer for slower animation)
        self.portalAnimationTimer += dt
        if self.portalAnimationTimer >= self.portalAnimationSpeed:
            self.portalAnimationTimer = 0
            if self.portalFrames:
                self.currentPortalFrame = (self.currentPortalFrame + 1) % len(self.portalFrames)
                # Recreate portal sprite with new frame
                frame = self.portalFrames[self.currentPortalFrame]
                self.blockSprites[BlockType.NETHER_PORTAL] = self._createPortalBlock(frame)
        
        # Update end portal animation (parallax scrolling layers)
        self.endPortalAnimationTimer += dt
        if self.endPortalAnimationTimer >= self.endPortalAnimationSpeed:
            self.endPortalAnimationTimer = 0
            self.endPortalScrollOffset += 1.0
            if self.endPortalScrollOffset > 256:
                self.endPortalScrollOffset = 0
            # Recreate end portal sprites with new scroll offset
            if self.endPortalTexture:
                self.blockSprites[BlockType.END_PORTAL] = self._createEndPortalBlock(isGateway=False)
                self.blockSprites[BlockType.END_GATEWAY] = self._createEndPortalBlock(isGateway=True)
        
        # Update fire animation
        self.fireAnimationTimer += dt
        if self.fireAnimationTimer >= self.fireAnimationSpeed:
            self.fireAnimationTimer = 0
            if self.fireFrames:
                self.currentFireFrame = (self.currentFireFrame + 1) % len(self.fireFrames)
                # Recreate fire sprite with new frame
                frame = self.fireFrames[self.currentFireFrame]
                self.blockSprites[BlockType.FIRE] = self._createFireBlock(frame)
            if self.soulFireFrames:
                soulFrame = self.soulFireFrames[self.currentFireFrame % len(self.soulFireFrames)]
                self.blockSprites[BlockType.SOUL_FIRE] = self._createFireBlock(soulFrame, isSoulFire=True)
        
        # Update spawner particles
        self.spawnerParticleTimer += dt
        if self.spawnerParticleTimer >= self.spawnerParticleSpeed:
            self.spawnerParticleTimer = 0
            # Update existing particles
            for particle in self.spawnerParticles[:]:
                particle["life"] -= 1
                particle["px"] += particle["vx"]
                particle["py"] += particle["vy"]
                particle["vy"] -= 0.1  # Float upward
                if particle["life"] <= 0:
                    self.spawnerParticles.remove(particle)
        
        # Initialize oxidizing copper sprite if not done yet
        if not self.oxidizingCopperInitialized:
            tex = self.textures.get("copper_block.png")
            if tex:
                self.blockSprites[BlockType.OXIDIZING_COPPER] = self._createIsometricBlock(tex, tex, tex)
                self.oxidizingCopperInitialized = True
        
        # Update oxidizing copper (slow oxidation) - stops at fully oxidized
        if self.oxidizingCopperStage < 3:  # Only animate if not fully oxidized
            self.oxidizingCopperTimer += dt
            if self.oxidizingCopperTimer >= self.oxidizingCopperSpeed:
                self.oxidizingCopperTimer = 0
                self.oxidizingCopperStage += 1  # Advance to next stage (max 3)
                # Update the oxidizing copper sprite with new stage texture
                texName = self.copperStageTextures[self.oxidizingCopperStage]
                tex = self.textures.get(texName)
                if tex:
                    self.blockSprites[BlockType.OXIDIZING_COPPER] = self._createIsometricBlock(tex, tex, tex)
    
    def _createBlockSprites(self):
        """Create isometric block sprites from textures"""
        for blockType, blockDef in BLOCK_DEFINITIONS.items():
            topTex = self.textures.get(blockDef.textureTop)
            sideTex = self.textures.get(blockDef.textureSide)
            frontTex = self.textures.get(blockDef.textureFront) if blockDef.textureFront else sideTex
            
            # Apply tinting for grass and leaves (grayscale textures in vanilla)
            if topTex and blockDef.tintTop:
                # Use leaves tint for leaf blocks, grass tint for grass
                tint = LEAVES_TINT if "leaves" in blockDef.textureTop else GRASS_TINT
                topTex = self._tintTexture(topTex, tint)
            
            if sideTex and blockDef.tintSide:
                tint = LEAVES_TINT if "leaves" in blockDef.textureSide else GRASS_TINT
                sideTex = self._tintTexture(sideTex, tint)
            
            # Also tint front texture for leaves (right face)
            if frontTex and blockDef.tintSide:
                tint = LEAVES_TINT if "leaves" in (blockDef.textureFront or blockDef.textureSide) else GRASS_TINT
                frontTex = self._tintTexture(frontTex, tint)
            
            # Apply water/lava tinting
            if blockDef.isLiquid:
                if blockType == BlockType.WATER:
                    if topTex:
                        topTex = self._tintLiquid(topTex, WATER_TINT)
                    if sideTex:
                        sideTex = self._tintLiquid(sideTex, WATER_TINT)
                    if frontTex:
                        frontTex = self._tintLiquid(frontTex, WATER_TINT)
                elif blockType == BlockType.LAVA:
                    if topTex:
                        topTex = self._tintLiquid(topTex, LAVA_TINT)
                    if sideTex:
                        sideTex = self._tintLiquid(sideTex, LAVA_TINT)
                    if frontTex:
                        frontTex = self._tintLiquid(frontTex, LAVA_TINT)
            
            # Handle special block types
            if blockDef.isThin:
                # Thin blocks like doors - create open/closed variants
                # Store default (closed) as the main sprite
                self.blockSprites[blockType] = self._createDoorBlock(
                    topTex, sideTex, frontTex, Facing.SOUTH, isOpen=False
                )
                # Create open and closed variants
                for isOpen in [False, True]:
                    sprite = self._createDoorBlock(topTex, sideTex, frontTex, Facing.SOUTH, isOpen)
                    self.doorSprites[(blockType, isOpen)] = sprite
            elif blockDef.isStair:
                # Stair blocks - create all facing variants
                self.blockSprites[blockType] = self._createStairBlock(
                    topTex, sideTex, frontTex, Facing.SOUTH
                )
                # Create all stair variants
                for facing in Facing:
                    sprite = self._createStairBlock(topTex, sideTex, frontTex, facing)
                    self.stairSprites[(blockType, facing)] = sprite
            elif blockDef.isSlab:
                # Slab blocks - create top and bottom variants
                self.blockSprites[blockType] = self._createSlabBlock(
                    topTex, sideTex, frontTex, SlabPosition.BOTTOM
                )
                # Create both slab variants
                for position in SlabPosition:
                    sprite = self._createSlabBlock(topTex, sideTex, frontTex, position)
                    self.slabSprites[(blockType, position)] = sprite
            elif blockDef.isLiquid:
                # Liquid blocks - slightly lower than full block
                self.blockSprites[blockType] = self._createLiquidBlock(
                    topTex, sideTex, frontTex, blockType == BlockType.WATER
                )
            elif blockDef.isPortal:
                # Portal blocks - use animated frames
                if blockType == BlockType.NETHER_PORTAL:
                    if self.portalFrames:
                        self.blockSprites[blockType] = self._createPortalBlock(self.portalFrames[0])
                    else:
                        self.blockSprites[blockType] = self._createPortalBlock(topTex)
                elif blockType in (BlockType.END_PORTAL, BlockType.END_GATEWAY):
                    # End portal and gateway use parallax layered animation
                    if self.endPortalTexture:
                        isGateway = (blockType == BlockType.END_GATEWAY)
                        self.blockSprites[blockType] = self._createEndPortalBlock(isGateway=isGateway)
                    else:
                        self.blockSprites[blockType] = self._createIsometricBlock(topTex, sideTex, frontTex, True)
                else:
                    # Fallback to static texture if no frames loaded
                    self.blockSprites[blockType] = self._createPortalBlock(topTex)
            elif blockType == BlockType.FIRE:
                # Fire uses animated frames
                if self.fireFrames:
                    self.blockSprites[blockType] = self._createFireBlock(self.fireFrames[0])
                else:
                    self.blockSprites[blockType] = self._createIsometricBlock(topTex, sideTex, frontTex, True)
            elif blockType == BlockType.SOUL_FIRE:
                # Soul fire uses animated frames
                if self.soulFireFrames:
                    self.blockSprites[blockType] = self._createFireBlock(self.soulFireFrames[0], isSoulFire=True)
                else:
                    self.blockSprites[blockType] = self._createIsometricBlock(topTex, sideTex, frontTex, True)
            elif blockType in (BlockType.CHEST, BlockType.ENDER_CHEST, BlockType.TRAPPED_CHEST, 
                              BlockType.CHRISTMAS_CHEST, BlockType.COPPER_CHEST, BlockType.COPPER_CHEST_EXPOSED,
                              BlockType.COPPER_CHEST_WEATHERED, BlockType.COPPER_CHEST_OXIDIZED):
                # Chest blocks - use extracted chest face textures with latch
                chestName = {
                    BlockType.CHEST: "normal",
                    BlockType.ENDER_CHEST: "ender",
                    BlockType.TRAPPED_CHEST: "trapped",
                    BlockType.CHRISTMAS_CHEST: "christmas",
                    BlockType.COPPER_CHEST: "copper",
                    BlockType.COPPER_CHEST_EXPOSED: "copper_exposed",
                    BlockType.COPPER_CHEST_WEATHERED: "copper_weathered",
                    BlockType.COPPER_CHEST_OXIDIZED: "copper_oxidized",
                }.get(blockType, "normal")
                
                # Latch colors per chest type
                latchColors = {
                    "normal": (80, 60, 40),      # Brown/gold
                    "ender": (40, 80, 60),       # Green-ish
                    "trapped": (120, 80, 40),    # Orange-gold
                    "christmas": (200, 40, 40),  # Red
                    "copper": (180, 100, 60),    # Copper
                    "copper_exposed": (160, 110, 80),
                    "copper_weathered": (100, 130, 100),
                    "copper_oxidized": (60, 140, 130),
                }
                latchColor = latchColors.get(chestName, (80, 60, 40))
                
                chestTop = self.textures.get(f"chest_{chestName}_top.png")
                chestFront = self.textures.get(f"chest_{chestName}_front.png")
                chestSide = self.textures.get(f"chest_{chestName}_side.png")
                
                if chestTop and chestFront and chestSide:
                    # Use dedicated chest method with latch
                    # Left face = side texture, Right face = front texture
                    self.blockSprites[blockType] = self._createChestBlock(chestTop, chestSide, chestFront, latchColor)
                else:
                    # Fallback to regular block
                    self.blockSprites[blockType] = self._createIsometricBlock(topTex, sideTex, frontTex, False)
            else:
                # Regular full block (skip OXIDIZING_COPPER - handled in updateAnimation)
                if blockType != BlockType.OXIDIZING_COPPER:
                    self.blockSprites[blockType] = self._createIsometricBlock(
                        topTex, sideTex, frontTex, blockDef.transparent
                    )
    
    def _tintTexture(self, texture: pygame.Surface, tint: Tuple[int, int, int]) -> pygame.Surface:
        """Apply a color tint to a grayscale texture (like Minecraft biome coloring)"""
        tinted = texture.copy()
        tinted.lock()
        
        for y in range(texture.get_height()):
            for x in range(texture.get_width()):
                color = texture.get_at((x, y))
                # Use the grayscale value as intensity multiplier
                intensity = color.r / 255.0  # Grayscale, so r=g=b
                newR = int(tint[0] * intensity)
                newG = int(tint[1] * intensity)
                newB = int(tint[2] * intensity)
                tinted.set_at((x, y), (newR, newG, newB, color.a))
        
        tinted.unlock()
        return tinted
    
    def _tintLiquid(self, texture: pygame.Surface, tint: Tuple[int, int, int]) -> pygame.Surface:
        """Apply a color tint to liquid textures (water/lava) while preserving original brightness patterns"""
        tinted = texture.copy()
        tinted.lock()
        
        for y in range(texture.get_height()):
            for x in range(texture.get_width()):
                color = texture.get_at((x, y))
                # Calculate brightness from original color
                brightness = (color.r + color.g + color.b) / (3.0 * 255.0)
                # Apply tint with brightness
                newR = int(min(255, tint[0] * brightness * 1.5))
                newG = int(min(255, tint[1] * brightness * 1.5))
                newB = int(min(255, tint[2] * brightness * 1.5))
                tinted.set_at((x, y), (newR, newG, newB, color.a))
        
        tinted.unlock()
        return tinted
    
    def _createIsometricBlock(self, topTexture: pygame.Surface, 
                              leftTexture: pygame.Surface,
                              rightTexture: pygame.Surface,
                              transparent: bool = False) -> pygame.Surface:
        """
        Create an isometric block sprite from three face textures.
        Uses a cleaner texture mapping approach.
        """
        W = TILE_WIDTH
        H = TILE_HEIGHT + BLOCK_HEIGHT
        halfW = W // 2
        halfH = TILE_HEIGHT // 2
        
        surface = pygame.Surface((W, H), pygame.SRCALPHA)
        
        # Scale textures to match our block dimensions for better quality
        texW = halfW  # Each face spans half width
        texH = BLOCK_HEIGHT  # Side faces are this tall
        
        if topTexture:
            topTex = pygame.transform.smoothscale(topTexture, (texW, texW))
        else:
            topTex = pygame.Surface((texW, texW))
            topTex.fill((100, 100, 100))
        
        if leftTexture:
            leftTex = pygame.transform.smoothscale(leftTexture, (texW, texH))
        else:
            leftTex = pygame.Surface((texW, texH))
            leftTex.fill((80, 80, 80))
            
        if rightTexture:
            rightTex = pygame.transform.smoothscale(rightTexture, (texW, texH))
        else:
            rightTex = pygame.Surface((texW, texH))
            rightTex.fill((60, 60, 60))
        
        # Define face polygons
        topPoints = [(halfW, 0), (W-1, halfH), (halfW, TILE_HEIGHT-1), (0, halfH)]
        leftPoints = [(0, halfH), (halfW, TILE_HEIGHT-1), (halfW, H-1), (0, halfH + BLOCK_HEIGHT)]
        rightPoints = [(halfW, TILE_HEIGHT-1), (W-1, halfH), (W-1, halfH + BLOCK_HEIGHT), (halfW, H-1)]
        
        # For opaque blocks, fill with average colors first to prevent gaps
        if not transparent:
            topAvg = self._getAverageColor(topTex)
            leftAvg = self._darkenColor(self._getAverageColor(leftTex), 0.7)
            rightAvg = self._darkenColor(self._getAverageColor(rightTex), 0.85)
            pygame.draw.polygon(surface, topAvg, topPoints)
            pygame.draw.polygon(surface, leftAvg, leftPoints)
            pygame.draw.polygon(surface, rightAvg, rightPoints)
        
        # TOP FACE - isometric diamond
        for py in range(TILE_HEIGHT):
            # Calculate horizontal span for this row
            if py <= halfH:
                spanRatio = py / halfH if halfH > 0 else 0
            else:
                spanRatio = (TILE_HEIGHT - py) / halfH if halfH > 0 else 0
            
            span = int(halfW * spanRatio)
            if span <= 0:
                continue
                
            leftX = halfW - span
            rightX = halfW + span
            
            for px in range(leftX, rightX):
                # Map to texture coordinates using isometric transform
                # Convert screen (px, py) to texture (u, v)
                relX = px - halfW
                relY = py - halfH
                
                # Inverse isometric projection
                u = (relX / halfW + relY / halfH) * 0.5 + 0.5
                v = (-relX / halfW + relY / halfH) * 0.5 + 0.5
                
                texX = int(u * (texW - 1))
                texY = int(v * (texW - 1))
                
                texX = max(0, min(texW - 1, texX))
                texY = max(0, min(texW - 1, texY))
                
                color = topTex.get_at((texX, texY))
                if color.a > 0:
                    surface.set_at((px, py), color)
        
        # LEFT FACE - parallelogram (side view)
        for px in range(halfW):
            topY = halfH + int((px / halfW) * halfH)
            bottomY = min(topY + BLOCK_HEIGHT, H)
            
            for py in range(topY, bottomY):
                texX = int((px / halfW) * (texW - 1))
                texY = int(((py - topY) / BLOCK_HEIGHT) * (texH - 1))
                
                texX = max(0, min(texW - 1, texX))
                texY = max(0, min(texH - 1, texY))
                
                color = leftTex.get_at((texX, texY))
                if color.a > 0:
                    shade = 0.8 if transparent else 0.7
                    shaded = (int(color.r * shade), int(color.g * shade), 
                             int(color.b * shade), color.a)
                    surface.set_at((px, py), shaded)
        
        # RIGHT FACE - parallelogram (front view)
        for px in range(halfW, W):
            relX = px - halfW
            topY = TILE_HEIGHT - 1 - int((relX / halfW) * halfH)
            bottomY = min(topY + BLOCK_HEIGHT, H)
            
            for py in range(max(0, topY), bottomY):
                texX = int((relX / halfW) * (texW - 1))
                texY = int(((py - topY) / BLOCK_HEIGHT) * (texH - 1))
                
                texX = max(0, min(texW - 1, texX))
                texY = max(0, min(texH - 1, texY))
                
                color = rightTex.get_at((texX, texY))
                if color.a > 0:
                    shade = 0.9 if transparent else 0.85
                    shaded = (int(color.r * shade), int(color.g * shade),
                             int(color.b * shade), color.a)
                    surface.set_at((px, py), shaded)
        
        # Draw subtle outlines for definition (thinner, less prominent)
        if transparent:
            outlineColor = (80, 80, 80, 100)
        else:
            outlineColor = (50, 50, 50)
        # Only draw key edges, not full polygons
        pygame.draw.line(surface, outlineColor, topPoints[0], topPoints[1], 1)
        pygame.draw.line(surface, outlineColor, topPoints[0], topPoints[3], 1)
        pygame.draw.line(surface, outlineColor, leftPoints[2], leftPoints[3], 1)
        pygame.draw.line(surface, outlineColor, rightPoints[2], rightPoints[3], 1)
        
        return surface
    
    def _createChestBlock(self, topTexture: pygame.Surface,
                          sideTexture: pygame.Surface,
                          frontTexture: pygame.Surface,
                          latchColor: Tuple[int, int, int] = (80, 60, 40)) -> pygame.Surface:
        """
        Create an isometric chest block with a visible latch on the front.
        The latch is drawn as a small metal nib protruding from the front face.
        """
        W = TILE_WIDTH
        H = TILE_HEIGHT + BLOCK_HEIGHT
        halfW = W // 2
        halfH = TILE_HEIGHT // 2
        
        # First create the base block
        surface = self._createIsometricBlock(topTexture, sideTexture, frontTexture, False)
        
        # Now draw the latch (metal nib) on the front/right face
        # The latch should be a small 3D protrusion in the middle of the front
        # Front face spans from (halfW, TILE_HEIGHT-1-halfH) to (W-1, TILE_HEIGHT-1+halfH)
        
        # Calculate center position on the right face
        # The right face top-left corner is at (halfW, halfH) sloping to (W, TILE_HEIGHT)
        # Center horizontally: 3/4 across the face from left edge
        latchCenterX = halfW + int(halfW * 0.5)
        
        # Vertical center: middle of the face
        # At latchCenterX, the top edge y is: TILE_HEIGHT - 1 - (relX/halfW)*halfH
        relX = latchCenterX - halfW
        faceTopY = TILE_HEIGHT - 1 - int((relX / halfW) * halfH)
        latchCenterY = faceTopY + BLOCK_HEIGHT // 2
        
        # Draw a small metal latch nib - a 3x4 pixel protrusion
        latchW, latchH = 3, 5
        latchX = latchCenterX - latchW // 2
        latchY = latchCenterY - latchH // 2
        
        # Brighter top/front, darker sides - metal look
        latchBright = (min(255, latchColor[0] + 40), min(255, latchColor[1] + 30), min(255, latchColor[2] + 20))
        latchDark = (max(0, latchColor[0] - 20), max(0, latchColor[1] - 20), max(0, latchColor[2] - 20))
        
        # Draw the latch as a small rectangle with shading
        for dy in range(latchH):
            for dx in range(latchW):
                px = latchX + dx
                py = latchY + dy
                if 0 <= px < W and 0 <= py < H:
                    # Shade based on position
                    if dy == 0:  # Top edge - brightest
                        color = latchBright
                    elif dx == 0:  # Left edge - darker
                        color = latchDark
                    else:  # Body
                        color = latchColor
                    surface.set_at((px, py), color)
        
        # Add a small highlight on the latch
        if latchW > 1 and latchH > 1:
            highlight = (min(255, latchColor[0] + 60), min(255, latchColor[1] + 50), min(255, latchColor[2] + 40))
            surface.set_at((latchX + 1, latchY + 1), highlight)
        
        return surface
    
    def _getAverageColor(self, surface: pygame.Surface) -> Tuple[int, int, int]:
        """Get the average color of a surface"""
        totalR, totalG, totalB = 0, 0, 0
        count = 0
        
        for x in range(surface.get_width()):
            for y in range(surface.get_height()):
                color = surface.get_at((x, y))
                totalR += color.r
                totalG += color.g
                totalB += color.b
                count += 1
        
        if count == 0:
            return (128, 128, 128)
        
        return (totalR // count, totalG // count, totalB // count)
    
    def _darkenColor(self, color: Tuple[int, int, int], factor: float) -> Tuple[int, int, int]:
        """Darken a color by a factor"""
        return (
            int(color[0] * factor),
            int(color[1] * factor),
            int(color[2] * factor)
        )
    
    def _renderVoxelBox(self, surface: pygame.Surface,
                        boxX: float, boxY: float, boxZ: float,
                        boxW: float, boxH: float, boxD: float,
                        topTex: pygame.Surface = None,
                        sideTex: pygame.Surface = None,
                        frontTex: pygame.Surface = None,
                        baseOffsetX: int = 0, baseOffsetY: int = 0) -> None:
        """
        Render a 3D box in isometric view onto a surface.
        This is the core renderer - like Minecraft's block model system.
        
        Box coordinates are in "voxel space" (0-16 range like Minecraft):
        - boxX, boxY, boxZ: position of box corner (0-16)
        - boxW: width (X axis - goes to the right in iso)
        - boxH: height (Y axis - goes up)  
        - boxD: depth (Z axis - goes to the left in iso)
        
        baseOffsetX/Y: pixel offset for where to render on the surface
        """
        # Convert voxel coordinates to pixel coordinates
        # In isometric: X goes right-down, Z goes left-down, Y goes up
        VOXEL_SCALE = TILE_WIDTH / 16.0  # pixels per voxel unit
        
        # Calculate pixel dimensions
        pxW = boxW * VOXEL_SCALE / 2  # half because isometric
        pxD = boxD * VOXEL_SCALE / 2
        pxH = boxH * (BLOCK_HEIGHT / 16.0)  # height scaling
        
        # Calculate the top-center point of this box in screen space
        # Start from the block's top center, then offset by box position
        centerX = baseOffsetX + TILE_WIDTH // 2
        centerY = baseOffsetY + TILE_HEIGHT // 2
        
        # Apply voxel position offset (isometric projection)
        # X moves right-down, Z moves left-down
        isoOffX = (boxX - boxZ) * (VOXEL_SCALE / 4)
        isoOffY = (boxX + boxZ) * (VOXEL_SCALE / 8) - boxY * (BLOCK_HEIGHT / 16.0)
        
        topCenterX = centerX + isoOffX
        topCenterY = centerY + isoOffY
        
        # Scale textures to 16x16 if provided
        texSize = 16
        if topTex:
            topTex = pygame.transform.scale(topTex, (texSize, texSize))
        if sideTex:
            sideTex = pygame.transform.scale(sideTex, (texSize, texSize))
        if frontTex:
            frontTex = pygame.transform.scale(frontTex, (texSize, texSize))
        else:
            frontTex = sideTex
        
        # Get colors for fallback
        topColor = self._getAverageColor(topTex) if topTex else (128, 128, 128)
        sideColor = self._darkenColor(self._getAverageColor(sideTex) if sideTex else (100, 100, 100), 0.7)
        frontColor = self._darkenColor(self._getAverageColor(frontTex) if frontTex else (100, 100, 100), 0.85)
        
        # Calculate face corners in screen space
        # TOP FACE (diamond shape)
        topPts = [
            (topCenterX, topCenterY - pxD - pxW + pxD + pxW),  # top
            (topCenterX + pxW, topCenterY - pxD + pxW),  # right
            (topCenterX, topCenterY + pxD + pxW - pxD - pxW + pxD * 2 + pxW * 2 - pxD - pxW),  # Recalc
            (topCenterX - pxD, topCenterY - pxW + pxD),  # left
        ]
        
        # Simpler approach - calculate corners directly
        halfW = int(pxW)
        halfD = int(pxD)
        h = int(pxH)
        cx = int(topCenterX)
        cy = int(topCenterY)
        
        # Top face diamond
        topPts = [
            (cx, cy - halfD - halfW // 2),  # top point
            (cx + halfW, cy - halfD // 2),  # right point  
            (cx, cy + halfD - halfW // 2 + halfW),  # bottom point
            (cx - halfD, cy + halfW // 2 - halfW // 2),  # left point
        ]
        
        # Actually let's use a cleaner calculation
        # Top diamond corners
        top = (cx, cy - int((halfD + halfW) / 2))
        right = (cx + halfW, cy + int((halfW - halfD) / 2))
        bottom = (cx, cy + int((halfD + halfW) / 2))
        left = (cx - halfD, cy + int((halfD - halfW) / 2))
        
        topPts = [top, right, bottom, left]
        
        # Left face (parallelogram going down from left edge of top)
        leftPts = [
            left,
            bottom,
            (bottom[0], bottom[1] + h),
            (left[0], left[1] + h)
        ]
        
        # Right face (parallelogram going down from right edge of top)
        rightPts = [
            bottom,
            right,
            (right[0], right[1] + h),
            (bottom[0], bottom[1] + h)
        ]
        
        # Draw faces with solid colors first, then texture
        pygame.draw.polygon(surface, topColor, topPts)
        pygame.draw.polygon(surface, sideColor, leftPts)
        pygame.draw.polygon(surface, frontColor, rightPts)
        
        # Apply textures using scanline fill
        if topTex and halfW > 0 and halfD > 0:
            # Top face texture mapping
            minY = min(p[1] for p in topPts)
            maxY = max(p[1] for p in topPts)
            minX = min(p[0] for p in topPts)
            maxX = max(p[0] for p in topPts)
            
            for py in range(int(minY), int(maxY) + 1):
                for px in range(int(minX), int(maxX) + 1):
                    # Check if point is inside diamond
                    relX = px - cx
                    relY = py - cy
                    # Diamond test
                    if halfW > 0 and halfD > 0:
                        t1 = abs(relX / halfW + relY / ((halfD + halfW) / 2))
                        t2 = abs(relX / halfW - relY / ((halfD + halfW) / 2))
                        if t1 <= 1 and t2 <= 1:
                            # Map to texture UV
                            u = (relX / halfW + relY / halfD) * 0.5 + 0.5 if halfD > 0 else 0.5
                            v = (-relX / halfW + relY / halfD) * 0.5 + 0.5 if halfD > 0 else 0.5
                            texX = max(0, min(texSize - 1, int(u * (texSize - 1))))
                            texY = max(0, min(texSize - 1, int(v * (texSize - 1))))
                            try:
                                color = topTex.get_at((texX, texY))
                                if color.a > 0:
                                    surface.set_at((px, py), color)
                            except:
                                pass
        
        # Left face texture
        if sideTex and halfD > 0 and h > 0:
            for px in range(int(left[0]), int(bottom[0]) + 1):
                if halfD == 0:
                    continue
                ratio = (px - left[0]) / halfD if halfD > 0 else 0
                topY = int(left[1] + ratio * (bottom[1] - left[1]))
                bottomY = topY + h
                for py in range(topY, bottomY + 1):
                    texX = int(ratio * (texSize - 1))
                    texY = int(((py - topY) / h) * (texSize - 1)) if h > 0 else 0
                    texX = max(0, min(texSize - 1, texX))
                    texY = max(0, min(texSize - 1, texY))
                    try:
                        color = sideTex.get_at((texX, texY))
                        if color.a > 0:
                            r, g, b = int(color.r * 0.7), int(color.g * 0.7), int(color.b * 0.7)
                            surface.set_at((px, py), (r, g, b, 255))
                    except:
                        pass
        
        # Right face texture
        if frontTex and halfW > 0 and h > 0:
            for px in range(int(bottom[0]), int(right[0]) + 1):
                if halfW == 0:
                    continue
                ratio = (px - bottom[0]) / halfW if halfW > 0 else 0
                topY = int(bottom[1] - ratio * (bottom[1] - right[1]))
                bottomY = topY + h
                for py in range(topY, bottomY + 1):
                    texX = int(ratio * (texSize - 1))
                    texY = int(((py - topY) / h) * (texSize - 1)) if h > 0 else 0
                    texX = max(0, min(texSize - 1, texX))
                    texY = max(0, min(texSize - 1, texY))
                    try:
                        color = frontTex.get_at((texX, texY))
                        if color.a > 0:
                            r, g, b = int(color.r * 0.85), int(color.g * 0.85), int(color.b * 0.85)
                            surface.set_at((px, py), (r, g, b, 255))
                    except:
                        pass

    def _createDoorBlock(self, topTexture: pygame.Surface, 
                         sideTexture: pygame.Surface,
                         frontTexture: pygame.Surface,
                         facing: Facing = Facing.SOUTH,
                         isOpen: bool = False) -> pygame.Surface:
        """
        Create a door as a thin 3D panel using the 'Texture Surgery' method:
        - Render as two stacked half-blocks (top half + bottom half)
        - Use edge pixel sampling for the thin side faces
        - Clamp UVs to prevent wrapping artifacts
        """
        W = TILE_WIDTH          # 64
        halfW = W // 2          # 32
        halfH = TILE_HEIGHT // 2  # 16
        blockH = BLOCK_HEIGHT     # 38 (one block)
        doorH = blockH * 2        # 76 (two blocks tall)
        H = TILE_HEIGHT + doorH   # Total sprite height
        texSize = 16
        thickness = 3  # Door thickness in screen pixels
        
        surface = pygame.Surface((W, H), pygame.SRCALPHA)
        
        # Prepare textures - top half and bottom half of door
        topHalfTex = pygame.transform.smoothscale(topTexture, (texSize, texSize)) if topTexture else None
        botHalfTex = pygame.transform.smoothscale(sideTexture, (texSize, texSize)) if sideTexture else None
        
        if topHalfTex is None:
            topHalfTex = pygame.Surface((texSize, texSize))
            topHalfTex.fill((139, 90, 43))  # Wood brown
        if botHalfTex is None:
            botHalfTex = topHalfTex.copy()
        
        # EDGE PIXEL SAMPLING: Get the edge column for door thickness
        # This creates a matching "hinge" color from the texture edge
        edgeColor = topHalfTex.get_at((0, texSize // 2))
        edgeColorDark = (int(edgeColor.r * 0.5), int(edgeColor.g * 0.5), int(edgeColor.b * 0.5))
        
        # Top cap color from average
        topCapColor = self._getAverageColor(topHalfTex)
        
        if not isOpen:
            # ===== CLOSED DOOR: Faces RIGHT (standard isometric right face) =====
            
            # Draw from back to front for proper layering
            # 1. TOP CAP (thin strip at very top)
            for px in range(halfW - thickness, W):
                if px < halfW:
                    capY = halfH + int(((halfW - px) / thickness) * 2)
                else:
                    relX = px - halfW
                    capY = TILE_HEIGHT - 1 - int((relX / halfW) * halfH) - thickness
                capY = max(0, min(H - thickness, capY))
                for py in range(capY, min(capY + thickness, H)):
                    surface.set_at((px, py), topCapColor)
            
            # 2. MAIN FACE (right-facing panel with two texture halves)
            for px in range(halfW, W):
                relX = px - halfW
                colTop = TILE_HEIGHT - 1 - int((relX / halfW) * halfH)
                
                # Draw full door height at this column
                for py in range(max(0, colTop), min(colTop + doorH, H)):
                    # UV mapping with clamping
                    u = relX / halfW
                    u = max(0.01, min(0.99, u))  # Clamp to avoid edge bleeding
                    
                    # Determine which texture half to use
                    doorProgress = (py - colTop) / doorH
                    if doorProgress < 0.5:
                        # Top half of door
                        v = doorProgress * 2  # 0-1 within top half
                        v = max(0.01, min(0.99, v))
                        texX = int(u * (texSize - 1))
                        texY = int(v * (texSize - 1))
                        color = topHalfTex.get_at((texX, texY))
                    else:
                        # Bottom half of door  
                        v = (doorProgress - 0.5) * 2  # 0-1 within bottom half
                        v = max(0.01, min(0.99, v))
                        texX = int(u * (texSize - 1))
                        texY = int(v * (texSize - 1))
                        color = botHalfTex.get_at((texX, texY))
                    
                    if color.a > 32:
                        r = int(color.r * 0.85)
                        g = int(color.g * 0.85)
                        b = int(color.b * 0.85)
                        surface.set_at((px, py), (r, g, b, 255))
            
            # 3. THICKNESS EDGE (left side, using edge pixel color)
            for px in range(halfW - thickness, halfW):
                t = (px - (halfW - thickness)) / thickness
                colTop = TILE_HEIGHT - 1 + int((1 - t) * thickness)
                for py in range(max(0, colTop), min(colTop + doorH, H)):
                    surface.set_at((px, py), edgeColorDark)
        
        else:
            # ===== OPEN DOOR: Faces LEFT (swung open 90 degrees) =====
            
            # 1. TOP CAP
            for px in range(0, halfW + thickness):
                if px < halfW:
                    capY = halfH + int((px / halfW) * halfH) - thickness
                else:
                    capY = TILE_HEIGHT - 1 - int(((px - halfW) / thickness) * 2) - thickness
                capY = max(0, min(H - thickness, capY))
                for py in range(capY, min(capY + thickness, H)):
                    surface.set_at((px, py), topCapColor)
            
            # 2. MAIN FACE (left-facing panel)
            for px in range(halfW):
                colTop = halfH + int((px / halfW) * halfH)
                
                for py in range(max(0, colTop), min(colTop + doorH, H)):
                    u = px / halfW
                    u = max(0.01, min(0.99, u))
                    
                    doorProgress = (py - colTop) / doorH
                    if doorProgress < 0.5:
                        v = doorProgress * 2
                        v = max(0.01, min(0.99, v))
                        texX = int(u * (texSize - 1))
                        texY = int(v * (texSize - 1))
                        color = topHalfTex.get_at((texX, texY))
                    else:
                        v = (doorProgress - 0.5) * 2
                        v = max(0.01, min(0.99, v))
                        texX = int(u * (texSize - 1))
                        texY = int(v * (texSize - 1))
                        color = botHalfTex.get_at((texX, texY))
                    
                    if color.a > 32:
                        r = int(color.r * 0.7)
                        g = int(color.g * 0.7)
                        b = int(color.b * 0.7)
                        surface.set_at((px, py), (r, g, b, 255))
            
            # 3. THICKNESS EDGE (right side)
            for px in range(halfW, halfW + thickness):
                t = (px - halfW) / thickness
                colTop = TILE_HEIGHT - 1 - int(t * thickness)
                for py in range(max(0, colTop), min(colTop + doorH, H)):
                    surface.set_at((px, py), edgeColorDark)
        
        return surface
    
    def _createThinBlock(self, topTexture: pygame.Surface, 
                         sideTexture: pygame.Surface,
                         frontTexture: pygame.Surface,
                         transparent: bool = False) -> pygame.Surface:
        """Legacy method - redirects to _createDoorBlock for backwards compatibility"""
        return self._createDoorBlock(topTexture, sideTexture, frontTexture, Facing.SOUTH, False)
    
    def _createStairBlock(self, topTexture: pygame.Surface, 
                          sideTexture: pygame.Surface,
                          frontTexture: pygame.Surface,
                          facing: Facing = Facing.SOUTH) -> pygame.Surface:
        """
        THE LEGO METHOD: Render stairs as two simple primitives.
        
        Component A: Base slab (full 1x1 width, 0.5 height) at ground level
        Component B: Back step (full 1x1 width, 0.5 height) raised up
        
        The engine knows how to draw cubes perfectly. By faking a stair as 
        two simple slabs, we bypass all complex geometry math.
        Rotation = moving the top slab to different quadrant positions.
        """
        W = TILE_WIDTH            # 64
        halfW = W // 2            # 32
        halfH = TILE_HEIGHT // 2  # 16
        fullH = BLOCK_HEIGHT      # 38
        slabH = fullH // 2        # 19
        H = TILE_HEIGHT + fullH   # 70
        texSize = 16
        
        surface = pygame.Surface((W, H), pygame.SRCALPHA)
        
        # Prepare textures
        topTex = pygame.transform.smoothscale(topTexture, (texSize, texSize)) if topTexture else None
        sideTex = pygame.transform.smoothscale(sideTexture, (texSize, texSize)) if sideTexture else None
        
        if topTex is None:
            topTex = pygame.Surface((texSize, texSize))
            topTex.fill((128, 128, 128))
        if sideTex is None:
            sideTex = topTex.copy()
            
        # Get base colors for filling
        topAvg = self._getAverageColor(topTex)
        sideAvgLeft = self._darkenColor(self._getAverageColor(sideTex), 0.7)
        sideAvgRight = self._darkenColor(self._getAverageColor(sideTex), 0.85)
        
        # ===== SIMPLE SLAB RENDERER =====
        def renderSlab(yOff, height, drawLeft=True, drawRight=True, drawTop=True):
            """Render a simple full-width slab at yOff with given height"""
            # TOP FACE
            if drawTop:
                for py in range(TILE_HEIGHT):
                    if py <= halfH:
                        span = int(halfW * (py / halfH))
                    else:
                        span = int(halfW * ((TILE_HEIGHT - py) / halfH))
                    for px in range(halfW - span, halfW + span):
                        relX = px - halfW
                        relY = py - halfH
                        u = (relX / halfW + relY / halfH) * 0.5 + 0.5
                        v = (-relX / halfW + relY / halfH) * 0.5 + 0.5
                        u, v = max(0, min(1, u)), max(0, min(1, v))
                        tx, ty = int(u * (texSize-1)), int(v * (texSize-1))
                        c = topTex.get_at((tx, ty))
                        if c.a > 0:
                            dy = yOff + py
                            if 0 <= dy < H:
                                surface.set_at((px, dy), c)
            
            # LEFT FACE
            if drawLeft:
                for px in range(halfW):
                    top = yOff + halfH + int((px / halfW) * halfH)
                    for py in range(top, min(top + height, H)):
                        u = px / halfW
                        v = (py - top) / height if height > 0 else 0
                        u, v = max(0, min(1, u)), max(0, min(1, v))
                        tx, ty = int(u * (texSize-1)), int(v * (texSize-1))
                        c = sideTex.get_at((tx, ty))
                        if c.a > 0:
                            r, g, b = int(c.r * 0.7), int(c.g * 0.7), int(c.b * 0.7)
                            surface.set_at((px, py), (r, g, b, 255))
            
            # RIGHT FACE
            if drawRight:
                for px in range(halfW, W):
                    rx = px - halfW
                    top = yOff + TILE_HEIGHT - 1 - int((rx / halfW) * halfH)
                    for py in range(max(0, top), min(top + height, H)):
                        u = rx / halfW
                        v = (py - top) / height if height > 0 else 0
                        u, v = max(0, min(1, u)), max(0, min(1, v))
                        tx, ty = int(u * (texSize-1)), int(v * (texSize-1))
                        c = sideTex.get_at((tx, ty))
                        if c.a > 0:
                            r, g, b = int(c.r * 0.85), int(c.g * 0.85), int(c.b * 0.85)
                            surface.set_at((px, py), (r, g, b, 255))
        
        # ===== HALF-WIDTH STEP RENDERER =====
        def renderHalfStep(side, yOff, height):
            """
            Render a half-width step on left or right side.
            side: 'left' or 'right'
            """
            if side == 'left':
                # Left half - TOP
                for py in range(TILE_HEIGHT):
                    if py <= halfH:
                        span = int(halfW * (py / halfH))
                    else:
                        span = int(halfW * ((TILE_HEIGHT - py) / halfH))
                    for px in range(halfW - span, halfW):
                        relX = px - halfW
                        relY = py - halfH
                        u = (relX / halfW + relY / halfH) * 0.5 + 0.5
                        v = (-relX / halfW + relY / halfH) * 0.5 + 0.5
                        u, v = max(0, min(1, u)), max(0, min(1, v))
                        tx, ty = int(u * (texSize-1)), int(v * (texSize-1))
                        c = topTex.get_at((tx, ty))
                        if c.a > 0:
                            dy = yOff + py
                            if 0 <= dy < H:
                                surface.set_at((px, dy), c)
                # Left half - LEFT FACE (full)
                for px in range(halfW):
                    top = yOff + halfH + int((px / halfW) * halfH)
                    for py in range(top, min(top + height, H)):
                        u = px / halfW
                        v = (py - top) / height if height > 0 else 0
                        u, v = max(0, min(1, u)), max(0, min(1, v))
                        tx, ty = int(u * (texSize-1)), int(v * (texSize-1))
                        c = sideTex.get_at((tx, ty))
                        if c.a > 0:
                            r, g, b = int(c.r * 0.7), int(c.g * 0.7), int(c.b * 0.7)
                            surface.set_at((px, py), (r, g, b, 255))
                # Riser face at center
                for py in range(yOff + halfH, min(yOff + halfH + height, H)):
                    for px in range(halfW - 2, halfW + 2):
                        if 0 <= px < W:
                            surface.set_at((px, py), sideAvgRight)
            else:
                # Right half - TOP
                for py in range(TILE_HEIGHT):
                    if py <= halfH:
                        span = int(halfW * (py / halfH))
                    else:
                        span = int(halfW * ((TILE_HEIGHT - py) / halfH))
                    for px in range(halfW, halfW + span):
                        relX = px - halfW
                        relY = py - halfH
                        u = (relX / halfW + relY / halfH) * 0.5 + 0.5
                        v = (-relX / halfW + relY / halfH) * 0.5 + 0.5
                        u, v = max(0, min(1, u)), max(0, min(1, v))
                        tx, ty = int(u * (texSize-1)), int(v * (texSize-1))
                        c = topTex.get_at((tx, ty))
                        if c.a > 0:
                            dy = yOff + py
                            if 0 <= dy < H:
                                surface.set_at((px, dy), c)
                # Right half - RIGHT FACE (full)
                for px in range(halfW, W):
                    rx = px - halfW
                    top = yOff + TILE_HEIGHT - 1 - int((rx / halfW) * halfH)
                    for py in range(max(0, top), min(top + height, H)):
                        u = rx / halfW
                        v = (py - top) / height if height > 0 else 0
                        u, v = max(0, min(1, u)), max(0, min(1, v))
                        tx, ty = int(u * (texSize-1)), int(v * (texSize-1))
                        c = sideTex.get_at((tx, ty))
                        if c.a > 0:
                            r, g, b = int(c.r * 0.85), int(c.g * 0.85), int(c.b * 0.85)
                            surface.set_at((px, py), (r, g, b, 255))
                # Riser face at center
                for py in range(yOff + halfH, min(yOff + halfH + height, H)):
                    for px in range(halfW - 2, halfW + 2):
                        if 0 <= px < W:
                            surface.set_at((px, py), sideAvgLeft)
        
        # ===== BACK/FRONT HALF RENDERER =====
        def renderBackHalf(yOff, height):
            """Render back half of block (top portion of sprite)"""
            # TOP - back half only
            for py in range(halfH + 1):
                span = int(halfW * (py / halfH)) if halfH > 0 else 0
                for px in range(halfW - span, halfW + span):
                    relX = px - halfW
                    relY = py - halfH
                    u = (relX / halfW + relY / halfH) * 0.5 + 0.5
                    v = (-relX / halfW + relY / halfH) * 0.5 + 0.5
                    u, v = max(0, min(1, u)), max(0, min(1, v))
                    tx, ty = int(u * (texSize-1)), int(v * (texSize-1))
                    c = topTex.get_at((tx, ty))
                    if c.a > 0:
                        dy = yOff + py
                        if 0 <= dy < H:
                            surface.set_at((px, dy), c)
            # LEFT FACE - back portion
            for px in range(halfW):
                top = yOff + int((px / halfW) * halfH)
                for py in range(max(0, top), min(top + height, H)):
                    u = px / halfW
                    v = (py - top) / height if height > 0 else 0
                    u, v = max(0, min(1, u)), max(0, min(1, v))
                    tx, ty = int(u * (texSize-1)), int(v * (texSize-1))
                    c = sideTex.get_at((tx, ty))
                    if c.a > 0:
                        r, g, b = int(c.r * 0.7), int(c.g * 0.7), int(c.b * 0.7)
                        surface.set_at((px, py), (r, g, b, 255))
            # RIGHT FACE - back portion
            for px in range(halfW, W):
                rx = px - halfW
                top = yOff + halfH - int((rx / halfW) * halfH)
                for py in range(max(0, top), min(top + height, H)):
                    u = rx / halfW
                    v = (py - top) / height if height > 0 else 0
                    u, v = max(0, min(1, u)), max(0, min(1, v))
                    tx, ty = int(u * (texSize-1)), int(v * (texSize-1))
                    c = sideTex.get_at((tx, ty))
                    if c.a > 0:
                        r, g, b = int(c.r * 0.85), int(c.g * 0.85), int(c.b * 0.85)
                        surface.set_at((px, py), (r, g, b, 255))
            # Front riser
            for px in range(W):
                if px < halfW:
                    ry = yOff + int((px / halfW) * halfH)
                else:
                    ry = yOff + halfH - int(((px - halfW) / halfW) * halfH)
                for py in range(ry, min(ry + height, H)):
                    surface.set_at((px, py), sideAvgRight)
        
        def renderFrontHalf(yOff, height):
            """Render front half of block (bottom portion of sprite)"""
            # TOP - front half only
            for py in range(halfH, TILE_HEIGHT):
                span = int(halfW * ((TILE_HEIGHT - py) / halfH)) if halfH > 0 else 0
                for px in range(halfW - span, halfW + span):
                    relX = px - halfW
                    relY = py - halfH
                    u = (relX / halfW + relY / halfH) * 0.5 + 0.5
                    v = (-relX / halfW + relY / halfH) * 0.5 + 0.5
                    u, v = max(0, min(1, u)), max(0, min(1, v))
                    tx, ty = int(u * (texSize-1)), int(v * (texSize-1))
                    c = topTex.get_at((tx, ty))
                    if c.a > 0:
                        dy = yOff + py
                        if 0 <= dy < H:
                            surface.set_at((px, dy), c)
            # LEFT + RIGHT FACES (full height from front edge)
            for px in range(halfW):
                top = yOff + halfH + int((px / halfW) * halfH)
                for py in range(top, min(top + height, H)):
                    u = px / halfW
                    v = (py - top) / height if height > 0 else 0
                    u, v = max(0, min(1, u)), max(0, min(1, v))
                    tx, ty = int(u * (texSize-1)), int(v * (texSize-1))
                    c = sideTex.get_at((tx, ty))
                    if c.a > 0:
                        r, g, b = int(c.r * 0.7), int(c.g * 0.7), int(c.b * 0.7)
                        surface.set_at((px, py), (r, g, b, 255))
            for px in range(halfW, W):
                rx = px - halfW
                top = yOff + TILE_HEIGHT - 1 - int((rx / halfW) * halfH)
                for py in range(max(0, top), min(top + height, H)):
                    u = rx / halfW
                    v = (py - top) / height if height > 0 else 0
                    u, v = max(0, min(1, u)), max(0, min(1, v))
                    tx, ty = int(u * (texSize-1)), int(v * (texSize-1))
                    c = sideTex.get_at((tx, ty))
                    if c.a > 0:
                        r, g, b = int(c.r * 0.85), int(c.g * 0.85), int(c.b * 0.85)
                        surface.set_at((px, py), (r, g, b, 255))
        
        # ===== RENDER BASED ON FACING =====
        # LEGO principle: Draw back-to-front for correct occlusion
        
        if facing == Facing.SOUTH:
            # Step in back: draw bottom slab, then back step on top
            renderSlab(slabH, slabH)    # Bottom slab
            renderBackHalf(0, slabH)    # Top step at back
            
        elif facing == Facing.NORTH:
            # Step in front: draw back slab, then front step
            renderSlab(0, slabH, drawLeft=False, drawRight=False)  # Back slab (top only)
            renderFrontHalf(0, fullH)   # Front step (full height)
            
        elif facing == Facing.WEST:
            # Step on left: draw right slab, then left step
            renderHalfStep('right', slabH, slabH)  # Right half slab
            renderHalfStep('left', 0, fullH)       # Left step (full height)
            
        else:  # EAST
            # Step on right: draw left slab, then right step
            renderHalfStep('left', slabH, slabH)   # Left half slab
            renderHalfStep('right', 0, fullH)      # Right step (full height)
        
        return surface
    
    def _createHalfBlock(self, topTexture: pygame.Surface, 
                         sideTexture: pygame.Surface,
                         frontTexture: pygame.Surface) -> pygame.Surface:
        """
        Create a half-height block (like a slab) for use in stairs.
        Uses same rendering approach as _createBlock but with half height.
        """
        W = TILE_WIDTH
        halfW = W // 2
        halfH = TILE_HEIGHT // 2
        blockH = BLOCK_HEIGHT // 2  # Half the normal block height
        H = TILE_HEIGHT + blockH
        
        surface = pygame.Surface((W, H), pygame.SRCALPHA)
        
        # Scale textures
        texSize = 16
        if topTexture:
            topTex = pygame.transform.scale(topTexture, (texSize, texSize))
        else:
            topTex = pygame.Surface((texSize, texSize))
            topTex.fill((128, 128, 128))
        
        if sideTexture:
            sideTex = pygame.transform.scale(sideTexture, (texSize, texSize))
        else:
            sideTex = topTex.copy()
        
        if frontTexture:
            frontTex = pygame.transform.scale(frontTexture, (texSize, texSize))
        else:
            frontTex = sideTex.copy()
        
        # Get colors
        topAvg = self._getAverageColor(topTex)
        leftAvg = self._darkenColor(self._getAverageColor(sideTex), 0.7)
        rightAvg = self._darkenColor(self._getAverageColor(frontTex), 0.85)
        
        # Define face polygons
        topPts = [(halfW, 0), (W-1, halfH), (halfW, TILE_HEIGHT-1), (0, halfH)]
        leftPts = [(0, halfH), (halfW, TILE_HEIGHT-1), (halfW, TILE_HEIGHT-1+blockH), (0, halfH+blockH)]
        rightPts = [(halfW, TILE_HEIGHT-1), (W-1, halfH), (W-1, halfH+blockH), (halfW, TILE_HEIGHT-1+blockH)]
        
        # Fill base colors
        pygame.draw.polygon(surface, topAvg, topPts)
        pygame.draw.polygon(surface, leftAvg, leftPts)
        pygame.draw.polygon(surface, rightAvg, rightPts)
        
        # TOP FACE texture mapping
        for py in range(TILE_HEIGHT):
            if py <= halfH:
                spanRatio = py / halfH if halfH > 0 else 0
            else:
                spanRatio = (TILE_HEIGHT - py) / halfH if halfH > 0 else 0
            span = int(halfW * spanRatio)
            if span <= 0:
                continue
            for px in range(halfW - span, halfW + span):
                relX = px - halfW
                relY = py - halfH
                u = (relX / halfW + relY / halfH) * 0.5 + 0.5 if halfW > 0 and halfH > 0 else 0.5
                v = (-relX / halfW + relY / halfH) * 0.5 + 0.5 if halfW > 0 and halfH > 0 else 0.5
                texX = max(0, min(texSize-1, int(u * (texSize-1))))
                texY = max(0, min(texSize-1, int(v * (texSize-1))))
                color = topTex.get_at((texX, texY))
                if color.a > 0:
                    surface.set_at((px, py), color)
        
        # LEFT FACE texture mapping
        for px in range(halfW):
            topY = halfH + int((px / halfW) * halfH) if halfW > 0 else halfH
            for py in range(topY, topY + blockH):
                texX = int((px / halfW) * (texSize-1)) if halfW > 0 else 0
                texY = int(((py - topY) / blockH) * (texSize-1)) if blockH > 0 else 0
                texX = max(0, min(texSize-1, texX))
                texY = max(0, min(texSize-1, texY))
                color = sideTex.get_at((texX, texY))
                if color.a > 0:
                    shaded = (int(color.r*0.7), int(color.g*0.7), int(color.b*0.7), 255)
                    surface.set_at((px, py), shaded)
        
        # RIGHT FACE texture mapping
        for px in range(halfW, W):
            relX = px - halfW
            topY = TILE_HEIGHT - 1 - int((relX / halfW) * halfH) if halfW > 0 else halfH
            for py in range(max(0, topY), topY + blockH):
                texX = int((relX / halfW) * (texSize-1)) if halfW > 0 else 0
                texY = int(((py - topY) / blockH) * (texSize-1)) if blockH > 0 else 0
                texX = max(0, min(texSize-1, texX))
                texY = max(0, min(texSize-1, texY))
                color = frontTex.get_at((texX, texY))
                if color.a > 0:
                    shaded = (int(color.r*0.85), int(color.g*0.85), int(color.b*0.85), 255)
                    surface.set_at((px, py), shaded)
        
        return surface
    
    def _pointInPolygon(self, x: float, y: float, polygon: list) -> bool:
        """Simple point-in-polygon test using ray casting"""
        n = len(polygon)
        inside = False
        j = n - 1
        for i in range(n):
            xi, yi = polygon[i]
            xj, yj = polygon[j]
            if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
                inside = not inside
            j = i
        return inside
    
    def _createSlabBlock(self, topTexture: pygame.Surface, 
                         sideTexture: pygame.Surface,
                         frontTexture: pygame.Surface,
                         position: SlabPosition = SlabPosition.BOTTOM) -> pygame.Surface:
        """
        Create a slab block (half-height block).
        Position determines if slab sits at bottom or top of the block space.
        Uses actual texture mapping with polygon fill.
        """
        W = TILE_WIDTH
        H = TILE_HEIGHT + BLOCK_HEIGHT
        halfW = W // 2
        halfH = TILE_HEIGHT // 2
        slabH = BLOCK_HEIGHT // 2  # Half the normal block height
        
        surface = pygame.Surface((W, H), pygame.SRCALPHA)
        
        # Scale textures
        texSize = 16
        if topTexture:
            topTex = pygame.transform.scale(topTexture, (texSize, texSize))
        else:
            topTex = None
        if sideTexture:
            sideTex = pygame.transform.scale(sideTexture, (texSize, texSize))
        else:
            sideTex = None
        if frontTexture:
            frontTex = pygame.transform.scale(frontTexture, (texSize, texSize))
        else:
            frontTex = sideTex
        
        # Get colors from texture for polygon fills
        if topTexture:
            baseColor = self._getAverageColor(topTexture)
        else:
            baseColor = (128, 128, 128)
        
        topColor = baseColor
        leftColor = self._darkenColor(baseColor, 0.7)
        rightColor = self._darkenColor(baseColor, 0.85)
        
        # Vertical offset depends on position
        # BOTTOM: slab sits at bottom (offset = slabH to push top face down)
        # TOP: slab sits at top (offset = 0, top face at normal position)
        if position == SlabPosition.BOTTOM:
            vOffset = slabH
        else:  # TOP
            vOffset = 0
        
        # TOP FACE - texture mapped diamond
        topPoints = [(halfW, vOffset), (W-1, halfH + vOffset), (halfW, TILE_HEIGHT - 1 + vOffset), (0, halfH + vOffset)]
        pygame.draw.polygon(surface, topColor, topPoints)
        
        # Texture map the top face
        for py in range(int(TILE_HEIGHT)):
            if py <= halfH:
                spanRatio = py / halfH if halfH > 0 else 0
            else:
                spanRatio = (TILE_HEIGHT - py) / halfH if halfH > 0 else 0
            
            span = int(halfW * spanRatio)
            if span <= 0:
                continue
            
            leftX = halfW - span
            rightX = halfW + span
            
            for px in range(leftX, rightX):
                relX = px - halfW
                relY = py - halfH
                
                u = (relX / halfW + relY / halfH) * 0.5 + 0.5
                v = (-relX / halfW + relY / halfH) * 0.5 + 0.5
                
                if topTex:
                    texX = int(u * (texSize - 1))
                    texY = int(v * (texSize - 1))
                    texX = max(0, min(texSize - 1, texX))
                    texY = max(0, min(texSize - 1, texY))
                    color = topTex.get_at((texX, texY))
                    surface.set_at((px, py + vOffset), color)
        
        # LEFT FACE - texture mapped
        leftPoints = [(0, halfH + vOffset), (halfW, TILE_HEIGHT - 1 + vOffset), 
                     (halfW, TILE_HEIGHT - 1 + vOffset + slabH), (0, halfH + vOffset + slabH)]
        pygame.draw.polygon(surface, leftColor, leftPoints)
        
        for px in range(halfW):
            topY = halfH + int((px / halfW) * halfH) if halfW > 0 else halfH
            bottomY = topY + slabH
            
            for py in range(topY + vOffset, bottomY + vOffset):
                texX = int((px / halfW) * (texSize - 1)) if halfW > 0 else 0
                texY = int(((py - topY - vOffset) / slabH) * (texSize // 2 - 1)) if slabH > 0 else 0
                texX = max(0, min(texSize - 1, texX))
                texY = max(0, min(texSize - 1, texY))
                
                if sideTex:
                    color = sideTex.get_at((texX, texY))
                    r = int(color.r * 0.7)
                    g = int(color.g * 0.7)
                    b = int(color.b * 0.7)
                    surface.set_at((px, py), (r, g, b, color.a))
        
        # RIGHT FACE - texture mapped
        rightPoints = [(halfW, TILE_HEIGHT - 1 + vOffset), (W-1, halfH + vOffset), 
                      (W-1, halfH + vOffset + slabH), (halfW, TILE_HEIGHT - 1 + vOffset + slabH)]
        pygame.draw.polygon(surface, rightColor, rightPoints)
        
        for px in range(halfW, W):
            relX = px - halfW
            topY = TILE_HEIGHT - 1 - int((relX / halfW) * halfH) if halfW > 0 else halfH
            bottomY = topY + slabH
            
            for py in range(max(0, topY + vOffset), bottomY + vOffset):
                texX = int((relX / halfW) * (texSize - 1)) if halfW > 0 else 0
                texY = int(((py - topY - vOffset) / slabH) * (texSize // 2 - 1)) if slabH > 0 else 0
                texX = max(0, min(texSize - 1, texX))
                texY = max(0, min(texSize - 1, texY))
                
                if frontTex:
                    color = frontTex.get_at((texX, texY))
                    r = int(color.r * 0.85)
                    g = int(color.g * 0.85)
                    b = int(color.b * 0.85)
                    surface.set_at((px, py), (r, g, b, color.a))
        
        # Outlines for definition
        outlineColor = (50, 50, 50)
        pygame.draw.line(surface, outlineColor, topPoints[0], topPoints[1], 1)
        pygame.draw.line(surface, outlineColor, topPoints[0], topPoints[3], 1)
        pygame.draw.line(surface, outlineColor, leftPoints[2], leftPoints[3], 1)
        pygame.draw.line(surface, outlineColor, rightPoints[2], rightPoints[3], 1)
        
        return surface
    
    def _createLiquidBlock(self, topTexture: pygame.Surface, 
                           leftTexture: pygame.Surface,
                           rightTexture: pygame.Surface,
                           isWater: bool = False,
                           level: int = 8) -> pygame.Surface:
        """
        Create a liquid block sprite (water/lava) at a specific level.
        Level 8 = source/full, Level 1 = lowest flow.
        Uses actual texture mapping for animated look.
        """
        W = TILE_WIDTH
        H = TILE_HEIGHT + BLOCK_HEIGHT
        halfW = W // 2
        halfH = TILE_HEIGHT // 2
        
        # Height based on level (8 = full, 1 = 1/8 height)
        liquidHeight = int(BLOCK_HEIGHT * (level / 8.0) * 0.9)
        if liquidHeight < 4:
            liquidHeight = 4  # Minimum visible height
        
        surface = pygame.Surface((W, H), pygame.SRCALPHA)
        alpha = 180 if isWater else 255
        topOffset = BLOCK_HEIGHT - liquidHeight
        
        # Scale textures if provided
        texSize = 16  # Standard Minecraft texture size
        if topTexture:
            topTex = pygame.transform.scale(topTexture, (texSize, texSize))
        else:
            topTex = None
            
        if leftTexture:
            leftTex = pygame.transform.scale(leftTexture, (texSize, texSize))
        else:
            leftTex = None
            
        if rightTexture:
            rightTex = pygame.transform.scale(rightTexture, (texSize, texSize))
        else:
            rightTex = None
        
        # Default colors if no textures
        defaultColor = (63, 118, 228) if isWater else (207, 92, 15)
        
        # TOP FACE - texture mapped diamond
        for py in range(int(TILE_HEIGHT)):
            if py <= halfH:
                spanRatio = py / halfH if halfH > 0 else 0
            else:
                spanRatio = (TILE_HEIGHT - py) / halfH if halfH > 0 else 0
            
            span = int(halfW * spanRatio)
            if span <= 0:
                continue
            
            leftX = halfW - span
            rightX = halfW + span
            
            for px in range(leftX, rightX):
                relX = px - halfW
                relY = py - halfH
                
                # Inverse isometric projection
                u = (relX / halfW + relY / halfH) * 0.5 + 0.5
                v = (-relX / halfW + relY / halfH) * 0.5 + 0.5
                
                if topTex:
                    texX = int(u * (texSize - 1))
                    texY = int(v * (texSize - 1))
                    texX = max(0, min(texSize - 1, texX))
                    texY = max(0, min(texSize - 1, texY))
                    color = topTex.get_at((texX, texY))
                    surface.set_at((px, py + topOffset), (color.r, color.g, color.b, alpha))
                else:
                    surface.set_at((px, py + topOffset), (*defaultColor, alpha))
        
        # LEFT FACE - texture mapped
        for px in range(halfW):
            topY = halfH + int((px / halfW) * halfH) if halfW > 0 else halfH
            bottomY = min(topY + liquidHeight, H)
            
            for py in range(topY + topOffset, bottomY + topOffset):
                texX = int((px / halfW) * (texSize - 1)) if halfW > 0 else 0
                texY = int(((py - topY - topOffset) / liquidHeight) * (texSize - 1)) if liquidHeight > 0 else 0
                texX = max(0, min(texSize - 1, texX))
                texY = max(0, min(texSize - 1, texY))
                
                if leftTex:
                    color = leftTex.get_at((texX, texY))
                    # Darken for left face
                    r = int(color.r * 0.75)
                    g = int(color.g * 0.75)
                    b = int(color.b * 0.75)
                    surface.set_at((px, py), (r, g, b, alpha))
                else:
                    dc = self._darkenColor(defaultColor, 0.75)
                    surface.set_at((px, py), (*dc, alpha))
        
        # RIGHT FACE - texture mapped
        for px in range(halfW, W):
            relX = px - halfW
            topY = TILE_HEIGHT - 1 - int((relX / halfW) * halfH) if halfW > 0 else halfH
            bottomY = min(topY + liquidHeight, H)
            
            for py in range(max(0, topY + topOffset), bottomY + topOffset):
                texX = int((relX / halfW) * (texSize - 1)) if halfW > 0 else 0
                texY = int(((py - topY - topOffset) / liquidHeight) * (texSize - 1)) if liquidHeight > 0 else 0
                texX = max(0, min(texSize - 1, texX))
                texY = max(0, min(texSize - 1, texY))
                
                if rightTex:
                    color = rightTex.get_at((texX, texY))
                    # Slight darken for right face
                    r = int(color.r * 0.9)
                    g = int(color.g * 0.9)
                    b = int(color.b * 0.9)
                    surface.set_at((px, py), (r, g, b, alpha))
                else:
                    dc = self._darkenColor(defaultColor, 0.9)
                    surface.set_at((px, py), (*dc, alpha))
        
        return surface
    
    def _createPortalBlock(self, portalTexture: pygame.Surface) -> pygame.Surface:
        """
        Create an isometric nether portal block sprite.
        Portal is rendered as a thin vertical plane with transparency.
        """
        W = TILE_WIDTH
        H = TILE_HEIGHT + BLOCK_HEIGHT
        halfW = W // 2
        halfH = TILE_HEIGHT // 2
        
        surface = pygame.Surface((W, H), pygame.SRCALPHA)
        
        # Portal is semi-transparent
        alpha = 200
        
        # Scale texture
        texSize = 16
        if portalTexture:
            portalTex = pygame.transform.scale(portalTexture, (texSize, texSize))
        else:
            portalTex = None
        
        # Portal purple color fallback
        portalColor = (138, 43, 226)
        
        # Render portal as a thin vertical plane facing the viewer (similar to door)
        # But portal fills the full block space with a swirling texture
        
        # TOP FACE - thin sliver to show it's a flat plane
        topThickness = 3
        for py in range(halfH - topThickness, halfH + topThickness):
            for px in range(halfW - 2, halfW + 2):
                if portalTex:
                    texX = int(((px - halfW + 2) / 4) * (texSize - 1))
                    texY = int(((py - halfH + topThickness) / (topThickness * 2)) * (texSize - 1))
                    texX = max(0, min(texSize - 1, texX))
                    texY = max(0, min(texSize - 1, texY))
                    color = portalTex.get_at((texX, texY))
                    surface.set_at((px, py), (color.r, color.g, color.b, alpha))
                else:
                    surface.set_at((px, py), (*portalColor, alpha))
        
        # LEFT FACE - main visible portal face
        for px in range(halfW):
            topY = halfH + int((px / halfW) * halfH) if halfW > 0 else halfH
            bottomY = topY + BLOCK_HEIGHT
            
            for py in range(topY, min(bottomY, H)):
                texX = int((px / halfW) * (texSize - 1)) if halfW > 0 else 0
                texY = int(((py - topY) / BLOCK_HEIGHT) * (texSize - 1)) if BLOCK_HEIGHT > 0 else 0
                texX = max(0, min(texSize - 1, texX))
                texY = max(0, min(texSize - 1, texY))
                
                if portalTex:
                    color = portalTex.get_at((texX, texY))
                    # Darken slightly for depth
                    r = int(color.r * 0.85)
                    g = int(color.g * 0.85)
                    b = int(color.b * 0.85)
                    surface.set_at((px, py), (r, g, b, alpha))
                else:
                    dc = self._darkenColor(portalColor, 0.85)
                    surface.set_at((px, py), (*dc, alpha))
        
        # RIGHT FACE - other visible portal face
        for px in range(halfW, W):
            relX = px - halfW
            topY = TILE_HEIGHT - 1 - int((relX / halfW) * halfH) if halfW > 0 else halfH
            bottomY = topY + BLOCK_HEIGHT
            
            for py in range(max(0, topY), min(bottomY, H)):
                texX = int((relX / halfW) * (texSize - 1)) if halfW > 0 else 0
                texY = int(((py - topY) / BLOCK_HEIGHT) * (texSize - 1)) if BLOCK_HEIGHT > 0 else 0
                texX = max(0, min(texSize - 1, texX))
                texY = max(0, min(texSize - 1, texY))
                
                if portalTex:
                    color = portalTex.get_at((texX, texY))
                    surface.set_at((px, py), (color.r, color.g, color.b, alpha))
                else:
                    surface.set_at((px, py), (*portalColor, alpha))
        
        return surface
    
    def _createEndPortalBlock(self, isGateway: bool = False) -> pygame.Surface:
        """
        Create an isometric end portal/gateway block sprite.
        Uses the actual end_portal.png texture with scrolling animation effect.
        """
        W = TILE_WIDTH
        H = TILE_HEIGHT + BLOCK_HEIGHT
        halfW = W // 2
        halfH = TILE_HEIGHT // 2
        
        surface = pygame.Surface((W, H), pygame.SRCALPHA)
        
        # Get scroll offset for animation
        scrollOffset = int(self.endPortalScrollOffset) if hasattr(self, 'endPortalScrollOffset') else 0
        
        # Use actual texture if available
        texSize = 16
        if self.endPortalTexture:
            baseTex = pygame.transform.scale(self.endPortalTexture, (texSize, texSize))
        else:
            baseTex = None
        
        # Color tinting for gateway vs portal
        if isGateway:
            tintR, tintG, tintB = 0.5, 0.8, 1.0  # Cyan tint
        else:
            tintR, tintG, tintB = 0.8, 0.5, 1.0  # Purple tint
        
        # TOP FACE - main portal surface (full isometric diamond)
        for py in range(TILE_HEIGHT):
            # Calculate horizontal span for this row - diamond shape
            if py <= halfH:
                spanRatio = py / halfH if halfH > 0 else 0
            else:
                spanRatio = (TILE_HEIGHT - py) / halfH if halfH > 0 else 0
            
            span = int(halfW * spanRatio)
            if span <= 0:
                continue
            
            startX = halfW - span
            endX = halfW + span
            
            for px in range(startX, endX):
                # Map to texture coordinates using isometric transform
                relX = px - halfW
                relY = py - halfH
                
                # Inverse isometric projection
                u = (relX / halfW + relY / halfH) * 0.5 + 0.5 if halfW > 0 and halfH > 0 else 0.5
                v = (-relX / halfW + relY / halfH) * 0.5 + 0.5 if halfW > 0 and halfH > 0 else 0.5
                
                texX = (int(u * (texSize - 1)) + scrollOffset) % texSize
                texY = (int(v * (texSize - 1)) + scrollOffset // 2) % texSize
                
                texX = max(0, min(texSize - 1, texX))
                texY = max(0, min(texSize - 1, texY))
                
                if baseTex:
                    color = baseTex.get_at((texX, texY))
                    r = int(min(255, color.r * tintR))
                    g = int(min(255, color.g * tintG))
                    b = int(min(255, color.b * tintB))
                    surface.set_at((px, py), (r, g, b, 240))
                else:
                    # Fallback purple/cyan
                    if isGateway:
                        surface.set_at((px, py), (30, 80, 100, 240))
                    else:
                        surface.set_at((px, py), (50, 20, 80, 240))
        
        # LEFT FACE - darker
        for px in range(halfW):
            topY = halfH + int((px / halfW) * halfH) if halfW > 0 else halfH
            bottomY = topY + BLOCK_HEIGHT
            
            for py in range(topY, min(bottomY, H)):
                u = px / halfW if halfW > 0 else 0
                v = (py - topY) / BLOCK_HEIGHT if BLOCK_HEIGHT > 0 else 0
                
                texX = (int(u * (texSize - 1)) + scrollOffset) % texSize
                texY = int(v * (texSize - 1))
                
                if baseTex:
                    color = baseTex.get_at((texX, texY))
                    r = int(min(255, color.r * tintR * 0.5))
                    g = int(min(255, color.g * tintG * 0.5))
                    b = int(min(255, color.b * tintB * 0.5))
                    surface.set_at((px, py), (r, g, b, 240))
                else:
                    if isGateway:
                        surface.set_at((px, py), (15, 40, 50, 240))
                    else:
                        surface.set_at((px, py), (25, 10, 40, 240))
        
        # RIGHT FACE - medium brightness
        for px in range(halfW, W):
            relX = px - halfW
            topY = TILE_HEIGHT - 1 - int((relX / halfW) * halfH) if halfW > 0 else halfH
            bottomY = topY + BLOCK_HEIGHT
            
            for py in range(max(0, topY), min(bottomY, H)):
                u = relX / halfW if halfW > 0 else 0
                v = (py - topY) / BLOCK_HEIGHT if BLOCK_HEIGHT > 0 else 0
                
                texX = (int(u * (texSize - 1)) + scrollOffset) % texSize
                texY = int(v * (texSize - 1))
                
                if baseTex:
                    color = baseTex.get_at((texX, texY))
                    r = int(min(255, color.r * tintR * 0.65))
                    g = int(min(255, color.g * tintG * 0.65))
                    b = int(min(255, color.b * tintB * 0.65))
                    surface.set_at((px, py), (r, g, b, 240))
                else:
                    if isGateway:
                        surface.set_at((px, py), (20, 55, 70, 240))
                    else:
                        surface.set_at((px, py), (35, 15, 55, 240))
        
        return surface
    
    def _createFireBlock(self, fireTexture: pygame.Surface, isSoulFire: bool = False) -> pygame.Surface:
        """
        Create an isometric fire block sprite.
        Fire is rendered as a transparent animated sprite on a 1x1x1 block space.
        """
        W = TILE_WIDTH
        H = TILE_HEIGHT + BLOCK_HEIGHT
        halfW = W // 2
        halfH = TILE_HEIGHT // 2
        
        surface = pygame.Surface((W, H), pygame.SRCALPHA)
        
        # Scale fire texture to block height (fires are taller than wide in Minecraft)
        if fireTexture:
            # Scale fire to fit in the block space, maintaining aspect ratio
            fireW = int(TILE_WIDTH * 0.7)
            fireH = int(BLOCK_HEIGHT * 1.2)
            fireTex = pygame.transform.scale(fireTexture, (fireW, fireH))
            
            # Center fire horizontally, position at bottom of block
            fireX = (W - fireW) // 2
            fireY = halfH  # Start at top of the block face area
            
            # Draw fire texture with full transparency support
            surface.blit(fireTex, (fireX, fireY))
            
            # Optionally add a second fire layer shifted slightly for depth
            fireTex2 = pygame.transform.flip(fireTex, True, False)
            surface.blit(fireTex2, (fireX + 2, fireY - 2), special_flags=pygame.BLEND_RGBA_ADD)
        else:
            # Fallback color
            fireColor = (20, 150, 200) if isSoulFire else (255, 100, 0)
            for py in range(halfH, H - 5):
                for px in range(halfW - 10, halfW + 10):
                    surface.set_at((px, py), (*fireColor, 180))
        
        return surface
    
    def createLiquidAtLevel(self, isWater: bool, level: int) -> pygame.Surface:
        """Create a liquid block at a specific level (1-8)"""
        if isWater and self.waterFrames:
            frame = self.waterFrames[self.currentWaterFrame]
            return self._createLiquidBlock(frame, frame, frame, isWater=True, level=level)
        elif not isWater and self.lavaFrames:
            frame = self.lavaFrames[self.currentLavaFrame]
            return self._createLiquidBlock(frame, frame, frame, isWater=False, level=level)
        else:
            return self._createLiquidBlock(None, None, None, isWater=isWater, level=level)
    
    def _createIconSprites(self):
        """Create high-resolution icon sprites for the inventory panel"""
        # Chest block types for special handling
        chestTypes = (BlockType.CHEST, BlockType.ENDER_CHEST, BlockType.TRAPPED_CHEST, 
                     BlockType.CHRISTMAS_CHEST, BlockType.COPPER_CHEST, BlockType.COPPER_CHEST_EXPOSED,
                     BlockType.COPPER_CHEST_WEATHERED, BlockType.COPPER_CHEST_OXIDIZED)
        
        for blockType, blockDef in BLOCK_DEFINITIONS.items():
            # Create a dedicated high-res icon by rendering at larger size
            if blockDef.isThin:
                # For doors, show just the door texture as a flat icon
                icon = self._createDoorIcon(blockType, blockDef, ICON_SIZE)
            elif blockDef.isSlab:
                # For slabs, show half-height block
                icon = self._createSlabIcon(blockType, blockDef, ICON_SIZE)
            elif blockDef.isStair:
                # For stairs, show stair shape
                icon = self._createStairIcon(blockType, blockDef, ICON_SIZE)
            elif blockDef.isPortal:
                # For portal, use animated frame or static texture
                icon = self._createPortalIcon(blockType, blockDef, ICON_SIZE)
            elif blockType in (BlockType.FIRE, BlockType.SOUL_FIRE):
                # For fire, create a 2D icon from the fire texture
                icon = self._createFireIcon(blockType, ICON_SIZE)
            elif blockType in chestTypes:
                # For chests, use extracted chest textures
                icon = self._createChestIcon(blockType, ICON_SIZE)
            else:
                icon = self._createIconBlock(blockType, blockDef, ICON_SIZE)
            self.iconSprites[blockType] = icon
    
    def _createDoorIcon(self, blockType: BlockType, blockDef, size: int) -> pygame.Surface:
        """Create a simple door icon showing the door texture"""
        # Load door texture
        doorTex = self.textures.get(blockDef.textureSide)  # Side is the door texture
        
        surface = pygame.Surface((size, size), pygame.SRCALPHA)
        
        if doorTex:
            # Scale door texture to fit icon, preserving aspect ratio - use scale for crisp pixels
            doorW = int(size * 0.6)
            doorH = int(size * 0.9)
            doorTex = pygame.transform.scale(doorTex, (doorW, doorH))
            
            # Center the door in the icon
            x = (size - doorW) // 2
            y = (size - doorH) // 2
            
            # Draw door texture
            surface.blit(doorTex, (x, y))
            
            # Add subtle border
            pygame.draw.rect(surface, (60, 40, 20), (x, y, doorW, doorH), 2)
        else:
            # Fallback solid color
            pygame.draw.rect(surface, (139, 90, 43), (size//5, size//10, size*3//5, size*4//5))
        
        return surface
    
    def _createSlabIcon(self, blockType: BlockType, blockDef, size: int) -> pygame.Surface:
        """
        Create a slab icon - a half-height block for the inventory panel.
        Uses the same proven rendering approach as the main block renderer.
        """
        topTex = self.textures.get(blockDef.textureTop)
        sideTex = self.textures.get(blockDef.textureSide)
        frontTex = self.textures.get(blockDef.textureFront) if blockDef.textureFront else sideTex
        
        # Calculate dimensions scaled to icon size
        scale = size / TILE_WIDTH
        W = size
        halfW = W // 2
        halfH = int(TILE_HEIGHT * scale / 2)
        tileH = int(TILE_HEIGHT * scale)
        blockH = int(BLOCK_HEIGHT * scale / 2)  # Half height for slab
        H = tileH + blockH
        
        surface = pygame.Surface((W, H), pygame.SRCALPHA)
        
        # Scale textures
        texSize = 16
        if topTex:
            topTex = pygame.transform.smoothscale(topTex, (texSize, texSize))
        else:
            topTex = pygame.Surface((texSize, texSize))
            topTex.fill((100, 100, 100))
        
        if sideTex:
            sideTex = pygame.transform.smoothscale(sideTex, (texSize, texSize))
        else:
            sideTex = topTex.copy()
        
        if frontTex:
            frontTex = pygame.transform.smoothscale(frontTex, (texSize, texSize))
        else:
            frontTex = sideTex.copy()
        
        # Get colors
        topAvg = self._getAverageColor(topTex)
        leftAvg = self._darkenColor(self._getAverageColor(sideTex), 0.7)
        rightAvg = self._darkenColor(self._getAverageColor(frontTex), 0.85)
        
        # Define polygons for half-height block
        topPts = [(halfW, 0), (W-1, halfH), (halfW, tileH-1), (0, halfH)]
        leftPts = [(0, halfH), (halfW, tileH-1), (halfW, tileH-1+blockH), (0, halfH+blockH)]
        rightPts = [(halfW, tileH-1), (W-1, halfH), (W-1, halfH+blockH), (halfW, tileH-1+blockH)]
        
        # Fill polygons
        pygame.draw.polygon(surface, topAvg, topPts)
        pygame.draw.polygon(surface, leftAvg, leftPts)
        pygame.draw.polygon(surface, rightAvg, rightPts)
        
        # Texture map top face
        for py in range(tileH):
            if py <= halfH:
                spanRatio = py / halfH if halfH > 0 else 0
            else:
                spanRatio = (tileH - py) / halfH if halfH > 0 else 0
            span = int(halfW * spanRatio)
            if span <= 0:
                continue
            for px in range(halfW - span, halfW + span):
                relX = px - halfW
                relY = py - halfH
                u = (relX / halfW + relY / halfH) * 0.5 + 0.5 if halfW > 0 and halfH > 0 else 0.5
                v = (-relX / halfW + relY / halfH) * 0.5 + 0.5 if halfW > 0 and halfH > 0 else 0.5
                texX = max(0, min(texSize-1, int(u * (texSize-1))))
                texY = max(0, min(texSize-1, int(v * (texSize-1))))
                color = topTex.get_at((texX, texY))
                if color.a > 0:
                    surface.set_at((px, py), color)
        
        # Texture map left face
        for px in range(halfW):
            topY = halfH + int((px / halfW) * halfH) if halfW > 0 else halfH
            for py in range(topY, topY + blockH):
                texX = int((px / halfW) * (texSize-1)) if halfW > 0 else 0
                # Only use top half of texture for slab
                texY = int(((py - topY) / blockH) * (texSize//2 - 1)) if blockH > 0 else 0
                texX = max(0, min(texSize-1, texX))
                texY = max(0, min(texSize-1, texY))
                color = sideTex.get_at((texX, texY))
                if color.a > 0:
                    shaded = (int(color.r*0.7), int(color.g*0.7), int(color.b*0.7), 255)
                    surface.set_at((px, py), shaded)
        
        # Texture map right face
        for px in range(halfW, W):
            relX = px - halfW
            topY = tileH - 1 - int((relX / halfW) * halfH) if halfW > 0 else halfH
            for py in range(max(0, topY), topY + blockH):
                texX = int((relX / halfW) * (texSize-1)) if halfW > 0 else 0
                texY = int(((py - topY) / blockH) * (texSize//2 - 1)) if blockH > 0 else 0
                texX = max(0, min(texSize-1, texX))
                texY = max(0, min(texSize-1, texY))
                color = frontTex.get_at((texX, texY))
                if color.a > 0:
                    shaded = (int(color.r*0.85), int(color.g*0.85), int(color.b*0.85), 255)
                    surface.set_at((px, py), shaded)
        
        # Add outlines
        outlineColor = (50, 50, 50)
        pygame.draw.line(surface, outlineColor, topPts[0], topPts[1], 1)
        pygame.draw.line(surface, outlineColor, topPts[0], topPts[3], 1)
        pygame.draw.line(surface, outlineColor, leftPts[2], leftPts[3], 1)
        pygame.draw.line(surface, outlineColor, rightPts[2], rightPts[3], 1)
        
        return surface
    
    def _createStairIcon(self, blockType: BlockType, blockDef, size: int) -> pygame.Surface:
        """Create a stair icon with stepped shape"""
        topTex = self.textures.get(blockDef.textureTop)
        
        texSize = size
        if topTex:
            topTex = pygame.transform.scale(topTex, (texSize, texSize))
        else:
            topTex = pygame.Surface((texSize, texSize))
            topTex.fill((100, 100, 100))
        
        # Use same proportions as applet - scale from TILE_WIDTH to icon size
        scale = size / TILE_WIDTH
        W = size
        halfW = W // 2
        quarterW = W // 4
        tileH = int(TILE_HEIGHT * scale / 2)  # Half of top diamond height
        blockH = int(BLOCK_HEIGHT * scale)  # Full block height
        stepH = blockH // 2  # Each step is half block height
        
        # Total height
        cubeH = tileH * 2 + blockH
        
        surface = pygame.Surface((W, cubeH), pygame.SRCALPHA)
        
        # Get colors
        topAvg = self._getAverageColor(topTex)
        leftAvg = self._darkenColor(topAvg, 0.7)
        rightAvg = self._darkenColor(topAvg, 0.85)
        
        # Draw top step (back left portion)
        topStepTop = [(halfW, 0), (halfW, tileH), (quarterW, tileH + tileH//2), (0, tileH)]
        pygame.draw.polygon(surface, topAvg, topStepTop)
        # Top step left side
        topStepLeft = [(0, tileH), (quarterW, tileH + tileH//2), (quarterW, tileH + tileH//2 + stepH), (0, tileH + stepH)]
        pygame.draw.polygon(surface, leftAvg, topStepLeft)
        # Top step front (riser)
        topStepFront = [(quarterW, tileH + tileH//2), (halfW, tileH), (halfW, tileH + stepH), (quarterW, tileH + tileH//2 + stepH)]
        pygame.draw.polygon(surface, rightAvg, topStepFront)
        
        # Draw bottom step (full width, lower)
        bottomStepTop = [(halfW, tileH), (W-1, tileH + tileH), (halfW, tileH*3 - 1), (quarterW, tileH + tileH//2 + stepH)]
        pygame.draw.polygon(surface, topAvg, bottomStepTop)
        # Bottom step left
        bottomStepLeft = [(quarterW, tileH + tileH//2 + stepH), (halfW, tileH*3 - 1), (halfW, cubeH-1), (quarterW, tileH + tileH//2 + stepH*2)]
        pygame.draw.polygon(surface, leftAvg, bottomStepLeft)
        # Bottom step right
        bottomStepRight = [(halfW, tileH*3 - 1), (W-1, tileH*2), (W-1, tileH*2 + stepH), (halfW, cubeH-1)]
        pygame.draw.polygon(surface, rightAvg, bottomStepRight)
        
        # Outlines
        outlineColor = (50, 50, 50)
        pygame.draw.line(surface, outlineColor, (halfW, 0), (0, tileH), 1)
        pygame.draw.line(surface, outlineColor, (0, tileH), (0, tileH + stepH), 1)
        pygame.draw.line(surface, outlineColor, (halfW, tileH), (W-1, tileH*2), 1)
        pygame.draw.line(surface, outlineColor, (W-1, tileH*2), (W-1, tileH*2 + stepH), 1)
        
        return surface
    
    def _createPortalIcon(self, blockType: BlockType, blockDef, size: int) -> pygame.Surface:
        """Create a portal icon with swirling purple texture"""
        # Get portal texture (use first animation frame if available)
        if self.portalFrames:
            portalTex = self.portalFrames[0]
        else:
            portalTex = self.textures.get(blockDef.textureTop)
        
        if portalTex:
            portalTex = pygame.transform.scale(portalTex, (size, size))
        else:
            # Create purple gradient fallback
            portalTex = pygame.Surface((size, size), pygame.SRCALPHA)
            portalTex.fill((138, 43, 226))
        
        # Use same proportions as regular blocks
        scale = size / TILE_WIDTH
        W = size
        halfW = W // 2
        tileH = int(TILE_HEIGHT * scale / 2)
        blockH = int(BLOCK_HEIGHT * scale)
        cubeH = tileH * 2 + blockH
        
        surface = pygame.Surface((W, cubeH), pygame.SRCALPHA)
        
        # Get average color for faces
        topAvg = self._getAverageColor(portalTex)
        leftAvg = self._darkenColor(topAvg, 0.75)
        rightAvg = self._darkenColor(topAvg, 0.9)
        
        # Top face (thin diamond)
        topPoints = [(halfW, 0), (W-1, tileH), (halfW, tileH*2-1), (0, tileH)]
        pygame.draw.polygon(surface, topAvg, topPoints)
        
        # Left face
        leftPoints = [(0, tileH), (halfW, tileH*2-1), (halfW, tileH*2 + blockH - 1), (0, tileH + blockH)]
        pygame.draw.polygon(surface, leftAvg, leftPoints)
        
        # Right face
        rightPoints = [(halfW, tileH*2-1), (W-1, tileH), (W-1, tileH + blockH), (halfW, tileH*2 + blockH - 1)]
        pygame.draw.polygon(surface, rightAvg, rightPoints)
        
        # Add glow effect (purple border)
        glowColor = (180, 100, 255)
        pygame.draw.polygon(surface, glowColor, topPoints, 1)
        pygame.draw.polygon(surface, glowColor, leftPoints, 1)
        pygame.draw.polygon(surface, glowColor, rightPoints, 1)
        
        return surface
    
    def _createFireIcon(self, blockType: BlockType, size: int) -> pygame.Surface:
        """Create a 2D fire icon from the fire animation frames"""
        # Get the appropriate fire frames
        if blockType == BlockType.SOUL_FIRE and self.soulFireFrames:
            fireTex = self.soulFireFrames[0]
        elif self.fireFrames:
            fireTex = self.fireFrames[0]
        else:
            fireTex = None
        
        surface = pygame.Surface((size, size), pygame.SRCALPHA)
        
        if fireTex:
            # Scale fire texture to fill the icon nicely
            fireW = int(size * 0.9)
            fireH = int(size * 0.95)
            scaledFire = pygame.transform.scale(fireTex, (fireW, fireH))
            
            # Center the fire in the icon
            x = (size - fireW) // 2
            y = (size - fireH) // 2
            
            surface.blit(scaledFire, (x, y))
        else:
            # Fallback - draw a simple fire shape
            fireColor = (20, 150, 200) if blockType == BlockType.SOUL_FIRE else (255, 100, 0)
            pygame.draw.polygon(surface, fireColor, [
                (size//2, 2), (size-4, size-2), (size//2, size//2), (4, size-2)
            ])
        
        return surface
    
    def _createChestIcon(self, blockType: BlockType, size: int) -> pygame.Surface:
        """Create an icon for chest blocks using extracted chest textures"""
        chestName = {
            BlockType.CHEST: "normal",
            BlockType.ENDER_CHEST: "ender",
            BlockType.TRAPPED_CHEST: "trapped",
            BlockType.CHRISTMAS_CHEST: "christmas",
            BlockType.COPPER_CHEST: "copper",
            BlockType.COPPER_CHEST_EXPOSED: "copper_exposed",
            BlockType.COPPER_CHEST_WEATHERED: "copper_weathered",
            BlockType.COPPER_CHEST_OXIDIZED: "copper_oxidized",
        }.get(blockType, "normal")
        
        topTex = self.textures.get(f"chest_{chestName}_top.png")
        frontTex = self.textures.get(f"chest_{chestName}_front.png")
        sideTex = self.textures.get(f"chest_{chestName}_side.png")
        
        # If textures are missing, use fallback
        if not (topTex and frontTex and sideTex):
            blockDef = BLOCK_DEFINITIONS.get(blockType)
            if blockDef:
                return self._createIconBlock(blockType, blockDef, size)
            else:
                return pygame.Surface((size, size), pygame.SRCALPHA)
        
        # Scale from TILE_WIDTH to icon size
        scale = size / TILE_WIDTH
        W = size
        halfW = W // 2
        tileH = int(TILE_HEIGHT * scale / 2)
        blockH = int(BLOCK_HEIGHT * scale)
        cubeH = tileH * 2 + blockH
        
        surface = pygame.Surface((W, cubeH), pygame.SRCALPHA)
        
        texSize = 16
        topTex = pygame.transform.scale(topTex, (texSize, texSize))
        frontTex = pygame.transform.scale(frontTex, (texSize, texSize))
        sideTex = pygame.transform.scale(sideTex, (texSize, texSize))
        
        # Get average colors for faces
        topAvg = self._getAverageColor(topTex)
        leftAvg = self._darkenColor(self._getAverageColor(sideTex), 0.7)
        rightAvg = self._darkenColor(self._getAverageColor(frontTex), 0.85)
        
        # Draw faces
        topPoints = [(halfW, 0), (W-1, tileH), (halfW, tileH*2-1), (0, tileH)]
        pygame.draw.polygon(surface, topAvg, topPoints)
        
        leftPoints = [(0, tileH), (halfW, tileH*2-1), (halfW, tileH*2 + blockH - 1), (0, tileH + blockH)]
        pygame.draw.polygon(surface, leftAvg, leftPoints)
        
        rightPoints = [(halfW, tileH*2-1), (W-1, tileH), (W-1, tileH + blockH), (halfW, tileH*2 + blockH - 1)]
        pygame.draw.polygon(surface, rightAvg, rightPoints)
        
        # Outlines
        outlineColor = (50, 50, 50)
        pygame.draw.polygon(surface, outlineColor, topPoints, 1)
        pygame.draw.polygon(surface, outlineColor, leftPoints, 1)
        pygame.draw.polygon(surface, outlineColor, rightPoints, 1)
        
        return surface
    
    def _createIconBlock(self, blockType: BlockType, blockDef, size: int) -> pygame.Surface:
        """Create a crisp isometric block icon at the specified size"""
        topTex = self.textures.get(blockDef.textureTop)
        sideTex = self.textures.get(blockDef.textureSide)
        frontTex = self.textures.get(blockDef.textureFront) if blockDef.textureFront else sideTex
        
        # Apply tinting if needed
        if topTex and blockDef.tintTop:
            tint = LEAVES_TINT if "leaves" in blockDef.textureTop else GRASS_TINT
            topTex = self._tintTexture(topTex, tint)
        
        if sideTex and blockDef.tintSide:
            tint = LEAVES_TINT if "leaves" in blockDef.textureSide else GRASS_TINT
            sideTex = self._tintTexture(sideTex, tint)
        
        # Also tint front texture for leaves
        if frontTex and blockDef.tintSide:
            tint = LEAVES_TINT if "leaves" in (blockDef.textureFront or blockDef.textureSide) else GRASS_TINT
            frontTex = self._tintTexture(frontTex, tint)
        
        # Apply water/lava tinting for icons
        if blockDef.isLiquid:
            if blockType == BlockType.WATER:
                if topTex:
                    topTex = self._tintLiquid(topTex, WATER_TINT)
                if sideTex:
                    sideTex = self._tintLiquid(sideTex, WATER_TINT)
                if frontTex:
                    frontTex = self._tintLiquid(frontTex, WATER_TINT)
            elif blockType == BlockType.LAVA:
                if topTex:
                    topTex = self._tintLiquid(topTex, LAVA_TINT)
                if sideTex:
                    sideTex = self._tintLiquid(sideTex, LAVA_TINT)
                if frontTex:
                    frontTex = self._tintLiquid(frontTex, LAVA_TINT)
        
        # Scale textures for icons - use scale (nearest neighbor) for crisp pixels
        texSize = size  # Use icon size for texture
        if topTex:
            topTex = pygame.transform.scale(topTex, (texSize, texSize))
        else:
            topTex = pygame.Surface((texSize, texSize))
            topTex.fill((100, 100, 100))
        
        if sideTex:
            sideTex = pygame.transform.scale(sideTex, (texSize, texSize))
        else:
            sideTex = pygame.Surface((texSize, texSize))
            sideTex.fill((80, 80, 80))
        
        if frontTex:
            frontTex = pygame.transform.scale(frontTex, (texSize, texSize))
        else:
            frontTex = sideTex
        
        transparent = blockDef.transparent
        
        # Use same proportions as applet blocks: TILE_HEIGHT = TILE_WIDTH/2, BLOCK_HEIGHT slightly taller
        # Scale factor from base tile size to icon size
        scale = size / TILE_WIDTH
        W = size
        halfW = W // 2
        tileH = int(TILE_HEIGHT * scale / 2)  # Half of top diamond height
        blockH = int(BLOCK_HEIGHT * scale)  # Side face height - matches applet proportion
        cubeH = tileH * 2 + blockH
        
        # Create surface that can hold the cube
        surface = pygame.Surface((W, cubeH), pygame.SRCALPHA)
        
        # Define face polygons for proper cube
        topPoints = [(halfW, 0), (W-1, tileH), (halfW, tileH*2-1), (0, tileH)]
        leftPoints = [(0, tileH), (halfW, tileH*2-1), (halfW, tileH*2-1 + blockH), (0, tileH + blockH)]
        rightPoints = [(halfW, tileH*2-1), (W-1, tileH), (W-1, tileH + blockH), (halfW, tileH*2-1 + blockH)]
        
        # Get average colors
        topAvg = self._getAverageColor(topTex)
        leftAvg = self._darkenColor(self._getAverageColor(sideTex), 0.7)
        rightAvg = self._darkenColor(self._getAverageColor(frontTex), 0.85)
        
        # Fill faces with base colors
        if not transparent:
            pygame.draw.polygon(surface, topAvg, topPoints)
            pygame.draw.polygon(surface, leftAvg, leftPoints)
            pygame.draw.polygon(surface, rightAvg, rightPoints)
        
        # TOP FACE with proper isometric texture mapping
        for py in range(tileH * 2):
            if py <= tileH:
                spanRatio = py / tileH if tileH > 0 else 0
            else:
                spanRatio = (tileH * 2 - py) / tileH if tileH > 0 else 0
            
            span = int(halfW * spanRatio)
            if span <= 0:
                continue
                
            leftX = halfW - span
            rightX = halfW + span
            
            for px in range(leftX, rightX):
                relX = px - halfW
                relY = py - tileH
                
                # Inverse isometric projection
                u = (relX / halfW + relY / tileH) * 0.5 + 0.5
                v = (-relX / halfW + relY / tileH) * 0.5 + 0.5
                
                texX = int(u * (texSize - 1))
                texY = int(v * (texSize - 1))
                
                texX = max(0, min(texSize - 1, texX))
                texY = max(0, min(texSize - 1, texY))
                
                color = topTex.get_at((texX, texY))
                if color.a > 0:
                    surface.set_at((px, py), color)
        
        # LEFT FACE
        for px in range(halfW):
            topY = tileH + int((px / halfW) * tileH) if halfW > 0 else tileH
            bottomY = min(topY + blockH, cubeH)
            
            for py in range(topY, bottomY):
                texX = int((px / halfW) * (texSize - 1)) if halfW > 0 else 0
                texY = int(((py - topY) / blockH) * (texSize - 1)) if blockH > 0 else 0
                
                texX = max(0, min(texSize - 1, texX))
                texY = max(0, min(texSize - 1, texY))
                
                color = sideTex.get_at((texX, texY))
                if color.a > 0:
                    shade = 0.8 if transparent else 0.7
                    shaded = (int(color.r * shade), int(color.g * shade), int(color.b * shade), color.a)
                    surface.set_at((px, py), shaded)
        
        # RIGHT FACE
        for px in range(halfW, W):
            relX = px - halfW
            topY = tileH * 2 - 1 - int((relX / halfW) * tileH) if halfW > 0 else tileH
            bottomY = min(topY + blockH, cubeH)
            
            for py in range(max(0, topY), bottomY):
                texX = int((relX / halfW) * (texSize - 1)) if halfW > 0 else 0
                texY = int(((py - topY) / blockH) * (texSize - 1)) if blockH > 0 else 0
                
                texX = max(0, min(texSize - 1, texX))
                texY = max(0, min(texSize - 1, texY))
                
                color = frontTex.get_at((texX, texY))
                if color.a > 0:
                    shade = 0.9 if transparent else 0.85
                    shaded = (int(color.r * shade), int(color.g * shade), int(color.b * shade), color.a)
                    surface.set_at((px, py), shaded)
        
        # Subtle outlines
        outlineColor = (50, 50, 50) if not transparent else (80, 80, 80, 100)
        pygame.draw.line(surface, outlineColor, topPoints[0], topPoints[1], 1)
        pygame.draw.line(surface, outlineColor, topPoints[0], topPoints[3], 1)
        pygame.draw.line(surface, outlineColor, leftPoints[2], leftPoints[3], 1)
        pygame.draw.line(surface, outlineColor, rightPoints[2], rightPoints[3], 1)
        
        return surface
    
    def _loadSounds(self):
        """Load sounds from Sound Hub for each block material type"""
        # Sound categories to load (from dig folder for place/break sounds)
        soundCategories = ["grass", "gravel", "stone", "wood", "cloth", "sand"]
        
        # Load dig sounds for each category
        digDir = os.path.join(SOUNDS_DIR, "dig")
        
        for category in soundCategories:
            self.sounds[category] = []
            
            # Find all sound files for this category (e.g., grass1.ogg, grass2.ogg, etc.)
            for i in range(1, 10):  # Check for up to 9 variants
                soundPath = os.path.join(digDir, f"{category}{i}.ogg")
                if os.path.exists(soundPath):
                    try:
                        sound = pygame.mixer.Sound(soundPath)
                        sound.set_volume(0.6)
                        self.sounds[category].append(sound)
                    except Exception as e:
                        print(f"Warning: Could not load {soundPath}: {e}")
            
            if self.sounds[category]:
                print(f"    Loaded {len(self.sounds[category])} {category} sounds")
        
        # Load glass break sounds from random folder (for breaking)
        self.sounds["glass"] = []
        randomDir = os.path.join(SOUNDS_DIR, "random")
        for i in range(1, 5):
            glassPath = os.path.join(randomDir, f"glass{i}.ogg")
            if os.path.exists(glassPath):
                try:
                    sound = pygame.mixer.Sound(glassPath)
                    sound.set_volume(0.6)
                    self.sounds["glass"].append(sound)
                except Exception as e:
                    print(f"Warning: Could not load {glassPath}: {e}")
        if self.sounds["glass"]:
            print(f"    Loaded {len(self.sounds['glass'])} glass sounds")
        
        # Glass placing uses stone sounds
        self.sounds["glass_place"] = self.sounds.get("stone", [])
        
        # Load water sounds from liquid folder
        self.sounds["water"] = []
        liquidDir = os.path.join(SOUNDS_DIR, "liquid")
        waterPath = os.path.join(liquidDir, "water.ogg")
        if os.path.exists(waterPath):
            try:
                sound = pygame.mixer.Sound(waterPath)
                sound.set_volume(0.5)
                self.sounds["water"].append(sound)
                print(f"    Loaded water sound")
            except Exception as e:
                print(f"Warning: Could not load water sound: {e}")
        # Add splash sounds for water
        for i in ["splash.ogg", "splash2.ogg"]:
            splashPath = os.path.join(liquidDir, i)
            if os.path.exists(splashPath):
                try:
                    sound = pygame.mixer.Sound(splashPath)
                    sound.set_volume(0.5)
                    self.sounds["water"].append(sound)
                except:
                    pass
        
        # Load lava sounds from liquid folder
        self.sounds["lava"] = []
        lavaPath = os.path.join(liquidDir, "lava.ogg")
        if os.path.exists(lavaPath):
            try:
                sound = pygame.mixer.Sound(lavaPath)
                sound.set_volume(0.5)
                self.sounds["lava"].append(sound)
                print(f"    Loaded lava sound")
            except Exception as e:
                print(f"Warning: Could not load lava sound: {e}")
        lavapopPath = os.path.join(liquidDir, "lavapop.ogg")
        if os.path.exists(lavapopPath):
            try:
                sound = pygame.mixer.Sound(lavapopPath)
                sound.set_volume(0.5)
                self.sounds["lava"].append(sound)
            except:
                pass
        
        # Load UI click sound
        clickPath = os.path.join(SOUNDS_DIR, "random", "click.ogg")
        if os.path.exists(clickPath):
            try:
                self.clickSound = pygame.mixer.Sound(clickPath)
                self.clickSound.set_volume(0.4)
                print(f"    Loaded click sound")
            except Exception as e:
                print(f"Warning: Could not load click sound: {e}")
        
        # Load block-specific sounds from block/ folder
        # These have their own unique sounds (nether_bricks, netherrack, copper, bone_block, spawner, sculk_sensor)
        blockSoundCategories = ["nether_bricks", "netherrack", "copper", "bone_block", "spawner", "sculk_sensor"]
        blockDir = os.path.join(SOUNDS_DIR, "block")
        
        for category in blockSoundCategories:
            self.sounds[category] = []
            categoryDir = os.path.join(blockDir, category)
            
            if os.path.exists(categoryDir):
                # Look for break sounds (break1.ogg, break2.ogg, etc.)
                for i in range(1, 10):
                    breakPath = os.path.join(categoryDir, f"break{i}.ogg")
                    if os.path.exists(breakPath):
                        try:
                            sound = pygame.mixer.Sound(breakPath)
                            sound.set_volume(0.6)
                            self.sounds[category].append(sound)
                        except Exception as e:
                            print(f"Warning: Could not load {breakPath}: {e}")
                
                if self.sounds[category]:
                    print(f"    Loaded {len(self.sounds[category])} {category} sounds")
        
        # Load enchanting table sounds from block/enchantment_table
        self.sounds["enchantment_table"] = []
        enchantDir = os.path.join(blockDir, "enchantment_table")
        if os.path.exists(enchantDir):
            for i in range(1, 5):
                enchantPath = os.path.join(enchantDir, f"enchant{i}.ogg")
                if os.path.exists(enchantPath):
                    try:
                        sound = pygame.mixer.Sound(enchantPath)
                        sound.set_volume(0.5)
                        self.sounds["enchantment_table"].append(sound)
                    except Exception as e:
                        print(f"Warning: Could not load {enchantPath}: {e}")
            if self.sounds["enchantment_table"]:
                print(f"    Loaded {len(self.sounds['enchantment_table'])} enchantment_table sounds")
        
        # Load chest sounds from block/chest
        self.sounds["chest"] = []
        chestDir = os.path.join(blockDir, "chest")
        if os.path.exists(chestDir):
            # Try to load open sounds
            openPath = os.path.join(chestDir, "open.ogg")
            if os.path.exists(openPath):
                try:
                    sound = pygame.mixer.Sound(openPath)
                    sound.set_volume(0.6)
                    self.sounds["chest"].append(sound)
                except: pass
            # Load close sounds
            for i in range(1, 5):
                closePath = os.path.join(chestDir, f"close{i}.ogg")
                if os.path.exists(closePath):
                    try:
                        sound = pygame.mixer.Sound(closePath)
                        sound.set_volume(0.6)
                        self.sounds["chest"].append(sound)
                    except: pass
            if self.sounds["chest"]:
                print(f"    Loaded {len(self.sounds['chest'])} chest sounds")
        
        # Load ender chest sounds from block/enderchest
        self.sounds["enderchest"] = []
        enderChestDir = os.path.join(blockDir, "enderchest")
        if os.path.exists(enderChestDir):
            for sndFile in ["open.ogg", "close.ogg"]:
                sndPath = os.path.join(enderChestDir, sndFile)
                if os.path.exists(sndPath):
                    try:
                        sound = pygame.mixer.Sound(sndPath)
                        sound.set_volume(0.6)
                        self.sounds["enderchest"].append(sound)
                    except: pass
            if self.sounds["enderchest"]:
                print(f"    Loaded {len(self.sounds['enderchest'])} enderchest sounds")
        
        # Load end portal sounds from block/end_portal
        self.sounds["end_portal"] = []
        endPortalDir = os.path.join(blockDir, "end_portal")
        if os.path.exists(endPortalDir):
            portalPath = os.path.join(endPortalDir, "endportal.ogg")
            if os.path.exists(portalPath):
                try:
                    sound = pygame.mixer.Sound(portalPath)
                    sound.set_volume(0.4)
                    self.sounds["end_portal"].append(sound)
                except: pass
            # Also load eye placement sounds
            for i in range(1, 5):
                eyePath = os.path.join(endPortalDir, f"eyeplace{i}.ogg")
                if os.path.exists(eyePath):
                    try:
                        sound = pygame.mixer.Sound(eyePath)
                        sound.set_volume(0.5)
                        self.sounds["end_portal"].append(sound)
                    except: pass
            if self.sounds["end_portal"]:
                print(f"    Loaded {len(self.sounds['end_portal'])} end_portal sounds")
        
        # Load fire sounds from fire/ folder
        self.sounds["fire"] = []
        fireDir = os.path.join(SOUNDS_DIR, "fire")
        if os.path.exists(fireDir):
            for sndFile in ["fire.ogg", "ignite.ogg"]:
                firePath = os.path.join(fireDir, sndFile)
                if os.path.exists(firePath):
                    try:
                        sound = pygame.mixer.Sound(firePath)
                        sound.set_volume(0.5)
                        self.sounds["fire"].append(sound)
                    except: pass
            if self.sounds["fire"]:
                print(f"    Loaded {len(self.sounds['fire'])} fire sounds")
        
        # Load sculk sounds from block/sculk folder
        self.sounds["sculk"] = []
        sculkDir = os.path.join(blockDir, "sculk")
        if os.path.exists(sculkDir):
            for i in range(1, 15):
                breakPath = os.path.join(sculkDir, f"break{i}.ogg")
                if os.path.exists(breakPath):
                    try:
                        sound = pygame.mixer.Sound(breakPath)
                        sound.set_volume(0.6)
                        self.sounds["sculk"].append(sound)
                    except: pass
            if self.sounds["sculk"]:
                print(f"    Loaded {len(self.sounds['sculk'])} sculk sounds")
        
        # Load copper chest sounds from entity/copper_chest folder
        entitySoundDir = os.path.join(SOUNDS_DIR, "entity")
        copperChestDir = os.path.join(entitySoundDir, "copper_chest")
        if os.path.exists(copperChestDir):
            # Load regular copper chest sounds
            self.sounds["copper_chest"] = []
            for i in range(1, 5):
                for sndType in ["open", "close"]:
                    sndPath = os.path.join(copperChestDir, f"copper_chest_{sndType}{i}.ogg")
                    if os.path.exists(sndPath):
                        try:
                            sound = pygame.mixer.Sound(sndPath)
                            sound.set_volume(0.6)
                            self.sounds["copper_chest"].append(sound)
                        except: pass
            if self.sounds["copper_chest"]:
                print(f"    Loaded {len(self.sounds['copper_chest'])} copper_chest sounds")
            
            # Load weathered copper chest sounds
            self.sounds["copper_chest_weathered"] = []
            for i in range(1, 5):
                for sndType in ["open", "close"]:
                    sndPath = os.path.join(copperChestDir, f"copper_chest_weathered_{sndType}{i}.ogg")
                    if os.path.exists(sndPath):
                        try:
                            sound = pygame.mixer.Sound(sndPath)
                            sound.set_volume(0.6)
                            self.sounds["copper_chest_weathered"].append(sound)
                        except: pass
            if self.sounds["copper_chest_weathered"]:
                print(f"    Loaded {len(self.sounds['copper_chest_weathered'])} copper_chest_weathered sounds")
            
            # Load oxidized copper chest sounds
            self.sounds["copper_chest_oxidized"] = []
            for i in range(1, 5):
                for sndType in ["open", "close"]:
                    sndPath = os.path.join(copperChestDir, f"copper_chest_oxidized_{sndType}{i}.ogg")
                    if os.path.exists(sndPath):
                        try:
                            sound = pygame.mixer.Sound(sndPath)
                            sound.set_volume(0.6)
                            self.sounds["copper_chest_oxidized"].append(sound)
                        except: pass
            if self.sounds["copper_chest_oxidized"]:
                print(f"    Loaded {len(self.sounds['copper_chest_oxidized'])} copper_chest_oxidized sounds")
        
        # Load door sounds from random folder (wood doors)
        self.doorOpenSound = None
        self.doorCloseSound = None
        doorOpenPath = os.path.join(SOUNDS_DIR, "random", "door_open.ogg")
        doorClosePath = os.path.join(SOUNDS_DIR, "random", "door_close.ogg")
        if os.path.exists(doorOpenPath):
            try:
                self.doorOpenSound = pygame.mixer.Sound(doorOpenPath)
                self.doorOpenSound.set_volume(0.7)
                print(f"    Loaded door open sound")
            except Exception as e:
                print(f"Warning: Could not load door open sound: {e}")
        if os.path.exists(doorClosePath):
            try:
                self.doorCloseSound = pygame.mixer.Sound(doorClosePath)
                self.doorCloseSound.set_volume(0.7)
                print(f"    Loaded door close sound")
            except Exception as e:
                print(f"Warning: Could not load door close sound: {e}")
        
        # Load iron door sounds from block/iron_door folder
        self.ironDoorOpenSounds = []
        self.ironDoorCloseSounds = []
        ironDoorDir = os.path.join(SOUNDS_DIR, "block", "iron_door")
        if os.path.exists(ironDoorDir):
            for i in range(1, 5):
                openPath = os.path.join(ironDoorDir, f"open{i}.ogg")
                closePath = os.path.join(ironDoorDir, f"close{i}.ogg")
                if os.path.exists(openPath):
                    try:
                        snd = pygame.mixer.Sound(openPath)
                        snd.set_volume(0.7)
                        self.ironDoorOpenSounds.append(snd)
                    except: pass
                if os.path.exists(closePath):
                    try:
                        snd = pygame.mixer.Sound(closePath)
                        snd.set_volume(0.7)
                        self.ironDoorCloseSounds.append(snd)
                    except: pass
            if self.ironDoorOpenSounds:
                print(f"    Loaded {len(self.ironDoorOpenSounds)} iron door open sounds")
            if self.ironDoorCloseSounds:
                print(f"    Loaded {len(self.ironDoorCloseSounds)} iron door close sounds")
    
    def _loadUITextures(self):
        """Load UI textures for Minecraft-style buttons and panels"""
        widgetDir = os.path.join(GUI_DIR, "sprites", "widget")
        
        # Load button textures
        buttonPath = os.path.join(widgetDir, "button.png")
        buttonHoverPath = os.path.join(widgetDir, "button_highlighted.png")
        buttonDisabledPath = os.path.join(widgetDir, "button_disabled.png")
        slotPath = os.path.join(widgetDir, "slot_frame.png")
        
        if os.path.exists(buttonPath):
            self.buttonNormal = pygame.image.load(buttonPath).convert_alpha()
        if os.path.exists(buttonHoverPath):
            self.buttonHover = pygame.image.load(buttonHoverPath).convert_alpha()
        if os.path.exists(buttonDisabledPath):
            self.buttonDisabled = pygame.image.load(buttonDisabledPath).convert_alpha()
        if os.path.exists(slotPath):
            self.slotFrame = pygame.image.load(slotPath).convert_alpha()
    
    def _createBackground(self, dimension: str = DIMENSION_OVERWORLD):
        """Create a dark repeating texture background based on dimension"""
        # Choose texture based on dimension
        if dimension == DIMENSION_NETHER:
            textureName = "netherrack.png"
            darkenFactor = (80, 70, 70)  # Reddish dark tint
            fallbackColor = (60, 30, 30)
        elif dimension == DIMENSION_END:
            textureName = "end_stone.png"
            darkenFactor = (85, 85, 90)  # Slight purple tint
            fallbackColor = (50, 50, 55)
        else:  # Overworld
            textureName = "dirt.png"
            darkenFactor = (90, 90, 90)  # Neutral dark
            fallbackColor = (50, 45, 40)
        
        texturePath = os.path.join(TEXTURES_DIR, textureName)
        if os.path.exists(texturePath):
            tex = pygame.image.load(texturePath).convert()
            # Darken it for menu-style background
            darkTex = tex.copy()
            darkTex.fill(darkenFactor, special_flags=pygame.BLEND_RGB_MULT)
            # Scale to larger size for less busy look
            self.backgroundTile = pygame.transform.scale(darkTex, (BG_TILE_SIZE, BG_TILE_SIZE))
        else:
            # Fallback to solid color
            self.backgroundTile = pygame.Surface((BG_TILE_SIZE, BG_TILE_SIZE))
            self.backgroundTile.fill(fallbackColor)
    
    def drawBackground(self, screen: pygame.Surface):
        """Draw the tiled dirt background"""
        if self.backgroundTile:
            tileW = self.backgroundTile.get_width()
            tileH = self.backgroundTile.get_height()
            for y in range(0, screen.get_height(), tileH):
                for x in range(0, screen.get_width(), tileW):
                    screen.blit(self.backgroundTile, (x, y))
    
    def drawButton(self, screen: pygame.Surface, rect: pygame.Rect, 
                   text: str, font: pygame.font.Font, 
                   hovered: bool = False, selected: bool = False):
        """Draw a Minecraft-style button"""
        # Choose texture based on state
        if selected:
            texture = self.buttonHover if self.buttonHover else self.buttonNormal
        elif hovered:
            texture = self.buttonHover if self.buttonHover else self.buttonNormal
        else:
            texture = self.buttonNormal
        
        if texture:
            # Scale texture to button size using 9-slice or simple scale
            scaledBtn = pygame.transform.scale(texture, (rect.width, rect.height))
            screen.blit(scaledBtn, rect.topleft)
        else:
            # Fallback to simple rectangle
            color = (100, 100, 100) if hovered else (80, 80, 80)
            pygame.draw.rect(screen, color, rect)
            pygame.draw.rect(screen, (60, 60, 60), rect, 2)
        
        # Draw text with shadow
        shadowSurf = font.render(text, True, (60, 60, 60))
        shadowRect = shadowSurf.get_rect(center=(rect.centerx + 1, rect.centery + 1))
        screen.blit(shadowSurf, shadowRect)
        
        textSurf = font.render(text, True, (255, 255, 255))
        textRect = textSurf.get_rect(center=rect.center)
        screen.blit(textSurf, textRect)
    
    def drawSlot(self, screen: pygame.Surface, rect: pygame.Rect, selected: bool = False):
        """Draw a Minecraft-style inventory slot"""
        if self.slotFrame:
            scaledSlot = pygame.transform.scale(self.slotFrame, (rect.width, rect.height))
            screen.blit(scaledSlot, rect.topleft)
        else:
            # Fallback
            pygame.draw.rect(screen, (60, 60, 60), rect)
            pygame.draw.rect(screen, (40, 40, 40), rect, 2)
        
        if selected:
            pygame.draw.rect(screen, SELECTED_COLOR, rect, 3)

    def playSound(self, soundCategory: str):
        """Play a random sound from the specified category"""
        if soundCategory in self.sounds and self.sounds[soundCategory]:
            # Pick a random variant for natural variation
            sound = random.choice(self.sounds[soundCategory])
            sound.play()
    
    def playClickSound(self):
        """Play the UI click sound"""
        if self.clickSound:
            self.clickSound.play()
    
    def playDoorSound(self, isOpening: bool, blockType: BlockType = None):
        """Play door open or close sound - iron doors use metal door sounds"""
        import random
        # Iron doors use proper metal door sounds
        if blockType == BlockType.IRON_DOOR:
            if isOpening and self.ironDoorOpenSounds:
                random.choice(self.ironDoorOpenSounds).play()
            elif not isOpening and self.ironDoorCloseSounds:
                random.choice(self.ironDoorCloseSounds).play()
            else:
                # Fallback to stone sound if iron door sounds not loaded
                self.playSound("stone")
        else:
            # Wood doors use proper door sounds
            if isOpening and self.doorOpenSound:
                self.doorOpenSound.play()
            elif not isOpening and self.doorCloseSound:
                self.doorCloseSound.play()
    
    def playBlockSound(self, blockType: BlockType, isPlace: bool = True):
        """Play the appropriate sound for a block type"""
        if blockType in BLOCK_SOUNDS:
            soundDef = BLOCK_SOUNDS[blockType]
            category = soundDef.placeSound if isPlace else soundDef.breakSound
            
            # Special handling for glass - use stone for placing, glass for breaking
            if blockType == BlockType.GLASS:
                if isPlace:
                    category = "stone"  # Glass placing sounds like stone
                else:
                    category = "glass"  # Glass breaking has unique sound
            
            self.playSound(category)
    
    def getBlockSprite(self, blockType: BlockType) -> Optional[pygame.Surface]:
        """Get the isometric sprite for a block type"""
        return self.blockSprites.get(blockType)
    
    def getIconSprite(self, blockType: BlockType) -> Optional[pygame.Surface]:
        """Get the icon sprite for a block type"""
        return self.iconSprites.get(blockType)


# ============================================================================
# WORLD MANAGEMENT
# ============================================================================

class World:
    """
    Manages the 3D voxel grid for the building area.
    
    Uses a dictionary-based sparse storage for efficient memory usage,
    storing only non-air blocks.
    """
    
    def __init__(self, width: int, depth: int, height: int):
        """
        Initialize the world.
        
        Args:
            width: X dimension of the world
            depth: Y dimension of the world  
            height: Z dimension (vertical) of the world
        """
        self.width = width
        self.depth = depth
        self.height = height
        self.blocks: Dict[Tuple[int, int, int], BlockType] = {}
        # Block properties for special blocks (doors, slabs, stairs)
        self.blockProperties: Dict[Tuple[int, int, int], BlockProperties] = {}
        # Water/lava levels (1-8, where 8 = source)
        self.liquidLevels: Dict[Tuple[int, int, int], int] = {}
        # Separate queues for water and lava flow updates
        self.waterUpdateQueue: List[Tuple[int, int, int]] = []
        self.lavaUpdateQueue: List[Tuple[int, int, int]] = []
    
    def getBlock(self, x: int, y: int, z: int) -> BlockType:
        """Get the block type at a position"""
        if not self.isInBounds(x, y, z):
            return BlockType.AIR
        return self.blocks.get((x, y, z), BlockType.AIR)
    
    def getBlockProperties(self, x: int, y: int, z: int) -> Optional[BlockProperties]:
        """Get the properties for a block at a position (None if no special properties)"""
        return self.blockProperties.get((x, y, z))
    
    def setBlockProperties(self, x: int, y: int, z: int, props: BlockProperties):
        """Set properties for a block at a position"""
        if self.isInBounds(x, y, z):
            self.blockProperties[(x, y, z)] = props
    
    def getLiquidLevel(self, x: int, y: int, z: int) -> int:
        """Get the liquid level at a position (0 = no liquid, 8 = source)"""
        return self.liquidLevels.get((x, y, z), 0)
    
    def setBlock(self, x: int, y: int, z: int, blockType: BlockType) -> bool:
        """
        Set a block at a position.
        
        Args:
            x, y, z: Position coordinates
            blockType: Type of block to place
            
        Returns:
            True if block was placed successfully
        """
        if not self.isInBounds(x, y, z):
            return False
        
        if blockType == BlockType.AIR:
            # Remove block
            if (x, y, z) in self.blocks:
                del self.blocks[(x, y, z)]
            # Also remove liquid level
            if (x, y, z) in self.liquidLevels:
                del self.liquidLevels[(x, y, z)]
                # Queue neighbors for update (liquid might flow in)
                self._queueNeighborUpdates(x, y, z)
            # Remove block properties
            if (x, y, z) in self.blockProperties:
                del self.blockProperties[(x, y, z)]
        else:
            # Place block
            self.blocks[(x, y, z)] = blockType
            # Set liquid level for water/lava
            if blockType == BlockType.WATER:
                self.liquidLevels[(x, y, z)] = 8  # Source block
                self.waterUpdateQueue.append((x, y, z))
            elif blockType == BlockType.LAVA:
                self.liquidLevels[(x, y, z)] = 8  # Source block
                self.lavaUpdateQueue.append((x, y, z))
        
        return True
    
    def _queueNeighborUpdates(self, x: int, y: int, z: int):
        """Queue neighboring liquid blocks for update"""
        neighbors = [(x+1, y, z), (x-1, y, z), (x, y+1, z), (x, y-1, z), (x, y, z+1)]
        for nx, ny, nz in neighbors:
            block = self.getBlock(nx, ny, nz)
            if block == BlockType.WATER:
                if (nx, ny, nz) not in self.waterUpdateQueue:
                    self.waterUpdateQueue.append((nx, ny, nz))
            elif block == BlockType.LAVA:
                if (nx, ny, nz) not in self.lavaUpdateQueue:
                    self.lavaUpdateQueue.append((nx, ny, nz))
    
    def updateLiquids(self, liquidType: BlockType = None) -> List[Tuple[int, int, int, BlockType, int]]:
        """
        Process liquid flow updates for a specific type (water or lava).
        Minecraft-style flow: prioritizes flowing down, then spreads horizontally
        only when there's no downward path. Flow seeks out holes/lower areas.
        Returns list of (x, y, z, blockType, level) for changed blocks.
        """
        # Select the appropriate queue
        if liquidType == BlockType.WATER:
            queue = self.waterUpdateQueue
        elif liquidType == BlockType.LAVA:
            queue = self.lavaUpdateQueue
        else:
            return []
        
        if not queue:
            return []
        
        changes = []
        processed = set()
        
        # Process up to 3 updates per tick (reduced for performance)
        for _ in range(min(3, len(queue))):
            if not queue:
                break
                
            pos = queue.pop(0)
            if pos in processed:
                continue
            processed.add(pos)
            
            x, y, z = pos
            block = self.getBlock(x, y, z)
            level = self.getLiquidLevel(x, y, z)
            
            if block != liquidType or level <= 0:
                continue
            
            flowedDown = False
            
            # PRIORITY 1: Try to flow straight down
            if z > 0 and self.getBlock(x, y, z-1) == BlockType.AIR:
                self.blocks[(x, y, z-1)] = block
                self.liquidLevels[(x, y, z-1)] = 8  # Falling liquid is full
                changes.append((x, y, z-1, block, 8))
                queue.append((x, y, z-1))
                flowedDown = True
            
            # PRIORITY 2: Check if any horizontal neighbor has a hole below it
            # This makes water seek out holes like in Minecraft
            if level > 1 and not flowedDown:
                neighbors = [(x+1, y, z), (x-1, y, z), (x, y+1, z), (x, y-1, z)]
                newLevel = level - 1
                
                # First pass: find neighbors that lead to a drop
                neighborsWithDrop = []
                neighborsFlat = []
                
                for nx, ny, nz in neighbors:
                    if not self.isInBounds(nx, ny, nz):
                        continue
                    neighborBlock = self.getBlock(nx, ny, nz)
                    neighborLevel = self.getLiquidLevel(nx, ny, nz)
                    
                    if neighborBlock == BlockType.AIR or (neighborBlock == block and neighborLevel < newLevel):
                        # Check if this neighbor has a drop below it
                        if nz > 0 and self.getBlock(nx, ny, nz - 1) == BlockType.AIR:
                            neighborsWithDrop.append((nx, ny, nz, neighborBlock, neighborLevel))
                        else:
                            neighborsFlat.append((nx, ny, nz, neighborBlock, neighborLevel))
                
                # Prioritize neighbors that lead to a drop (seeks holes)
                prioritizedNeighbors = neighborsWithDrop + neighborsFlat
                
                for nx, ny, nz, neighborBlock, neighborLevel in prioritizedNeighbors:
                    if neighborBlock == BlockType.AIR:
                        self.blocks[(nx, ny, nz)] = block
                        self.liquidLevels[(nx, ny, nz)] = newLevel
                        changes.append((nx, ny, nz, block, newLevel))
                        if newLevel > 1:
                            queue.append((nx, ny, nz))
                    elif neighborBlock == block and neighborLevel < newLevel:
                        self.liquidLevels[(nx, ny, nz)] = newLevel
                        changes.append((nx, ny, nz, block, newLevel))
                        queue.append((nx, ny, nz))
        
        return changes
    
    def isInBounds(self, x: int, y: int, z: int) -> bool:
        """Check if coordinates are within world bounds"""
        return 0 <= x < self.width and 0 <= y < self.depth and 0 <= z < self.height
    
    def clear(self):
        """Clear all blocks from the world"""
        self.blocks.clear()
        self.blockProperties.clear()
        self.liquidLevels.clear()
        self.waterUpdateQueue.clear()
        self.lavaUpdateQueue.clear()
    
    def hasBlockType(self, blockType: BlockType) -> bool:
        """Check if the world contains any blocks of the specified type"""
        for block in self.blocks.values():
            if block == blockType:
                return True
        return False
    
    def getHighestBlock(self, x: int, y: int) -> int:
        """Get the height of the highest block at (x, y)"""
        for z in range(self.height - 1, -1, -1):
            if self.getBlock(x, y, z) != BlockType.AIR:
                return z
        return -1
    
    def placeStructure(self, structure: Dict, offsetX: int, offsetY: int, offsetZ: int):
        """
        Place a premade structure at an offset position.
        
        Args:
            structure: Structure definition dictionary
            offsetX, offsetY, offsetZ: Position offset for placement
        """
        for block in structure["blocks"]:
            x, y, z, blockType = block
            newX = x + offsetX
            newY = y + offsetY
            newZ = z + offsetZ
            
            if self.isInBounds(newX, newY, newZ):
                self.setBlock(newX, newY, newZ, blockType)


# ============================================================================
# ISOMETRIC RENDERER
# ============================================================================

class IsometricRenderer:
    """
    Handles conversion between 3D world coordinates and 2D screen coordinates
    using 2:1 dimetric (pseudo-isometric) projection.
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
    
    def worldToScreen(self, x: int, y: int, z: int) -> Tuple[int, int]:
        """
        Convert 3D world coordinates to 2D screen coordinates.
        
        Args:
            x, y, z: World coordinates
            
        Returns:
            Tuple of (screenX, screenY)
        """
        screenX = (x - y) * (TILE_WIDTH // 2) + self.offsetX
        screenY = (x + y) * (TILE_HEIGHT // 2) - z * BLOCK_HEIGHT + self.offsetY
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
        # Adjust for offset and Z level
        adjustedX = screenX - self.offsetX
        adjustedY = screenY - self.offsetY + targetZ * BLOCK_HEIGHT
        
        # Inverse of the projection formulas
        worldX = (adjustedX / (TILE_WIDTH / 2) + adjustedY / (TILE_HEIGHT / 2)) / 2
        worldY = (adjustedY / (TILE_HEIGHT / 2) - adjustedX / (TILE_WIDTH / 2)) / 2
        
        return (round(worldX), round(worldY))
    
    def setOffset(self, offsetX: int, offsetY: int):
        """Update the screen offset"""
        self.offsetX = offsetX
        self.offsetY = offsetY


# ============================================================================
# MAIN GAME CLASS
# ============================================================================

class MinecraftBuilder:
    """
    Main application class for Bite Sized Minecraft.
    
    Handles the game loop, user input, rendering, and coordination between
    the world, renderer, and asset manager.
    """
    
    def __init__(self):
        """Initialize the application"""
        # Set app icon BEFORE creating display (important for Windows taskbar)
        self._setAppIconEarly()
        
        # Set up display
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()
        self.running = True
        
        # Initialize components
        self.assetManager = AssetManager()
        self.world = World(GRID_WIDTH, GRID_DEPTH, GRID_HEIGHT)
        
        # Calculate center offset for rendering
        centerX = (WINDOW_WIDTH - PANEL_WIDTH) // 2
        centerY = WINDOW_HEIGHT // 3
        self.renderer = IsometricRenderer(centerX, centerY)
        
        # UI state
        self.selectedBlock = BlockType.GRASS
        self.hoveredCell: Optional[Tuple[int, int, int]] = None
        self.panelHovered = False
        
        # Inventory scroll state
        self.inventoryScroll = 0
        self.maxScroll = 0
        
        # Font
        self.font = pygame.font.Font(None, 24)
        self.smallFont = pygame.font.Font(None, 18)
        
        # Panning state
        self.panning = False
        self.panStartX = 0
        self.panStartY = 0
        self.panOffsetX = 0
        self.panOffsetY = 0
        
        # Structure placement mode
        self.structurePlacementMode = False
        self.selectedStructure: Optional[str] = None
        
        # Liquid flow timing (milliseconds)
        self.waterFlowDelay = 400  # Water flows every 400ms (slower, smoother)
        self.lavaFlowDelay = 1200  # Lava flows every 1200ms (3x slower than water)
        self.lastWaterFlowTime = 0
        self.lastLavaFlowTime = 0
        
        # Main section expanded state (Blocks, Problems, Experimental, Structures)
        self.blocksExpanded = False
        self.problemsExpanded = False
        self.experimentalExpanded = False
        self.structuresExpanded = False
        
        # Current dimension (affects background, floor, and music)
        self.currentDimension = DIMENSION_OVERWORLD
        
        # Sub-category expanded state (within Blocks section)
        self.expandedCategories: Dict[str, bool] = {}
        for category in CATEGORY_ORDER:
            if category != "Problems":  # Problems has its own main section
                self.expandedCategories[category] = False
    
    def _setAppIconEarly(self):
        """Set app icon BEFORE display is created (critical for Windows taskbar)"""
        iconSize = 32
        icon = pygame.Surface((iconSize, iconSize), pygame.SRCALPHA)
        
        # Load textures directly (before AssetManager is created)
        # Note: Don't use convert_alpha() before display is set
        topPath = os.path.join(TEXTURES_DIR, "grass_block_top.png")
        sidePath = os.path.join(TEXTURES_DIR, "grass_block_side.png")
        
        if os.path.exists(topPath) and os.path.exists(sidePath):
            topTex = pygame.image.load(topPath)
            sideTex = pygame.image.load(sidePath)
            
            # Manual tinting for grass
            topTex = self._tintTextureSimple(topTex, GRASS_TINT)
            
            texSize = 16
            topTex = pygame.transform.scale(topTex, (texSize, texSize))
            sideTex = pygame.transform.scale(sideTex, (texSize, texSize))
            
            W = iconSize
            H = iconSize
            halfW = W // 2
            tileH = W // 4
            blockH = W // 2
            
            # Define face polygons
            topPoints = [(halfW, 0), (W-1, tileH), (halfW, tileH*2-1), (0, tileH)]
            leftPoints = [(0, tileH), (halfW, tileH*2-1), (halfW, H-1), (0, tileH + blockH-1)]
            rightPoints = [(halfW, tileH*2-1), (W-1, tileH), (W-1, tileH + blockH-1), (halfW, H-1)]
            
            # Get average colors
            topAvg = self._getAvgColor(topTex)
            sideAvg = self._getAvgColor(sideTex)
            leftAvg = (int(sideAvg[0]*0.7), int(sideAvg[1]*0.7), int(sideAvg[2]*0.7))
            rightAvg = (int(sideAvg[0]*0.85), int(sideAvg[1]*0.85), int(sideAvg[2]*0.85))
            
            # Fill faces
            pygame.draw.polygon(icon, topAvg, topPoints)
            pygame.draw.polygon(icon, leftAvg, leftPoints)
            pygame.draw.polygon(icon, rightAvg, rightPoints)
            
            # Draw outline
            outlineColor = (20, 20, 20)
            pygame.draw.polygon(icon, outlineColor, topPoints, 1)
            pygame.draw.polygon(icon, outlineColor, leftPoints, 1)
            pygame.draw.polygon(icon, outlineColor, rightPoints, 1)
            
            pygame.display.set_icon(icon)
    
    def _tintTextureSimple(self, texture: pygame.Surface, tint: Tuple[int, int, int]) -> pygame.Surface:
        """Simple texture tinting (used before AssetManager exists)"""
        tinted = texture.copy()
        tinted.lock()
        for y in range(texture.get_height()):
            for x in range(texture.get_width()):
                color = texture.get_at((x, y))
                intensity = color.r / 255.0
                newR = int(tint[0] * intensity)
                newG = int(tint[1] * intensity)
                newB = int(tint[2] * intensity)
                tinted.set_at((x, y), (newR, newG, newB, color.a))
        tinted.unlock()
        return tinted
    
    def _getAvgColor(self, surface: pygame.Surface) -> Tuple[int, int, int]:
        """Get average color of a surface"""
        total_r, total_g, total_b = 0, 0, 0
        count = 0
        for y in range(surface.get_height()):
            for x in range(surface.get_width()):
                color = surface.get_at((x, y))
                if color.a > 0:
                    total_r += color.r
                    total_g += color.g
                    total_b += color.b
                    count += 1
        if count > 0:
            return (total_r // count, total_g // count, total_b // count)
        return (128, 128, 128)
    
    def _setAppIcon(self):
        """Update app icon with high quality version (called after assets load)"""
        # On Windows, re-set the icon AFTER display is created to ensure taskbar shows it
        iconSize = 32
        icon = pygame.Surface((iconSize, iconSize), pygame.SRCALPHA)
        
        # Try to get grass textures from loaded assets
        topTex = self.assetManager.textures.get("grass_block_top")
        sideTex = self.assetManager.textures.get("grass_block_side")
        
        if topTex and sideTex:
            texSize = 16
            topTex = pygame.transform.scale(topTex, (texSize, texSize))
            sideTex = pygame.transform.scale(sideTex, (texSize, texSize))
            
            W = iconSize
            H = iconSize
            halfW = W // 2
            tileH = W // 4
            blockH = W // 2
            
            # Define face polygons
            topPoints = [(halfW, 0), (W-1, tileH), (halfW, tileH*2-1), (0, tileH)]
            leftPoints = [(0, tileH), (halfW, tileH*2-1), (halfW, H-1), (0, tileH + blockH-1)]
            rightPoints = [(halfW, tileH*2-1), (W-1, tileH), (W-1, tileH + blockH-1), (halfW, H-1)]
            
            # Get average colors and apply to faces
            topAvg = self.assetManager._getAverageColor(topTex)
            sideAvg = self.assetManager._getAverageColor(sideTex)
            leftAvg = (int(sideAvg[0]*0.7), int(sideAvg[1]*0.7), int(sideAvg[2]*0.7))
            rightAvg = (int(sideAvg[0]*0.85), int(sideAvg[1]*0.85), int(sideAvg[2]*0.85))
            
            # Fill faces
            pygame.draw.polygon(icon, topAvg, topPoints)
            pygame.draw.polygon(icon, leftAvg, leftPoints)
            pygame.draw.polygon(icon, rightAvg, rightPoints)
            
            # Draw outline
            outlineColor = (20, 20, 20)
            pygame.draw.polygon(icon, outlineColor, topPoints, 1)
            pygame.draw.polygon(icon, outlineColor, leftPoints, 1)
            pygame.draw.polygon(icon, outlineColor, rightPoints, 1)
            
            pygame.display.set_icon(icon)
    
    def run(self):
        """Main application loop"""
        # Load assets
        if not self.assetManager.loadAllAssets():
            print("Failed to load assets!")
            return
        
        # Set 3D app icon (after assets loaded)
        self._setAppIcon()
        
        # Play random menu music
        self._playMenuMusic()
        
        # Create initial floor
        self._createInitialFloor()
        
        print("\n=== Bite Sized Minecraft Started ===")
        print("Controls:")
        print("  Left Click: Place block / Select from panel")
        print("  Right Click: Remove block / Open-Close doors")
        print("  Middle Click + Drag: Pan view")
        print("  1-5: Select block type")
        print("  H: Place house structure")
        print("  T: Place tree structure")
        print("  R: Rotate stairs")
        print("  F: Flip slab (top/bottom)")
        print("  C: Clear world")
        print("  ESC: Quit")
        print("================================\n")
        
        # Main loop
        while self.running:
            self._handleEvents()
            self._update()
            self._render()
            self.clock.tick(60)
        
        pygame.mixer.music.stop()
        pygame.quit()
    
    def _playMenuMusic(self, dimension: str = None):
        """Play a random song based on dimension"""
        if dimension is None:
            dimension = self.currentDimension
        
        # Choose music directory based on dimension
        if dimension == DIMENSION_NETHER:
            musicDir = MUSIC_DIR_NETHER
        elif dimension == DIMENSION_END:
            musicDir = MUSIC_DIR_END
        else:
            musicDir = MUSIC_DIR
        
        # Collect all ogg files recursively (for nether subdirectories)
        musicFiles = []
        if os.path.exists(musicDir):
            for root, dirs, files in os.walk(musicDir):
                for f in files:
                    if f.endswith('.ogg'):
                        musicFiles.append(os.path.join(root, f))
        
        if musicFiles:
            selectedPath = random.choice(musicFiles)
            selectedName = os.path.basename(selectedPath)
            try:
                pygame.mixer.music.load(selectedPath)
                pygame.mixer.music.set_volume(0.3)
                pygame.mixer.music.play(-1)  # Loop indefinitely
                print(f"Now playing: {selectedName}")
            except Exception as e:
                print(f"Could not play music: {e}")
    
    def _createInitialFloor(self, dimension: str = None):
        """Create an initial floor for building on based on dimension"""
        if dimension is None:
            dimension = self.currentDimension
        
        # Choose floor block type based on dimension
        if dimension == DIMENSION_NETHER:
            floorBlock = BlockType.NETHERRACK
        elif dimension == DIMENSION_END:
            floorBlock = BlockType.END_STONE
        else:
            floorBlock = BlockType.GRASS
        
        for x in range(GRID_WIDTH):
            for y in range(GRID_DEPTH):
                self.world.setBlock(x, y, 0, floorBlock)
    
    def _switchDimension(self, newDimension: str):
        """Switch to a different dimension (changes background, floor, and music)"""
        if newDimension == self.currentDimension:
            return  # Already in this dimension
        
        self.currentDimension = newDimension
        
        # Update background
        self.assetManager._createBackground(newDimension)
        
        # Clear and recreate floor
        self.world.clear()
        self._createInitialFloor(newDimension)
        
        # Switch music
        self._playMenuMusic(newDimension)
        
        dimensionName = newDimension.capitalize()
        print(f"Switched to {dimensionName} dimension")
    
    def _handleEvents(self):
        """Handle pygame events"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                self._handleMouseDown(event)
            
            elif event.type == pygame.MOUSEBUTTONUP:
                self._handleMouseUp(event)
            
            elif event.type == pygame.MOUSEMOTION:
                self._handleMouseMotion(event)
            
            elif event.type == pygame.KEYDOWN:
                self._handleKeyDown(event)
            
            elif event.type == pygame.MOUSEWHEEL:
                self._handleMouseWheel(event)
    
    def _handleMouseWheel(self, event):
        """Handle mouse wheel scrolling for inventory"""
        mouseX, mouseY = pygame.mouse.get_pos()
        
        # Only scroll if mouse is over the panel
        if mouseX > WINDOW_WIDTH - PANEL_WIDTH:
            # Scroll speed
            scrollAmount = 30
            
            # event.y is positive when scrolling up, negative when scrolling down
            self.inventoryScroll -= event.y * scrollAmount
            
            # Clamp scroll to valid range
            self.inventoryScroll = max(0, min(self.inventoryScroll, self.maxScroll))
    
    def _handleMouseDown(self, event):
        """Handle mouse button press"""
        mouseX, mouseY = event.pos
        
        # Check if clicking on panel
        if mouseX > WINDOW_WIDTH - PANEL_WIDTH:
            if event.button == 1:  # Left click
                self._handlePanelClick(mouseX, mouseY)
                self.assetManager.playClickSound()
            return
        
        if event.button == 1:  # Left click - place block
            if self.structurePlacementMode and self.selectedStructure:
                self._placeStructureAtMouse(mouseX, mouseY)
                self.structurePlacementMode = False
                self.selectedStructure = None
            else:
                self._placeBlockAtMouse(mouseX, mouseY)
        
        elif event.button == 3:  # Right click - interact or remove block
            # First try to interact with doors
            if self.hoveredCell:
                x, y, z = self.hoveredCell
                # Check if there's a door at or below the hover position
                for checkZ in range(z, -1, -1):
                    blockType = self.world.getBlock(x, y, checkZ)
                    if blockType != BlockType.AIR:
                        # Try to toggle door first
                        if self._toggleDoor(x, y, checkZ):
                            return
                        break
            # If not a door, remove the block
            self._removeBlockAtMouse(mouseX, mouseY)
        
        elif event.button == 2:  # Middle click - start panning
            self.panning = True
            self.panStartX = mouseX
            self.panStartY = mouseY
    
    def _handleMouseUp(self, event):
        """Handle mouse button release"""
        if event.button == 2:  # Middle click release
            self.panning = False
    
    def _handleMouseMotion(self, event):
        """Handle mouse movement"""
        mouseX, mouseY = event.pos
        
        # Check panel hover
        self.panelHovered = mouseX > WINDOW_WIDTH - PANEL_WIDTH
        
        # Handle panning
        if self.panning:
            dx = mouseX - self.panStartX
            dy = mouseY - self.panStartY
            self.renderer.offsetX += dx
            self.renderer.offsetY += dy
            self.panStartX = mouseX
            self.panStartY = mouseY
            return
        
        # Update hovered cell
        if not self.panelHovered:
            self._updateHoveredCell(mouseX, mouseY)
        else:
            self.hoveredCell = None
    
    def _handleKeyDown(self, event):
        """Handle keyboard input"""
        if event.key == pygame.K_ESCAPE:
            self.running = False
        
        elif event.key == pygame.K_1:
            self.selectedBlock = BlockType.GRASS
            self.assetManager.playClickSound()
        elif event.key == pygame.K_2:
            self.selectedBlock = BlockType.DIRT
            self.assetManager.playClickSound()
        elif event.key == pygame.K_3:
            self.selectedBlock = BlockType.STONE
            self.assetManager.playClickSound()
        elif event.key == pygame.K_4:
            self.selectedBlock = BlockType.OAK_PLANKS
            self.assetManager.playClickSound()
        elif event.key == pygame.K_5:
            self.selectedBlock = BlockType.COBBLESTONE
            self.assetManager.playClickSound()
        
        elif event.key == pygame.K_h:
            self.structurePlacementMode = True
            self.selectedStructure = "house"
            print("House placement mode - click to place")
        
        elif event.key == pygame.K_t:
            self.structurePlacementMode = True
            self.selectedStructure = "tree"
            print("Tree placement mode - click to place")
        
        elif event.key == pygame.K_c:
            self.world.clear()
            if hasattr(self, 'liquidSpriteCache'):
                self.liquidSpriteCache.clear()
            self._createInitialFloor()
            self.assetManager.playSound("stone")
            print("World cleared")
        
        elif event.key == pygame.K_r:
            # Rotate hovered block (if it's a special block)
            self._rotateHoveredBlock()
        
        elif event.key == pygame.K_f:
            # Toggle slab position (top/bottom)
            self._toggleSlabPosition()
    
    def _handlePanelClick(self, mouseX: int, mouseY: int):
        """Handle click on the inventory panel with three main dropdown buttons"""
        panelX = mouseX - (WINDOW_WIDTH - PANEL_WIDTH)
        panelY = mouseY
        
        # Layout settings matching _renderPanel
        mainButtonHeight = 35
        subCategoryHeight = 24
        slotSize = ICON_SIZE + 8
        headerHeight = 10
        startY = headerHeight
        
        # Track current Y position (matching _renderPanel)
        currentY = startY - self.inventoryScroll
        
        # ===== CHECK BLOCKS MAIN BUTTON =====
        blocksTop = currentY
        blocksBottom = currentY + mainButtonHeight
        
        if blocksTop <= panelY <= blocksBottom and ICON_MARGIN <= panelX <= PANEL_WIDTH - ICON_MARGIN:
            self.blocksExpanded = not self.blocksExpanded
            return
        
        currentY += mainButtonHeight + 5
        
        # Check blocks sub-content if expanded
        if self.blocksExpanded:
            for category in CATEGORY_ORDER:
                if category == "Problematic":
                    continue
                
                blocks = BLOCK_CATEGORIES.get(category, [])
                isExpanded = self.expandedCategories.get(category, False)
                
                # Check sub-category header
                subHeaderTop = currentY
                subHeaderBottom = currentY + subCategoryHeight
                
                if subHeaderTop <= panelY <= subHeaderBottom and 15 <= panelX <= PANEL_WIDTH - 15:
                    self.expandedCategories[category] = not self.expandedCategories[category]
                    return
                
                currentY += subCategoryHeight
                
                # Check block buttons if sub-category expanded
                if isExpanded:
                    blocksStartY = currentY + 2
                    
                    for i, blockType in enumerate(blocks):
                        row = i // ICONS_PER_ROW
                        col = i % ICONS_PER_ROW
                        
                        btnX = ICON_MARGIN + col * (slotSize + 4)
                        btnY = blocksStartY + row * (slotSize + 4)
                        
                        if btnX <= panelX <= btnX + slotSize and btnY <= panelY <= btnY + slotSize:
                            self.selectedBlock = blockType
                            return
                    
                    numRows = (len(blocks) + ICONS_PER_ROW - 1) // ICONS_PER_ROW
                    currentY += numRows * (slotSize + 4) + 5
            
            currentY += 5
        
        # ===== CHECK PROBLEMS MAIN BUTTON =====
        problemsTop = currentY
        problemsBottom = currentY + mainButtonHeight
        
        if problemsTop <= panelY <= problemsBottom and ICON_MARGIN <= panelX <= PANEL_WIDTH - ICON_MARGIN:
            self.problemsExpanded = not self.problemsExpanded
            return
        
        currentY += mainButtonHeight + 5
        
        # Check problematic blocks if expanded
        if self.problemsExpanded:
            problemBlocks = BLOCK_CATEGORIES.get("Problematic", [])
            blocksStartY = currentY + 2
            
            for i, blockType in enumerate(problemBlocks):
                row = i // ICONS_PER_ROW
                col = i % ICONS_PER_ROW
                
                btnX = ICON_MARGIN + col * (slotSize + 4)
                btnY = blocksStartY + row * (slotSize + 4)
                
                if btnX <= panelX <= btnX + slotSize and btnY <= panelY <= btnY + slotSize:
                    self.selectedBlock = blockType
                    return
            
            numRows = (len(problemBlocks) + ICONS_PER_ROW - 1) // ICONS_PER_ROW
            currentY += numRows * (slotSize + 4) + 10
        
        # ===== CHECK EXPERIMENTAL MAIN BUTTON =====
        experimentalTop = currentY
        experimentalBottom = currentY + mainButtonHeight
        
        if experimentalTop <= panelY <= experimentalBottom and ICON_MARGIN <= panelX <= PANEL_WIDTH - ICON_MARGIN:
            self.experimentalExpanded = not self.experimentalExpanded
            return
        
        currentY += mainButtonHeight + 5
        
        # Check dimension buttons if expanded
        if self.experimentalExpanded:
            dimensions = [
                (DIMENSION_OVERWORLD, "Overworld"),
                (DIMENSION_NETHER, "Nether"),
                (DIMENSION_END, "End")
            ]
            dimY = currentY + 2
            
            for dimKey, dimName in dimensions:
                if dimY <= panelY <= dimY + 30 and ICON_MARGIN + 10 <= panelX <= PANEL_WIDTH - ICON_MARGIN - 10:
                    self._switchDimension(dimKey)
                    return
                dimY += 35
            
            currentY = dimY + 5
        
        # ===== CHECK STRUCTURES MAIN BUTTON =====
        structuresTop = currentY
        structuresBottom = currentY + mainButtonHeight
        
        if structuresTop <= panelY <= structuresBottom and ICON_MARGIN <= panelX <= PANEL_WIDTH - ICON_MARGIN:
            self.structuresExpanded = not self.structuresExpanded
            return
        
        currentY += mainButtonHeight + 5
        
        # Check structure buttons if expanded
        if self.structuresExpanded:
            structureY = currentY + 2
            
            for structName, structData in PREMADE_STRUCTURES.items():
                if structureY <= panelY <= structureY + 30 and ICON_MARGIN + 10 <= panelX <= PANEL_WIDTH - ICON_MARGIN - 10:
                    self.structurePlacementMode = True
                    self.selectedStructure = structName
                    print(f"{structData['name']} placement mode - click to place")
                    return
                structureY += 35
    
    def _updateHoveredCell(self, mouseX: int, mouseY: int):
        """Update the currently hovered cell"""
        # Try different Z levels from top to bottom
        for z in range(GRID_HEIGHT - 1, -1, -1):
            worldX, worldY = self.renderer.screenToWorld(mouseX, mouseY, z)
            
            if self.world.isInBounds(worldX, worldY, z):
                # Check if there's a block at this position or we can place on top
                if self.world.getBlock(worldX, worldY, z) != BlockType.AIR:
                    # Hovered on existing block - target position is on top
                    if z + 1 < GRID_HEIGHT:
                        self.hoveredCell = (worldX, worldY, z + 1)
                    else:
                        self.hoveredCell = (worldX, worldY, z)
                    return
        
        # Default to ground level
        worldX, worldY = self.renderer.screenToWorld(mouseX, mouseY, 0)
        if self.world.isInBounds(worldX, worldY, 0):
            highestZ = self.world.getHighestBlock(worldX, worldY)
            targetZ = min(highestZ + 1, GRID_HEIGHT - 1)
            self.hoveredCell = (worldX, worldY, targetZ)
        else:
            self.hoveredCell = None
    
    def _placeBlockAtMouse(self, mouseX: int, mouseY: int):
        """Place a block at the mouse position"""
        if self.hoveredCell:
            x, y, z = self.hoveredCell
            if self.world.setBlock(x, y, z, self.selectedBlock):
                self.assetManager.playBlockSound(self.selectedBlock, isPlace=True)
                
                # Set properties for special blocks
                blockDef = BLOCK_DEFINITIONS.get(self.selectedBlock)
                if blockDef:
                    if blockDef.isDoor or blockDef.isStair or blockDef.isSlab:
                        # Determine facing based on camera/cursor position
                        # Default facing towards the camera (SOUTH)
                        # Later can make this smarter based on where player is looking
                        facing = self._determineFacing(x, y)
                        props = BlockProperties(
                            facing=facing,
                            isOpen=False,
                            slabPosition=SlabPosition.BOTTOM
                        )
                        self.world.setBlockProperties(x, y, z, props)
    
    def _determineFacing(self, blockX: int, blockY: int) -> Facing:
        """Determine which direction a placed block should face based on cursor position"""
        # For now, default to SOUTH (facing the camera) 
        # Can be made smarter later to face away from adjacent blocks or towards player
        return Facing.SOUTH
    
    def _rotateHoveredBlock(self):
        """Rotate the block under the cursor (stairs only - doors use right-click to open/close)"""
        if not self.hoveredCell:
            return
        
        x, y, z = self.hoveredCell
        # Check block below hover position (hover is where new block would go)
        for checkZ in range(z, -1, -1):
            blockType = self.world.getBlock(x, y, checkZ)
            if blockType != BlockType.AIR:
                blockDef = BLOCK_DEFINITIONS.get(blockType)
                # Only stairs can rotate - doors open/close with right-click
                if blockDef and blockDef.isStair:
                    props = self.world.getBlockProperties(x, y, checkZ)
                    if props:
                        # Rotate clockwise: NORTH -> EAST -> SOUTH -> WEST -> NORTH
                        newFacing = Facing((props.facing.value + 1) % 4)
                        props.facing = newFacing
                        self.world.setBlockProperties(x, y, checkZ, props)
                        self.assetManager.playClickSound()
                        print(f"Rotated {blockType.name} to face {newFacing.name}")
                return
    
    def _toggleSlabPosition(self):
        """Toggle the slab position (top/bottom) of hovered slab"""
        if not self.hoveredCell:
            return
        
        x, y, z = self.hoveredCell
        # Check block below hover position
        for checkZ in range(z, -1, -1):
            blockType = self.world.getBlock(x, y, checkZ)
            if blockType != BlockType.AIR:
                blockDef = BLOCK_DEFINITIONS.get(blockType)
                if blockDef and blockDef.isSlab:
                    props = self.world.getBlockProperties(x, y, checkZ)
                    if props:
                        # Toggle between BOTTOM and TOP
                        if props.slabPosition == SlabPosition.BOTTOM:
                            props.slabPosition = SlabPosition.TOP
                        else:
                            props.slabPosition = SlabPosition.BOTTOM
                        self.world.setBlockProperties(x, y, checkZ, props)
                        self.assetManager.playClickSound()
                        print(f"Toggled slab to {props.slabPosition.name}")
                return
    
    def _toggleDoor(self, x: int, y: int, z: int):
        """Toggle a door open/closed at the given position"""
        blockType = self.world.getBlock(x, y, z)
        blockDef = BLOCK_DEFINITIONS.get(blockType)
        if blockDef and blockDef.isDoor:
            props = self.world.getBlockProperties(x, y, z)
            if props:
                props.isOpen = not props.isOpen
                self.world.setBlockProperties(x, y, z, props)
                # Play proper door open/close sound (pass blockType for iron/wood)
                self.assetManager.playDoorSound(props.isOpen, blockType)
                print(f"Door {'opened' if props.isOpen else 'closed'}")
                return True
        return False
    
    def _removeBlockAtMouse(self, mouseX: int, mouseY: int):
        """Remove a block at the mouse position"""
        # First, try the hoveredCell approach - it already found the block
        if self.hoveredCell:
            x, y, z = self.hoveredCell
            # The hovered cell points to where we'd place a new block (one above the existing)
            # So check the block at z-1 first
            for checkZ in range(z, -1, -1):
                blockType = self.world.getBlock(x, y, checkZ)
                if blockType != BlockType.AIR:
                    self.world.setBlock(x, y, checkZ, BlockType.AIR)
                    # Clean up liquid sprite cache
                    if hasattr(self, 'liquidSpriteCache') and (x, y, checkZ) in self.liquidSpriteCache:
                        del self.liquidSpriteCache[(x, y, checkZ)]
                    self.assetManager.playBlockSound(blockType, isPlace=False)
                    print(f"Removed {blockType.name} at ({x}, {y}, {checkZ})")
                    return
        
        # Fallback: Try all blocks in a small area around where we clicked
        # Check multiple possible world coordinates at each Z level
        for z in range(GRID_HEIGHT - 1, -1, -1):
            worldX, worldY = self.renderer.screenToWorld(mouseX, mouseY, z)
            
            # Check the exact position and neighboring cells
            for dx in range(-1, 2):
                for dy in range(-1, 2):
                    checkX = worldX + dx
                    checkY = worldY + dy
                    
                    if self.world.isInBounds(checkX, checkY, z):
                        blockType = self.world.getBlock(checkX, checkY, z)
                        if blockType != BlockType.AIR:
                            # Verify this block is actually under the mouse by checking screen position
                            blockScreenX, blockScreenY = self.renderer.worldToScreen(checkX, checkY, z)
                            # Check if mouse is within the block's visual bounds
                            if (abs(mouseX - blockScreenX - TILE_WIDTH//2) < TILE_WIDTH//2 + 5 and
                                abs(mouseY - blockScreenY - TILE_HEIGHT//2) < TILE_HEIGHT//2 + BLOCK_HEIGHT//2 + 5):
                                self.world.setBlock(checkX, checkY, z, BlockType.AIR)
                                # Clean up liquid sprite cache
                                if hasattr(self, 'liquidSpriteCache') and (checkX, checkY, z) in self.liquidSpriteCache:
                                    del self.liquidSpriteCache[(checkX, checkY, z)]
                                self.assetManager.playBlockSound(blockType, isPlace=False)
                                print(f"Removed {blockType.name} at ({checkX}, {checkY}, {z})")
                                return
    
    def _placeStructureAtMouse(self, mouseX: int, mouseY: int):
        """Place a structure at the mouse position"""
        if self.hoveredCell and self.selectedStructure:
            x, y, z = self.hoveredCell
            structure = PREMADE_STRUCTURES.get(self.selectedStructure)
            if structure:
                self.world.placeStructure(structure, x, y, z)
                # Play appropriate sound for structure type
                if self.selectedStructure == "end_portal":
                    self.assetManager.playSound("end_portal")
                elif self.selectedStructure == "nether_portal":
                    self.assetManager.playSound("nether_bricks")
                else:
                    self.assetManager.playSound("wood")
                print(f"Placed {structure['name']} at ({x}, {y}, {z})")
    
    def _update(self):
        """Update game state"""
        # Update liquid animations
        dt = self.clock.get_time()  # Time since last frame in ms
        self.assetManager.updateAnimation(dt)
        
        # Update liquid flow
        self._updateLiquidFlow()
        
        # Update portal ambient sound based on portal presence
        self._updatePortalSound()
        
        # Update spawner particles
        self._updateSpawnerParticles(dt)
    
    def _updateLiquidFlow(self):
        """Process liquid flow updates with separate timing for water and lava"""
        currentTime = pygame.time.get_ticks()
        allChanges = []
        
        # Update water if enough time has passed
        if currentTime - self.lastWaterFlowTime >= self.waterFlowDelay:
            waterChanges = self.world.updateLiquids(BlockType.WATER)
            allChanges.extend(waterChanges)
            self.lastWaterFlowTime = currentTime
        
        # Update lava if enough time has passed (slower)
        if currentTime - self.lastLavaFlowTime >= self.lavaFlowDelay:
            lavaChanges = self.world.updateLiquids(BlockType.LAVA)
            allChanges.extend(lavaChanges)
            self.lastLavaFlowTime = currentTime
        
        # Ensure sprite cache exists
        if not hasattr(self, 'liquidSpriteCache'):
            self.liquidSpriteCache = {}
        
        # Track last animation frames to only regenerate when animation changes
        if not hasattr(self, 'lastWaterFrame'):
            self.lastWaterFrame = -1
        if not hasattr(self, 'lastLavaFrame'):
            self.lastLavaFrame = -1
        
        # Only regenerate sprites when animation frame changes (much more efficient)
        waterFrameChanged = self.assetManager.currentWaterFrame != self.lastWaterFrame
        lavaFrameChanged = self.assetManager.currentLavaFrame != self.lastLavaFrame
        
        if waterFrameChanged or lavaFrameChanged:
            for pos in list(self.liquidSpriteCache.keys()):
                x, y, z = pos
                blockType = self.world.getBlock(x, y, z)
                if blockType == BlockType.WATER and waterFrameChanged:
                    level = self.world.getLiquidLevel(x, y, z)
                    self.liquidSpriteCache[pos] = self.assetManager.createLiquidAtLevel(True, level)
                elif blockType == BlockType.LAVA and lavaFrameChanged:
                    level = self.world.getLiquidLevel(x, y, z)
                    self.liquidSpriteCache[pos] = self.assetManager.createLiquidAtLevel(False, level)
            
            self.lastWaterFrame = self.assetManager.currentWaterFrame
            self.lastLavaFrame = self.assetManager.currentLavaFrame
        
        # Update sprites for new flowing blocks only
        for x, y, z, blockType, level in allChanges:
            isWater = blockType == BlockType.WATER
            sprite = self.assetManager.createLiquidAtLevel(isWater, level)
            self.liquidSpriteCache[(x, y, z)] = sprite
    
    def _updatePortalSound(self):
        """Check for portal blocks and play/stop ambient sound accordingly"""
        # Check if any portal blocks exist in the world
        hasPortal = self.world.hasBlockType(BlockType.NETHER_PORTAL)
        
        if hasPortal:
            # Start playing portal ambient sound if not already playing
            if self.assetManager.portalAmbientSound:
                if self.assetManager.portalSoundChannel is None or not self.assetManager.portalSoundChannel.get_busy():
                    self.assetManager.portalSoundChannel = self.assetManager.portalAmbientSound.play(-1)  # Loop forever
        else:
            # Stop portal sound if no portals exist
            if self.assetManager.portalSoundChannel and self.assetManager.portalSoundChannel.get_busy():
                self.assetManager.portalSoundChannel.stop()
                self.assetManager.portalSoundChannel = None
    
    def _updateSpawnerParticles(self, dt: int):
        """Update and spawn particles for mob spawners"""
        import random
        
        # Initialize particle list if needed
        if not hasattr(self, 'spawnerParticleList'):
            self.spawnerParticleList = []
            self.spawnerSpawnTimer = 0
        
        self.spawnerSpawnTimer += dt
        
        # Spawn new particles every 80ms
        if self.spawnerSpawnTimer >= 80:
            self.spawnerSpawnTimer = 0
            
            # Find all spawners in the world
            for (x, y, z), blockType in self.world.blocks.items():
                if blockType == BlockType.MOB_SPAWNER:
                    # Spawn 1-2 particles per spawner
                    for _ in range(random.randint(1, 2)):
                        # Random position around the spawner
                        px = x + random.uniform(-0.3, 0.3)
                        py = y + random.uniform(-0.3, 0.3)
                        pz = z + random.uniform(0, 0.5)
                        
                        # Particle properties
                        particle = {
                            "x": x, "y": y, "z": z,  # Block position for sorting
                            "px": px, "py": py, "pz": pz,  # Actual position
                            "vx": random.uniform(-0.02, 0.02),
                            "vy": random.uniform(-0.02, 0.02),
                            "vz": random.uniform(0.01, 0.03),  # Float upward
                            "life": random.randint(15, 30),
                            "color": random.choice([
                                (255, 100, 50),   # Orange flame
                                (255, 200, 100),  # Yellow
                                (255, 150, 50),   # Orange-yellow
                            ])
                        }
                        self.spawnerParticleList.append(particle)
        
        # Update existing particles
        for particle in self.spawnerParticleList[:]:
            particle["life"] -= 1
            particle["px"] += particle["vx"]
            particle["py"] += particle["vy"]
            particle["pz"] += particle["vz"]
            
            if particle["life"] <= 0:
                self.spawnerParticleList.remove(particle)

    def _render(self):
        """Render the game"""
        # Draw tiled dirt background
        self.assetManager.drawBackground(self.screen)
        
        # Draw grid and blocks
        self._renderWorld()
        
        # Draw ghost block preview
        if self.hoveredCell and not self.panelHovered and not self.structurePlacementMode:
            self._renderGhostBlock()
        
        # Draw UI panel
        self._renderPanel()
        
        # Draw status text
        self._renderStatus()
        
        # Update display
        pygame.display.flip()
    
    def _renderWorld(self):
        """Render the world blocks in correct order"""
        # Collect all blocks with their sort keys
        blocksToDraw = []
        
        for (x, y, z), blockType in self.world.blocks.items():
            sortKey = x + y + z  # Painter's algorithm sort key
            blocksToDraw.append((sortKey, x, y, z, blockType))
        
        # Sort by depth (furthest first)
        blocksToDraw.sort(key=lambda b: b[0])
        
        # Draw blocks
        for _, x, y, z, blockType in blocksToDraw:
            screenX, screenY = self.renderer.worldToScreen(x, y, z)
            
            # Check if this is a liquid with a specific level
            if blockType in (BlockType.WATER, BlockType.LAVA):
                level = self.world.getLiquidLevel(x, y, z)
                if level < 8 and level > 0:
                    # Use cached level sprite or generate one
                    if hasattr(self, 'liquidSpriteCache') and (x, y, z) in self.liquidSpriteCache:
                        sprite = self.liquidSpriteCache[(x, y, z)]
                    else:
                        isWater = blockType == BlockType.WATER
                        sprite = self.assetManager.createLiquidAtLevel(isWater, level)
                        if not hasattr(self, 'liquidSpriteCache'):
                            self.liquidSpriteCache = {}
                        self.liquidSpriteCache[(x, y, z)] = sprite
                else:
                    sprite = self.assetManager.getBlockSprite(blockType)
            else:
                # Check for special blocks with properties
                blockDef = BLOCK_DEFINITIONS.get(blockType)
                props = self.world.getBlockProperties(x, y, z)
                
                if blockDef and blockDef.isDoor and props:
                    # Door - use open/closed state only
                    key = (blockType, props.isOpen)
                    sprite = self.assetManager.doorSprites.get(key)
                    if not sprite:
                        sprite = self.assetManager.getBlockSprite(blockType)
                elif blockDef and blockDef.isStair and props:
                    # Stair - use facing
                    key = (blockType, props.facing)
                    sprite = self.assetManager.stairSprites.get(key)
                    if not sprite:
                        sprite = self.assetManager.getBlockSprite(blockType)
                elif blockDef and blockDef.isSlab and props:
                    # Slab - use position
                    key = (blockType, props.slabPosition)
                    sprite = self.assetManager.slabSprites.get(key)
                    if not sprite:
                        sprite = self.assetManager.getBlockSprite(blockType)
                else:
                    sprite = self.assetManager.getBlockSprite(blockType)
            
            if sprite:
                # worldToScreen returns the TOP vertex of the tile diamond
                # Sprite's top vertex is at (TILE_WIDTH // 2, 0), so offset to align
                drawX = screenX - TILE_WIDTH // 2
                drawY = screenY
                
                # Doors are 2 blocks tall - shift up by one block height
                blockDef = BLOCK_DEFINITIONS.get(blockType)
                if blockDef and blockDef.isDoor:
                    drawY -= BLOCK_HEIGHT
                
                self.screen.blit(sprite, (drawX, drawY))
        
        # Render spawner particles
        self._renderSpawnerParticles()
    
    def _renderSpawnerParticles(self):
        """Render spawner flame particles"""
        if not hasattr(self, 'spawnerParticleList'):
            return
        
        for particle in self.spawnerParticleList:
            # Convert world position to screen
            screenX, screenY = self.renderer.worldToScreen(
                particle["px"], particle["py"], particle["pz"]
            )
            
            # Particle size based on life (shrinks as it fades)
            size = max(1, min(4, particle["life"] // 8 + 1))
            
            # Fade alpha based on life
            alpha = min(255, particle["life"] * 12)
            
            # Draw particle as a small glowing circle
            color = particle["color"]
            particleSurf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(particleSurf, (*color, alpha), (size, size), size)
            
            self.screen.blit(particleSurf, (int(screenX) - size, int(screenY) - size))
    
    def _renderGhostBlock(self):
        """Render a transparent preview of the block to be placed"""
        x, y, z = self.hoveredCell
        screenX, screenY = self.renderer.worldToScreen(x, y, z)
        
        sprite = self.assetManager.getBlockSprite(self.selectedBlock)
        if sprite:
            # Create transparent copy
            ghostSprite = sprite.copy()
            ghostSprite.set_alpha(128)
            
            drawX = screenX - TILE_WIDTH // 2
            drawY = screenY
            self.screen.blit(ghostSprite, (drawX, drawY))
    
    def _renderPanel(self):
        """Render the inventory panel with three main dropdown buttons: Blocks, Problems, Structures"""
        panelRect = pygame.Rect(WINDOW_WIDTH - PANEL_WIDTH, 0, PANEL_WIDTH, WINDOW_HEIGHT)
        panelX = WINDOW_WIDTH - PANEL_WIDTH
        
        # Panel background - darker dirt-style
        if self.assetManager.backgroundTile:
            tileSize = self.assetManager.backgroundTile.get_width()
            for y in range(0, WINDOW_HEIGHT, tileSize):
                for x in range(panelX, WINDOW_WIDTH, tileSize):
                    darkTile = self.assetManager.backgroundTile.copy()
                    darkTile.fill((70, 70, 70), special_flags=pygame.BLEND_RGB_MULT)
                    self.screen.blit(darkTile, (x, y))
        else:
            pygame.draw.rect(self.screen, PANEL_COLOR, panelRect)
        
        # Panel border
        pygame.draw.rect(self.screen, (50, 50, 50), panelRect, 3)
        
        mouseX, mouseY = pygame.mouse.get_pos()
        
        # Main button settings
        mainButtonHeight = 35
        subCategoryHeight = 24
        slotSize = ICON_SIZE + 8
        headerHeight = 10
        startY = headerHeight
        
        # Calculate total content height
        totalHeight = 0
        
        # Blocks main button + content
        totalHeight += mainButtonHeight
        if self.blocksExpanded:
            for category in CATEGORY_ORDER:
                if category == "Problematic":
                    continue
                totalHeight += subCategoryHeight
                if self.expandedCategories.get(category, False):
                    blocks = BLOCK_CATEGORIES.get(category, [])
                    numRows = (len(blocks) + ICONS_PER_ROW - 1) // ICONS_PER_ROW
                    totalHeight += numRows * (slotSize + 4) + 5
            totalHeight += 10
        
        # Problematic main button + content
        totalHeight += mainButtonHeight
        if self.problemsExpanded:
            problemBlocks = BLOCK_CATEGORIES.get("Problematic", [])
            numRows = (len(problemBlocks) + ICONS_PER_ROW - 1) // ICONS_PER_ROW
            totalHeight += numRows * (slotSize + 4) + 15
        
        # Experimental main button + content (3 dimension buttons)
        totalHeight += mainButtonHeight
        if self.experimentalExpanded:
            totalHeight += 3 * 35 + 15  # 3 dimension buttons
        
        # Structures main button + content
        totalHeight += mainButtonHeight
        if self.structuresExpanded:
            totalHeight += len(PREMADE_STRUCTURES) * 35 + 15
        
        # Controls section
        totalHeight += 150
        
        # Available height for scrollable area
        availableHeight = WINDOW_HEIGHT - headerHeight
        self.maxScroll = max(0, totalHeight - availableHeight)
        
        # Create clipping region for scrollable content
        clipRect = pygame.Rect(panelX, startY, PANEL_WIDTH, availableHeight)
        self.screen.set_clip(clipRect)
        
        currentY = startY - self.inventoryScroll
        
        # ===== BLOCKS MAIN BUTTON =====
        blocksRect = pygame.Rect(panelX + ICON_MARGIN, currentY, PANEL_WIDTH - 2 * ICON_MARGIN, mainButtonHeight)
        blocksHovered = blocksRect.collidepoint(mouseX, mouseY)
        self.assetManager.drawButton(self.screen, blocksRect, "Blocks", self.font, blocksHovered, self.blocksExpanded)
        currentY += mainButtonHeight + 5
        
        # Blocks content (sub-categories)
        if self.blocksExpanded:
            for category in CATEGORY_ORDER:
                if category == "Problematic":
                    continue
                    
                blocks = BLOCK_CATEGORIES.get(category, [])
                isExpanded = self.expandedCategories.get(category, False)
                
                # Sub-category header
                subHeaderRect = pygame.Rect(panelX + 15, currentY, PANEL_WIDTH - 30, subCategoryHeight)
                isSubHovered = subHeaderRect.collidepoint(mouseX, mouseY)
                subColor = (65, 65, 75) if isSubHovered else (50, 50, 60)
                pygame.draw.rect(self.screen, subColor, subHeaderRect, border_radius=3)
                pygame.draw.rect(self.screen, (80, 80, 90), subHeaderRect, 1, border_radius=3)
                
                # Draw expand/collapse indicator as a simple triangle shape
                indicatorX = panelX + 22
                indicatorY = currentY + subCategoryHeight // 2
                if isExpanded:
                    # Down-pointing triangle
                    points = [(indicatorX - 4, indicatorY - 2), (indicatorX + 4, indicatorY - 2), (indicatorX, indicatorY + 3)]
                else:
                    # Right-pointing triangle
                    points = [(indicatorX - 2, indicatorY - 4), (indicatorX + 3, indicatorY), (indicatorX - 2, indicatorY + 4)]
                pygame.draw.polygon(self.screen, (180, 180, 180), points)
                
                # Category name
                catText = self.smallFont.render(category, True, (220, 220, 220))
                self.screen.blit(catText, (panelX + 35, currentY + 4))
                
                # Count
                countText = self.smallFont.render(f"({len(blocks)})", True, (120, 120, 120))
                self.screen.blit(countText, (panelX + PANEL_WIDTH - 50, currentY + 4))
                
                currentY += subCategoryHeight
                
                # Draw blocks if sub-category expanded
                if isExpanded:
                    blocksStartY = currentY + 2
                    for i, blockType in enumerate(blocks):
                        row = i // ICONS_PER_ROW
                        col = i % ICONS_PER_ROW
                        
                        btnX = panelX + ICON_MARGIN + col * (slotSize + 4)
                        btnY = blocksStartY + row * (slotSize + 4)
                        
                        if btnY + slotSize >= startY and btnY <= startY + availableHeight:
                            slotRect = pygame.Rect(btnX, btnY, slotSize, slotSize)
                            isSelected = blockType == self.selectedBlock
                            self.assetManager.drawSlot(self.screen, slotRect, isSelected)
                            
                            icon = self.assetManager.getIconSprite(blockType)
                            if icon:
                                iconX = btnX + (slotSize - ICON_SIZE) // 2
                                iconY = btnY + (slotSize - ICON_SIZE) // 2
                                self.screen.blit(icon, (iconX, iconY))
                    
                    numRows = (len(blocks) + ICONS_PER_ROW - 1) // ICONS_PER_ROW
                    currentY += numRows * (slotSize + 4) + 5
            
            currentY += 5
        
        # ===== PROBLEMATIC MAIN BUTTON =====
        problemsRect = pygame.Rect(panelX + ICON_MARGIN, currentY, PANEL_WIDTH - 2 * ICON_MARGIN, mainButtonHeight)
        problemsHovered = problemsRect.collidepoint(mouseX, mouseY)
        self.assetManager.drawButton(self.screen, problemsRect, "Problematic", self.font, problemsHovered, self.problemsExpanded)
        currentY += mainButtonHeight + 5
        
        # Problematic content
        if self.problemsExpanded:
            problemBlocks = BLOCK_CATEGORIES.get("Problematic", [])
            blocksStartY = currentY + 2
            
            for i, blockType in enumerate(problemBlocks):
                row = i // ICONS_PER_ROW
                col = i % ICONS_PER_ROW
                
                btnX = panelX + ICON_MARGIN + col * (slotSize + 4)
                btnY = blocksStartY + row * (slotSize + 4)
                
                if btnY + slotSize >= startY and btnY <= startY + availableHeight:
                    slotRect = pygame.Rect(btnX, btnY, slotSize, slotSize)
                    isSelected = blockType == self.selectedBlock
                    self.assetManager.drawSlot(self.screen, slotRect, isSelected)
                    
                    icon = self.assetManager.getIconSprite(blockType)
                    if icon:
                        iconX = btnX + (slotSize - ICON_SIZE) // 2
                        iconY = btnY + (slotSize - ICON_SIZE) // 2
                        self.screen.blit(icon, (iconX, iconY))
            
            numRows = (len(problemBlocks) + ICONS_PER_ROW - 1) // ICONS_PER_ROW
            currentY += numRows * (slotSize + 4) + 10
        
        # ===== EXPERIMENTAL MAIN BUTTON =====
        experimentalRect = pygame.Rect(panelX + ICON_MARGIN, currentY, PANEL_WIDTH - 2 * ICON_MARGIN, mainButtonHeight)
        experimentalHovered = experimentalRect.collidepoint(mouseX, mouseY)
        self.assetManager.drawButton(self.screen, experimentalRect, "Experimental", self.font, experimentalHovered, self.experimentalExpanded)
        currentY += mainButtonHeight + 5
        
        # Experimental content (dimension buttons)
        if self.experimentalExpanded:
            dimensions = [
                (DIMENSION_OVERWORLD, "Overworld"),
                (DIMENSION_NETHER, "Nether"),
                (DIMENSION_END, "End")
            ]
            dimY = currentY + 2
            
            for dimKey, dimName in dimensions:
                btnRect = pygame.Rect(panelX + ICON_MARGIN + 10, dimY, PANEL_WIDTH - 2 * ICON_MARGIN - 20, 30)
                
                if dimY + 30 >= startY and dimY <= startY + availableHeight:
                    isHovered = btnRect.collidepoint(mouseX, mouseY)
                    isSelected = self.currentDimension == dimKey
                    
                    self.assetManager.drawButton(
                        self.screen, btnRect, dimName, 
                        self.smallFont, isHovered, isSelected
                    )
                
                dimY += 35
            
            currentY = dimY + 5
        
        # ===== STRUCTURES MAIN BUTTON =====
        structuresRect = pygame.Rect(panelX + ICON_MARGIN, currentY, PANEL_WIDTH - 2 * ICON_MARGIN, mainButtonHeight)
        structuresHovered = structuresRect.collidepoint(mouseX, mouseY)
        self.assetManager.drawButton(self.screen, structuresRect, "Structures", self.font, structuresHovered, self.structuresExpanded)
        currentY += mainButtonHeight + 5
        
        # Structures content
        if self.structuresExpanded:
            structureY = currentY + 2
            
            for structName, structData in PREMADE_STRUCTURES.items():
                btnRect = pygame.Rect(panelX + ICON_MARGIN + 10, structureY, PANEL_WIDTH - 2 * ICON_MARGIN - 20, 30)
                
                if structureY + 30 >= startY and structureY <= startY + availableHeight:
                    isHovered = btnRect.collidepoint(mouseX, mouseY)
                    isSelected = self.structurePlacementMode and self.selectedStructure == structName
                    
                    self.assetManager.drawButton(
                        self.screen, btnRect, structData["name"], 
                        self.smallFont, isHovered, isSelected
                    )
                
                structureY += 35
            
            currentY = structureY + 5
        
        # ===== CONTROLS SECTION =====
        controlsY = currentY + 15
        pygame.draw.line(
            self.screen, PANEL_BORDER,
            (panelX + 10, controlsY - 5),
            (WINDOW_WIDTH - 10, controlsY - 5), 1
        )
        
        controls = [
            "LMB: Place block",
            "RMB: Interact/Remove",
            "MMB: Pan view",
            "R: Rotate stairs",
            "F: Flip slab",
            "H/T: Place structure"
        ]
        
        for i, ctrl in enumerate(controls):
            ctrlY = controlsY + i * 18
            if ctrlY >= startY and ctrlY <= startY + availableHeight:
                ctrlText = self.smallFont.render(ctrl, True, (150, 150, 150))
                self.screen.blit(ctrlText, (panelX + 10, ctrlY))
        
        # Reset clipping
        self.screen.set_clip(None)
        
        # Draw scroll indicator if needed
        if self.maxScroll > 0:
            scrollBarHeight = max(20, availableHeight * availableHeight // totalHeight)
            scrollBarY = startY + (self.inventoryScroll * (availableHeight - scrollBarHeight) // self.maxScroll)
            scrollBarRect = pygame.Rect(WINDOW_WIDTH - 8, scrollBarY, 4, scrollBarHeight)
            pygame.draw.rect(self.screen, (150, 150, 150), scrollBarRect)
    
    def _renderStatus(self):
        """Render status information"""
        # Mode indicator
        if self.structurePlacementMode and self.selectedStructure:
            structName = PREMADE_STRUCTURES[self.selectedStructure]["name"]
            modeText = self.font.render(f"Placing: {structName} (Click to confirm)", True, HIGHLIGHT_COLOR)
            self.screen.blit(modeText, (10, 10))
        
        # Hovered position
        if self.hoveredCell and not self.panelHovered:
            x, y, z = self.hoveredCell
            posText = self.smallFont.render(f"Position: ({x}, {y}, {z})", True, TEXT_COLOR)
            self.screen.blit(posText, (10, WINDOW_HEIGHT - 30))


# ============================================================================
# ENTRY POINT
# ============================================================================

def main():
    """Main entry point for the application"""
    print("=" * 50)
    print("  Isometric Minecraft Building Simulator")
    print("=" * 50)
    
    try:
        app = MinecraftBuilder()
        app.run()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        pygame.quit()
        sys.exit(1)


if __name__ == "__main__":
    main()
