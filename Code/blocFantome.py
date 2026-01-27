"""
Bloc Fantôme

An isometric 2.5D building simulator using Pygame. Users can place blocks from an
inventory panel onto a grid-based building area, load premade structures, and 
create custom builds with authentic sounds and textures.

The simulator features a 12x12x12 building grid with 2:1 dimetric projection for 
pixel-perfect isometric rendering, supporting block placement, removal, and 
structure loading.

Note: Users must run setup_assets.py to extract textures and sounds from their
own Minecraft Java Edition installation (version 1.21.1+).

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
from typing import Dict, List, Tuple, Optional, Any, Set
from dataclasses import dataclass
from enum import Enum
import random

# Import splash screen module
from splash import SplashScreen, show_splash

# Import horror system module
from horror import HorrorManager

# Windows-specific: Set AppUserModelID for proper taskbar icon
if sys.platform == 'win32':
    try:
        import ctypes
        myappid = 'blocfantome.builder.1.0'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass

# Initialize pygame
pygame.init()
pygame.mixer.init()
pygame.mixer.set_num_channels(32)  # Increase for ambient, rain, horror, block sounds

# ============================================================================
# CONSTANTS AND CONFIGURATION
# ============================================================================

# Window settings
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800
TITLE = "Bloc Fantome"

# Grid settings
GRID_WIDTH = 12
GRID_DEPTH = 12
GRID_HEIGHT = 12

# Isometric projection settings (2:1 dimetric)
# Higher resolution tiles for crisp textures
# Mathematically correct 2:1 would have BLOCK_HEIGHT = TILE_HEIGHT
# But visually, slightly taller sides look more "cube-like" to human perception
TILE_WIDTH = 64
TILE_HEIGHT = 32
BLOCK_HEIGHT = 38  # Slightly taller than mathematical 32 for better visual cube appearance

# Splash screen timing (in frames at 60 FPS)
SPLASH_DISPLAY_FRAMES = 90    # 1.5 seconds at full opacity (was 2.5s)
SPLASH_FADE_FRAMES = 60       # 1 second fade to game (was 1.5s)
SPLASH_ICON_SIZE = 256        # Icon size on splash screen (high-res)

# Sound settings
SOUND_VOLUME_DEFAULT = 0.6    # Default volume for block sounds
SOUND_VOLUME_AMBIENT = 0.5    # Ambient sounds (water, lava, etc.)
SOUND_VOLUME_UI = 0.4         # UI click sounds
SOUND_VOLUME_DOOR = 0.7       # Door sounds
SOUND_MAX_VARIANTS = 10       # Max sound variants to search for (1-9)

# Animation settings
PORTAL_FRAME_DELAY = 50       # ms between portal animation frames
FIRE_FRAME_DELAY = 80         # ms between fire animation frames
CHEST_FRAME_DELAY = 40        # ms between chest animation frames
OXIDATION_INTERVAL = 10000    # ms between copper oxidation steps

# Rain/Weather settings
RAIN_DROP_COUNT_BASE = 150    # Base number of rain drops
RAIN_INTENSITY_MIN = 0.5
RAIN_INTENSITY_MAX = 1.5
THUNDER_MIN_DELAY = 8000      # Min ms between thunder
THUNDER_MAX_DELAY = 25000     # Max ms between thunder

# Liquid flow timing (milliseconds)
WATER_FLOW_DELAY = 400        # Water flows every 400ms
LAVA_FLOW_DELAY = 2400        # Lava flows every 2400ms (6x slower than water, like Minecraft)


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
        except (pygame.error, IndexError) as e:
            print(f"Warning: Could not get average color: {e}")
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
                    except (IndexError, pygame.error):
                        pass  # Out of bounds pixel access is expected at edges
    
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

# Asset paths - handles both script and frozen executable
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    BASE_DIR = os.path.dirname(sys.executable)
    ASSETS_DIR = os.path.join(BASE_DIR, "Assets")
else:
    # Running as script
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
ICONS_DIR = os.path.join(ASSETS_DIR, "Icons")
FONTS_DIR = os.path.join(ASSETS_DIR, "Fonts")
SAVES_DIR = os.path.join(BASE_DIR, "saves")  # Saves folder next to exe or in Code folder
CUSTOM_MUSIC_DIR = os.path.join(SAVES_DIR, "custom_music")  # User-added music folder
APP_CONFIG_FILE = os.path.join(BASE_DIR, ".app_config.json")  # App preferences file

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
    # Additional wood types
    ACACIA_LOG = 22
    ACACIA_PLANKS = 23
    ACACIA_LEAVES = 24
    JUNGLE_LOG = 25
    JUNGLE_PLANKS = 26
    JUNGLE_LEAVES = 27
    # Nether wood types (stems)
    CRIMSON_STEM = 260
    CRIMSON_PLANKS = 261
    WARPED_STEM = 262
    WARPED_PLANKS = 263
    CRIMSON_NYLIUM = 264
    WARPED_NYLIUM = 265
    # Stripped logs
    STRIPPED_OAK_LOG = 270
    STRIPPED_BIRCH_LOG = 271
    STRIPPED_SPRUCE_LOG = 272
    STRIPPED_DARK_OAK_LOG = 273
    STRIPPED_ACACIA_LOG = 274
    STRIPPED_JUNGLE_LOG = 275
    STRIPPED_CRIMSON_STEM = 276
    STRIPPED_WARPED_STEM = 277
    # Ores and minerals
    COAL_ORE = 30
    IRON_ORE = 31
    GOLD_ORE = 32
    DIAMOND_ORE = 33
    COAL_BLOCK = 34
    IRON_BLOCK = 35
    GOLD_BLOCK = 36
    DIAMOND_BLOCK = 37
    LAPIS_ORE = 38
    LAPIS_BLOCK = 39
    EMERALD_ORE = 230
    EMERALD_BLOCK = 231
    REDSTONE_ORE = 232
    REDSTONE_BLOCK = 233
    QUARTZ_BLOCK = 234
    QUARTZ_PILLAR = 235
    CHISELED_QUARTZ = 236
    SMOOTH_QUARTZ = 237
    QUARTZ_BRICKS = 238
    # Building blocks
    BRICKS = 40
    STONE_BRICKS = 41
    MOSSY_STONE_BRICKS = 42
    MOSSY_COBBLESTONE = 43
    SANDSTONE = 44
    RED_SANDSTONE = 45
    # Stone variants
    GRANITE = 46
    POLISHED_GRANITE = 47
    DIORITE = 48
    POLISHED_DIORITE = 49
    ANDESITE = 280
    POLISHED_ANDESITE = 281
    SMOOTH_STONE = 282
    CHISELED_STONE_BRICKS = 283
    CRACKED_STONE_BRICKS = 284
    # Decorative
    GLASS = 50
    BOOKSHELF = 51
    GLOWSTONE = 52
    # Wool colors (all 16)
    WHITE_WOOL = 60
    RED_WOOL = 61
    BLUE_WOOL = 62
    GREEN_WOOL = 63
    YELLOW_WOOL = 64
    BLACK_WOOL = 65
    ORANGE_WOOL = 290
    MAGENTA_WOOL = 291
    LIGHT_BLUE_WOOL = 292
    LIME_WOOL = 293
    PINK_WOOL = 294
    GRAY_WOOL = 295
    LIGHT_GRAY_WOOL = 296
    CYAN_WOOL = 297
    PURPLE_WOOL = 298
    BROWN_WOOL = 299
    # Stained Glass (all 16)
    WHITE_STAINED_GLASS = 300
    ORANGE_STAINED_GLASS = 301
    MAGENTA_STAINED_GLASS = 302
    LIGHT_BLUE_STAINED_GLASS = 303
    YELLOW_STAINED_GLASS = 304
    LIME_STAINED_GLASS = 305
    PINK_STAINED_GLASS = 306
    GRAY_STAINED_GLASS = 307
    LIGHT_GRAY_STAINED_GLASS = 308
    CYAN_STAINED_GLASS = 309
    PURPLE_STAINED_GLASS = 310
    BLUE_STAINED_GLASS = 311
    BROWN_STAINED_GLASS = 312
    GREEN_STAINED_GLASS = 313
    RED_STAINED_GLASS = 314
    BLACK_STAINED_GLASS = 315
    # Terracotta (all 16 + base)
    TERRACOTTA = 320
    WHITE_TERRACOTTA = 321
    ORANGE_TERRACOTTA = 322
    MAGENTA_TERRACOTTA = 323
    LIGHT_BLUE_TERRACOTTA = 324
    YELLOW_TERRACOTTA = 325
    LIME_TERRACOTTA = 326
    PINK_TERRACOTTA = 327
    GRAY_TERRACOTTA = 328
    LIGHT_GRAY_TERRACOTTA = 329
    CYAN_TERRACOTTA = 330
    PURPLE_TERRACOTTA = 331
    BLUE_TERRACOTTA = 332
    BROWN_TERRACOTTA = 333
    GREEN_TERRACOTTA = 334
    RED_TERRACOTTA = 335
    BLACK_TERRACOTTA = 336
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
    CARVED_PUMPKIN = 135
    # Miscellaneous full blocks
    SPONGE = 240
    WET_SPONGE = 241
    NOTE_BLOCK = 242
    JUKEBOX = 243
    SLIME_BLOCK = 244
    HONEY_BLOCK = 245
    DRAGON_EGG = 246
    # Prismarine variants
    PRISMARINE = 250
    PRISMARINE_BRICKS = 251
    DARK_PRISMARINE = 252
    SEA_LANTERN = 253
    # Purpur blocks
    PURPUR_BLOCK = 254
    PURPUR_PILLAR = 255
    # Magma
    MAGMA_BLOCK = 256
    # Nether Update 1.16 blocks
    BLACKSTONE = 340
    POLISHED_BLACKSTONE = 341
    POLISHED_BLACKSTONE_BRICKS = 342
    CHISELED_POLISHED_BLACKSTONE = 343
    CRACKED_POLISHED_BLACKSTONE_BRICKS = 344
    GILDED_BLACKSTONE = 345
    BASALT = 346
    POLISHED_BASALT = 347
    SMOOTH_BASALT = 348
    NETHER_GOLD_ORE = 349
    ANCIENT_DEBRIS = 350
    NETHERITE_BLOCK = 351
    CRYING_OBSIDIAN = 352
    NETHER_WART_BLOCK = 353
    WARPED_WART_BLOCK = 354
    SHROOMLIGHT = 355
    SOUL_SOIL = 356
    RESPAWN_ANCHOR = 357
    LODESTONE = 358
    TARGET = 359
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
    MATRIX = 209  # Animated Matrix falling code effect


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
    lightLevel: int = 0  # Light emission level (0-15, like Minecraft)
    lightColor: Tuple[int, int, int] = (255, 200, 150)  # Light color RGB (warm orange default)


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
    # Wood - Acacia
    BlockType.ACACIA_LOG: BlockDefinition("Acacia Log", "acacia_log_top.png", "acacia_log.png", "acacia_log_top.png"),
    BlockType.ACACIA_PLANKS: BlockDefinition("Acacia Planks", "acacia_planks.png", "acacia_planks.png", "acacia_planks.png"),
    BlockType.ACACIA_LEAVES: BlockDefinition("Acacia Leaves", "acacia_leaves.png", "acacia_leaves.png", "acacia_leaves.png", transparent=True, tintTop=True, tintSide=True),
    # Wood - Jungle
    BlockType.JUNGLE_LOG: BlockDefinition("Jungle Log", "jungle_log_top.png", "jungle_log.png", "jungle_log_top.png"),
    BlockType.JUNGLE_PLANKS: BlockDefinition("Jungle Planks", "jungle_planks.png", "jungle_planks.png", "jungle_planks.png"),
    BlockType.JUNGLE_LEAVES: BlockDefinition("Jungle Leaves", "jungle_leaves.png", "jungle_leaves.png", "jungle_leaves.png", transparent=True, tintTop=True, tintSide=True),
    # Nether Wood - Crimson
    BlockType.CRIMSON_STEM: BlockDefinition("Crimson Stem", "crimson_stem_top.png", "crimson_stem.png", "crimson_stem_top.png"),
    BlockType.CRIMSON_PLANKS: BlockDefinition("Crimson Planks", "crimson_planks.png", "crimson_planks.png", "crimson_planks.png"),
    BlockType.CRIMSON_NYLIUM: BlockDefinition("Crimson Nylium", "crimson_nylium.png", "crimson_nylium_side.png", "netherrack.png"),
    # Nether Wood - Warped
    BlockType.WARPED_STEM: BlockDefinition("Warped Stem", "warped_stem_top.png", "warped_stem.png", "warped_stem_top.png"),
    BlockType.WARPED_PLANKS: BlockDefinition("Warped Planks", "warped_planks.png", "warped_planks.png", "warped_planks.png"),
    BlockType.WARPED_NYLIUM: BlockDefinition("Warped Nylium", "warped_nylium.png", "warped_nylium_side.png", "netherrack.png"),
    # Stripped Logs
    BlockType.STRIPPED_OAK_LOG: BlockDefinition("Stripped Oak Log", "stripped_oak_log_top.png", "stripped_oak_log.png", "stripped_oak_log_top.png"),
    BlockType.STRIPPED_BIRCH_LOG: BlockDefinition("Stripped Birch Log", "stripped_birch_log_top.png", "stripped_birch_log.png", "stripped_birch_log_top.png"),
    BlockType.STRIPPED_SPRUCE_LOG: BlockDefinition("Stripped Spruce Log", "stripped_spruce_log_top.png", "stripped_spruce_log.png", "stripped_spruce_log_top.png"),
    BlockType.STRIPPED_DARK_OAK_LOG: BlockDefinition("Stripped Dark Oak Log", "stripped_dark_oak_log_top.png", "stripped_dark_oak_log.png", "stripped_dark_oak_log_top.png"),
    BlockType.STRIPPED_ACACIA_LOG: BlockDefinition("Stripped Acacia Log", "stripped_acacia_log_top.png", "stripped_acacia_log.png", "stripped_acacia_log_top.png"),
    BlockType.STRIPPED_JUNGLE_LOG: BlockDefinition("Stripped Jungle Log", "stripped_jungle_log_top.png", "stripped_jungle_log.png", "stripped_jungle_log_top.png"),
    BlockType.STRIPPED_CRIMSON_STEM: BlockDefinition("Stripped Crimson Stem", "stripped_crimson_stem_top.png", "stripped_crimson_stem.png", "stripped_crimson_stem_top.png"),
    BlockType.STRIPPED_WARPED_STEM: BlockDefinition("Stripped Warped Stem", "stripped_warped_stem_top.png", "stripped_warped_stem.png", "stripped_warped_stem_top.png"),
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
    BlockType.LAPIS_ORE: BlockDefinition("Lapis Ore", "lapis_ore.png", "lapis_ore.png", "lapis_ore.png"),
    BlockType.LAPIS_BLOCK: BlockDefinition("Lapis Block", "lapis_block.png", "lapis_block.png", "lapis_block.png"),
    BlockType.EMERALD_ORE: BlockDefinition("Emerald Ore", "emerald_ore.png", "emerald_ore.png", "emerald_ore.png"),
    BlockType.EMERALD_BLOCK: BlockDefinition("Emerald Block", "emerald_block.png", "emerald_block.png", "emerald_block.png"),
    BlockType.REDSTONE_ORE: BlockDefinition("Redstone Ore", "redstone_ore.png", "redstone_ore.png", "redstone_ore.png"),
    BlockType.REDSTONE_BLOCK: BlockDefinition("Redstone Block", "redstone_block.png", "redstone_block.png", "redstone_block.png"),
    # Quartz blocks
    BlockType.QUARTZ_BLOCK: BlockDefinition("Quartz Block", "quartz_block_top.png", "quartz_block_side.png", "quartz_block_bottom.png"),
    BlockType.QUARTZ_PILLAR: BlockDefinition("Quartz Pillar", "quartz_pillar_top.png", "quartz_pillar.png", "quartz_pillar_top.png"),
    BlockType.CHISELED_QUARTZ: BlockDefinition("Chiseled Quartz", "chiseled_quartz_block_top.png", "chiseled_quartz_block.png", "chiseled_quartz_block_top.png"),
    BlockType.SMOOTH_QUARTZ: BlockDefinition("Smooth Quartz", "quartz_block_bottom.png", "quartz_block_bottom.png", "quartz_block_bottom.png"),
    BlockType.QUARTZ_BRICKS: BlockDefinition("Quartz Bricks", "quartz_bricks.png", "quartz_bricks.png", "quartz_bricks.png"),
    # Building blocks
    BlockType.BRICKS: BlockDefinition("Bricks", "bricks.png", "bricks.png", "bricks.png"),
    BlockType.STONE_BRICKS: BlockDefinition("Stone Bricks", "stone_bricks.png", "stone_bricks.png", "stone_bricks.png"),
    BlockType.MOSSY_STONE_BRICKS: BlockDefinition("Mossy Stone Bricks", "mossy_stone_bricks.png", "mossy_stone_bricks.png", "mossy_stone_bricks.png"),
    BlockType.MOSSY_COBBLESTONE: BlockDefinition("Mossy Cobblestone", "mossy_cobblestone.png", "mossy_cobblestone.png", "mossy_cobblestone.png"),
    BlockType.SANDSTONE: BlockDefinition("Sandstone", "sandstone_top.png", "sandstone.png", "sandstone_bottom.png"),
    BlockType.RED_SANDSTONE: BlockDefinition("Red Sandstone", "red_sandstone_top.png", "red_sandstone.png", "red_sandstone_bottom.png"),
    # Stone variants
    BlockType.GRANITE: BlockDefinition("Granite", "granite.png", "granite.png", "granite.png"),
    BlockType.POLISHED_GRANITE: BlockDefinition("Polished Granite", "polished_granite.png", "polished_granite.png", "polished_granite.png"),
    BlockType.DIORITE: BlockDefinition("Diorite", "diorite.png", "diorite.png", "diorite.png"),
    BlockType.POLISHED_DIORITE: BlockDefinition("Polished Diorite", "polished_diorite.png", "polished_diorite.png", "polished_diorite.png"),
    BlockType.ANDESITE: BlockDefinition("Andesite", "andesite.png", "andesite.png", "andesite.png"),
    BlockType.POLISHED_ANDESITE: BlockDefinition("Polished Andesite", "polished_andesite.png", "polished_andesite.png", "polished_andesite.png"),
    BlockType.SMOOTH_STONE: BlockDefinition("Smooth Stone", "smooth_stone.png", "smooth_stone.png", "smooth_stone.png"),
    BlockType.CHISELED_STONE_BRICKS: BlockDefinition("Chiseled Stone Bricks", "chiseled_stone_bricks.png", "chiseled_stone_bricks.png", "chiseled_stone_bricks.png"),
    BlockType.CRACKED_STONE_BRICKS: BlockDefinition("Cracked Stone Bricks", "cracked_stone_bricks.png", "cracked_stone_bricks.png", "cracked_stone_bricks.png"),
    # Decorative
    BlockType.GLASS: BlockDefinition("Glass", "glass.png", "glass.png", "glass.png", transparent=True),
    BlockType.BOOKSHELF: BlockDefinition("Bookshelf", "oak_planks.png", "bookshelf.png", "oak_planks.png"),
    BlockType.GLOWSTONE: BlockDefinition("Glowstone", "glowstone.png", "glowstone.png", "glowstone.png", lightLevel=15, lightColor=(255, 200, 100)),  # Warm yellow-orange
    BlockType.GLOWSTONE_BLOCK: BlockDefinition("Glowstone", "glowstone.png", "glowstone.png", "glowstone.png", lightLevel=15, lightColor=(255, 200, 100)),  # Alias
    # Wool (all 16 colors)
    BlockType.WHITE_WOOL: BlockDefinition("White Wool", "white_wool.png", "white_wool.png", "white_wool.png"),
    BlockType.RED_WOOL: BlockDefinition("Red Wool", "red_wool.png", "red_wool.png", "red_wool.png"),
    BlockType.BLUE_WOOL: BlockDefinition("Blue Wool", "blue_wool.png", "blue_wool.png", "blue_wool.png"),
    BlockType.GREEN_WOOL: BlockDefinition("Green Wool", "green_wool.png", "green_wool.png", "green_wool.png"),
    BlockType.YELLOW_WOOL: BlockDefinition("Yellow Wool", "yellow_wool.png", "yellow_wool.png", "yellow_wool.png"),
    BlockType.BLACK_WOOL: BlockDefinition("Black Wool", "black_wool.png", "black_wool.png", "black_wool.png"),
    BlockType.ORANGE_WOOL: BlockDefinition("Orange Wool", "orange_wool.png", "orange_wool.png", "orange_wool.png"),
    BlockType.MAGENTA_WOOL: BlockDefinition("Magenta Wool", "magenta_wool.png", "magenta_wool.png", "magenta_wool.png"),
    BlockType.LIGHT_BLUE_WOOL: BlockDefinition("Light Blue Wool", "light_blue_wool.png", "light_blue_wool.png", "light_blue_wool.png"),
    BlockType.LIME_WOOL: BlockDefinition("Lime Wool", "lime_wool.png", "lime_wool.png", "lime_wool.png"),
    BlockType.PINK_WOOL: BlockDefinition("Pink Wool", "pink_wool.png", "pink_wool.png", "pink_wool.png"),
    BlockType.GRAY_WOOL: BlockDefinition("Gray Wool", "gray_wool.png", "gray_wool.png", "gray_wool.png"),
    BlockType.LIGHT_GRAY_WOOL: BlockDefinition("Light Gray Wool", "light_gray_wool.png", "light_gray_wool.png", "light_gray_wool.png"),
    BlockType.CYAN_WOOL: BlockDefinition("Cyan Wool", "cyan_wool.png", "cyan_wool.png", "cyan_wool.png"),
    BlockType.PURPLE_WOOL: BlockDefinition("Purple Wool", "purple_wool.png", "purple_wool.png", "purple_wool.png"),
    BlockType.BROWN_WOOL: BlockDefinition("Brown Wool", "brown_wool.png", "brown_wool.png", "brown_wool.png"),
    # Stained Glass (all 16 colors)
    BlockType.WHITE_STAINED_GLASS: BlockDefinition("White Stained Glass", "white_stained_glass.png", "white_stained_glass.png", "white_stained_glass.png", transparent=True),
    BlockType.ORANGE_STAINED_GLASS: BlockDefinition("Orange Stained Glass", "orange_stained_glass.png", "orange_stained_glass.png", "orange_stained_glass.png", transparent=True),
    BlockType.MAGENTA_STAINED_GLASS: BlockDefinition("Magenta Stained Glass", "magenta_stained_glass.png", "magenta_stained_glass.png", "magenta_stained_glass.png", transparent=True),
    BlockType.LIGHT_BLUE_STAINED_GLASS: BlockDefinition("Light Blue Stained Glass", "light_blue_stained_glass.png", "light_blue_stained_glass.png", "light_blue_stained_glass.png", transparent=True),
    BlockType.YELLOW_STAINED_GLASS: BlockDefinition("Yellow Stained Glass", "yellow_stained_glass.png", "yellow_stained_glass.png", "yellow_stained_glass.png", transparent=True),
    BlockType.LIME_STAINED_GLASS: BlockDefinition("Lime Stained Glass", "lime_stained_glass.png", "lime_stained_glass.png", "lime_stained_glass.png", transparent=True),
    BlockType.PINK_STAINED_GLASS: BlockDefinition("Pink Stained Glass", "pink_stained_glass.png", "pink_stained_glass.png", "pink_stained_glass.png", transparent=True),
    BlockType.GRAY_STAINED_GLASS: BlockDefinition("Gray Stained Glass", "gray_stained_glass.png", "gray_stained_glass.png", "gray_stained_glass.png", transparent=True),
    BlockType.LIGHT_GRAY_STAINED_GLASS: BlockDefinition("Light Gray Stained Glass", "light_gray_stained_glass.png", "light_gray_stained_glass.png", "light_gray_stained_glass.png", transparent=True),
    BlockType.CYAN_STAINED_GLASS: BlockDefinition("Cyan Stained Glass", "cyan_stained_glass.png", "cyan_stained_glass.png", "cyan_stained_glass.png", transparent=True),
    BlockType.PURPLE_STAINED_GLASS: BlockDefinition("Purple Stained Glass", "purple_stained_glass.png", "purple_stained_glass.png", "purple_stained_glass.png", transparent=True),
    BlockType.BLUE_STAINED_GLASS: BlockDefinition("Blue Stained Glass", "blue_stained_glass.png", "blue_stained_glass.png", "blue_stained_glass.png", transparent=True),
    BlockType.BROWN_STAINED_GLASS: BlockDefinition("Brown Stained Glass", "brown_stained_glass.png", "brown_stained_glass.png", "brown_stained_glass.png", transparent=True),
    BlockType.GREEN_STAINED_GLASS: BlockDefinition("Green Stained Glass", "green_stained_glass.png", "green_stained_glass.png", "green_stained_glass.png", transparent=True),
    BlockType.RED_STAINED_GLASS: BlockDefinition("Red Stained Glass", "red_stained_glass.png", "red_stained_glass.png", "red_stained_glass.png", transparent=True),
    BlockType.BLACK_STAINED_GLASS: BlockDefinition("Black Stained Glass", "black_stained_glass.png", "black_stained_glass.png", "black_stained_glass.png", transparent=True),
    # Terracotta (all 16 colors + base)
    BlockType.TERRACOTTA: BlockDefinition("Terracotta", "terracotta.png", "terracotta.png", "terracotta.png"),
    BlockType.WHITE_TERRACOTTA: BlockDefinition("White Terracotta", "white_terracotta.png", "white_terracotta.png", "white_terracotta.png"),
    BlockType.ORANGE_TERRACOTTA: BlockDefinition("Orange Terracotta", "orange_terracotta.png", "orange_terracotta.png", "orange_terracotta.png"),
    BlockType.MAGENTA_TERRACOTTA: BlockDefinition("Magenta Terracotta", "magenta_terracotta.png", "magenta_terracotta.png", "magenta_terracotta.png"),
    BlockType.LIGHT_BLUE_TERRACOTTA: BlockDefinition("Light Blue Terracotta", "light_blue_terracotta.png", "light_blue_terracotta.png", "light_blue_terracotta.png"),
    BlockType.YELLOW_TERRACOTTA: BlockDefinition("Yellow Terracotta", "yellow_terracotta.png", "yellow_terracotta.png", "yellow_terracotta.png"),
    BlockType.LIME_TERRACOTTA: BlockDefinition("Lime Terracotta", "lime_terracotta.png", "lime_terracotta.png", "lime_terracotta.png"),
    BlockType.PINK_TERRACOTTA: BlockDefinition("Pink Terracotta", "pink_terracotta.png", "pink_terracotta.png", "pink_terracotta.png"),
    BlockType.GRAY_TERRACOTTA: BlockDefinition("Gray Terracotta", "gray_terracotta.png", "gray_terracotta.png", "gray_terracotta.png"),
    BlockType.LIGHT_GRAY_TERRACOTTA: BlockDefinition("Light Gray Terracotta", "light_gray_terracotta.png", "light_gray_terracotta.png", "light_gray_terracotta.png"),
    BlockType.CYAN_TERRACOTTA: BlockDefinition("Cyan Terracotta", "cyan_terracotta.png", "cyan_terracotta.png", "cyan_terracotta.png"),
    BlockType.PURPLE_TERRACOTTA: BlockDefinition("Purple Terracotta", "purple_terracotta.png", "purple_terracotta.png", "purple_terracotta.png"),
    BlockType.BLUE_TERRACOTTA: BlockDefinition("Blue Terracotta", "blue_terracotta.png", "blue_terracotta.png", "blue_terracotta.png"),
    BlockType.BROWN_TERRACOTTA: BlockDefinition("Brown Terracotta", "brown_terracotta.png", "brown_terracotta.png", "brown_terracotta.png"),
    BlockType.GREEN_TERRACOTTA: BlockDefinition("Green Terracotta", "green_terracotta.png", "green_terracotta.png", "green_terracotta.png"),
    BlockType.RED_TERRACOTTA: BlockDefinition("Red Terracotta", "red_terracotta.png", "red_terracotta.png", "red_terracotta.png"),
    BlockType.BLACK_TERRACOTTA: BlockDefinition("Black Terracotta", "black_terracotta.png", "black_terracotta.png", "black_terracotta.png"),
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
    BlockType.LAVA: BlockDefinition("Lava", "lava_flow.png", "lava_flow.png", "lava_flow.png", isLiquid=True, lightLevel=15, lightColor=(255, 100, 50)),  # Red-orange lava glow
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
    BlockType.NETHER_PORTAL: BlockDefinition("Nether Portal", "nether_portal.png", "nether_portal.png", "nether_portal.png", transparent=True, isPortal=True, lightLevel=11, lightColor=(180, 80, 255)),  # Purple portal glow
    BlockType.NETHER_BRICKS: BlockDefinition("Nether Bricks", "nether_bricks.png", "nether_bricks.png", "nether_bricks.png"),
    BlockType.NETHERRACK: BlockDefinition("Netherrack", "netherrack.png", "netherrack.png", "netherrack.png"),
    BlockType.SOUL_SAND: BlockDefinition("Soul Sand", "soul_sand.png", "soul_sand.png", "soul_sand.png"),
    # Plants
    BlockType.CACTUS: BlockDefinition("Cactus", "cactus_top.png", "cactus_side.png", "cactus_bottom.png"),
    BlockType.PUMPKIN: BlockDefinition("Pumpkin", "pumpkin_top.png", "pumpkin_side.png", "pumpkin_top.png"),
    BlockType.JACK_O_LANTERN: BlockDefinition("Jack o'Lantern", "pumpkin_top.png", "pumpkin_side.png", "pumpkin_top.png", textureFront="jack_o_lantern.png", lightLevel=15, lightColor=(255, 180, 80)),  # Orange pumpkin glow
    BlockType.HAY_BLOCK: BlockDefinition("Hay Block", "hay_block_top.png", "hay_block_side.png", "hay_block_top.png"),
    BlockType.MELON: BlockDefinition("Melon", "melon_top.png", "melon_side.png", "melon_top.png"),
    BlockType.CARVED_PUMPKIN: BlockDefinition("Carved Pumpkin", "pumpkin_top.png", "pumpkin_side.png", "pumpkin_top.png", textureFront="carved_pumpkin.png"),
    # Miscellaneous full blocks
    BlockType.SPONGE: BlockDefinition("Sponge", "sponge.png", "sponge.png", "sponge.png"),
    BlockType.WET_SPONGE: BlockDefinition("Wet Sponge", "wet_sponge.png", "wet_sponge.png", "wet_sponge.png"),
    BlockType.NOTE_BLOCK: BlockDefinition("Note Block", "note_block.png", "note_block.png", "note_block.png"),
    BlockType.JUKEBOX: BlockDefinition("Jukebox", "jukebox_top.png", "jukebox_side.png", "jukebox_side.png"),
    BlockType.SLIME_BLOCK: BlockDefinition("Slime Block", "slime_block.png", "slime_block.png", "slime_block.png", transparent=True),
    BlockType.HONEY_BLOCK: BlockDefinition("Honey Block", "honey_block_top.png", "honey_block_side.png", "honey_block_bottom.png", transparent=True),
    BlockType.DRAGON_EGG: BlockDefinition("Dragon Egg", "dragon_egg.png", "dragon_egg.png", "dragon_egg.png"),
    # Prismarine variants
    BlockType.PRISMARINE: BlockDefinition("Prismarine", "prismarine.png", "prismarine.png", "prismarine.png"),
    BlockType.PRISMARINE_BRICKS: BlockDefinition("Prismarine Bricks", "prismarine_bricks.png", "prismarine_bricks.png", "prismarine_bricks.png"),
    BlockType.DARK_PRISMARINE: BlockDefinition("Dark Prismarine", "dark_prismarine.png", "dark_prismarine.png", "dark_prismarine.png"),
    BlockType.SEA_LANTERN: BlockDefinition("Sea Lantern", "sea_lantern.png", "sea_lantern.png", "sea_lantern.png", lightLevel=15, lightColor=(150, 220, 255)),  # Cool cyan-white
    # Purpur blocks
    BlockType.PURPUR_BLOCK: BlockDefinition("Purpur Block", "purpur_block.png", "purpur_block.png", "purpur_block.png"),
    BlockType.PURPUR_PILLAR: BlockDefinition("Purpur Pillar", "purpur_pillar_top.png", "purpur_pillar.png", "purpur_pillar_top.png"),
    # Magma
    BlockType.MAGMA_BLOCK: BlockDefinition("Magma Block", "magma.png", "magma.png", "magma.png", lightLevel=3, lightColor=(255, 80, 40)),  # Deep red-orange
    # Nether Update 1.16 blocks
    BlockType.BLACKSTONE: BlockDefinition("Blackstone", "blackstone_top.png", "blackstone.png", "blackstone_top.png"),
    BlockType.POLISHED_BLACKSTONE: BlockDefinition("Polished Blackstone", "polished_blackstone.png", "polished_blackstone.png", "polished_blackstone.png"),
    BlockType.POLISHED_BLACKSTONE_BRICKS: BlockDefinition("Polished Blackstone Bricks", "polished_blackstone_bricks.png", "polished_blackstone_bricks.png", "polished_blackstone_bricks.png"),
    BlockType.CHISELED_POLISHED_BLACKSTONE: BlockDefinition("Chiseled Polished Blackstone", "chiseled_polished_blackstone.png", "chiseled_polished_blackstone.png", "chiseled_polished_blackstone.png"),
    BlockType.CRACKED_POLISHED_BLACKSTONE_BRICKS: BlockDefinition("Cracked Polished Blackstone Bricks", "cracked_polished_blackstone_bricks.png", "cracked_polished_blackstone_bricks.png", "cracked_polished_blackstone_bricks.png"),
    BlockType.GILDED_BLACKSTONE: BlockDefinition("Gilded Blackstone", "gilded_blackstone.png", "gilded_blackstone.png", "gilded_blackstone.png"),
    BlockType.BASALT: BlockDefinition("Basalt", "basalt_top.png", "basalt_side.png", "basalt_top.png"),
    BlockType.POLISHED_BASALT: BlockDefinition("Polished Basalt", "polished_basalt_top.png", "polished_basalt_side.png", "polished_basalt_top.png"),
    BlockType.SMOOTH_BASALT: BlockDefinition("Smooth Basalt", "smooth_basalt.png", "smooth_basalt.png", "smooth_basalt.png"),
    BlockType.NETHER_GOLD_ORE: BlockDefinition("Nether Gold Ore", "nether_gold_ore.png", "nether_gold_ore.png", "nether_gold_ore.png"),
    BlockType.ANCIENT_DEBRIS: BlockDefinition("Ancient Debris", "ancient_debris_top.png", "ancient_debris_side.png", "ancient_debris_top.png"),
    BlockType.NETHERITE_BLOCK: BlockDefinition("Netherite Block", "netherite_block.png", "netherite_block.png", "netherite_block.png"),
    BlockType.CRYING_OBSIDIAN: BlockDefinition("Crying Obsidian", "crying_obsidian.png", "crying_obsidian.png", "crying_obsidian.png", lightLevel=10, lightColor=(200, 100, 255)),  # Purple tears
    BlockType.NETHER_WART_BLOCK: BlockDefinition("Nether Wart Block", "nether_wart_block.png", "nether_wart_block.png", "nether_wart_block.png"),
    BlockType.WARPED_WART_BLOCK: BlockDefinition("Warped Wart Block", "warped_wart_block.png", "warped_wart_block.png", "warped_wart_block.png"),
    BlockType.SHROOMLIGHT: BlockDefinition("Shroomlight", "shroomlight.png", "shroomlight.png", "shroomlight.png", lightLevel=15, lightColor=(255, 220, 150)),  # Warm fungal glow
    BlockType.SOUL_SOIL: BlockDefinition("Soul Soil", "soul_soil.png", "soul_soil.png", "soul_soil.png"),
    BlockType.RESPAWN_ANCHOR: BlockDefinition("Respawn Anchor", "respawn_anchor_top_off.png", "respawn_anchor_side0.png", "respawn_anchor_bottom.png"),
    BlockType.LODESTONE: BlockDefinition("Lodestone", "lodestone_top.png", "lodestone_side.png", "lodestone_top.png"),
    BlockType.TARGET: BlockDefinition("Target", "target_top.png", "target_side.png", "target_top.png"),
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
    BlockType.MATRIX: BlockDefinition("Matrix", "black_concrete.png", "black_concrete.png", "black_concrete.png"),  # Animated falling code
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
    # Wood - Acacia
    BlockType.ACACIA_LOG: SoundDefinition("wood", "wood"),
    BlockType.ACACIA_PLANKS: SoundDefinition("wood", "wood"),
    BlockType.ACACIA_LEAVES: SoundDefinition("grass", "grass"),
    # Wood - Jungle
    BlockType.JUNGLE_LOG: SoundDefinition("wood", "wood"),
    BlockType.JUNGLE_PLANKS: SoundDefinition("wood", "wood"),
    BlockType.JUNGLE_LEAVES: SoundDefinition("grass", "grass"),
    # Nether Wood - Crimson
    BlockType.CRIMSON_STEM: SoundDefinition("nether_wood", "nether_wood"),
    BlockType.CRIMSON_PLANKS: SoundDefinition("nether_wood", "nether_wood"),
    BlockType.CRIMSON_NYLIUM: SoundDefinition("nylium", "nylium"),
    # Nether Wood - Warped
    BlockType.WARPED_STEM: SoundDefinition("nether_wood", "nether_wood"),
    BlockType.WARPED_PLANKS: SoundDefinition("nether_wood", "nether_wood"),
    BlockType.WARPED_NYLIUM: SoundDefinition("nylium", "nylium"),
    # Stripped Logs
    BlockType.STRIPPED_OAK_LOG: SoundDefinition("wood", "wood"),
    BlockType.STRIPPED_BIRCH_LOG: SoundDefinition("wood", "wood"),
    BlockType.STRIPPED_SPRUCE_LOG: SoundDefinition("wood", "wood"),
    BlockType.STRIPPED_DARK_OAK_LOG: SoundDefinition("wood", "wood"),
    BlockType.STRIPPED_ACACIA_LOG: SoundDefinition("wood", "wood"),
    BlockType.STRIPPED_JUNGLE_LOG: SoundDefinition("wood", "wood"),
    BlockType.STRIPPED_CRIMSON_STEM: SoundDefinition("nether_wood", "nether_wood"),
    BlockType.STRIPPED_WARPED_STEM: SoundDefinition("nether_wood", "nether_wood"),
    # Ores and minerals
    BlockType.COAL_ORE: SoundDefinition("stone", "stone"),
    BlockType.IRON_ORE: SoundDefinition("stone", "stone"),
    BlockType.GOLD_ORE: SoundDefinition("stone", "stone"),
    BlockType.DIAMOND_ORE: SoundDefinition("stone", "stone"),
    BlockType.COAL_BLOCK: SoundDefinition("stone", "stone"),
    BlockType.IRON_BLOCK: SoundDefinition("stone", "stone"),
    BlockType.GOLD_BLOCK: SoundDefinition("stone", "stone"),
    BlockType.DIAMOND_BLOCK: SoundDefinition("stone", "stone"),
    BlockType.LAPIS_ORE: SoundDefinition("stone", "stone"),
    BlockType.LAPIS_BLOCK: SoundDefinition("stone", "stone"),
    BlockType.EMERALD_ORE: SoundDefinition("stone", "stone"),
    BlockType.EMERALD_BLOCK: SoundDefinition("stone", "stone"),
    BlockType.REDSTONE_ORE: SoundDefinition("stone", "stone"),
    BlockType.REDSTONE_BLOCK: SoundDefinition("stone", "stone"),
    BlockType.QUARTZ_BLOCK: SoundDefinition("stone", "stone"),
    BlockType.QUARTZ_PILLAR: SoundDefinition("stone", "stone"),
    BlockType.CHISELED_QUARTZ: SoundDefinition("stone", "stone"),
    BlockType.SMOOTH_QUARTZ: SoundDefinition("stone", "stone"),
    BlockType.QUARTZ_BRICKS: SoundDefinition("stone", "stone"),
    # Building
    BlockType.BRICKS: SoundDefinition("stone", "stone"),
    BlockType.STONE_BRICKS: SoundDefinition("stone", "stone"),
    BlockType.MOSSY_STONE_BRICKS: SoundDefinition("stone", "stone"),
    BlockType.MOSSY_COBBLESTONE: SoundDefinition("stone", "stone"),
    BlockType.SANDSTONE: SoundDefinition("stone", "stone"),
    BlockType.RED_SANDSTONE: SoundDefinition("stone", "stone"),
    # Stone variants
    BlockType.GRANITE: SoundDefinition("stone", "stone"),
    BlockType.POLISHED_GRANITE: SoundDefinition("stone", "stone"),
    BlockType.DIORITE: SoundDefinition("stone", "stone"),
    BlockType.POLISHED_DIORITE: SoundDefinition("stone", "stone"),
    BlockType.ANDESITE: SoundDefinition("stone", "stone"),
    BlockType.POLISHED_ANDESITE: SoundDefinition("stone", "stone"),
    BlockType.SMOOTH_STONE: SoundDefinition("stone", "stone"),
    BlockType.CHISELED_STONE_BRICKS: SoundDefinition("stone", "stone"),
    BlockType.CRACKED_STONE_BRICKS: SoundDefinition("stone", "stone"),
    # Decorative
    BlockType.GLASS: SoundDefinition("glass", "glass"),
    BlockType.BOOKSHELF: SoundDefinition("wood", "wood"),
    BlockType.GLOWSTONE: SoundDefinition("glass", "glass"),  # Glowstone uses glass sounds in Minecraft
    BlockType.GLOWSTONE_BLOCK: SoundDefinition("glass", "glass"),  # Alias
    # Wool (cloth sound in Minecraft)
    BlockType.WHITE_WOOL: SoundDefinition("cloth", "cloth"),
    BlockType.RED_WOOL: SoundDefinition("cloth", "cloth"),
    BlockType.BLUE_WOOL: SoundDefinition("cloth", "cloth"),
    BlockType.GREEN_WOOL: SoundDefinition("cloth", "cloth"),
    BlockType.YELLOW_WOOL: SoundDefinition("cloth", "cloth"),
    BlockType.BLACK_WOOL: SoundDefinition("cloth", "cloth"),
    BlockType.ORANGE_WOOL: SoundDefinition("cloth", "cloth"),
    BlockType.MAGENTA_WOOL: SoundDefinition("cloth", "cloth"),
    BlockType.LIGHT_BLUE_WOOL: SoundDefinition("cloth", "cloth"),
    BlockType.LIME_WOOL: SoundDefinition("cloth", "cloth"),
    BlockType.PINK_WOOL: SoundDefinition("cloth", "cloth"),
    BlockType.GRAY_WOOL: SoundDefinition("cloth", "cloth"),
    BlockType.LIGHT_GRAY_WOOL: SoundDefinition("cloth", "cloth"),
    BlockType.CYAN_WOOL: SoundDefinition("cloth", "cloth"),
    BlockType.PURPLE_WOOL: SoundDefinition("cloth", "cloth"),
    BlockType.BROWN_WOOL: SoundDefinition("cloth", "cloth"),
    # Stained Glass (all 16 colors)
    BlockType.WHITE_STAINED_GLASS: SoundDefinition("glass", "glass"),
    BlockType.ORANGE_STAINED_GLASS: SoundDefinition("glass", "glass"),
    BlockType.MAGENTA_STAINED_GLASS: SoundDefinition("glass", "glass"),
    BlockType.LIGHT_BLUE_STAINED_GLASS: SoundDefinition("glass", "glass"),
    BlockType.YELLOW_STAINED_GLASS: SoundDefinition("glass", "glass"),
    BlockType.LIME_STAINED_GLASS: SoundDefinition("glass", "glass"),
    BlockType.PINK_STAINED_GLASS: SoundDefinition("glass", "glass"),
    BlockType.GRAY_STAINED_GLASS: SoundDefinition("glass", "glass"),
    BlockType.LIGHT_GRAY_STAINED_GLASS: SoundDefinition("glass", "glass"),
    BlockType.CYAN_STAINED_GLASS: SoundDefinition("glass", "glass"),
    BlockType.PURPLE_STAINED_GLASS: SoundDefinition("glass", "glass"),
    BlockType.BLUE_STAINED_GLASS: SoundDefinition("glass", "glass"),
    BlockType.BROWN_STAINED_GLASS: SoundDefinition("glass", "glass"),
    BlockType.GREEN_STAINED_GLASS: SoundDefinition("glass", "glass"),
    BlockType.RED_STAINED_GLASS: SoundDefinition("glass", "glass"),
    BlockType.BLACK_STAINED_GLASS: SoundDefinition("glass", "glass"),
    # Terracotta (all 16 colors + base)
    BlockType.TERRACOTTA: SoundDefinition("stone", "stone"),
    BlockType.WHITE_TERRACOTTA: SoundDefinition("stone", "stone"),
    BlockType.ORANGE_TERRACOTTA: SoundDefinition("stone", "stone"),
    BlockType.MAGENTA_TERRACOTTA: SoundDefinition("stone", "stone"),
    BlockType.LIGHT_BLUE_TERRACOTTA: SoundDefinition("stone", "stone"),
    BlockType.YELLOW_TERRACOTTA: SoundDefinition("stone", "stone"),
    BlockType.LIME_TERRACOTTA: SoundDefinition("stone", "stone"),
    BlockType.PINK_TERRACOTTA: SoundDefinition("stone", "stone"),
    BlockType.GRAY_TERRACOTTA: SoundDefinition("stone", "stone"),
    BlockType.LIGHT_GRAY_TERRACOTTA: SoundDefinition("stone", "stone"),
    BlockType.CYAN_TERRACOTTA: SoundDefinition("stone", "stone"),
    BlockType.PURPLE_TERRACOTTA: SoundDefinition("stone", "stone"),
    BlockType.BLUE_TERRACOTTA: SoundDefinition("stone", "stone"),
    BlockType.BROWN_TERRACOTTA: SoundDefinition("stone", "stone"),
    BlockType.GREEN_TERRACOTTA: SoundDefinition("stone", "stone"),
    BlockType.RED_TERRACOTTA: SoundDefinition("stone", "stone"),
    BlockType.BLACK_TERRACOTTA: SoundDefinition("stone", "stone"),
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
    BlockType.CARVED_PUMPKIN: SoundDefinition("wood", "wood"),
    # Miscellaneous blocks
    BlockType.SPONGE: SoundDefinition("grass", "grass"),
    BlockType.WET_SPONGE: SoundDefinition("grass", "grass"),
    BlockType.NOTE_BLOCK: SoundDefinition("wood", "wood"),
    BlockType.JUKEBOX: SoundDefinition("wood", "wood"),
    BlockType.SLIME_BLOCK: SoundDefinition("sand", "sand"),  # Slime uses sand-like squishy sounds
    BlockType.HONEY_BLOCK: SoundDefinition("honeyblock", "honeyblock"),
    BlockType.DRAGON_EGG: SoundDefinition("stone", "stone"),
    # Prismarine
    BlockType.PRISMARINE: SoundDefinition("stone", "stone"),
    BlockType.PRISMARINE_BRICKS: SoundDefinition("stone", "stone"),
    BlockType.DARK_PRISMARINE: SoundDefinition("stone", "stone"),
    BlockType.SEA_LANTERN: SoundDefinition("glass", "glass"),
    # Purpur
    BlockType.PURPUR_BLOCK: SoundDefinition("stone", "stone"),
    BlockType.PURPUR_PILLAR: SoundDefinition("stone", "stone"),
    # Magma
    BlockType.MAGMA_BLOCK: SoundDefinition("stone", "stone"),
    # Nether Update 1.16 blocks
    BlockType.BLACKSTONE: SoundDefinition("stone", "stone"),
    BlockType.POLISHED_BLACKSTONE: SoundDefinition("stone", "stone"),
    BlockType.POLISHED_BLACKSTONE_BRICKS: SoundDefinition("stone", "stone"),
    BlockType.CHISELED_POLISHED_BLACKSTONE: SoundDefinition("stone", "stone"),
    BlockType.CRACKED_POLISHED_BLACKSTONE_BRICKS: SoundDefinition("stone", "stone"),
    BlockType.GILDED_BLACKSTONE: SoundDefinition("stone", "stone"),
    BlockType.BASALT: SoundDefinition("basalt", "basalt"),
    BlockType.POLISHED_BASALT: SoundDefinition("basalt", "basalt"),
    BlockType.SMOOTH_BASALT: SoundDefinition("basalt", "basalt"),
    BlockType.NETHER_GOLD_ORE: SoundDefinition("nether_ore", "nether_ore"),
    BlockType.ANCIENT_DEBRIS: SoundDefinition("ancient_debris", "ancient_debris"),
    BlockType.NETHERITE_BLOCK: SoundDefinition("netherite", "netherite"),
    BlockType.CRYING_OBSIDIAN: SoundDefinition("stone", "stone"),
    BlockType.NETHER_WART_BLOCK: SoundDefinition("netherwart", "netherwart"),
    BlockType.WARPED_WART_BLOCK: SoundDefinition("netherwart", "netherwart"),
    BlockType.SHROOMLIGHT: SoundDefinition("shroomlight", "shroomlight"),
    BlockType.SOUL_SOIL: SoundDefinition("soul_soil", "soul_soil"),
    BlockType.RESPAWN_ANCHOR: SoundDefinition("stone", "stone"),  # Uses stone sounds (block folder has ambient/charge only)
    BlockType.LODESTONE: SoundDefinition("stone", "stone"),  # Uses stone sounds (block folder has place/lock only)
    BlockType.TARGET: SoundDefinition("grass", "grass"),
    BlockType.SNOW: SoundDefinition("snow", "snow"),  # Snow has its own dig sounds
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
    BlockType.MATRIX: SoundDefinition("nether_bricks", "nether_bricks"),  # Matrix block sounds
}


# ============================================================================
# BLOCK CATEGORIES (for dropdown UI)
# ============================================================================

# Define categories and which blocks belong to each
BLOCK_CATEGORIES = {
    "Natural": [
        BlockType.GRASS, BlockType.DIRT, BlockType.STONE, BlockType.COBBLESTONE,
        BlockType.GRAVEL, BlockType.SAND, BlockType.CLAY,
        BlockType.SNOW, BlockType.ICE, BlockType.PACKED_ICE,
        BlockType.CACTUS, BlockType.PUMPKIN, BlockType.CARVED_PUMPKIN,
        BlockType.HAY_BLOCK, BlockType.MELON, BlockType.SPONGE, BlockType.WET_SPONGE
    ],
    "Wood": [
        BlockType.OAK_LOG, BlockType.OAK_PLANKS, BlockType.OAK_LEAVES,
        BlockType.BIRCH_LOG, BlockType.BIRCH_PLANKS, BlockType.BIRCH_LEAVES,
        BlockType.SPRUCE_LOG, BlockType.SPRUCE_PLANKS, BlockType.SPRUCE_LEAVES,
        BlockType.DARK_OAK_LOG, BlockType.DARK_OAK_PLANKS, BlockType.DARK_OAK_LEAVES,
        BlockType.ACACIA_LOG, BlockType.ACACIA_PLANKS, BlockType.ACACIA_LEAVES,
        BlockType.JUNGLE_LOG, BlockType.JUNGLE_PLANKS, BlockType.JUNGLE_LEAVES,
        BlockType.STRIPPED_OAK_LOG, BlockType.STRIPPED_BIRCH_LOG, BlockType.STRIPPED_SPRUCE_LOG,
        BlockType.STRIPPED_DARK_OAK_LOG, BlockType.STRIPPED_ACACIA_LOG, BlockType.STRIPPED_JUNGLE_LOG
    ],
    "Stone & Brick": [
        BlockType.GRANITE, BlockType.POLISHED_GRANITE, BlockType.DIORITE, BlockType.POLISHED_DIORITE,
        BlockType.ANDESITE, BlockType.POLISHED_ANDESITE, BlockType.SMOOTH_STONE,
        BlockType.STONE_BRICKS, BlockType.MOSSY_STONE_BRICKS, BlockType.CHISELED_STONE_BRICKS,
        BlockType.CRACKED_STONE_BRICKS, BlockType.MOSSY_COBBLESTONE,
        BlockType.BRICKS, BlockType.SANDSTONE, BlockType.RED_SANDSTONE,
        BlockType.PRISMARINE, BlockType.PRISMARINE_BRICKS, BlockType.DARK_PRISMARINE,
        BlockType.PURPUR_BLOCK, BlockType.PURPUR_PILLAR
    ],
    "Ores & Minerals": [
        BlockType.COAL_ORE, BlockType.IRON_ORE, BlockType.GOLD_ORE, BlockType.DIAMOND_ORE,
        BlockType.LAPIS_ORE, BlockType.EMERALD_ORE, BlockType.REDSTONE_ORE,
        BlockType.COAL_BLOCK, BlockType.IRON_BLOCK, BlockType.GOLD_BLOCK, BlockType.DIAMOND_BLOCK,
        BlockType.LAPIS_BLOCK, BlockType.EMERALD_BLOCK, BlockType.REDSTONE_BLOCK,
        BlockType.COPPER_BLOCK, BlockType.EXPOSED_COPPER, BlockType.WEATHERED_COPPER, BlockType.OXIDIZED_COPPER,
        BlockType.CUT_COPPER, BlockType.EXPOSED_CUT_COPPER, BlockType.WEATHERED_CUT_COPPER, BlockType.OXIDIZED_CUT_COPPER
    ],
    "Colored Blocks": [
        BlockType.WHITE_WOOL, BlockType.ORANGE_WOOL, BlockType.MAGENTA_WOOL, BlockType.LIGHT_BLUE_WOOL,
        BlockType.YELLOW_WOOL, BlockType.LIME_WOOL, BlockType.PINK_WOOL, BlockType.GRAY_WOOL,
        BlockType.LIGHT_GRAY_WOOL, BlockType.CYAN_WOOL, BlockType.PURPLE_WOOL, BlockType.BLUE_WOOL,
        BlockType.BROWN_WOOL, BlockType.GREEN_WOOL, BlockType.RED_WOOL, BlockType.BLACK_WOOL,
        BlockType.WHITE_STAINED_GLASS, BlockType.ORANGE_STAINED_GLASS, BlockType.MAGENTA_STAINED_GLASS, BlockType.LIGHT_BLUE_STAINED_GLASS,
        BlockType.YELLOW_STAINED_GLASS, BlockType.LIME_STAINED_GLASS, BlockType.PINK_STAINED_GLASS, BlockType.GRAY_STAINED_GLASS,
        BlockType.LIGHT_GRAY_STAINED_GLASS, BlockType.CYAN_STAINED_GLASS, BlockType.PURPLE_STAINED_GLASS, BlockType.BLUE_STAINED_GLASS,
        BlockType.BROWN_STAINED_GLASS, BlockType.GREEN_STAINED_GLASS, BlockType.RED_STAINED_GLASS, BlockType.BLACK_STAINED_GLASS,
        BlockType.TERRACOTTA, BlockType.WHITE_TERRACOTTA, BlockType.ORANGE_TERRACOTTA, BlockType.MAGENTA_TERRACOTTA,
        BlockType.LIGHT_BLUE_TERRACOTTA, BlockType.YELLOW_TERRACOTTA, BlockType.LIME_TERRACOTTA, BlockType.PINK_TERRACOTTA,
        BlockType.GRAY_TERRACOTTA, BlockType.LIGHT_GRAY_TERRACOTTA, BlockType.CYAN_TERRACOTTA, BlockType.PURPLE_TERRACOTTA,
        BlockType.BLUE_TERRACOTTA, BlockType.BROWN_TERRACOTTA, BlockType.GREEN_TERRACOTTA, BlockType.RED_TERRACOTTA,
        BlockType.BLACK_TERRACOTTA,
        BlockType.WHITE_CONCRETE, BlockType.RED_CONCRETE, BlockType.BLUE_CONCRETE
    ],
    "Decorative": [
        BlockType.GLASS, BlockType.BOOKSHELF, BlockType.BONE_BLOCK, BlockType.SCULK,
        BlockType.SLIME_BLOCK, BlockType.HONEY_BLOCK, BlockType.TARGET,
        BlockType.QUARTZ_BLOCK, BlockType.QUARTZ_PILLAR, BlockType.CHISELED_QUARTZ,
        BlockType.SMOOTH_QUARTZ, BlockType.QUARTZ_BRICKS,
        BlockType.JACK_O_LANTERN
    ],
    "Light Sources": [
        BlockType.GLOWSTONE, BlockType.SEA_LANTERN, BlockType.SHROOMLIGHT,
        BlockType.JACK_O_LANTERN, BlockType.MAGMA_BLOCK, BlockType.CRYING_OBSIDIAN
    ],
    "Nether": [
        BlockType.NETHERRACK, BlockType.NETHER_BRICKS, BlockType.SOUL_SAND, BlockType.SOUL_SOIL,
        BlockType.MAGMA_BLOCK, BlockType.OBSIDIAN, BlockType.CRYING_OBSIDIAN, BlockType.NETHER_PORTAL,
        BlockType.CRIMSON_NYLIUM, BlockType.WARPED_NYLIUM,
        BlockType.CRIMSON_STEM, BlockType.CRIMSON_PLANKS,
        BlockType.WARPED_STEM, BlockType.WARPED_PLANKS,
        BlockType.STRIPPED_CRIMSON_STEM, BlockType.STRIPPED_WARPED_STEM,
        BlockType.NETHER_WART_BLOCK, BlockType.WARPED_WART_BLOCK, BlockType.SHROOMLIGHT,
        BlockType.BLACKSTONE, BlockType.POLISHED_BLACKSTONE, BlockType.POLISHED_BLACKSTONE_BRICKS,
        BlockType.CHISELED_POLISHED_BLACKSTONE, BlockType.CRACKED_POLISHED_BLACKSTONE_BRICKS, BlockType.GILDED_BLACKSTONE,
        BlockType.BASALT, BlockType.POLISHED_BASALT, BlockType.SMOOTH_BASALT,
        BlockType.NETHER_GOLD_ORE, BlockType.ANCIENT_DEBRIS, BlockType.NETHERITE_BLOCK,
        BlockType.GLOWSTONE
    ],
    "End": [
        BlockType.END_STONE, BlockType.END_STONE_BRICKS, BlockType.END_PORTAL_FRAME,
        BlockType.END_PORTAL, BlockType.END_GATEWAY, BlockType.DRAGON_EGG,
        BlockType.PURPUR_BLOCK, BlockType.PURPUR_PILLAR
    ],
    "Functional": [
        BlockType.CRAFTING_TABLE, BlockType.FURNACE, BlockType.NOTE_BLOCK, BlockType.JUKEBOX,
        BlockType.TNT, BlockType.BEDROCK, BlockType.RESPAWN_ANCHOR, BlockType.LODESTONE,
        BlockType.CHEST, BlockType.TRAPPED_CHEST, BlockType.ENDER_CHEST, BlockType.CHRISTMAS_CHEST,
        BlockType.COPPER_CHEST, BlockType.COPPER_CHEST_EXPOSED, BlockType.COPPER_CHEST_WEATHERED, BlockType.COPPER_CHEST_OXIDIZED,
        BlockType.WATER, BlockType.LAVA, BlockType.MOB_SPAWNER, BlockType.TRIAL_SPAWNER
    ],
    "Slabs": [
        BlockType.OAK_SLAB, BlockType.COBBLESTONE_SLAB, BlockType.STONE_BRICK_SLAB, BlockType.STONE_SLAB
    ],
    "Experimental": [
        BlockType.OAK_STAIRS, BlockType.COBBLESTONE_STAIRS, BlockType.STONE_BRICK_STAIRS,
        BlockType.OAK_DOOR, BlockType.IRON_DOOR,
        BlockType.OXIDIZING_COPPER, BlockType.ENCHANTING_TABLE, BlockType.SCULK_SENSOR,
        BlockType.FIRE, BlockType.SOUL_FIRE, BlockType.MATRIX
    ],
}

# Order of categories in the UI
CATEGORY_ORDER = ["Natural", "Wood", "Stone & Brick", "Ores & Minerals", "Colored Blocks", "Decorative", "Light Sources", "Nether", "End", "Functional", "Slabs", "Experimental"]


# ============================================================================
# PREMADE STRUCTURES
# ============================================================================

# ===== TUTORIAL SHOWCASE STRUCTURES (100+ blocks each) =====

# Welcome Showcase - Decorative platform for users to build on
# A raised stone brick platform with decorative pillars and flower beds
STRUCTURE_WELCOME_SHOWCASE = {
    "name": "Welcome Platform",
    "blocks": [
        # Main platform base - 12x12 stone brick floor
        *[(x, y, 0, BlockType.STONE_BRICKS) for x in range(12) for y in range(12)],
        
        # Decorative border - polished andesite ring
        *[(x, 0, 1, BlockType.POLISHED_ANDESITE) for x in range(12)],
        *[(x, 11, 1, BlockType.POLISHED_ANDESITE) for x in range(12)],
        *[(0, y, 1, BlockType.POLISHED_ANDESITE) for y in range(12)],
        *[(11, y, 1, BlockType.POLISHED_ANDESITE) for y in range(12)],
        
        # Corner pillars - quartz with glowstone tops (4 corners)
        *[(0, 0, z, BlockType.QUARTZ_PILLAR) for z in range(2, 5)],
        *[(11, 0, z, BlockType.QUARTZ_PILLAR) for z in range(2, 5)],
        *[(0, 11, z, BlockType.QUARTZ_PILLAR) for z in range(2, 5)],
        *[(11, 11, z, BlockType.QUARTZ_PILLAR) for z in range(2, 5)],
        (0, 0, 5, BlockType.GLOWSTONE),
        (11, 0, 5, BlockType.GLOWSTONE),
        (0, 11, 5, BlockType.GLOWSTONE),
        (11, 11, 5, BlockType.GLOWSTONE),
        
        # Inner decorative flower beds (grass with flowers implied by context)
        *[(1, 1, 1, BlockType.GRASS), (2, 1, 1, BlockType.GRASS), (1, 2, 1, BlockType.GRASS)],
        *[(9, 1, 1, BlockType.GRASS), (10, 1, 1, BlockType.GRASS), (10, 2, 1, BlockType.GRASS)],
        *[(1, 9, 1, BlockType.GRASS), (1, 10, 1, BlockType.GRASS), (2, 10, 1, BlockType.GRASS)],
        *[(9, 10, 1, BlockType.GRASS), (10, 9, 1, BlockType.GRASS), (10, 10, 1, BlockType.GRASS)],
        
        # Central raised display area - smooth stone
        *[(x, y, 1, BlockType.SMOOTH_STONE) for x in range(4, 8) for y in range(4, 8)],
        
        # Benches/seating areas on sides - oak planks
        *[(x, 2, 1, BlockType.OAK_PLANKS) for x in range(4, 8)],
        *[(x, 9, 1, BlockType.OAK_PLANKS) for x in range(4, 8)],
        *[(2, y, 1, BlockType.OAK_PLANKS) for y in range(4, 8)],
        *[(9, y, 1, BlockType.OAK_PLANKS) for y in range(4, 8)],
    ]
}

# Camera Demo - A decorative tower structure good for rotating around
STRUCTURE_CAMERA_DEMO = {
    "name": "Rotating Tower",
    "blocks": [
        # Foundation - 7x7 cobblestone base
        *[(x, y, 0, BlockType.COBBLESTONE) for x in range(7) for y in range(7)],
        
        # Tower base - stone brick walls 5x5
        *[(x, y, z, BlockType.STONE_BRICKS) for x in [1, 5] for y in range(1, 6) for z in range(1, 4)],
        *[(x, y, z, BlockType.STONE_BRICKS) for x in range(1, 6) for y in [1, 5] for z in range(1, 4)],
        
        # Corner pillars - oak logs
        *[(1, 1, z, BlockType.OAK_LOG) for z in range(1, 8)],
        *[(5, 1, z, BlockType.OAK_LOG) for z in range(1, 8)],
        *[(1, 5, z, BlockType.OAK_LOG) for z in range(1, 8)],
        *[(5, 5, z, BlockType.OAK_LOG) for z in range(1, 8)],
        
        # Windows - glass at z=2
        (3, 1, 2, BlockType.GLASS), (3, 5, 2, BlockType.GLASS),
        (1, 3, 2, BlockType.GLASS), (5, 3, 2, BlockType.GLASS),
        
        # Second floor platform
        *[(x, y, 4, BlockType.OAK_PLANKS) for x in range(1, 6) for y in range(1, 6)],
        
        # Second floor walls
        *[(x, y, z, BlockType.STONE_BRICKS) for x in [1, 5] for y in range(1, 6) for z in range(5, 7)],
        *[(x, y, z, BlockType.STONE_BRICKS) for x in range(1, 6) for y in [1, 5] for z in range(5, 7)],
        
        # More windows on second floor
        (3, 1, 5, BlockType.GLASS), (3, 5, 5, BlockType.GLASS),
        (1, 3, 5, BlockType.GLASS), (5, 3, 5, BlockType.GLASS),
        
        # Roof - flat top with decorative edge
        *[(x, y, 7, BlockType.STONE_BRICKS) for x in range(7) for y in range(7)],
        *[(x, y, 8, BlockType.STONE_BRICKS) for x in [0, 6] for y in range(7)],
        *[(x, y, 8, BlockType.STONE_BRICKS) for x in range(7) for y in [0, 6]],
        
        # Central spire
        *[(3, 3, z, BlockType.STONE_BRICKS) for z in range(8, 11)],
        (3, 3, 11, BlockType.GLOWSTONE),
        
        # Flag poles at corners
        (0, 0, 9, BlockType.OAK_LOG),
        (6, 0, 9, BlockType.OAK_LOG),
        (0, 6, 9, BlockType.OAK_LOG),
        (6, 6, 9, BlockType.OAK_LOG),
    ]
}

# Liquids Demo - Empty basins at different heights for water placement
STRUCTURE_WATER_BASINS = {
    "name": "Water Basins",
    "blocks": [
        # Ground base - stone brick platform 15x10
        *[(x, y, 0, BlockType.STONE_BRICKS) for x in range(15) for y in range(10)],
        
        # Basin 1 - Ground level pool (left side) - walls only, empty inside
        *[(x, 0, 1, BlockType.STONE_BRICKS) for x in range(6)],
        *[(x, 5, 1, BlockType.STONE_BRICKS) for x in range(6)],
        *[(0, y, 1, BlockType.STONE_BRICKS) for y in range(6)],
        *[(5, y, 1, BlockType.STONE_BRICKS) for y in range(6)],
        # Water at bottom of basin 1
        *[(x, y, 0, BlockType.WATER) for x in range(1, 5) for y in range(1, 5)],
        
        # Basin 2 - Raised level (middle) - 2 blocks up
        *[(x, y, 2, BlockType.STONE_BRICKS) for x in range(6, 10) for y in range(10)],
        *[(x, 0, 3, BlockType.STONE_BRICKS) for x in range(6, 10)],
        *[(x, 5, 3, BlockType.STONE_BRICKS) for x in range(6, 10)],
        *[(6, y, 3, BlockType.STONE_BRICKS) for y in range(6)],
        *[(9, y, 3, BlockType.STONE_BRICKS) for y in range(6)],
        
        # Basin 3 - Highest level (right side) - 4 blocks up
        *[(x, y, 4, BlockType.STONE_BRICKS) for x in range(10, 15) for y in range(6)],
        *[(x, 0, 5, BlockType.STONE_BRICKS) for x in range(10, 15)],
        *[(x, 5, 5, BlockType.STONE_BRICKS) for x in range(10, 15)],
        *[(10, y, 5, BlockType.STONE_BRICKS) for y in range(6)],
        *[(14, y, 5, BlockType.STONE_BRICKS) for y in range(6)],
        
        # Connecting channels/stairs between basins
        *[(5, 2, z, BlockType.STONE_BRICKS) for z in range(1, 3)],
        *[(5, 3, z, BlockType.STONE_BRICKS) for z in range(1, 3)],
        *[(9, 2, z, BlockType.STONE_BRICKS) for z in range(3, 5)],
        *[(9, 3, z, BlockType.STONE_BRICKS) for z in range(3, 5)],
        
        # Decorative pillars
        *[(0, 0, z, BlockType.STONE_BRICKS) for z in range(2, 4)],
        *[(5, 0, z, BlockType.STONE_BRICKS) for z in range(2, 4)],
        *[(6, 5, z, BlockType.STONE_BRICKS) for z in range(4, 6)],
        *[(9, 5, z, BlockType.STONE_BRICKS) for z in range(4, 6)],
        *[(10, 0, z, BlockType.STONE_BRICKS) for z in range(6, 8)],
        *[(14, 0, z, BlockType.STONE_BRICKS) for z in range(6, 8)],
    ]
}

# Lighting Demo - Cave room with dark spots to light up
STRUCTURE_DARK_CAVE = {
    "name": "Cave Room",
    "blocks": [
        # Cave floor - 12x12 stone
        *[(x, y, 0, BlockType.STONE) for x in range(12) for y in range(12)],
        
        # Cave walls - irregular stone/cobblestone mix
        *[(0, y, z, BlockType.STONE if (y + z) % 3 != 0 else BlockType.COBBLESTONE) 
          for y in range(12) for z in range(1, 6)],
        *[(11, y, z, BlockType.STONE if (y + z) % 3 != 0 else BlockType.COBBLESTONE) 
          for y in range(12) for z in range(1, 6)],
        *[(x, 0, z, BlockType.STONE if (x + z) % 3 != 0 else BlockType.COBBLESTONE) 
          for x in range(12) for z in range(1, 6)],
        *[(x, 11, z, BlockType.STONE if (x + z) % 3 != 0 else BlockType.COBBLESTONE) 
          for x in range(12) for z in range(1, 6)],
        
        # Cave ceiling - much more open with large central hole
        # Only blocks around the edges, center is open
        *[(x, y, 6, BlockType.STONE) for x in range(12) for y in range(12) 
          if (x < 2 or x > 9 or y < 2 or y > 9)],
        # A few hanging blocks for visual interest
        (2, 2, 6, BlockType.STONE),
        (9, 2, 6, BlockType.STONE),
        (2, 9, 6, BlockType.STONE),
        (9, 9, 6, BlockType.STONE),
        
        # Stalactites from ceiling edges
        *[(1, 5, z, BlockType.STONE) for z in range(4, 6)],
        *[(10, 6, z, BlockType.STONE) for z in range(5, 6)],
        
        # Stalagmites from floor
        *[(5, 4, z, BlockType.STONE) for z in range(1, 3)],
        *[(2, 8, z, BlockType.STONE) for z in range(1, 2)],
        *[(9, 6, z, BlockType.STONE) for z in range(1, 3)],
        
        # Light source spots (where user can place glowstone)
        # We put some coal ore to mark "dark spots"
        (2, 2, 1, BlockType.COAL_ORE),
        (9, 2, 1, BlockType.COAL_ORE),
        (2, 9, 1, BlockType.COAL_ORE),
        (9, 9, 1, BlockType.COAL_ORE),
        (5, 5, 1, BlockType.COAL_ORE),
        
        # Some ore veins for visual interest
        (4, 1, 2, BlockType.IRON_ORE),
        (4, 1, 3, BlockType.IRON_ORE),
        (7, 10, 2, BlockType.GOLD_ORE),
        (1, 6, 3, BlockType.DIAMOND_ORE),
        
        # Entrance opening
        (5, 0, 1, BlockType.AIR if hasattr(BlockType, 'AIR') else BlockType.GLASS),
        (6, 0, 1, BlockType.GLASS),
        (5, 0, 2, BlockType.GLASS),
        (6, 0, 2, BlockType.GLASS),
    ]
}

# Weather Demo - Pools/backroom structure without water
STRUCTURE_RAIN_COURTYARD = {
    "name": "Rain Courtyard",
    "blocks": [
        # Large courtyard floor - 14x14 smooth stone with pattern
        *[(x, y, 0, BlockType.SMOOTH_STONE if (x + y) % 2 == 0 else BlockType.STONE_BRICKS) 
          for x in range(14) for y in range(14)],
        
        # Outer walls - stone brick, 3 high with openings
        *[(0, y, z, BlockType.STONE_BRICKS) for y in range(14) for z in range(1, 4) 
          if not (y in [3, 4, 9, 10] and z < 3)],
        *[(13, y, z, BlockType.STONE_BRICKS) for y in range(14) for z in range(1, 4)
          if not (y in [3, 4, 9, 10] and z < 3)],
        *[(x, 0, z, BlockType.STONE_BRICKS) for x in range(14) for z in range(1, 4)
          if not (x in [6, 7] and z < 3)],
        *[(x, 13, z, BlockType.STONE_BRICKS) for x in range(14) for z in range(1, 4)],
        
        # Interior columns
        *[(3, 3, z, BlockType.QUARTZ_PILLAR) for z in range(1, 5)],
        *[(10, 3, z, BlockType.QUARTZ_PILLAR) for z in range(1, 5)],
        *[(3, 10, z, BlockType.QUARTZ_PILLAR) for z in range(1, 5)],
        *[(10, 10, z, BlockType.QUARTZ_PILLAR) for z in range(1, 5)],
        
        # Central dry pool area - recessed area (no water)
        *[(x, y, 0, BlockType.PRISMARINE) for x in range(5, 9) for y in range(5, 9)],
        
        # Roof overhangs at corners (partial roof for rain effect)
        *[(x, y, 4, BlockType.STONE_BRICKS) for x in range(4) for y in range(4)],
        *[(x, y, 4, BlockType.STONE_BRICKS) for x in range(10, 14) for y in range(4)],
        *[(x, y, 4, BlockType.STONE_BRICKS) for x in range(4) for y in range(10, 14)],
        *[(x, y, 4, BlockType.STONE_BRICKS) for x in range(10, 14) for y in range(10, 14)],
        
        # Benches
        *[(1, y, 1, BlockType.OAK_PLANKS) for y in range(5, 9)],
        *[(12, y, 1, BlockType.OAK_PLANKS) for y in range(5, 9)],
        
        # Lantern posts (using glowstone instead of actual lanterns)
        (2, 2, 1, BlockType.COBBLESTONE), (2, 2, 2, BlockType.COBBLESTONE), (2, 2, 3, BlockType.GLOWSTONE),
        (11, 2, 1, BlockType.COBBLESTONE), (11, 2, 2, BlockType.COBBLESTONE), (11, 2, 3, BlockType.GLOWSTONE),
        (2, 11, 1, BlockType.COBBLESTONE), (2, 11, 2, BlockType.COBBLESTONE), (2, 11, 3, BlockType.GLOWSTONE),
        (11, 11, 1, BlockType.COBBLESTONE), (11, 11, 2, BlockType.COBBLESTONE), (11, 11, 3, BlockType.GLOWSTONE),
    ]
}

# Structures Demo - Empty flat platform for placing structures
STRUCTURE_EMPTY_PLATFORM = {
    "name": "Building Platform",
    "blocks": [
        # Natural terrain with height variation - 16x16 base
        # Base layer of dirt/stone underground
        *[(x, y, 0, BlockType.STONE) for x in range(16) for y in range(16)],
        *[(x, y, 1, BlockType.DIRT) for x in range(16) for y in range(16)],
        
        # Grass layer with gentle hills (height 2-4)
        *[(x, y, 2, BlockType.GRASS) for x in range(16) for y in range(16)],
        
        # Raised hill in center-back area (natural mound)
        *[(x, y, 3, BlockType.DIRT) for x in range(5, 11) for y in range(8, 14)],
        *[(x, y, 3, BlockType.GRASS) for x in range(5, 11) for y in range(8, 14)],
        *[(x, y, 4, BlockType.DIRT) for x in range(6, 10) for y in range(9, 13)],
        *[(x, y, 4, BlockType.GRASS) for x in range(6, 10) for y in range(9, 13)],
        
        # Small raised area on left side
        *[(x, y, 3, BlockType.DIRT) for x in range(1, 4) for y in range(3, 7)],
        *[(x, y, 3, BlockType.GRASS) for x in range(1, 4) for y in range(3, 7)],
        
        # Random scattered grass patches for texture
        (10, 2, 3, BlockType.GRASS), (10, 2, 2, BlockType.DIRT),
        (12, 5, 3, BlockType.GRASS), (12, 5, 2, BlockType.DIRT),
        (3, 12, 3, BlockType.GRASS), (3, 12, 2, BlockType.DIRT),
        (14, 10, 3, BlockType.GRASS), (14, 10, 2, BlockType.DIRT),
        
        # Flowers/decorations for natural look
        (7, 5, 3, BlockType.DANDELION) if hasattr(BlockType, 'DANDELION') else (7, 5, 3, BlockType.GRASS),
        (4, 2, 3, BlockType.POPPY) if hasattr(BlockType, 'POPPY') else (4, 2, 3, BlockType.GRASS),
        (13, 8, 3, BlockType.DANDELION) if hasattr(BlockType, 'DANDELION') else (13, 8, 3, BlockType.GRASS),
    ]
}

# Fill Demo - Large area to practice fill tool
STRUCTURE_FILL_AREA = {
    "name": "Fill Practice Area",
    "blocks": [
        # Multi-level platform for fill practice - 12x12
        # Level 1 - Base
        *[(x, y, 0, BlockType.DIRT) for x in range(12) for y in range(12)],
        
        # Level 2 - Raised section (half the area)
        *[(x, y, 1, BlockType.DIRT) for x in range(6) for y in range(12)],
        
        # Level 3 - Higher section
        *[(x, y, 2, BlockType.DIRT) for x in range(3) for y in range(6)],
        
        # Framing walls to show fill boundaries
        *[(x, 0, z, BlockType.COBBLESTONE) for x in range(12) for z in range(1, 3)],
        *[(x, 11, z, BlockType.COBBLESTONE) for x in range(12) for z in range(1, 3)],
        
        # Example filled areas (so user can see what fill does)
        *[(x, y, 1, BlockType.STONE_BRICKS) for x in range(7, 11) for y in range(7, 11)],
        
        # Signs (using wool) showing "FILL HERE"
        (8, 5, 1, BlockType.WHITE_WOOL),
        (9, 5, 1, BlockType.WHITE_WOOL),
        
        # Corner pillars
        *[(0, 0, z, BlockType.OAK_LOG) for z in range(1, 4)],
        *[(11, 0, z, BlockType.OAK_LOG) for z in range(1, 4)],
        *[(0, 11, z, BlockType.OAK_LOG) for z in range(1, 4)],
        *[(11, 11, z, BlockType.OAK_LOG) for z in range(1, 4)],
    ]
}

# Mirror Demo - Half-built symmetric structure
STRUCTURE_MIRROR_DEMO = {
    "name": "Mirror Practice",
    "blocks": [
        # Base platform - 12x12
        *[(x, y, 0, BlockType.QUARTZ_BLOCK) for x in range(12) for y in range(12)],
        
        # Center line marker (the mirror axis)
        *[(6, y, 1, BlockType.GOLD_BLOCK) for y in range(12)],
        
        # LEFT HALF - Build this side, mirror will create right
        # Wall section
        *[(0, y, z, BlockType.STONE_BRICKS) for y in range(12) for z in range(1, 4)],
        *[(x, 0, z, BlockType.STONE_BRICKS) for x in range(6) for z in range(1, 4)],
        *[(x, 11, z, BlockType.STONE_BRICKS) for x in range(6) for z in range(1, 4)],
        
        # Decorative elements on left
        (2, 2, 1, BlockType.OAK_PLANKS),
        (2, 2, 2, BlockType.GLASS),
        (2, 9, 1, BlockType.OAK_PLANKS),
        (2, 9, 2, BlockType.GLASS),
        
        # Pattern to mirror
        (3, 5, 1, BlockType.BRICKS),
        (3, 6, 1, BlockType.BRICKS),
        (4, 5, 1, BlockType.BRICKS),
        (4, 6, 1, BlockType.BRICKS),
        (3, 5, 2, BlockType.BRICKS),
        (3, 6, 2, BlockType.BRICKS),
        
        # Pillar
        *[(5, 3, z, BlockType.QUARTZ_PILLAR) for z in range(1, 5)],
        *[(5, 8, z, BlockType.QUARTZ_PILLAR) for z in range(1, 5)],
    ]
}

# Brush Demo - Area showing different brush sizes
STRUCTURE_BRUSH_DEMO = {
    "name": "Brush Demo",
    "blocks": [
        # Platform - 14x10
        *[(x, y, 0, BlockType.SMOOTH_STONE) for x in range(14) for y in range(10)],
        
        # Section 1: 1x1 brush area (left)
        *[(x, y, 0, BlockType.OAK_PLANKS) for x in range(4) for y in range(10)],
        # Example 1x1 placements
        (1, 2, 1, BlockType.COBBLESTONE),
        (2, 4, 1, BlockType.COBBLESTONE),
        (1, 6, 1, BlockType.COBBLESTONE),
        (2, 8, 1, BlockType.COBBLESTONE),
        
        # Section 2: 2x2 brush area (middle)
        *[(x, y, 0, BlockType.BIRCH_PLANKS) for x in range(5, 9) for y in range(10)],
        # Example 2x2 placement
        *[(x, y, 1, BlockType.STONE_BRICKS) for x in range(5, 7) for y in range(4, 6)],
        
        # Section 3: 3x3 brush area (right)
        *[(x, y, 0, BlockType.SPRUCE_PLANKS) for x in range(10, 14) for y in range(10)],
        # Example 3x3 placement
        *[(x, y, 1, BlockType.BRICKS) for x in range(10, 13) for y in range(3, 6)],
        
        # Dividing pillars between sections
        *[(4, y, z, BlockType.OAK_LOG) for y in range(10) for z in range(1, 3)],
        *[(9, y, z, BlockType.OAK_LOG) for y in range(10) for z in range(1, 3)],
        
        # Labels (using colored wool)
        (1, 0, 1, BlockType.WHITE_WOOL),  # "1"
        (6, 0, 1, BlockType.ORANGE_WOOL), # "2"
        (11, 0, 1, BlockType.RED_WOOL),   # "3"
    ]
}

# Undo Demo - Structure with "mistakes" to undo
STRUCTURE_UNDO_DEMO = {
    "name": "Undo Practice",
    "blocks": [
        # Nice platform - 10x10
        *[(x, y, 0, BlockType.QUARTZ_BLOCK) for x in range(10) for y in range(10)],
        
        # Clean building structure
        *[(0, y, z, BlockType.STONE_BRICKS) for y in range(10) for z in range(1, 4)],
        *[(9, y, z, BlockType.STONE_BRICKS) for y in range(10) for z in range(1, 4)],
        *[(x, 0, z, BlockType.STONE_BRICKS) for x in range(10) for z in range(1, 4)],
        *[(x, 9, z, BlockType.STONE_BRICKS) for x in range(10) for z in range(1, 4)],
        
        # "Mistake" blocks (misplaced blocks to undo)
        (3, 3, 1, BlockType.DIRT),
        (5, 5, 1, BlockType.GRAVEL),
        (7, 2, 1, BlockType.SAND),
        (4, 7, 2, BlockType.COBBLESTONE),
        (6, 4, 3, BlockType.NETHERRACK),
        
        # Clean elements
        *[(x, y, 4, BlockType.OAK_PLANKS) for x in range(10) for y in range(10)],
        
        # Windows
        (2, 0, 2, BlockType.GLASS),
        (7, 0, 2, BlockType.GLASS),
        (0, 4, 2, BlockType.GLASS),
        (9, 4, 2, BlockType.GLASS),
    ]
}

# Rotate Demo - Asymmetric structure to rotate around
STRUCTURE_ROTATE_DEMO = {
    "name": "Rotating Monument",
    "blocks": [
        # Base - circular pattern
        *[(x, y, 0, BlockType.STONE_BRICKS) for x in range(9) for y in range(9)
          if (x - 4)**2 + (y - 4)**2 <= 20],
        
        # Central tower
        *[(4, 4, z, BlockType.QUARTZ_PILLAR) for z in range(1, 8)],
        (4, 4, 8, BlockType.GLOWSTONE),
        
        # Asymmetric wings (so rotation is visible)
        # North wing - tall
        *[(4, 0, z, BlockType.STONE_BRICKS) for z in range(1, 5)],
        *[(4, 1, z, BlockType.STONE_BRICKS) for z in range(1, 4)],
        
        # East wing - wide
        *[(7, 4, z, BlockType.STONE_BRICKS) for z in range(1, 3)],
        *[(8, 4, z, BlockType.STONE_BRICKS) for z in range(1, 3)],
        *[(8, 3, z, BlockType.STONE_BRICKS) for z in range(1, 3)],
        *[(8, 5, z, BlockType.STONE_BRICKS) for z in range(1, 3)],
        
        # South wing - short pillar
        *[(4, 7, z, BlockType.STONE_BRICKS) for z in range(1, 3)],
        *[(4, 8, z, BlockType.STONE_BRICKS) for z in range(1, 2)],
        
        # West wing - decorated
        *[(1, 4, z, BlockType.STONE_BRICKS) for z in range(1, 4)],
        *[(0, 4, z, BlockType.STONE_BRICKS) for z in range(1, 3)],
        (0, 4, 3, BlockType.GLOWSTONE),
        
        # Corner decorations
        (1, 1, 1, BlockType.OAK_LOG),
        (7, 1, 1, BlockType.BIRCH_LOG),
        (1, 7, 1, BlockType.SPRUCE_LOG),
        (7, 7, 1, BlockType.DARK_OAK_LOG),
    ]
}

# Save Demo - Impressive structure worth saving
STRUCTURE_SAVE_DEMO = {
    "name": "Temple to Save",
    "blocks": [
        # Temple platform - 12x12
        *[(x, y, 0, BlockType.QUARTZ_BLOCK) for x in range(12) for y in range(12)],
        
        # Steps leading up
        *[(x, 0, 1, BlockType.QUARTZ_BLOCK) for x in range(12)],
        *[(x, 1, 1, BlockType.QUARTZ_BLOCK) for x in range(12)],
        *[(x, 2, 1, BlockType.QUARTZ_BLOCK) for x in range(2, 10)],
        *[(x, 2, 2, BlockType.QUARTZ_BLOCK) for x in range(2, 10)],
        
        # Outer columns
        *[(0, 4, z, BlockType.QUARTZ_PILLAR) for z in range(1, 6)],
        *[(11, 4, z, BlockType.QUARTZ_PILLAR) for z in range(1, 6)],
        *[(0, 9, z, BlockType.QUARTZ_PILLAR) for z in range(1, 6)],
        *[(11, 9, z, BlockType.QUARTZ_PILLAR) for z in range(1, 6)],
        
        # Inner columns
        *[(3, 5, z, BlockType.QUARTZ_PILLAR) for z in range(1, 5)],
        *[(8, 5, z, BlockType.QUARTZ_PILLAR) for z in range(1, 5)],
        *[(3, 8, z, BlockType.QUARTZ_PILLAR) for z in range(1, 5)],
        *[(8, 8, z, BlockType.QUARTZ_PILLAR) for z in range(1, 5)],
        
        # Glass roof - can see inside!
        *[(x, y, 6, BlockType.GLASS) for x in range(12) for y in range(4, 11)],
        *[(x, y, 7, BlockType.GLASS) for x in range(2, 10) for y in range(5, 10)],
        
        # Central altar
        *[(5, 6, z, BlockType.STONE_BRICKS) for z in range(1, 3)],
        *[(6, 6, z, BlockType.STONE_BRICKS) for z in range(1, 3)],
        *[(5, 7, z, BlockType.STONE_BRICKS) for z in range(1, 3)],
        *[(6, 7, z, BlockType.STONE_BRICKS) for z in range(1, 3)],
        (5, 6, 3, BlockType.GLOWSTONE),
        (6, 7, 3, BlockType.GLOWSTONE),
        
        # Decorative chest
        (5, 7, 3, BlockType.CHEST),
        (6, 6, 3, BlockType.ENCHANTING_TABLE) if hasattr(BlockType, 'ENCHANTING_TABLE') else (6, 6, 3, BlockType.BOOKSHELF),
    ]
}

# Block Selection Demo - Colorful showcase
STRUCTURE_BLOCK_SHOWCASE = {
    "name": "Block Showcase",
    "blocks": [
        # Rainbow platform floor
        *[(x, 0, 0, BlockType.RED_WOOL) for x in range(10)],
        *[(x, 1, 0, BlockType.ORANGE_WOOL) for x in range(10)],
        *[(x, 2, 0, BlockType.YELLOW_WOOL) for x in range(10)],
        *[(x, 3, 0, BlockType.LIME_WOOL) for x in range(10)],
        *[(x, 4, 0, BlockType.GREEN_WOOL) for x in range(10)],
        *[(x, 5, 0, BlockType.CYAN_WOOL) for x in range(10)],
        *[(x, 6, 0, BlockType.LIGHT_BLUE_WOOL) for x in range(10)],
        *[(x, 7, 0, BlockType.BLUE_WOOL) for x in range(10)],
        *[(x, 8, 0, BlockType.PURPLE_WOOL) for x in range(10)],
        *[(x, 9, 0, BlockType.MAGENTA_WOOL) for x in range(10)],
        
        # Display pedestals
        *[(2, y, 1, BlockType.QUARTZ_BLOCK) for y in range(10)],
        *[(7, y, 1, BlockType.QUARTZ_BLOCK) for y in range(10)],
        
        # Sample blocks on display
        (2, 0, 2, BlockType.DIAMOND_BLOCK),
        (2, 2, 2, BlockType.EMERALD_BLOCK),
        (2, 4, 2, BlockType.GOLD_BLOCK),
        (2, 6, 2, BlockType.IRON_BLOCK),
        (2, 8, 2, BlockType.LAPIS_BLOCK),
        (7, 1, 2, BlockType.REDSTONE_BLOCK),
        (7, 3, 2, BlockType.COAL_BLOCK),
        (7, 5, 2, BlockType.COPPER_BLOCK),
        (7, 7, 2, BlockType.NETHERITE_BLOCK) if hasattr(BlockType, 'NETHERITE_BLOCK') else (7, 7, 2, BlockType.OBSIDIAN),
        (7, 9, 2, BlockType.GLOWSTONE),
        
        # Border
        *[(0, y, z, BlockType.STONE_BRICKS) for y in range(10) for z in range(1, 3)],
        *[(9, y, z, BlockType.STONE_BRICKS) for y in range(10) for z in range(1, 3)],
    ]
}

# ===== END TUTORIAL SHOWCASE STRUCTURES =====

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

# Horror Obsidian Monolith - Creepy tall obsidian structure with crying obsidian accents
STRUCTURE_HORROR_MONOLITH = {
    "name": "Corrupted Tower",
    "blocks": [
        # Chaotic base platform - crying obsidian and obsidian scattered
        *[(x, y, 0, BlockType.OBSIDIAN if (x + y) % 2 == 0 else BlockType.CRYING_OBSIDIAN) 
          for x in range(-4, 5) for y in range(-4, 5) if abs(x) <= 4 and abs(y) <= 4],
        
        # Random obsidian scattered around the base
        (-3, -3, 1, BlockType.OBSIDIAN),
        (3, -2, 1, BlockType.CRYING_OBSIDIAN),
        (-2, 3, 1, BlockType.OBSIDIAN),
        (4, 1, 1, BlockType.OBSIDIAN),
        (-4, -1, 1, BlockType.CRYING_OBSIDIAN),
        (2, 4, 1, BlockType.OBSIDIAN),
        
        # Central tower - twisted and tall
        *[(0, 0, z, BlockType.OBSIDIAN) for z in range(1, 15)],
        *[(1, 0, z, BlockType.OBSIDIAN) for z in range(1, 13)],
        *[(0, 1, z, BlockType.OBSIDIAN) for z in range(1, 12)],
        *[(-1, 0, z, BlockType.OBSIDIAN) for z in range(1, 11)],
        *[(0, -1, z, BlockType.OBSIDIAN) for z in range(1, 10)],
        *[(1, 1, z, BlockType.OBSIDIAN) for z in range(1, 9)],
        *[(-1, -1, z, BlockType.OBSIDIAN) for z in range(1, 8)],
        *[(1, -1, z, BlockType.OBSIDIAN) for z in range(1, 7)],
        *[(-1, 1, z, BlockType.OBSIDIAN) for z in range(1, 6)],
        
        # Crying obsidian weeping streaks (random distribution)
        (0, 0, 2, BlockType.CRYING_OBSIDIAN),
        (0, 0, 5, BlockType.CRYING_OBSIDIAN),
        (0, 0, 8, BlockType.CRYING_OBSIDIAN),
        (0, 0, 11, BlockType.CRYING_OBSIDIAN),
        (1, 0, 3, BlockType.CRYING_OBSIDIAN),
        (1, 0, 7, BlockType.CRYING_OBSIDIAN),
        (1, 0, 10, BlockType.CRYING_OBSIDIAN),
        (0, 1, 4, BlockType.CRYING_OBSIDIAN),
        (0, 1, 8, BlockType.CRYING_OBSIDIAN),
        (-1, 0, 3, BlockType.CRYING_OBSIDIAN),
        (-1, 0, 6, BlockType.CRYING_OBSIDIAN),
        (0, -1, 4, BlockType.CRYING_OBSIDIAN),
        (0, -1, 7, BlockType.CRYING_OBSIDIAN),
        (1, 1, 2, BlockType.CRYING_OBSIDIAN),
        (1, 1, 5, BlockType.CRYING_OBSIDIAN),
        (-1, -1, 3, BlockType.CRYING_OBSIDIAN),
        
        # Chaotic spikes jutting out at random angles
        (-3, 0, 2, BlockType.OBSIDIAN),
        (-3, 0, 3, BlockType.OBSIDIAN),
        (3, 0, 2, BlockType.OBSIDIAN),
        (3, 0, 3, BlockType.CRYING_OBSIDIAN),
        (0, -3, 2, BlockType.OBSIDIAN),
        (0, -3, 3, BlockType.OBSIDIAN),
        (0, 3, 2, BlockType.CRYING_OBSIDIAN),
        (0, 3, 3, BlockType.OBSIDIAN),
        (-2, -2, 3, BlockType.OBSIDIAN),
        (-2, -2, 4, BlockType.CRYING_OBSIDIAN),
        (2, -2, 3, BlockType.OBSIDIAN),
        (2, -2, 4, BlockType.OBSIDIAN),
        (-2, 2, 3, BlockType.CRYING_OBSIDIAN),
        (-2, 2, 4, BlockType.OBSIDIAN),
        (2, 2, 3, BlockType.OBSIDIAN),
        (2, 2, 4, BlockType.CRYING_OBSIDIAN),
        
        # Corner pillars - jagged
        (-4, -4, 1, BlockType.OBSIDIAN),
        (-4, -4, 2, BlockType.OBSIDIAN),
        (-4, -4, 3, BlockType.CRYING_OBSIDIAN),
        (4, -4, 1, BlockType.OBSIDIAN),
        (4, -4, 2, BlockType.CRYING_OBSIDIAN),
        (4, -4, 3, BlockType.OBSIDIAN),
        (-4, 4, 1, BlockType.CRYING_OBSIDIAN),
        (-4, 4, 2, BlockType.OBSIDIAN),
        (-4, 4, 3, BlockType.OBSIDIAN),
        (4, 4, 1, BlockType.OBSIDIAN),
        (4, 4, 2, BlockType.OBSIDIAN),
        (4, 4, 3, BlockType.CRYING_OBSIDIAN),
        
        # Bone blocks scattered around like remains
        (-3, -1, 1, BlockType.BONE_BLOCK),
        (3, 1, 1, BlockType.BONE_BLOCK),
        (-1, -3, 1, BlockType.BONE_BLOCK),
        (1, 3, 1, BlockType.BONE_BLOCK),
        (-2, 1, 1, BlockType.BONE_BLOCK),
        (2, -1, 1, BlockType.BONE_BLOCK),
        (0, 0, 0, BlockType.BONE_BLOCK),  # Center skull
        
        # Violent crown on top - spiking outward
        (0, 0, 15, BlockType.CRYING_OBSIDIAN),
        (-1, 0, 14, BlockType.OBSIDIAN),
        (1, 0, 14, BlockType.OBSIDIAN),
        (0, -1, 14, BlockType.OBSIDIAN),
        (0, 1, 14, BlockType.OBSIDIAN),
        (2, 0, 12, BlockType.OBSIDIAN),
        (2, 0, 13, BlockType.CRYING_OBSIDIAN),
        (-2, 0, 11, BlockType.OBSIDIAN),
        (-2, 0, 12, BlockType.CRYING_OBSIDIAN),
        (0, 2, 11, BlockType.OBSIDIAN),
        (0, 2, 12, BlockType.OBSIDIAN),
        (0, -2, 10, BlockType.CRYING_OBSIDIAN),
        (0, -2, 11, BlockType.OBSIDIAN),
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
    "horror_monolith": STRUCTURE_HORROR_MONOLITH,
    # Tutorial showcase structures
    "welcome_showcase": STRUCTURE_WELCOME_SHOWCASE,
    "camera_demo": STRUCTURE_CAMERA_DEMO,
    "water_basins": STRUCTURE_WATER_BASINS,
    "dark_cave": STRUCTURE_DARK_CAVE,
    "rain_courtyard": STRUCTURE_RAIN_COURTYARD,
    "empty_platform": STRUCTURE_EMPTY_PLATFORM,
    "fill_area": STRUCTURE_FILL_AREA,
    "mirror_demo": STRUCTURE_MIRROR_DEMO,
    "brush_demo": STRUCTURE_BRUSH_DEMO,
    "undo_demo": STRUCTURE_UNDO_DEMO,
    "rotate_demo": STRUCTURE_ROTATE_DEMO,
    "save_demo": STRUCTURE_SAVE_DEMO,
    "block_showcase": STRUCTURE_BLOCK_SHOWCASE,
}

# Tutorial configuration file path
TUTORIAL_CONFIG_FILE = os.path.join(BASE_DIR, ".tutorial_config.json")


# ============================================================================
# TUTORIAL SYSTEM
# ============================================================================

class TutorialScreen:
    """
    A Minecraft-themed tutorial overlay that guides users through the application.
    
    Features:
    - Multi-step tutorial with navigation (Next/Back/Skip)
    - Minecraft-style button textures and click sounds
    - Visual block icons per step
    - "Show on startup" checkbox preference
    
    Author: Jeffrey Morais
    """
    
    # Tutorial content - compact, visual-focused steps with demo structures
    # Each step can specify a "demo" key with: "structure_name" | "clear" | "save:filename" | None
    # Special "is_horror" flag triggers dark mode effects
    TUTORIAL_STEPS = [
        {
            "title": "Welcome to Building!",
            "content": [
                "Welcome to Minecraft Builder!",
                "",
                "Try building in the area on the left:",
                "- Left Click to place blocks",
                "- Right Click to remove blocks",
                "- WASD to move the camera",
                "",
                "Place some blocks to get started!"
            ],
            "icons": ["grass_block", "dirt", "stone", "oak_planks", "cobblestone"],
            "demo": "welcome_showcase"  # Decorative platform to build on
        },
        {
            "title": "Camera Controls",
            "content": [
                "Navigate your world with ease:",
                "",
                "- Middle Mouse to pan the camera",
                "- Scroll wheel to zoom in/out",
                "- Q and E to rotate the view",
                "",
                "Try rotating around this tower!"
            ],
            "icons": ["oak_log", "oak_planks", "glass", "cobblestone", "stone"],
            "demo": "camera_demo"  # Tower structure good for rotating
        },
        {
            "title": "Block Selection",
            "content": [
                "Choose blocks from the panel:",
                "",
                "- Click blocks in the right panel",
                "- Use Search to find specific blocks",
                "- Press 1-9 for hotbar quick-select",
                "",
                "Try selecting different colored blocks!"
            ],
            "icons": ["red_wool", "blue_wool", "yellow_wool", "green_wool", "white_wool"],
            "demo": "block_showcase"  # Rainbow showcase of blocks
        },
        {
            "title": "Fill Tool",
            "content": [
                "Fill large areas quickly!",
                "",
                "- Press F to toggle Fill mode",
                "- Click and drag to fill an area",
                "- Great for floors and walls",
                "",
                "Try filling the empty dirt areas!"
            ],
            "icons": ["stone_bricks", "quartz_block", "sandstone", "smooth_stone", "prismarine"],
            "demo": "fill_area"  # Multi-level area to practice fill
        },
        {
            "title": "Brush Size",
            "content": [
                "Place multiple blocks at once:",
                "",
                "- Press B to cycle brush size",
                "- Sizes: 1x1, 2x2, 3x3",
                "- Great for building pillars/walls",
                "",
                "See the 3 sections for each brush size!"
            ],
            "icons": ["oak_log", "spruce_log", "birch_log", "jungle_log", "dark_oak_log"],
            "demo": "brush_demo"  # Shows 1x1, 2x2, 3x3 sections
        },
        {
            "title": "Undo & Redo",
            "content": [
                "Made a mistake? No problem!",
                "",
                "- Ctrl+Z to Undo",
                "- Ctrl+Y to Redo",
                "- Unlimited undo history",
                "",
                "Try undoing the misplaced blocks!"
            ],
            "icons": ["stone", "cobblestone", "mossy_cobblestone", "andesite", "diorite"],
            "demo": "undo_demo"  # Structure with "mistakes" to undo
        },
        {
            "title": "Mirror Mode",
            "content": [
                "Build symmetrically:",
                "",
                "- Press M for X-axis mirror",
                "- Shift+M for Z-axis mirror",
                "- Press N for quad symmetry",
                "",
                "Build on the left, mirror to the right!"
            ],
            "icons": ["red_wool", "blue_wool", "yellow_wool", "green_wool", "purple_wool"],
            "demo": "mirror_demo"  # Half-built structure with mirror line
        },
        {
            "title": "Rotate View",
            "content": [
                "See your build from all angles:",
                "",
                "- Press Q to rotate left",
                "- Press E to rotate right",
                "- 4 rotation angles available",
                "",
                "Rotate around this monument!"
            ],
            "icons": ["stone_bricks", "oak_planks", "stone", "oak_log", "glass"],
            "demo": "rotate_demo"  # Asymmetric structure for rotation
        },
        {
            "title": "Liquids & Flow",
            "content": [
                "Water and lava flow realistically!",
                "",
                "- Place water/lava blocks",
                "- Watch them spread downward",
                "- Water + Lava = Obsidian!",
                "",
                "Fill the basins with water!"
            ],
            "icons": ["water", "lava", "ice", "packed_ice", "obsidian"],
            "demo": "water_basins"  # Empty basins to fill with water
        },
        {
            "title": "Structures Library",
            "content": [
                "Load pre-built structures:",
                "",
                "- Press T to place a watchtower",
                "- Or open Structures in the panel",
                "- Villages, temples, and more!",
                "",
                "Press T to place a watchtower!"
            ],
            "icons": ["bookshelf", "crafting_table", "furnace", "chest", "enchanting_table"],
            "demo": "empty_platform"  # Empty area to place structures
        },
        {
            "title": "The Nether",
            "content": [
                "Enter the dangerous Nether!",
                "",
                "- Click 'Nether' in Features",
                "- Fiery atmosphere and lava",
                "- Soul sand and netherrack",
                "",
                "Look at this warped forest!"
            ],
            "icons": ["netherrack", "soul_sand", "nether_bricks", "glowstone", "magma_block"],
            "demo": "save:warped_forest"  # Load warped_forest.json save
        },
        {
            "title": "The End",
            "content": [
                "Reach The End dimension!",
                "",
                "- Click 'End' in Features",
                "- Void and end stone",
                "- Eerie purple atmosphere",
                "",
                "Explore this End City tower!"
            ],
            "icons": ["end_stone", "purpur_block", "obsidian", "bedrock", "end_stone"],
            "demo": "save:end_city_tower"  # Load end_city_tower.json save
        },
        {
            "title": "Weather Effects",
            "content": [
                "Add atmosphere to your world:",
                "",
                "- Toggle Rain and Snow buttons",
                "- Toggle Sun/Moon for day/night",
                "- Toggle Clouds on/off",
                "",
                "Watch the rain fall in the courtyard!"
            ],
            "icons": ["snow_block", "ice", "packed_ice", "snow", "white_wool"],
            "demo": "rain_courtyard"  # Open courtyard for rain
        },
        {
            "title": "Lighting",
            "content": [
                "See dynamic lighting effects:",
                "",
                "- Toggle Lighting in Features",
                "- Light sources glow realistically",
                "- Creates depth and shadows",
                "",
                "Light up the dark cave!"
            ],
            "icons": ["glowstone", "sea_lantern", "jack_o_lantern", "shroomlight", "magma_block"],
            "demo": "dark_cave"  # Cave with dark spots to light
        },
        {
            "title": "Save Your Work",
            "content": [
                "Save your creations:",
                "",
                "- Ctrl+S to save build",
                "- Ctrl+O to load a save",
                "- Auto-saves your last session",
                "",
                "This temple is worth saving!"
            ],
            "icons": ["chest", "ender_chest", "bookshelf", "jukebox", "crafting_table"],
            "demo": "save_demo"  # Impressive temple structure
        },
        {
            "title": "H̷i̶d̵d̴e̳n̲",  # Corrupted title
            "content": [
                "Ş̴͔̦͐̌̈́͝ơ̵̱̗̓̊̈́m̵̨̛̛̮̯̪͙͖̺̏͌̅̀̚͝e̵̞̬̲̭͔̞̎͌t̶̨̧̺̹̞̀͋̓̒̈́͘h̷̼̻̖̠͍͐̏́̇̀̾͝i̶̧̩̣̮̳͓̹̾̀n̵̟̭͓̭̭̟̋g̵̦̥̠̱̝̈́̆̐ ̴̛͇̈́̈́̆̀̕f̵̱̺͖̣̞̮̽̀̈̃ͅë̶̞̥̫́̄͊̌̌̃͘e̵̗͑̋̄̿̕ĺ̴̢̮̠͇̞͎̜̌̽́͒̌͜s̸̞̲̥̎̌̓͘ ̶̢̛̙̫̖̺͈̃̐w̷̩͙̮̓͗̽͑̈́r̶̡̛̤̟̤͉̫̠͋̊̓̾o̵̳̓̎͋͋́́ǹ̶̺̹̼͇̺̗̪̇̾̎g̶̜̪̈́̋͑̑̈́̚.̷̛̭̹̲͕͈̣̆̈͐͗̚.̸̡̳̖̜̹̤͖͑̾.̶̨̧̛͖̟̮̩̈́̈́̓̀̈́͘",
                "",
                "T̸̨̤̰͓͔̏̓̏̊͠ḧ̷̲͕̪͈̲̗́̀͑̒̔̐̕ḛ̷̡̝̝̙̯̳͂͛̓̐̓͝ ̷̛̹̭̬̓͋͐͒̉̉͝b̸̡̻̟̗̘̣̯̙̔̅̏l̵̞̫̱̖͂̌̆̚a̷̡̛̮͈̯̮̭̐̿c̵̻̣͆k̶̠͇̯̈́̆̀̓̓̕ ̴̨̤̥̪̳̠͛̀̍́̈́̎r̷̘̥̦̼̣̱̀̉͝ą̸̨̹͇̖̲̓̓͋̕͜ͅi̸̡̡̦̩̲͌͋̓̂͜n̴̰̩̘̈́̈́̆̾̀͝ ̷̼͖͇̰̫̮͓̒͒̔f̵̤͛̇̾́̃̕a̶̟̩̔͐̐̎͗̚l̷̨̺̖̦͓̫̄̋̉̀l̸͙̣̗̟͔̈́̎̇̚ş̸͓̱̹͓̿̐̎̍̌̾̕",
                "R̴̛̖͙̰̱̫̮͛̎̃̀e̵̩̞̺̗͆̓̈́̃̃d̵̛̞͍̱̈̓͋̀̃̔ ̴̠̖̲̝͚͐̓̆͆l̸̤̯̦̈̎͋̅̚ị̷̜̠̒̇g̷̨̫̗̯̺͕͚͛̿͌̇̍̑̕h̷̛̜͍͈̲̲̥͎̀̊̈́̿ṫ̵̫̣̻͉̠̗̈́̓͛͋̚n̸̤̮̈̂̓̽̒ī̴͖̯̞͚͖͛͂͆̓͐n̴̰̤̯͖̯͌̀͊̅g̴̮͖̪͆͑̈́̕ ̷̼͓̲̮̪̯͋̆̆̔̽s̵̙̼̗̖̮̫̻͋t̵͉͖̬̮̑̽̃͒̇̀r̶͎̰̖̰̐̐͆̊͆͝ỉ̶̫͇̗̳̙̿̈́͑͐͜k̷̖͚̹̇̐̉̂͛̚e̵͔̰̲̟̊͗̑̀͜ͅš̸͙̭̩̤",
                "T̵̼̻̮̲̤́̓̈̑̓͊̂h̵̹̼͈̥̲́̑͂̔̀̏̕ě̸͙̳͓̼̅̃͊̄̚͝ ̸̡̦̙̾̋̉̊w̶̨̡̖̞̘͂̋͌o̴̢̺̪̪͈͆͛r̷̢̭͍̋͗̆̍l̸̪̗͍̙̙͙͔̽̏̈d̵̺̟̻̭̝͒̄̏͂́͑ ̷̜̟̮͔̻̪̆̿̃̇̀̀͘g̸͔̬͙̑̔̔̈́̐ͅr̶̨̰̳̹̫̈̒̿̕͝o̵̪̘̥̫̩͆͗̾̊̋̽͘w̵̢̫̞̥͔̘̑̈́̆̚s̶̛̜̘̊ ̴̥̟͉͙̤̟̱̒d̵̜̣̹̜̈́̾̅ḁ̸̰̖̯̪͔̿̅̊̈́̏̕r̸̦̝̪̥̊̏k̴̳̠̅",
                "",
                "Ţ̷̺͇͔̫͋̓̒ḧ̷̨̨̦̪̬́̆̎̑̋͝è̴̪͖̝̓͌́̚ÿ̵̳̠̱́̈́ ̷͍̙̑͒̓̑ą̶̛̗̯̳͈̎͆̎̓̀̈́r̶̤̹̮̉̒̚ȩ̶̲̝̰̰̱̟̎̆̀͐̃̐ ̶̪̝̭̬̦̇w̸̜̘̙̯̃̊̆̓a̸̗̮͖͋͘t̷̡̧̙͇̮͉̝͂͛́̑c̷͙̝̼̟̥̐̇h̴̞͇̳̯̿̅̈́̏ḯ̶̧̥̺̰̱̰̈́͝͠n̸̡̺̜͙͔͂͝ͅg̶̙̳̲̈̅̋.̸̡̱̮̼̐̓̂"
            ],
            "icons": ["crying_obsidian", "obsidian", "bone_block", "crying_obsidian", "obsidian"],
            "demo": "horror_monolith",
            "is_horror": True  # Triggers special effects
        },
        {
            "title": "Ready to Build!",
            "content": [
                "Quick Reference:",
                "",
                "- WASD = Move | Scroll = Zoom",
                "- LClick = Place | RClick = Remove",
                "- F = Fill | M = Mirror | B = Brush",
                "- Ctrl+Z = Undo | Ctrl+S = Save",
                "",
                "Press H to see this tutorial again!"
            ],
            "icons": ["diamond_block", "emerald_block", "gold_block", "iron_block", "lapis_block"],
            "demo": "clear"  # Clear for fresh start
        }
    ]
    
    def __init__(self, screenWidth: int, screenHeight: int):
        """
        Initialize the tutorial screen.
        
        Args:
            screenWidth: Width of the game window
            screenHeight: Height of the game window
        """
        self.screenWidth = screenWidth
        self.screenHeight = screenHeight
        self.currentStep = 0
        self.visible = False
        self.showOnStartup = True
        
        # Callback for demo structure loading (set by main app)
        self.onStepChange = None
        # Callback for when tutorial ends (set by main app)
        self.onTutorialEnd = None
        
        # Load saved preferences
        self._loadConfig()
        
        # Panel dimensions - positioned on RIGHT side to leave building area visible
        self.panelWidth = 400  # Narrower to leave more building space
        self.panelHeight = 500
        self.panelX = screenWidth - self.panelWidth - 20  # Right side with margin
        self.panelY = (screenHeight - self.panelHeight) // 2
        
        # Button dimensions
        self.buttonWidth = 90
        self.buttonHeight = 28
        self.buttonSpacing = 12
        
        # Checkbox dimensions
        self.checkboxSize = 18
        
        # Calculate button positions (at bottom of panel)
        buttonY = self.panelY + self.panelHeight - 75
        totalButtonWidth = 3 * self.buttonWidth + 2 * self.buttonSpacing
        startX = self.panelX + (self.panelWidth - totalButtonWidth) // 2
        
        self.backButtonRect = pygame.Rect(startX, buttonY, self.buttonWidth, self.buttonHeight)
        self.nextButtonRect = pygame.Rect(startX + self.buttonWidth + self.buttonSpacing, 
                                           buttonY, self.buttonWidth, self.buttonHeight)
        self.skipButtonRect = pygame.Rect(startX + 2 * (self.buttonWidth + self.buttonSpacing), 
                                           buttonY, self.buttonWidth, self.buttonHeight)
        
        # Checkbox position (below buttons, inside panel)
        checkboxY = buttonY + self.buttonHeight + 12
        self.checkboxRect = pygame.Rect(
            self.panelX + (self.panelWidth - 180) // 2,
            checkboxY,
            self.checkboxSize,
            self.checkboxSize
        )
        
        # UI textures (will be set from AssetManager)
        self.buttonNormal = None
        self.buttonHover = None
        self.checkboxTexture = None
        self.checkboxSelectedTexture = None
        self.clickSound = None
        self.assetManager = None  # For fetching block icons
        
        # Block icons to display per step (step index -> list of BlockTypes)
        self.stepIcons = {}
        
        # Fonts
        self.titleFont = pygame.font.Font(None, 36)
        self.contentFont = pygame.font.Font(None, 26)
        self.smallFont = pygame.font.Font(None, 22)
        
        # Hover states for buttons
        self.backHovered = False
        self.nextHovered = False
        self.skipHovered = False
        self.checkboxHovered = False
    
    def _loadConfig(self):
        """Load tutorial preferences from config file"""
        try:
            if os.path.exists(TUTORIAL_CONFIG_FILE):
                with open(TUTORIAL_CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    self.showOnStartup = config.get("showOnStartup", True)
        except Exception as e:
            print(f"Could not load tutorial config: {e}")
            self.showOnStartup = True
    
    def _saveConfig(self):
        """Save tutorial preferences to config file"""
        try:
            config = {"showOnStartup": self.showOnStartup}
            with open(TUTORIAL_CONFIG_FILE, 'w') as f:
                json.dump(config, f)
        except Exception as e:
            print(f"Could not save tutorial config: {e}")
    
    def setAssets(self, buttonNormal: pygame.Surface, buttonHover: pygame.Surface,
                  checkboxTexture: pygame.Surface, checkboxSelectedTexture: pygame.Surface,
                  clickSound: pygame.mixer.Sound, assetManager=None):
        """
        Set the UI assets from AssetManager.
        
        Args:
            buttonNormal: Normal button texture
            buttonHover: Hovered button texture
            checkboxTexture: Unchecked checkbox texture
            checkboxSelectedTexture: Checked checkbox texture
            clickSound: Click sound effect
            assetManager: AssetManager instance for fetching block icons
        """
        self.buttonNormal = buttonNormal
        self.buttonHover = buttonHover
        self.checkboxTexture = checkboxTexture
        self.checkboxSelectedTexture = checkboxSelectedTexture
        self.clickSound = clickSound
        self.assetManager = assetManager
    
    def show(self):
        """Show the tutorial from the beginning"""
        self.currentStep = 0
        self.visible = True
        # Notify main app to load demo for first step
        if self.onStepChange:
            self.onStepChange(self.currentStep)
    
    def hide(self):
        """Hide the tutorial"""
        self.visible = False
        # Notify main app that tutorial ended
        if self.onTutorialEnd:
            self.onTutorialEnd()
    
    def isVisible(self) -> bool:
        """Check if tutorial is currently visible"""
        return self.visible
    
    def shouldShowOnStartup(self) -> bool:
        """Check if tutorial should show on startup"""
        return self.showOnStartup
    
    def handleEvent(self, event: pygame.event.Event) -> bool:
        """
        Handle pygame events for the tutorial.
        
        Args:
            event: The pygame event to handle
            
        Returns:
            True if the event was consumed by the tutorial
        """
        if not self.visible:
            return False
        
        # Always allow QUIT events to pass through
        if event.type == pygame.QUIT:
            return False
        
        if event.type == pygame.MOUSEMOTION:
            mouseX, mouseY = event.pos
            self.backHovered = self.backButtonRect.collidepoint(mouseX, mouseY)
            self.nextHovered = self.nextButtonRect.collidepoint(mouseX, mouseY)
            self.skipHovered = self.skipButtonRect.collidepoint(mouseX, mouseY)
            self.checkboxHovered = self.checkboxRect.collidepoint(mouseX, mouseY)
            # Allow mouse motion to pass through for world interaction
            return False
        
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouseX, mouseY = event.pos
            
            # Check button clicks
            if self.backButtonRect.collidepoint(mouseX, mouseY):
                self._onBackClick()
                return True
            
            if self.nextButtonRect.collidepoint(mouseX, mouseY):
                self._onNextClick()
                return True
            
            if self.skipButtonRect.collidepoint(mouseX, mouseY):
                self._onSkipClick()
                return True
            
            if self.checkboxRect.collidepoint(mouseX, mouseY):
                self._onCheckboxClick()
                return True
            
            # Check if click is inside the panel - consume it
            panelRect = pygame.Rect(self.panelX, self.panelY, self.panelWidth, self.panelHeight)
            if panelRect.collidepoint(mouseX, mouseY):
                return True  # Click on panel - consume to prevent misclicks
            
            # Click outside panel - allow interaction with the world!
            return False
        
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._onSkipClick()
                return True
            if event.key == pygame.K_RIGHT or event.key == pygame.K_RETURN:
                self._onNextClick()
                return True
            if event.key == pygame.K_LEFT:
                self._onBackClick()
                return True
            # All other keys - allow through for building
            return False
        
        # Mouse motion and other events - allow through
        return False
    
    def _playClickSound(self):
        """Play the click sound if available"""
        if self.clickSound:
            self.clickSound.play()
    
    def _onBackClick(self):
        """Handle Back button click"""
        if self.currentStep > 0:
            self._playClickSound()
            self.currentStep -= 1
            # Notify main app of step change to load demo
            if self.onStepChange:
                self.onStepChange(self.currentStep)
    
    def _onNextClick(self):
        """Handle Next button click"""
        self._playClickSound()
        if self.currentStep < len(self.TUTORIAL_STEPS) - 1:
            self.currentStep += 1
            # Notify main app of step change to load demo
            if self.onStepChange:
                self.onStepChange(self.currentStep)
        else:
            # Last step - close tutorial
            self.hide()
    
    def _onSkipClick(self):
        """Handle Skip button click"""
        self._playClickSound()
        self.hide()
    
    def _onCheckboxClick(self):
        """Handle checkbox click"""
        self._playClickSound()
        self.showOnStartup = not self.showOnStartup
        self._saveConfig()
    
    def _iconNameToBlockType(self, name: str) -> Optional[BlockType]:
        """Convert an icon name string to BlockType enum"""
        # Map common names to BlockType
        nameMap = {
            "grass": BlockType.GRASS,
            "grass_block": BlockType.GRASS,
            "dirt": BlockType.DIRT,
            "stone": BlockType.STONE,
            "cobblestone": BlockType.COBBLESTONE,
            "oak_planks": BlockType.OAK_PLANKS,
            "oak_log": BlockType.OAK_LOG,
            "oak_leaves": BlockType.OAK_LEAVES,
            "bricks": BlockType.BRICKS,
            "glass": BlockType.GLASS,
            "water": BlockType.WATER,
            "lava": BlockType.LAVA,
            "glowstone": BlockType.GLOWSTONE,
            "sea_lantern": BlockType.SEA_LANTERN,
            "jack_o_lantern": BlockType.JACK_O_LANTERN,
            "magma_block": BlockType.MAGMA_BLOCK,
            "shroomlight": BlockType.SHROOMLIGHT,
            "iron_ore": BlockType.IRON_ORE,
            "diamond_block": BlockType.DIAMOND_BLOCK,
            "gold_block": BlockType.GOLD_BLOCK,
            "emerald_block": BlockType.EMERALD_BLOCK,
            "iron_block": BlockType.IRON_BLOCK,
            "copper_block": BlockType.COPPER_BLOCK,
            "netherrack": BlockType.NETHERRACK,
            "end_stone": BlockType.END_STONE,
            "obsidian": BlockType.OBSIDIAN,
            "crying_obsidian": BlockType.CRYING_OBSIDIAN,
            "snow_block": BlockType.SNOW,
            "snow": BlockType.SNOW,
            "ice": BlockType.ICE,
            "packed_ice": BlockType.PACKED_ICE,
            "blue_ice": BlockType.PACKED_ICE,  # Use packed_ice as fallback
            "powder_snow": BlockType.SNOW,  # Use snow as fallback
            "stone_bricks": BlockType.STONE_BRICKS,
            "mossy_stone_bricks": BlockType.MOSSY_STONE_BRICKS,
            "chiseled_stone_bricks": BlockType.CHISELED_STONE_BRICKS,
            "polished_andesite": BlockType.POLISHED_ANDESITE,
            "andesite": BlockType.ANDESITE,
            "diorite": BlockType.DIORITE,
            "granite": BlockType.GRANITE,
            "mossy_cobblestone": BlockType.MOSSY_COBBLESTONE,
            "polished_blackstone_bricks": BlockType.POLISHED_BLACKSTONE_BRICKS,
            "prismarine_bricks": BlockType.PRISMARINE_BRICKS,
            "prismarine": BlockType.PRISMARINE,
            "nether_bricks": BlockType.NETHER_BRICKS,
            "nether_wart_block": BlockType.NETHER_WART_BLOCK,
            "quartz_block": BlockType.QUARTZ_BLOCK,
            "smooth_stone": BlockType.SMOOTH_STONE,
            "sandstone": BlockType.SANDSTONE,
            "deepslate": BlockType.STONE,  # Use stone as fallback (no DEEPSLATE)
            "white_concrete": BlockType.WHITE_CONCRETE,
            "blue_stained_glass": BlockType.BLUE_STAINED_GLASS,
            "cyan_stained_glass": BlockType.CYAN_STAINED_GLASS,
            "red_stained_glass": BlockType.RED_STAINED_GLASS,
            "purple_stained_glass": BlockType.PURPLE_STAINED_GLASS,
            "spruce_planks": BlockType.SPRUCE_PLANKS,
            "spruce_log": BlockType.SPRUCE_LOG,
            "birch_log": BlockType.BIRCH_LOG,
            "jungle_log": BlockType.JUNGLE_LOG,
            "dark_oak_log": BlockType.DARK_OAK_LOG,
            "dark_oak_leaves": BlockType.DARK_OAK_LEAVES,
            "diamond_ore": BlockType.DIAMOND_ORE,
            "lapis_block": BlockType.LAPIS_BLOCK,
            "redstone_block": BlockType.REDSTONE_BLOCK,
            "crafting_table": BlockType.CRAFTING_TABLE,
            "furnace": BlockType.FURNACE,
            "chest": BlockType.CHEST,
            "ender_chest": BlockType.ENDER_CHEST,
            "enchanting_table": BlockType.ENCHANTING_TABLE,
            "jukebox": BlockType.JUKEBOX,
            "bookshelf": BlockType.BOOKSHELF,
            "torch": BlockType.GLOWSTONE,  # Use glowstone as fallback (no TORCH)
            "lantern": BlockType.SEA_LANTERN,  # Use sea_lantern as fallback
            "soul_sand": BlockType.SOUL_SAND,
            "purpur_block": BlockType.PURPUR_BLOCK,
            "red_wool": BlockType.RED_WOOL,
            "blue_wool": BlockType.BLUE_WOOL,
            "yellow_wool": BlockType.YELLOW_WOOL,
            "green_wool": BlockType.GREEN_WOOL,
            "white_wool": BlockType.WHITE_WOOL,
            "purple_wool": BlockType.PURPLE_WOOL,
            "black_wool": BlockType.BLACK_WOOL,
            "tnt": BlockType.TNT,
            "bedrock": BlockType.BEDROCK,
            "bone_block": BlockType.BONE_BLOCK,
            "dark_water": BlockType.WATER,  # Special dark water for horror tutorial
        }
        return nameMap.get(name.lower())
    
    def _createDarkWaterIcon(self, size: int) -> pygame.Surface:
        """Create a darkened water icon for horror tutorial mode"""
        if not self.assetManager:
            # Fallback: dark blue square
            surf = pygame.Surface((size, size), pygame.SRCALPHA)
            surf.fill((20, 30, 50, 200))
            return surf
        
        # Get the water sprite
        waterSprite = self.assetManager.getBlockSprite(BlockType.WATER)
        if not waterSprite:
            surf = pygame.Surface((size, size), pygame.SRCALPHA)
            surf.fill((20, 30, 50, 200))
            return surf
        
        # Scale to icon size
        spriteW, spriteH = waterSprite.get_size()
        scale = size / max(spriteW, spriteH)
        newW = int(spriteW * scale)
        newH = int(spriteH * scale)
        scaledSprite = pygame.transform.smoothscale(waterSprite, (newW, newH))
        
        # Create darkened version
        darkSurf = scaledSprite.copy()
        # Apply dark overlay
        darkOverlay = pygame.Surface((newW, newH), pygame.SRCALPHA)
        darkOverlay.fill((0, 0, 30, 180))  # Very dark blue overlay
        darkSurf.blit(darkOverlay, (0, 0))
        
        # Add subtle blue glow edge
        glowSurf = pygame.Surface((newW + 4, newH + 4), pygame.SRCALPHA)
        glowSurf.fill((30, 60, 120, 40))
        
        # Final surface
        finalSurf = pygame.Surface((size, size), pygame.SRCALPHA)
        offsetX = (size - newW) // 2
        offsetY = (size - newH) // 2
        finalSurf.blit(darkSurf, (offsetX, offsetY))
        
        return finalSurf

    def render(self, screen: pygame.Surface):
        """
        Render the tutorial overlay.
        
        Args:
            screen: The pygame surface to render to
        """
        if not self.visible:
            return
        
        # Get current step content
        step = self.TUTORIAL_STEPS[self.currentStep]
        is_horror = step.get("is_horror", False)
        
        # Horror mode: darken the entire screen significantly
        if is_horror:
            darkOverlay = pygame.Surface((self.screenWidth, self.screenHeight), pygame.SRCALPHA)
            darkOverlay.fill((0, 0, 0, 180))  # Darker overlay for horror effect
            screen.blit(darkOverlay, (0, 0))
        
        # Panel background (dark with border, darker for horror)
        panelColor = (15, 10, 20) if is_horror else (30, 30, 35)
        borderColor = (80, 20, 30) if is_horror else (80, 80, 90)
        panelRect = pygame.Rect(self.panelX, self.panelY, self.panelWidth, self.panelHeight)
        pygame.draw.rect(screen, panelColor, panelRect)
        pygame.draw.rect(screen, borderColor, panelRect, 3)
        
        # Inner border for depth effect
        innerColor = (30, 15, 25) if is_horror else (50, 50, 55)
        innerRect = pygame.Rect(self.panelX + 5, self.panelY + 5, 
                                 self.panelWidth - 10, self.panelHeight - 10)
        pygame.draw.rect(screen, innerColor, innerRect, 1)
        
        # Progress indicator
        progressText = f"Step {self.currentStep + 1} of {len(self.TUTORIAL_STEPS)}"
        progressColor = (100, 50, 50) if is_horror else (150, 150, 150)
        progressSurf = self.smallFont.render(progressText, True, progressColor)
        progressRect = progressSurf.get_rect(centerx=self.panelX + self.panelWidth // 2,
                                              top=self.panelY + 15)
        screen.blit(progressSurf, progressRect)
        
        # Progress bar
        barWidth = self.panelWidth - 60
        barHeight = 6
        barX = self.panelX + 30
        barY = self.panelY + 38
        pygame.draw.rect(screen, (60, 60, 70), (barX, barY, barWidth, barHeight))
        fillWidth = int(barWidth * (self.currentStep + 1) / len(self.TUTORIAL_STEPS))
        pygame.draw.rect(screen, (76, 175, 80), (barX, barY, fillWidth, barHeight))
        
        # Title
        titleSurf = self.titleFont.render(step["title"], True, (255, 255, 255))
        titleRect = titleSurf.get_rect(centerx=self.panelX + self.panelWidth // 2,
                                        top=self.panelY + 55)
        screen.blit(titleSurf, titleRect)
        
        # Decorative line under title
        lineY = titleRect.bottom + 8
        pygame.draw.line(screen, (80, 80, 90), 
                        (self.panelX + 40, lineY), 
                        (self.panelX + self.panelWidth - 40, lineY), 2)
        
        # Draw block icons for this step from step data
        iconNames = step.get("icons", [])
        if iconNames and self.assetManager:
            iconSize = 56  # Larger icons for better visibility
            iconSpacing = 10
            totalIconWidth = len(iconNames) * iconSize + (len(iconNames) - 1) * iconSpacing
            iconStartX = self.panelX + (self.panelWidth - totalIconWidth) // 2
            iconY = lineY + 12
            
            for i, iconName in enumerate(iconNames):
                iconX = iconStartX + i * (iconSize + iconSpacing)
                
                # Draw slot background - darker for horror mode
                slotRect = pygame.Rect(iconX - 3, iconY - 3, iconSize + 6, iconSize + 6)
                pygame.draw.rect(screen, (15, 20, 30), slotRect)
                pygame.draw.rect(screen, (30, 40, 60), slotRect, 1)
                
                # Check for special dark_water icon (horror tutorial)
                if iconName == "dark_water":
                    darkWaterIcon = self._createDarkWaterIcon(iconSize)
                    screen.blit(darkWaterIcon, (iconX, iconY))
                else:
                    # Convert icon name to BlockType
                    blockType = self._iconNameToBlockType(iconName)
                    if blockType:
                        blockSprite = self.assetManager.getBlockSprite(blockType)
                        if blockSprite:
                            spriteW, spriteH = blockSprite.get_size()
                            scale = iconSize / max(spriteW, spriteH)
                            newW = int(spriteW * scale)
                            newH = int(spriteH * scale)
                            # Use smoothscale for high-quality tutorial icons
                            scaledSprite = pygame.transform.smoothscale(blockSprite, (newW, newH))
                            offsetX = (iconSize - newW) // 2
                            offsetY = (iconSize - newH) // 2
                            screen.blit(scaledSprite, (iconX + offsetX, iconY + offsetY))
            
            contentY = iconY + iconSize + 15
        else:
            contentY = lineY + 15
        
        # Content - use smaller line spacing for compact display
        for line in step["content"]:
            if line:  # Skip empty lines but preserve spacing
                lineSurf = self.contentFont.render(line, True, (220, 220, 220))
                screen.blit(lineSurf, (self.panelX + 30, contentY))
            contentY += 24  # Tighter line spacing
        
        # Draw buttons
        self._drawButton(screen, self.backButtonRect, "Back", 
                        self.backHovered, self.currentStep == 0)
        
        # Next button shows "Finish" on last step
        nextText = "Finish" if self.currentStep == len(self.TUTORIAL_STEPS) - 1 else "Next"
        self._drawButton(screen, self.nextButtonRect, nextText, self.nextHovered, False)
        
        self._drawButton(screen, self.skipButtonRect, "Skip", self.skipHovered, False)
        
        # Draw checkbox
        self._drawCheckbox(screen)
    
    def _drawButton(self, screen: pygame.Surface, rect: pygame.Rect, 
                    text: str, hovered: bool, disabled: bool):
        """
        Draw a Minecraft-style button.
        
        Args:
            screen: Surface to draw on
            rect: Button rectangle
            text: Button label
            hovered: Whether button is being hovered
            disabled: Whether button is disabled
        """
        # Choose texture based on state
        if disabled:
            # Disabled state - darker and grayed out
            color = (50, 50, 55)
            textColor = (100, 100, 100)
        elif hovered:
            texture = self.buttonHover if self.buttonHover else None
            textColor = (255, 255, 160)  # Bright yellow on hover
        else:
            texture = self.buttonNormal if self.buttonNormal else None
            textColor = (255, 255, 255)
        
        if disabled:
            pygame.draw.rect(screen, color, rect)
            pygame.draw.rect(screen, (40, 40, 45), rect, 2)
        elif hovered and self.buttonHover:
            scaledBtn = pygame.transform.scale(self.buttonHover, (rect.width, rect.height))
            screen.blit(scaledBtn, rect.topleft)
        elif self.buttonNormal:
            scaledBtn = pygame.transform.scale(self.buttonNormal, (rect.width, rect.height))
            screen.blit(scaledBtn, rect.topleft)
        else:
            # Fallback rendering
            color = (90, 90, 100) if hovered else (70, 70, 80)
            pygame.draw.rect(screen, color, rect)
            pygame.draw.rect(screen, (50, 50, 60), rect, 2)
        
        # Text with shadow
        shadowSurf = self.smallFont.render(text, True, (30, 30, 30))
        shadowRect = shadowSurf.get_rect(center=(rect.centerx + 1, rect.centery + 1))
        screen.blit(shadowSurf, shadowRect)
        
        textSurf = self.smallFont.render(text, True, textColor)
        textRect = textSurf.get_rect(center=rect.center)
        screen.blit(textSurf, textRect)
    
    def _drawCheckbox(self, screen: pygame.Surface):
        """Draw the 'Show on startup' checkbox"""
        # Checkbox texture
        if self.showOnStartup and self.checkboxSelectedTexture:
            scaledCb = pygame.transform.scale(self.checkboxSelectedTexture, 
                                               (self.checkboxSize, self.checkboxSize))
            screen.blit(scaledCb, self.checkboxRect.topleft)
        elif not self.showOnStartup and self.checkboxTexture:
            scaledCb = pygame.transform.scale(self.checkboxTexture,
                                               (self.checkboxSize, self.checkboxSize))
            screen.blit(scaledCb, self.checkboxRect.topleft)
        else:
            # Fallback rendering
            pygame.draw.rect(screen, (60, 60, 70), self.checkboxRect)
            pygame.draw.rect(screen, (80, 80, 90), self.checkboxRect, 2)
            if self.showOnStartup:
                # Draw checkmark
                pygame.draw.line(screen, (76, 175, 80),
                               (self.checkboxRect.left + 4, self.checkboxRect.centery),
                               (self.checkboxRect.centerx - 2, self.checkboxRect.bottom - 5), 2)
                pygame.draw.line(screen, (76, 175, 80),
                               (self.checkboxRect.centerx - 2, self.checkboxRect.bottom - 5),
                               (self.checkboxRect.right - 4, self.checkboxRect.top + 5), 2)
        
        # Label
        labelColor = (200, 200, 200) if self.checkboxHovered else (170, 170, 170)
        labelSurf = self.smallFont.render("Show tutorial on startup", True, labelColor)
        labelX = self.checkboxRect.right + 10
        labelY = self.checkboxRect.centery - labelSurf.get_height() // 2
        screen.blit(labelSurf, (labelX, labelY))


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
        self.checkboxTexture: Optional[pygame.Surface] = None
        self.checkboxSelectedTexture: Optional[pygame.Surface] = None
        
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
        self.endPortalAnimationSpeed = 300  # milliseconds per update
        
        # Animation support for fire
        self.fireFrames: List[pygame.Surface] = []
        self.soulFireFrames: List[pygame.Surface] = []
        self.currentFireFrame = 0
        self.fireAnimationTimer = 0
        self.fireAnimationSpeed = 60  # milliseconds per frame (fast fire animation)
        
        # Matrix block animation (falling green code)
        self.matrixScrollOffset = 0  # Scroll offset for animation
        self.matrixAnimationTimer = 0
        self.matrixAnimationSpeed = 80  # milliseconds per frame
        
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
        
        # Fire ambient sound (crackling every ~5 seconds)
        self.fireAmbientTimer = 0
        self.fireAmbientInterval = 5000  # milliseconds (5 seconds)
        
        # Sound cooldown system to prevent sound spam
        self.soundLastPlayed: Dict[str, int] = {}  # Category -> last play time (ms)
        self.soundCooldown = 50  # Minimum ms between same sound category
        self.soundActiveChannels: Dict[str, int] = {}  # Category -> active channel count
        self.maxSoundsPerCategory = 4  # Max concurrent sounds per category
        
        # Rain system
        self.rainSounds: List[pygame.mixer.Sound] = []
        self.thunderSounds: List[pygame.mixer.Sound] = []
        self.thunderAmbientSounds: List[pygame.mixer.Sound] = []
        self.rainSoundChannel: Optional[pygame.mixer.Channel] = None
        self.rainTexture: Optional[pygame.Surface] = None
    
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
                texture = pygame.image.load(texturePath).convert_alpha()
                
                # Check if this texture has animation metadata (.mcmeta file)
                # If so, the texture might be a vertical strip of frames - extract just the first frame
                mcmetaPath = texturePath + ".mcmeta"
                if os.path.exists(mcmetaPath):
                    # Animated texture - assume square frames stacked vertically
                    frameWidth = texture.get_width()
                    # If height > width, it's an animated texture strip
                    if texture.get_height() > frameWidth:
                        # Extract just the first frame (top of the strip)
                        texture = texture.subsurface((0, 0, frameWidth, frameWidth))
                
                self.textures[textureName] = texture
        
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
                # Also update icon sprite for animated panel
                self._updateAnimatedIcon(BlockType.WATER)
            
            # Advance lava frame (slower than water)
            if self.lavaFrames and self.currentWaterFrame % 2 == 0:
                self.currentLavaFrame = (self.currentLavaFrame + 1) % len(self.lavaFrames)
                # Recreate lava sprite with new frame
                frame = self.lavaFrames[self.currentLavaFrame]
                self.blockSprites[BlockType.LAVA] = self._createLiquidBlock(
                    frame, frame, frame, isWater=False, level=8
                )
                # Also update icon sprite for animated panel
                self._updateAnimatedIcon(BlockType.LAVA)
        
        # Update portal animation (separate timer for slower animation)
        self.portalAnimationTimer += dt
        if self.portalAnimationTimer >= self.portalAnimationSpeed:
            self.portalAnimationTimer = 0
            if self.portalFrames:
                self.currentPortalFrame = (self.currentPortalFrame + 1) % len(self.portalFrames)
                # Recreate portal sprite with new frame
                frame = self.portalFrames[self.currentPortalFrame]
                self.blockSprites[BlockType.NETHER_PORTAL] = self._createPortalBlock(frame)
                # Also update icon sprite for animated panel
                self._updateAnimatedIcon(BlockType.NETHER_PORTAL)
        
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
                # Also update icon sprites for animated panel
                self._updateAnimatedIcon(BlockType.END_PORTAL)
                self._updateAnimatedIcon(BlockType.END_GATEWAY)
        
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
        
        # Update Matrix block animation (falling green code)
        self.matrixAnimationTimer += dt
        if self.matrixAnimationTimer >= self.matrixAnimationSpeed:
            self.matrixAnimationTimer = 0
            # Recreate matrix sprite
            self.blockSprites[BlockType.MATRIX] = self._createMatrixBlock()
            self._updateAnimatedIcon(BlockType.MATRIX)
        
        # Update spawner particles
        self.spawnerParticleTimer += dt
        if self.spawnerParticleTimer >= self.spawnerParticleSpeed:
            self.spawnerParticleTimer = 0
            # Update existing particles
            for particle in self.spawnerParticles:
                particle["life"] -= 1
                particle["px"] += particle["vx"]
                particle["py"] += particle["vy"]
                particle["vy"] -= 0.1  # Float upward
            # Remove dead particles efficiently
            self.spawnerParticles = [p for p in self.spawnerParticles if p["life"] > 0]
        
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
        
        # Decay sound active channel counts (sounds typically last < 500ms)
        # Every 200ms, decrement all counts to allow new sounds
        if hasattr(self, '_soundDecayTimer'):
            self._soundDecayTimer += dt
        else:
            self._soundDecayTimer = 0
        if self._soundDecayTimer >= 200:
            self._soundDecayTimer = 0
            for category in list(self.soundActiveChannels.keys()):
                if self.soundActiveChannels[category] > 0:
                    self.soundActiveChannels[category] -= 1
    
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
            elif blockType == BlockType.MATRIX:
                # Matrix block uses animated falling code effect
                self.blockSprites[blockType] = self._createMatrixBlock()
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
            topTex = pygame.transform.scale(topTexture, (texW, texW))
        else:
            topTex = pygame.Surface((texW, texW))
            topTex.fill((100, 100, 100))
        
        if leftTexture:
            leftTex = pygame.transform.scale(leftTexture, (texW, texH))
        else:
            leftTex = pygame.Surface((texW, texH))
            leftTex.fill((80, 80, 80))
            
        if rightTexture:
            rightTex = pygame.transform.scale(rightTexture, (texW, texH))
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
                            except (IndexError, pygame.error):
                                pass  # Edge pixel access
        
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
                    except (IndexError, pygame.error):
                        pass  # Edge pixel access
        
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
                    except (IndexError, pygame.error):
                        pass  # Edge pixel access

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
        topHalfTex = pygame.transform.scale(topTexture, (texSize, texSize)) if topTexture else None
        botHalfTex = pygame.transform.scale(sideTexture, (texSize, texSize)) if sideTexture else None
        
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
        topTex = pygame.transform.scale(topTexture, (texSize, texSize)) if topTexture else None
        sideTex = pygame.transform.scale(sideTexture, (texSize, texSize)) if sideTexture else None
        
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
        Portal is rendered as a full 1x1x1 cube with semi-transparent animated texture.
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
        
        # TOP FACE - full isometric diamond
        for py in range(TILE_HEIGHT):
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
                relX = px - halfW
                relY = py - halfH
                
                # Inverse isometric projection to texture coords
                u = (relX / halfW + relY / halfH) * 0.5 + 0.5 if halfW > 0 and halfH > 0 else 0.5
                v = (-relX / halfW + relY / halfH) * 0.5 + 0.5 if halfW > 0 and halfH > 0 else 0.5
                
                texX = int(u * (texSize - 1))
                texY = int(v * (texSize - 1))
                texX = max(0, min(texSize - 1, texX))
                texY = max(0, min(texSize - 1, texY))
                
                if portalTex:
                    color = portalTex.get_at((texX, texY))
                    surface.set_at((px, py), (color.r, color.g, color.b, alpha))
                else:
                    surface.set_at((px, py), (*portalColor, alpha))
        
        # LEFT FACE - full height
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
                    # Darken for left face
                    r = int(color.r * 0.75)
                    g = int(color.g * 0.75)
                    b = int(color.b * 0.75)
                    surface.set_at((px, py), (r, g, b, alpha))
                else:
                    dc = self._darkenColor(portalColor, 0.75)
                    surface.set_at((px, py), (*dc, alpha))
        
        # RIGHT FACE - full height
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
                    # Slightly darken for right face
                    r = int(color.r * 0.9)
                    g = int(color.g * 0.9)
                    b = int(color.b * 0.9)
                    surface.set_at((px, py), (r, g, b, alpha))
                else:
                    dc = self._darkenColor(portalColor, 0.9)
                    surface.set_at((px, py), (*dc, alpha))
        
        return surface
    
    def _createEndPortalBlock(self, isGateway: bool = False) -> pygame.Surface:
        """
        Create an isometric end portal/gateway block sprite.
        Uses the actual end_portal.png texture (grayscale starfield) with vertical scrolling animation.
        The grayscale values are used as intensity to create colorized stars with Tron-like trailing streaks.
        Animation scrolls vertically (upward) to match Minecraft's effect.
        """
        W = TILE_WIDTH
        H = TILE_HEIGHT + BLOCK_HEIGHT
        halfW = W // 2
        halfH = TILE_HEIGHT // 2
        
        surface = pygame.Surface((W, H), pygame.SRCALPHA)
        
        # Get scroll offset for animation - only vertical (Y-axis)
        scrollOffset = int(self.endPortalScrollOffset) if hasattr(self, 'endPortalScrollOffset') else 0
        
        # Use actual texture if available (256x256 grayscale starfield)
        texSize = 64  # Use larger sample for more detail
        if self.endPortalTexture:
            baseTex = pygame.transform.scale(self.endPortalTexture, (texSize, texSize))
        else:
            baseTex = None
        
        # Base colors for gateway (cyan/teal) vs portal (purple/magenta)
        if isGateway:
            baseColor = (20, 60, 80)      # Dark teal background
            starColor = (100, 200, 255)    # Bright cyan stars
            trailColor = (60, 160, 220)    # Cyan trail
        else:
            baseColor = (30, 10, 50)       # Dark purple background
            starColor = (180, 120, 255)    # Bright purple/magenta stars
            trailColor = (140, 80, 200)    # Purple trail
        
        # Trail length for Tron-like effect (in texture pixels)
        trailLength = 6
        
        # TOP FACE - main portal surface (full isometric diamond)
        for py in range(TILE_HEIGHT):
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
                relX = px - halfW
                relY = py - halfH
                
                # Inverse isometric projection
                u = (relX / halfW + relY / halfH) * 0.5 + 0.5 if halfW > 0 and halfH > 0 else 0.5
                v = (-relX / halfW + relY / halfH) * 0.5 + 0.5 if halfW > 0 and halfH > 0 else 0.5
                
                # Scroll only vertically (Y direction) - upward motion
                texX = int(u * (texSize - 1)) % texSize
                texY = (int(v * (texSize - 1)) + scrollOffset) % texSize
                texX = max(0, min(texSize - 1, texX))
                texY = max(0, min(texSize - 1, texY))
                
                if baseTex:
                    # Get grayscale value as intensity (0-255)
                    pixel = baseTex.get_at((texX, texY))
                    # Use first channel as intensity (grayscale image)
                    intensity = pixel[0] / 255.0
                    
                    # Check for trailing streak effect - sample pixels behind (below in scroll direction)
                    maxTrailIntensity = intensity
                    for trailOffset in range(1, trailLength + 1):
                        trailTexY = (texY + trailOffset) % texSize  # Look behind the scroll
                        trailPixel = baseTex.get_at((texX, trailTexY))
                        trailInt = trailPixel[0] / 255.0
                        # Fade the trail based on distance
                        fadedTrailInt = trailInt * (1.0 - trailOffset / (trailLength + 1))
                        if fadedTrailInt > maxTrailIntensity * 0.3:  # Only show trail if bright enough
                            maxTrailIntensity = max(maxTrailIntensity, fadedTrailInt * 0.7)
                    
                    # Use the combined intensity (star + trail)
                    combinedIntensity = min(1.0, max(intensity, maxTrailIntensity))
                    
                    # For bright stars, add extra glow
                    if intensity > 0.7:
                        r = int(baseColor[0] + (starColor[0] - baseColor[0]) * combinedIntensity)
                        g = int(baseColor[1] + (starColor[1] - baseColor[1]) * combinedIntensity)
                        b = int(baseColor[2] + (starColor[2] - baseColor[2]) * combinedIntensity)
                    elif combinedIntensity > intensity:
                        # This is a trail pixel - use trail color
                        r = int(baseColor[0] + (trailColor[0] - baseColor[0]) * combinedIntensity)
                        g = int(baseColor[1] + (trailColor[1] - baseColor[1]) * combinedIntensity)
                        b = int(baseColor[2] + (trailColor[2] - baseColor[2]) * combinedIntensity)
                    else:
                        # Normal star/background
                        r = int(baseColor[0] + (starColor[0] - baseColor[0]) * combinedIntensity)
                        g = int(baseColor[1] + (starColor[1] - baseColor[1]) * combinedIntensity)
                        b = int(baseColor[2] + (starColor[2] - baseColor[2]) * combinedIntensity)
                    
                    surface.set_at((px, py), (r, g, b, 240))
                else:
                    surface.set_at((px, py), (*baseColor, 240))
        
        # LEFT FACE - darker, also scrolls vertically with trails
        for px in range(halfW):
            topY = halfH + int((px / halfW) * halfH) if halfW > 0 else halfH
            bottomY = topY + BLOCK_HEIGHT
            
            for py in range(topY, min(bottomY, H)):
                u = px / halfW if halfW > 0 else 0
                v = (py - topY) / BLOCK_HEIGHT if BLOCK_HEIGHT > 0 else 0
                
                texX = int(u * (texSize - 1)) % texSize
                texY = (int(v * (texSize - 1)) + scrollOffset) % texSize
                texX = max(0, min(texSize - 1, texX))
                texY = max(0, min(texSize - 1, texY))
                
                if baseTex:
                    pixel = baseTex.get_at((texX, texY))
                    intensity = pixel[0] / 255.0
                    
                    # Trail effect for left face
                    maxTrailIntensity = intensity
                    for trailOffset in range(1, trailLength + 1):
                        trailTexY = (texY + trailOffset) % texSize
                        trailPixel = baseTex.get_at((texX, trailTexY))
                        trailInt = trailPixel[0] / 255.0
                        fadedTrailInt = trailInt * (1.0 - trailOffset / (trailLength + 1))
                        if fadedTrailInt > maxTrailIntensity * 0.3:
                            maxTrailIntensity = max(maxTrailIntensity, fadedTrailInt * 0.7)
                    
                    combinedIntensity = min(1.0, max(intensity, maxTrailIntensity)) * 0.5  # Darken for left face
                    r = int(baseColor[0] * 0.5 + (starColor[0] - baseColor[0]) * combinedIntensity * 0.5)
                    g = int(baseColor[1] * 0.5 + (starColor[1] - baseColor[1]) * combinedIntensity * 0.5)
                    b = int(baseColor[2] * 0.5 + (starColor[2] - baseColor[2]) * combinedIntensity * 0.5)
                    surface.set_at((px, py), (r, g, b, 240))
                else:
                    dark = tuple(int(c * 0.5) for c in baseColor)
                    surface.set_at((px, py), (*dark, 240))
        
        # RIGHT FACE - medium brightness, also scrolls vertically with trails
        for px in range(halfW, W):
            relX = px - halfW
            topY = TILE_HEIGHT - 1 - int((relX / halfW) * halfH) if halfW > 0 else halfH
            bottomY = topY + BLOCK_HEIGHT
            
            for py in range(max(0, topY), min(bottomY, H)):
                u = relX / halfW if halfW > 0 else 0
                v = (py - topY) / BLOCK_HEIGHT if BLOCK_HEIGHT > 0 else 0
                
                texX = int(u * (texSize - 1)) % texSize
                texY = (int(v * (texSize - 1)) + scrollOffset) % texSize
                texX = max(0, min(texSize - 1, texX))
                texY = max(0, min(texSize - 1, texY))
                
                if baseTex:
                    pixel = baseTex.get_at((texX, texY))
                    intensity = pixel[0] / 255.0
                    
                    # Trail effect for right face
                    maxTrailIntensity = intensity
                    for trailOffset in range(1, trailLength + 1):
                        trailTexY = (texY + trailOffset) % texSize
                        trailPixel = baseTex.get_at((texX, trailTexY))
                        trailInt = trailPixel[0] / 255.0
                        fadedTrailInt = trailInt * (1.0 - trailOffset / (trailLength + 1))
                        if fadedTrailInt > maxTrailIntensity * 0.3:
                            maxTrailIntensity = max(maxTrailIntensity, fadedTrailInt * 0.7)
                    
                    combinedIntensity = min(1.0, max(intensity, maxTrailIntensity)) * 0.65  # Medium brightness
                    r = int(baseColor[0] * 0.65 + (starColor[0] - baseColor[0]) * combinedIntensity * 0.65)
                    g = int(baseColor[1] * 0.65 + (starColor[1] - baseColor[1]) * combinedIntensity * 0.65)
                    b = int(baseColor[2] * 0.65 + (starColor[2] - baseColor[2]) * combinedIntensity * 0.65)
                    surface.set_at((px, py), (r, g, b, 240))
                else:
                    medium = tuple(int(c * 0.65) for c in baseColor)
                    surface.set_at((px, py), (*medium, 240))
        
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
    
    def _createMatrixBlock(self) -> pygame.Surface:
        """
        Create an isometric Matrix block sprite with falling green code effect.
        Uses a cleaner pixel-based rendering without per-character tracking.
        """
        import random
        
        W = TILE_WIDTH
        H = TILE_HEIGHT + BLOCK_HEIGHT
        halfW = W // 2
        halfH = TILE_HEIGHT // 2
        
        surface = pygame.Surface((W, H), pygame.SRCALPHA)
        
        # Get animation offset
        if not hasattr(self, 'matrixScrollOffset'):
            self.matrixScrollOffset = 0
        self.matrixScrollOffset = (self.matrixScrollOffset + 1) % 64
        
        # Use a seeded random for consistent patterns per-column
        # (real animation comes from scrollOffset change)
        
        # Black background
        bgColor = (5, 10, 5)  # Very dark green-black
        
        # TOP FACE - main portal surface (full isometric diamond)
        for py in range(TILE_HEIGHT):
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
                relX = px - halfW
                relY = py - halfH
                
                # Inverse isometric projection to get UV coords
                u = (relX / halfW + relY / halfH) * 0.5 + 0.5 if halfW > 0 and halfH > 0 else 0.5
                v = (-relX / halfW + relY / halfH) * 0.5 + 0.5 if halfW > 0 and halfH > 0 else 0.5
                
                # Map to virtual grid cell and get scroll position
                gridX = int(u * 32)
                gridY = int(v * 32)
                
                # Create pseudo-random value based on column (seeded by gridX)
                colSeed = (gridX * 7919 + 104729) % 65536
                colSpeed = 1 if (colSeed % 4) != 0 else 2
                colPhase = colSeed % 32
                
                # Calculate position in falling trail (scrolls down, display scrolls up)
                trailPos = (gridY + self.matrixScrollOffset * colSpeed + colPhase) % 32
                
                # Determine brightness based on position in trail
                if trailPos < 2:
                    # Head of trail - bright white-green
                    r, g, b = 180, 255, 180
                elif trailPos < 8:
                    # Body of trail - bright green fading
                    fade = 1.0 - (trailPos - 2) / 6.0
                    g = int(200 * fade + 50)
                    r, b = int(20 * fade), int(20 * fade)
                else:
                    # Background - very dark
                    r, g, b = bgColor
                
                surface.set_at((px, py), (r, g, b, 255))
        
        # LEFT FACE - darker, also with matrix effect
        for px in range(halfW):
            topY = halfH + int((px / halfW) * halfH) if halfW > 0 else halfH
            bottomY = topY + BLOCK_HEIGHT
            
            for py in range(topY, min(bottomY, H)):
                u = px / halfW if halfW > 0 else 0
                v = (py - topY) / BLOCK_HEIGHT if BLOCK_HEIGHT > 0 else 0
                
                gridX = int(u * 16)
                gridY = int(v * 24)
                
                colSeed = (gridX * 7919 + 104729) % 65536
                colSpeed = 1 if (colSeed % 4) != 0 else 2
                colPhase = colSeed % 24
                
                trailPos = (gridY + self.matrixScrollOffset * colSpeed + colPhase) % 24
                
                if trailPos < 2:
                    r, g, b = 80, 160, 80  # Darker head
                elif trailPos < 6:
                    fade = 1.0 - (trailPos - 2) / 4.0
                    g = int(120 * fade + 30)
                    r, b = int(10 * fade), int(10 * fade)
                else:
                    r, g, b = int(bgColor[0] * 0.5), int(bgColor[1] * 0.5), int(bgColor[2] * 0.5)
                
                surface.set_at((px, py), (r, g, b, 255))
        
        # RIGHT FACE - medium brightness, also with matrix effect
        for px in range(halfW, W):
            relX = px - halfW
            topY = TILE_HEIGHT - 1 - int((relX / halfW) * halfH) if halfW > 0 else halfH
            bottomY = topY + BLOCK_HEIGHT
            
            for py in range(max(0, topY), min(bottomY, H)):
                u = relX / halfW if halfW > 0 else 0
                v = (py - topY) / BLOCK_HEIGHT if BLOCK_HEIGHT > 0 else 0
                
                gridX = int(u * 16 + 16)
                gridY = int(v * 24)
                
                colSeed = (gridX * 7919 + 104729) % 65536
                colSpeed = 1 if (colSeed % 4) != 0 else 2
                colPhase = colSeed % 24
                
                trailPos = (gridY + self.matrixScrollOffset * colSpeed + colPhase) % 24
                
                if trailPos < 2:
                    r, g, b = 120, 200, 120  # Medium head
                elif trailPos < 6:
                    fade = 1.0 - (trailPos - 2) / 4.0
                    g = int(150 * fade + 40)
                    r, b = int(15 * fade), int(15 * fade)
                else:
                    r, g, b = int(bgColor[0] * 0.65), int(bgColor[1] * 0.65), int(bgColor[2] * 0.65)
                
                surface.set_at((px, py), (r, g, b, 255))
        
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
        """
        Create icon sprites for the inventory panel.
        
        For regular blocks: reuse the already-rendered blockSprites scaled down.
        This ensures icons match placed blocks exactly (same rendering logic).
        
        For special blocks (doors, stairs, slabs, etc.): use dedicated renderers
        since they have complex geometry that doesn't scale well.
        """
        for blockType, blockDef in BLOCK_DEFINITIONS.items():
            # Special blocks get dedicated icon rendering (they're problematic)
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
            else:
                # Regular blocks: reuse blockSprites scaled to icon size
                # This guarantees icons look identical to placed blocks
                if blockType in self.blockSprites:
                    blockSprite = self.blockSprites[blockType]
                    spriteW, spriteH = blockSprite.get_size()
                    # Scale to fit ICON_SIZE while maintaining aspect ratio
                    scale = ICON_SIZE / max(spriteW, spriteH)
                    newW = int(spriteW * scale)
                    newH = int(spriteH * scale)
                    # Use nearest-neighbor scaling to preserve pixel-perfect look
                    icon = pygame.transform.scale(blockSprite, (newW, newH))
                else:
                    # Fallback: create icon from scratch if blockSprite missing
                    icon = self._createIconBlock(blockType, blockDef, ICON_SIZE)
            self.iconSprites[blockType] = icon
    
    def _updateAnimatedIcon(self, blockType: BlockType):
        """Update icon sprite for animated blocks (water, lava, portals) to match current frame"""
        if blockType in self.blockSprites:
            blockSprite = self.blockSprites[blockType]
            spriteW, spriteH = blockSprite.get_size()
            # Scale to fit ICON_SIZE while maintaining aspect ratio
            scale = ICON_SIZE / max(spriteW, spriteH)
            newW = int(spriteW * scale)
            newH = int(spriteH * scale)
            # Use nearest-neighbor scaling to preserve pixel-perfect look
            self.iconSprites[blockType] = pygame.transform.scale(blockSprite, (newW, newH))
    
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
            topTex = pygame.transform.scale(topTex, (texSize, texSize))
        else:
            topTex = pygame.Surface((texSize, texSize))
            topTex.fill((100, 100, 100))
        
        if sideTex:
            sideTex = pygame.transform.scale(sideTex, (texSize, texSize))
        else:
            sideTex = topTex.copy()
        
        if frontTex:
            frontTex = pygame.transform.scale(frontTex, (texSize, texSize))
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
    
    def _loadSoundFiles(self, category: str, directory: str, pattern: str, 
                        maxVariants: int = SOUND_MAX_VARIANTS, 
                        volume: float = SOUND_VOLUME_DEFAULT) -> List[pygame.mixer.Sound]:
        """
        Generic helper to load sound files matching a pattern.
        
        Args:
            category: Name for logging (e.g., "grass", "chest")
            directory: Directory to search in
            pattern: Filename pattern with {i} placeholder (e.g., "break{i}.ogg")
            maxVariants: Maximum number to search for (1 to maxVariants-1)
            volume: Volume to set for loaded sounds
            
        Returns:
            List of loaded pygame Sound objects
        """
        sounds = []
        if not os.path.exists(directory):
            return sounds
            
        for i in range(1, maxVariants):
            soundPath = os.path.join(directory, pattern.format(i=i))
            if os.path.exists(soundPath):
                try:
                    sound = pygame.mixer.Sound(soundPath)
                    sound.set_volume(volume)
                    sounds.append(sound)
                except Exception as e:
                    print(f"Warning: Could not load {soundPath}: {e}")
        
        if sounds:
            print(f"    Loaded {len(sounds)} {category} sounds")
        return sounds
    
    def _loadSingleSound(self, path: str, volume: float = SOUND_VOLUME_DEFAULT) -> Optional[pygame.mixer.Sound]:
        """
        Load a single sound file.
        
        Args:
            path: Full path to the sound file
            volume: Volume to set
            
        Returns:
            Loaded Sound object or None if failed
        """
        if os.path.exists(path):
            try:
                sound = pygame.mixer.Sound(path)
                sound.set_volume(volume)
                return sound
            except Exception as e:
                print(f"Warning: Could not load {path}: {e}")
        return None
    
    def _loadSounds(self):
        """Load sounds from Sound Hub for each block material type"""
        digDir = os.path.join(SOUNDS_DIR, "dig")
        randomDir = os.path.join(SOUNDS_DIR, "random")
        liquidDir = os.path.join(SOUNDS_DIR, "liquid")
        blockDir = os.path.join(SOUNDS_DIR, "block")
        
        # Load dig sounds for basic material categories
        for category in ["grass", "gravel", "stone", "wood", "cloth", "sand"]:
            self.sounds[category] = self._loadSoundFiles(
                category, digDir, f"{category}{{i}}.ogg"
            )
        
        # Load additional sound variations (snow, coral, wet_grass)
        for category in ["snow", "coral", "wet_grass"]:
            self.sounds[category] = self._loadSoundFiles(
                category, digDir, f"{category}{{i}}.ogg"
            )
        
        # Glass break sounds (from random folder)
        self.sounds["glass"] = self._loadSoundFiles("glass", randomDir, "glass{i}.ogg", maxVariants=5)
        self.sounds["glass_place"] = self.sounds.get("stone", [])  # Glass placing uses stone sounds
        
        # Water and lava sounds
        self.sounds["water"] = []
        water = self._loadSingleSound(os.path.join(liquidDir, "water.ogg"), SOUND_VOLUME_AMBIENT)
        if water:
            self.sounds["water"].append(water)
            print(f"    Loaded water sound")
        for splashFile in ["splash.ogg", "splash2.ogg"]:
            splash = self._loadSingleSound(os.path.join(liquidDir, splashFile), SOUND_VOLUME_AMBIENT)
            if splash:
                self.sounds["water"].append(splash)
        
        self.sounds["lava"] = []
        lava = self._loadSingleSound(os.path.join(liquidDir, "lava.ogg"), SOUND_VOLUME_AMBIENT)
        if lava:
            self.sounds["lava"].append(lava)
            print(f"    Loaded lava sound")
        lavapop = self._loadSingleSound(os.path.join(liquidDir, "lavapop.ogg"), SOUND_VOLUME_AMBIENT)
        if lavapop:
            self.sounds["lava"].append(lavapop)
        
        # Load UI click sound
        self.clickSound = self._loadSingleSound(
            os.path.join(randomDir, "click.ogg"), SOUND_VOLUME_UI
        )
        if self.clickSound:
            print(f"    Loaded click sound")
        
        # Load block-specific sounds from block/ folder (break sounds)
        blockSoundCategories = [
            "nether_bricks", "netherrack", "copper", "bone_block", "spawner", "sculk_sensor",
            "nether_wood", "nylium", "basalt", "nether_ore", "ancient_debris", "netherite",
            "netherwart", "shroomlight", "soul_sand", "soul_soil", "honeyblock", "sponge",
            # Additional block sounds for variety
            "amethyst", "azalea", "azalea_leaves", "bamboo", "bamboo_wood", "beacon",
            "calcite", "candle", "chain", "cherry_leaves", "cherry_wood", "deepslate",
            "deepslate_bricks", "dripstone", "froglight", "fungus", "hanging_roots",
            "lantern", "mangrove_roots", "moss", "mud", "mud_bricks", "packed_mud",
            "pointed_dripstone", "powder_snow", "rooted_dirt", "roots", "scaffold",
            "sculk", "sculk_catalyst", "sculk_shrieker", "sculk_vein", "stem", "tuff",
            "tuff_bricks", "vine", "cobweb"
        ]
        for category in blockSoundCategories:
            categoryDir = os.path.join(blockDir, category)
            self.sounds[category] = self._loadSoundFiles(category, categoryDir, "break{i}.ogg")
            # Also try to load place sounds (some blocks have separate place sounds)
            placeSounds = self._loadSoundFiles(f"{category}_place", categoryDir, "place{i}.ogg")
            if placeSounds:
                self.sounds[f"{category}_place"] = placeSounds
        
        # Load enchanting table sounds
        enchantDir = os.path.join(blockDir, "enchantment_table")
        self.sounds["enchantment_table"] = self._loadSoundFiles(
            "enchantment_table", enchantDir, "enchant{i}.ogg", maxVariants=5, volume=SOUND_VOLUME_AMBIENT
        )
        
        # Load chest sounds (open + close variants)
        chestDir = os.path.join(blockDir, "chest")
        self.sounds["chest"] = []
        chestOpen = self._loadSingleSound(os.path.join(chestDir, "open.ogg"))
        if chestOpen:
            self.sounds["chest"].append(chestOpen)
        self.sounds["chest"].extend(self._loadSoundFiles("chest_close", chestDir, "close{i}.ogg", maxVariants=5))
        if self.sounds["chest"]:
            print(f"    Loaded {len(self.sounds['chest'])} chest sounds")
        
        # Load ender chest sounds
        enderChestDir = os.path.join(blockDir, "enderchest")
        self.sounds["enderchest"] = []
        for sndFile in ["open.ogg", "close.ogg"]:
            snd = self._loadSingleSound(os.path.join(enderChestDir, sndFile))
            if snd:
                self.sounds["enderchest"].append(snd)
        if self.sounds["enderchest"]:
            print(f"    Loaded {len(self.sounds['enderchest'])} enderchest sounds")
        
        # Load end portal sounds
        endPortalDir = os.path.join(blockDir, "end_portal")
        self.sounds["end_portal"] = []
        portal = self._loadSingleSound(os.path.join(endPortalDir, "endportal.ogg"), SOUND_VOLUME_UI)
        if portal:
            self.sounds["end_portal"].append(portal)
        self.sounds["end_portal"].extend(
            self._loadSoundFiles("end_portal_eye", endPortalDir, "eyeplace{i}.ogg", maxVariants=5, volume=SOUND_VOLUME_AMBIENT)
        )
        if self.sounds["end_portal"]:
            print(f"    Loaded {len(self.sounds['end_portal'])} end_portal sounds")
        
        # Load fire sounds
        fireDir = os.path.join(SOUNDS_DIR, "fire")
        self.sounds["fire"] = []
        for sndFile in ["fire.ogg", "ignite.ogg"]:
            snd = self._loadSingleSound(os.path.join(fireDir, sndFile), SOUND_VOLUME_AMBIENT)
            if snd:
                self.sounds["fire"].append(snd)
        if self.sounds["fire"]:
            print(f"    Loaded {len(self.sounds['fire'])} fire sounds")
        
        # Load sculk sounds (more variants)
        sculkDir = os.path.join(blockDir, "sculk")
        self.sounds["sculk"] = self._loadSoundFiles("sculk", sculkDir, "break{i}.ogg", maxVariants=15)
        
        # Load copper chest sounds (regular, weathered, oxidized)
        entitySoundDir = os.path.join(SOUNDS_DIR, "entity")
        copperChestDir = os.path.join(entitySoundDir, "copper_chest")
        for variant in ["", "_weathered", "_oxidized"]:
            key = f"copper_chest{variant}" if variant else "copper_chest"
            self.sounds[key] = []
            for i in range(1, 5):
                for sndType in ["open", "close"]:
                    snd = self._loadSingleSound(
                        os.path.join(copperChestDir, f"copper_chest{variant}_{sndType}{i}.ogg")
                    )
                    if snd:
                        self.sounds[key].append(snd)
            if self.sounds[key]:
                print(f"    Loaded {len(self.sounds[key])} {key} sounds")
        
        # Load door sounds
        self.doorOpenSound = self._loadSingleSound(
            os.path.join(randomDir, "door_open.ogg"), SOUND_VOLUME_DOOR
        )
        self.doorCloseSound = self._loadSingleSound(
            os.path.join(randomDir, "door_close.ogg"), SOUND_VOLUME_DOOR
        )
        if self.doorOpenSound:
            print(f"    Loaded door open sound")
        if self.doorCloseSound:
            print(f"    Loaded door close sound")
        
        # Load iron door sounds
        ironDoorDir = os.path.join(blockDir, "iron_door")
        self.ironDoorOpenSounds = self._loadSoundFiles(
            "iron_door_open", ironDoorDir, "open{i}.ogg", maxVariants=5, volume=SOUND_VOLUME_DOOR
        )
        self.ironDoorCloseSounds = self._loadSoundFiles(
            "iron_door_close", ironDoorDir, "close{i}.ogg", maxVariants=5, volume=SOUND_VOLUME_DOOR
        )
        
        # Load rain and thunder sounds from ambient/weather folder
        self.relaxingRainPath = None  # Path to the long rain track
        self.relaxingRainSound = None  # Pre-loaded rain Sound object (avoids stutter)
        self.thunderSounds = []
        weatherDir = os.path.join(SOUNDS_DIR, "ambient", "weather")
        if os.path.exists(weatherDir):
            # Load the single relaxing rain track (12 min mp3) - preload to avoid stutter
            relaxingPath = os.path.join(weatherDir, "relaxingrain.mp3")
            if os.path.exists(relaxingPath):
                self.relaxingRainPath = relaxingPath
                try:
                    self.relaxingRainSound = pygame.mixer.Sound(relaxingPath)
                    self.relaxingRainSound.set_volume(0.5)
                    print(f"    Pre-loaded relaxing rain track")
                except Exception as e:
                    print(f"    Could not pre-load rain track: {e}")
            # Load thunder sounds (thunder1.ogg through thunder3.ogg) - for lightning strikes
            for i in range(1, 4):
                thunderPath = os.path.join(weatherDir, f"thunder{i}.ogg")
                if os.path.exists(thunderPath):
                    try:
                        snd = pygame.mixer.Sound(thunderPath)
                        snd.set_volume(0.8)
                        self.thunderSounds.append(snd)
                    except pygame.error as e:
                        print(f"Warning: Could not load thunder sound {i}: {e}")
            # Load thunder ambient sounds (thunderambient.ogg through thunderambient3.ogg) - background rumbles
            for name in ["thunderambient.ogg", "thunderambient2.ogg", "thunderambient3.ogg"]:
                ambientPath = os.path.join(weatherDir, name)
                if os.path.exists(ambientPath):
                    try:
                        snd = pygame.mixer.Sound(ambientPath)
                        snd.set_volume(0.4)  # Background ambience
                        self.thunderAmbientSounds.append(snd)
                    except pygame.error as e:
                        print(f"Warning: Could not load thunder ambient {name}: {e}")
            if self.thunderSounds:
                print(f"    Loaded {len(self.thunderSounds)} thunder sounds")
            if self.thunderAmbientSounds:
                print(f"    Loaded {len(self.thunderAmbientSounds)} thunder ambient sounds")
        
        # Load rain texture from environment folder
        self.rainTexture = None
        rainTexPath = os.path.join(TEXTURES_DIR.replace("blocks", "environment"), "rain.png")
        if os.path.exists(rainTexPath):
            try:
                self.rainTexture = pygame.image.load(rainTexPath).convert_alpha()
                print(f"    Loaded rain texture")
            except Exception as e:
                print(f"Warning: Could not load rain texture: {e}")
        
        # Load ambient cave sounds for horror system
        self.caveSounds = []
        caveDir = os.path.join(SOUNDS_DIR, "ambient", "cave")
        if os.path.exists(caveDir):
            for i in range(1, 24):  # cave1.ogg through cave23.ogg (some are creepy!)
                cavePath = os.path.join(caveDir, f"cave{i}.ogg")
                if os.path.exists(cavePath):
                    try:
                        snd = pygame.mixer.Sound(cavePath)
                        snd.set_volume(0.3)  # Subtle volume for ambience
                        self.caveSounds.append(snd)
                    except pygame.error:
                        pass  # Optional sound file
            if self.caveSounds:
                print(f"    Loaded {len(self.caveSounds)} cave ambient sounds")
        
        # Load nether ambient sounds for horror in Nether dimension
        self.netherAmbientSounds = []
        netherAmbientDir = os.path.join(SOUNDS_DIR, "ambient", "nether")
        if os.path.exists(netherAmbientDir):
            for f in os.listdir(netherAmbientDir):
                if f.endswith('.ogg'):
                    netherPath = os.path.join(netherAmbientDir, f)
                    try:
                        snd = pygame.mixer.Sound(netherPath)
                        snd.set_volume(0.25)
                        self.netherAmbientSounds.append(snd)
                    except pygame.error:
                        pass  # Optional sound file
            if self.netherAmbientSounds:
                print(f"    Loaded {len(self.netherAmbientSounds)} nether ambient sounds")
        
        # Load phantom footstep sounds for horror system
        self.phantomFootsteps = []
        stepDir = os.path.join(SOUNDS_DIR, "step")
        if os.path.exists(stepDir):
            for stepType in ["stone", "wood", "grass"]:
                for i in range(1, 7):
                    stepPath = os.path.join(stepDir, f"{stepType}{i}.ogg")
                    if os.path.exists(stepPath):
                        try:
                            snd = pygame.mixer.Sound(stepPath)
                            snd.set_volume(0.08)  # Very quiet - phantom footsteps
                            self.phantomFootsteps.append(snd)
                        except pygame.error:
                            pass  # Optional sound file
            if self.phantomFootsteps:
                print(f"    Loaded {len(self.phantomFootsteps)} phantom footstep sounds")
        
        # Load distant knock sound for horror
        self.knockSound = None
        knockPath = os.path.join(SOUNDS_DIR, "random", "door_close.ogg")
        if os.path.exists(knockPath):
            try:
                self.knockSound = pygame.mixer.Sound(knockPath)
                self.knockSound.set_volume(0.05)  # Very quiet
                print(f"    Loaded distant knock sound")
            except pygame.error:
                pass  # Optional sound file
        
        # Load breathing sound for horror
        self.breathSound = None
        breathPath = os.path.join(SOUNDS_DIR, "random", "breath.ogg")
        if os.path.exists(breathPath):
            try:
                self.breathSound = pygame.mixer.Sound(breathPath)
                self.breathSound.set_volume(0.03)  # Very quiet
                print(f"    Loaded breathing sound")
            except pygame.error:
                pass  # Optional sound file
        
        # Load ghast moan sounds for Nether horror
        self.ghastMoans = []
        ghastDir = os.path.join(SOUNDS_DIR, "mob", "ghast")
        if os.path.exists(ghastDir):
            for i in range(1, 8):
                moanPath = os.path.join(ghastDir, f"moan{i}.ogg")
                if os.path.exists(moanPath):
                    try:
                        snd = pygame.mixer.Sound(moanPath)
                        snd.set_volume(0.04)  # Very quiet distant ghast
                        self.ghastMoans.append(snd)
                    except pygame.error:
                        pass  # Optional sound file
            if self.ghastMoans:
                print(f"    Loaded {len(self.ghastMoans)} ghast moan sounds")
        
        # Load enderman sounds for End horror
        self.endermanSounds = []
        endermanDir = os.path.join(SOUNDS_DIR, "mob", "endermen")
        if os.path.exists(endermanDir):
            for f in os.listdir(endermanDir):
                if f.startswith(("idle", "stare")) and f.endswith('.ogg'):
                    soundPath = os.path.join(endermanDir, f)
                    try:
                        snd = pygame.mixer.Sound(soundPath)
                        snd.set_volume(0.03)  # Very quiet
                        self.endermanSounds.append(snd)
                    except pygame.error:
                        pass  # Optional sound file
            if self.endermanSounds:
                print(f"    Loaded {len(self.endermanSounds)} enderman sounds")
    
    def _loadUITextures(self):
        """Load UI textures for Minecraft-style buttons and panels"""
        widgetDir = os.path.join(GUI_DIR, "sprites", "widget")
        
        # Load button textures
        buttonPath = os.path.join(widgetDir, "button.png")
        buttonHoverPath = os.path.join(widgetDir, "button_highlighted.png")
        buttonDisabledPath = os.path.join(widgetDir, "button_disabled.png")
        slotPath = os.path.join(widgetDir, "slot_frame.png")
        
        # Load checkbox textures for tutorial
        checkboxPath = os.path.join(widgetDir, "checkbox.png")
        checkboxSelectedPath = os.path.join(widgetDir, "checkbox_selected.png")
        
        if os.path.exists(buttonPath):
            self.buttonNormal = pygame.image.load(buttonPath).convert_alpha()
        if os.path.exists(buttonHoverPath):
            self.buttonHover = pygame.image.load(buttonHoverPath).convert_alpha()
        if os.path.exists(buttonDisabledPath):
            self.buttonDisabled = pygame.image.load(buttonDisabledPath).convert_alpha()
        if os.path.exists(slotPath):
            self.slotFrame = pygame.image.load(slotPath).convert_alpha()
        
        # Load checkbox textures
        if os.path.exists(checkboxPath):
            self.checkboxTexture = pygame.image.load(checkboxPath).convert_alpha()
        else:
            self.checkboxTexture = None
        if os.path.exists(checkboxSelectedPath):
            self.checkboxSelectedTexture = pygame.image.load(checkboxSelectedPath).convert_alpha()
        else:
            self.checkboxSelectedTexture = None
    
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
                   hovered: bool = False, selected: bool = False,
                   bgTexture: str = None, bgTint: Tuple[int, int, int] = None):
        """Draw a Minecraft-style button with optional block texture background and tint"""
        # Choose texture based on state
        if selected:
            texture = self.buttonHover if self.buttonHover else self.buttonNormal
        elif hovered:
            texture = self.buttonHover if self.buttonHover else self.buttonNormal
        else:
            texture = self.buttonNormal
        
        if bgTexture and bgTexture in self.textures:
            # Use block texture as repeating/stretched background
            blockTex = self.textures[bgTexture]
            # Apply tint if provided (for grayscale textures like grass_block_top)
            if bgTint:
                blockTex = self._tintTexture(blockTex, bgTint)
            bgSurf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            
            # Tile the texture to fill the button
            texW, texH = blockTex.get_size()
            for ty in range(0, rect.height, texH):
                for tx in range(0, rect.width, texW):
                    bgSurf.blit(blockTex, (tx, ty))
            
            # Darken slightly for better text visibility
            darkOverlay = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            darkOverlay.fill((0, 0, 0, 60))
            bgSurf.blit(darkOverlay, (0, 0))
            
            # Brighten on hover
            if hovered or selected:
                brightOverlay = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
                brightOverlay.fill((255, 255, 255, 40))
                bgSurf.blit(brightOverlay, (0, 0))
            
            screen.blit(bgSurf, rect.topleft)
            
            # Draw border
            borderColor = (255, 200, 50) if selected else ((180, 180, 180) if hovered else (80, 80, 80))
            pygame.draw.rect(screen, borderColor, rect, 2)
        elif texture:
            # Scale texture to button size using 9-slice or simple scale
            scaledBtn = pygame.transform.scale(texture, (rect.width, rect.height))
            screen.blit(scaledBtn, rect.topleft)
        else:
            # Fallback to simple rectangle
            baseColor = (100, 100, 100) if hovered else (80, 80, 80)
            borderColor = (60, 60, 60)
            pygame.draw.rect(screen, baseColor, rect)
            pygame.draw.rect(screen, borderColor, rect, 2)
        
        # Draw text with shadow
        shadowSurf = font.render(text, True, (30, 30, 30))
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

    def playSound(self, soundCategory: str, worldPos: Tuple[int, int, int] = None, effectsVolume: float = 1.0):
        """
        Play a random sound from the specified category with 3D positional audio.
        
        Features:
        - Distance-based volume falloff
        - Stereo panning based on horizontal screen position
        - Sound cooldown to prevent spam
        - Per-category concurrent sound limit
        """
        if soundCategory in self.sounds and self.sounds[soundCategory]:
            # Check cooldown to prevent sound spam
            currentTime = pygame.time.get_ticks()
            lastPlayed = self.soundLastPlayed.get(soundCategory, 0)
            if currentTime - lastPlayed < self.soundCooldown:
                return  # Too soon, skip this sound
            
            # Check concurrent sound limit for this category
            activeCount = self.soundActiveChannels.get(soundCategory, 0)
            if activeCount >= self.maxSoundsPerCategory:
                return  # Too many of this sound playing
            
            # Pick a random variant for natural variation
            sound = random.choice(self.sounds[soundCategory])
            
            # Calculate volume and panning based on position if provided
            volume = effectsVolume
            leftVol = volume
            rightVol = volume
            
            if worldPos is not None and hasattr(self, 'renderer'):
                # Get screen position of sound source
                screenX, screenY = self.renderer.worldToScreen(*worldPos)
                # Get center of screen (excluding panel)
                centerX = (WINDOW_WIDTH - PANEL_WIDTH) // 2
                centerY = WINDOW_HEIGHT // 2
                
                # Calculate distance for volume falloff
                dist = ((screenX - centerX) ** 2 + (screenY - centerY) ** 2) ** 0.5
                # Falloff: full volume within 200px, then linear falloff
                maxDist = 600
                if dist > 200:
                    falloff = max(0.2, 1.0 - (dist - 200) / (maxDist - 200))
                    volume *= falloff
                
                # Calculate stereo panning based on horizontal position
                # Pan ranges from -1 (full left) to +1 (full right)
                screenWidth = WINDOW_WIDTH - PANEL_WIDTH
                pan = (screenX - centerX) / (screenWidth / 2) if screenWidth > 0 else 0
                pan = max(-1.0, min(1.0, pan))  # Clamp to [-1, 1]
                
                # Convert pan to left/right volumes
                # At pan=0, both are equal. At pan=-1, left is full, right reduced. Vice versa.
                leftVol = volume * min(1.0, 1.0 - pan * 0.7)  # 0.7 for subtle panning
                rightVol = volume * min(1.0, 1.0 + pan * 0.7)
            
            # Use a channel for stereo panning control
            channel = pygame.mixer.find_channel()
            if channel:
                channel.set_volume(leftVol, rightVol)
                channel.play(sound)
                # Track cooldown and active channels
                self.soundLastPlayed[soundCategory] = currentTime
                self.soundActiveChannels[soundCategory] = activeCount + 1
                # Schedule decrement of active count when sound finishes
                # (We'll use a simple approach: decrement after estimated duration)
            else:
                # Fallback to simple playback if no channel available
                sound.set_volume(volume)
                sound.play()
                self.soundLastPlayed[soundCategory] = currentTime
    
    def playPlaceSound(self, worldPos: Tuple[int, int, int] = None):
        """Play a generic block placement sound (stone) - used for operations without specific block type"""
        self.playSound("stone", worldPos, 1.0)
    
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
    
    def playBlockSound(self, blockType: BlockType, isPlace: bool = True, worldPos: Tuple[int, int, int] = None, effectsVolume: float = 1.0):
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
            
            # Special handling for END_PORTAL - play the portal completion sound
            if blockType == BlockType.END_PORTAL and isPlace:
                # Play the endportal.ogg sound specifically (first sound in end_portal category)
                if "end_portal" in self.sounds and self.sounds["end_portal"]:
                    self.sounds["end_portal"][0].play()  # endportal.ogg is loaded first
                    return
            
            self.playSound(category, worldPos, effectsVolume)
    
    def getBlockSprite(self, blockType: BlockType) -> Optional[pygame.Surface]:
        """Get the isometric sprite for a block type"""
        return self.blockSprites.get(blockType)
    
    def getIconSprite(self, blockType: BlockType) -> Optional[pygame.Surface]:
        """Get the icon sprite for a block type"""
        return self.iconSprites.get(blockType)
    
    def clearZoomCache(self):
        """Clear cached sprites for zoom level change - sprites will be regenerated on next draw"""
        # Currently sprites are pre-generated at fixed size
        # For zoom, we scale them on-the-fly in the render pass instead of regenerating
        # This method is a placeholder for future optimization
        pass


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
            else:
                # Solid block removed - check if there's liquid above that should fall
                self._queueLiquidAbove(x, y, z)
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
    
    def _queueLiquidAbove(self, x: int, y: int, z: int):
        """Queue liquid blocks above and adjacent to this position for update (for when solid block is removed)"""
        # Check block directly above
        if z + 1 < self.height:
            blockAbove = self.getBlock(x, y, z + 1)
            if blockAbove == BlockType.WATER:
                if (x, y, z + 1) not in self.waterUpdateQueue:
                    self.waterUpdateQueue.insert(0, (x, y, z + 1))  # Priority - falling liquid
            elif blockAbove == BlockType.LAVA:
                if (x, y, z + 1) not in self.lavaUpdateQueue:
                    self.lavaUpdateQueue.insert(0, (x, y, z + 1))  # Priority - falling liquid
        
        # Also check horizontal neighbors at same level (they might now have a path to this hole)
        for nx, ny in [(x+1, y), (x-1, y), (x, y+1), (x, y-1)]:
            if self.isInBounds(nx, ny, z):
                block = self.getBlock(nx, ny, z)
                if block == BlockType.WATER:
                    if (nx, ny, z) not in self.waterUpdateQueue:
                        self.waterUpdateQueue.append((nx, ny, z))
                elif block == BlockType.LAVA:
                    if (nx, ny, z) not in self.lavaUpdateQueue:
                        self.lavaUpdateQueue.append((nx, ny, z))
    
    def updateLiquids(self, liquidType: BlockType = None, maxUpdates: int = 8) -> List[Tuple[int, int, int, BlockType, int]]:
        """
        Process liquid flow updates for a specific type (water or lava).
        Minecraft-style flow: Always flows down first, then spreads horizontally.
        Uses pathfinding to prefer directions that lead to nearby drops.
        Uses chunk-based processing to limit updates to active regions.
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
        
        # Chunk-based optimization: group updates by 4x4 chunks and process one chunk at a time
        CHUNK_SIZE = 4
        chunkUpdates = {}  # (chunk_x, chunk_y) -> list of positions
        
        # Categorize all queued positions by chunk
        for pos in queue:
            x, y, z = pos
            chunkKey = (x // CHUNK_SIZE, y // CHUNK_SIZE)
            if chunkKey not in chunkUpdates:
                chunkUpdates[chunkKey] = []
            chunkUpdates[chunkKey].append(pos)
        
        # Process updates from the chunk with most pending updates first (hotspot optimization)
        # But limit total updates per tick
        updatesThisTick = 0
        maxUpdatesPerChunk = max(2, maxUpdates // max(1, len(chunkUpdates)))  # Distribute across chunks
        
        # Sort chunks by number of pending updates (descending) to prioritize active areas
        sortedChunks = sorted(chunkUpdates.items(), key=lambda x: len(x[1]), reverse=True)
        
        for chunkKey, chunkPositions in sortedChunks:
            if updatesThisTick >= maxUpdates:
                break
            
            chunkProcessed = 0
            for pos in chunkPositions:
                if chunkProcessed >= maxUpdatesPerChunk or updatesThisTick >= maxUpdates:
                    break
                    
                if pos in processed:
                    # Remove from main queue
                    if pos in queue:
                        queue.remove(pos)
                    continue
                    
                processed.add(pos)
                if pos in queue:
                    queue.remove(pos)
                
                x, y, z = pos
                block = self.getBlock(x, y, z)
                level = self.getLiquidLevel(x, y, z)
                
                if block != liquidType or level <= 0:
                    chunkProcessed += 1
                    updatesThisTick += 1
                    continue
                
                # PRIORITY 1: Always try to flow straight down first
                if z > 0 and self.getBlock(x, y, z-1) == BlockType.AIR:
                    self.blocks[(x, y, z-1)] = block
                    self.liquidLevels[(x, y, z-1)] = 8  # Falling liquid is full strength
                    changes.append((x, y, z-1, block, 8))
                    queue.append((x, y, z-1))
                    # Don't spread horizontally if we flowed down - continue to next pos
                    chunkProcessed += 1
                    updatesThisTick += 1
                    continue
                
                # PRIORITY 2: Horizontal spread with pathfinding to holes
                if level > 1:
                    newLevel = level - 1
                    searchRadius = 5 if block == BlockType.WATER else 3
                    
                    # Find which directions lead to holes (drops)
                    holeDirections = self._findHoleDirections(x, y, z, block, searchRadius)
                    
                    # Determine flow directions
                    allDirections = [(1, 0), (-1, 0), (0, 1), (0, -1)]
                    
                    # If we found holes, ONLY flow toward them
                    # If no holes within range, flow in all directions
                    if holeDirections:
                        flowDirections = holeDirections
                    else:
                        flowDirections = allDirections
                    
                    for dx, dy in flowDirections:
                        nx, ny, nz = x + dx, y + dy, z
                        
                        if not self.isInBounds(nx, ny, nz):
                            continue
                        
                        neighborBlock = self.getBlock(nx, ny, nz)
                        neighborLevel = self.getLiquidLevel(nx, ny, nz)
                        
                        if neighborBlock == BlockType.AIR:
                            self.blocks[(nx, ny, nz)] = block
                            self.liquidLevels[(nx, ny, nz)] = newLevel
                            changes.append((nx, ny, nz, block, newLevel))
                            if newLevel > 1:
                                queue.append((nx, ny, nz))
                            # If this cell has air below, add to front for priority
                            if nz > 0 and self.getBlock(nx, ny, nz - 1) == BlockType.AIR:
                                queue.insert(0, (nx, ny, nz))
                        elif neighborBlock == block and neighborLevel < newLevel:
                            self.liquidLevels[(nx, ny, nz)] = newLevel
                            changes.append((nx, ny, nz, block, newLevel))
                            queue.append((nx, ny, nz))
                
                chunkProcessed += 1
                updatesThisTick += 1
        
        return changes
    
    def _findHoleDirections(self, startX: int, startY: int, z: int, liquidType: BlockType, maxRange: int) -> List[Tuple[int, int]]:
        """
        Use BFS to find which initial directions (dx, dy) lead to holes within range.
        A "hole" is a position where the block below is AIR.
        Returns list of (dx, dy) tuples for directions that reach holes,
        prioritized by distance (closest holes first).
        """
        from collections import deque
        
        # Track holes found from each initial direction: direction -> min distance
        directionHoles = {}
        
        visited = {(startX, startY)}
        # Queue: (x, y, initial_dx, initial_dy, distance)
        bfsQueue = deque()
        
        # Initialize BFS with the 4 cardinal neighbors
        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            nx, ny = startX + dx, startY + dy
            if not self.isInBounds(nx, ny, z):
                continue
            
            neighborBlock = self.getBlock(nx, ny, z)
            # Can we flow to this cell?
            if neighborBlock != BlockType.AIR and neighborBlock != liquidType:
                continue
            
            visited.add((nx, ny))
            
            # Check if this immediate neighbor has a hole below
            if z > 0 and self.getBlock(nx, ny, z - 1) == BlockType.AIR:
                directionHoles[(dx, dy)] = 1  # Distance 1
            
            bfsQueue.append((nx, ny, dx, dy, 1))
        
        # Continue BFS to find holes further away
        while bfsQueue:
            cx, cy, initDx, initDy, dist = bfsQueue.popleft()
            
            # Stop searching beyond max range
            if dist >= maxRange:
                continue
            
            # Explore all 4 directions from current position
            for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                nx, ny = cx + dx, cy + dy
                
                if (nx, ny) in visited:
                    continue
                
                if not self.isInBounds(nx, ny, z):
                    continue
                
                neighborBlock = self.getBlock(nx, ny, z)
                if neighborBlock != BlockType.AIR and neighborBlock != liquidType:
                    continue
                
                visited.add((nx, ny))
                newDist = dist + 1
                
                # Check if this position has a hole below
                if z > 0 and self.getBlock(nx, ny, z - 1) == BlockType.AIR:
                    # Record if this is closest hole for this initial direction
                    if (initDx, initDy) not in directionHoles:
                        directionHoles[(initDx, initDy)] = newDist
                
                # Continue searching
                bfsQueue.append((nx, ny, initDx, initDy, newDist))
        
        # Return directions sorted by closest hole distance
        if not directionHoles:
            return []
        
        # Find minimum distance and return all directions within +2 of that
        minDist = min(directionHoles.values())
        goodDirections = [(d, dist) for d, dist in directionHoles.items() if dist <= minDist + 2]
        goodDirections.sort(key=lambda x: x[1])  # Sort by distance
        
        return [d for d, _ in goodDirections]
    
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
    
    def clearLiquids(self) -> int:
        """Clear all water and lava blocks from the world. Returns count of removed blocks."""
        removed = 0
        toRemove = []
        for pos, blockType in self.blocks.items():
            if blockType == BlockType.WATER or blockType == BlockType.LAVA:
                toRemove.append(pos)
        
        for pos in toRemove:
            del self.blocks[pos]
            if pos in self.liquidLevels:
                del self.liquidLevels[pos]
            removed += 1
        
        # Clear update queues
        self.waterUpdateQueue.clear()
        self.lavaUpdateQueue.clear()
        
        return removed
    
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
    
    # ============================================================================
    # LIGHTING SYSTEM (Experimental)
    # ============================================================================
    
    def calculateLighting(self) -> Dict[Tuple[int, int, int], Tuple[int, Tuple[int, int, int]]]:
        """
        Calculate light levels and colors for all positions in the world.
        Uses flood-fill algorithm like Minecraft's block light.
        Returns dict of (x, y, z) -> (light level (0-15), light color RGB).
        Light spreads equally in all 6 directions (±X, ±Y, ±Z).
        """
        # lightMap stores (level, color) tuples
        lightMap = {}
        
        # First, collect all light sources
        lightSources = []
        for (x, y, z), blockType in self.blocks.items():
            blockDef = BLOCK_DEFINITIONS.get(blockType)
            if blockDef and blockDef.lightLevel > 0:
                lightColor = getattr(blockDef, 'lightColor', (255, 200, 150))
                lightSources.append((x, y, z, blockDef.lightLevel, lightColor))
                lightMap[(x, y, z)] = (blockDef.lightLevel, lightColor)
        
        if not lightSources:
            return lightMap
        
        # Flood fill light from each source using BFS
        from collections import deque
        
        # Track the highest light level seen at each position
        visited = {}  # position -> highest light level processed
        
        # Queue format: (x, y, z, level, color)
        queue = deque()
        
        # Initialize: add all light source positions to visited and queue their neighbors
        for x, y, z, level, color in lightSources:
            visited[(x, y, z)] = level
            # Queue all 6 neighbors equally
            if level > 1:
                for dx, dy, dz in [(1,0,0), (-1,0,0), (0,1,0), (0,-1,0), (0,0,1), (0,0,-1)]:
                    nx, ny, nz = x + dx, y + dy, z + dz
                    if self.isInBounds(nx, ny, nz):
                        queue.append((nx, ny, nz, level - 1, color))
        
        # Process light propagation
        while queue:
            x, y, z, level, color = queue.popleft()
            
            if level <= 0:
                continue
            
            # Skip if we've already processed this position with equal or higher light
            if (x, y, z) in visited and visited[(x, y, z)] >= level:
                continue
            
            # Check if position is blocked by a solid block
            block = self.getBlock(x, y, z)
            if block != BlockType.AIR:
                blockDef = BLOCK_DEFINITIONS.get(block)
                # Only transparent blocks and liquids allow light through
                if blockDef and not blockDef.transparent and not blockDef.isLiquid:
                    continue
            
            # Update visited
            visited[(x, y, z)] = level
            
            # Update lightMap - blend colors if needed
            if (x, y, z) in lightMap:
                oldLevel, oldColor = lightMap[(x, y, z)]
                if level > oldLevel:
                    lightMap[(x, y, z)] = (level, color)
                elif level == oldLevel:
                    # Blend colors for equal light levels
                    blendedColor = (
                        (oldColor[0] + color[0]) // 2,
                        (oldColor[1] + color[1]) // 2,
                        (oldColor[2] + color[2]) // 2
                    )
                    lightMap[(x, y, z)] = (level, blendedColor)
            else:
                lightMap[(x, y, z)] = (level, color)
            
            # Propagate to all 6 neighbors equally (light decreases by 1 per block)
            if level > 1:
                newLevel = level - 1
                for dx, dy, dz in [(1,0,0), (-1,0,0), (0,1,0), (0,-1,0), (0,0,1), (0,0,-1)]:
                    nx, ny, nz = x + dx, y + dy, z + dz
                    if self.isInBounds(nx, ny, nz):
                        # Only queue if we might improve the light level
                        if (nx, ny, nz) not in visited or visited[(nx, ny, nz)] < newLevel:
                            queue.append((nx, ny, nz, newLevel, color))
        
        return lightMap
    
    def calculateAmbientOcclusion(self, x: int, y: int, z: int) -> Tuple[float, float, float]:
        """
        Calculate ambient occlusion factors for a block's 3 visible faces.
        Returns (topAO, leftAO, rightAO) where each is 0.0 (dark) to 1.0 (bright).
        """
        topAO = 1.0
        leftAO = 1.0
        rightAO = 1.0
        
        # Check blocks around for AO on top face
        # Top face is darkened by blocks above and diagonally above
        aboveBlocks = 0
        for dx, dy in [(1,0), (-1,0), (0,1), (0,-1), (1,1), (-1,1), (1,-1), (-1,-1)]:
            if self.getBlock(x + dx, y + dy, z + 1) != BlockType.AIR:
                aboveBlocks += 1
        topAO = max(0.5, 1.0 - aboveBlocks * 0.06)
        
        # Left face (facing -X in isometric view) - check blocks to left and diagonally
        leftBlocks = 0
        for dy, dz in [(1,0), (-1,0), (0,1), (0,-1), (1,1), (-1,1), (1,-1), (-1,-1)]:
            if self.getBlock(x - 1, y + dy, z + dz) != BlockType.AIR:
                leftBlocks += 1
        leftAO = max(0.4, 1.0 - leftBlocks * 0.075)
        
        # Right face (facing +Y in isometric view) - check blocks to right and diagonally
        rightBlocks = 0
        for dx, dz in [(1,0), (-1,0), (0,1), (0,-1), (1,1), (-1,1), (1,-1), (-1,-1)]:
            if self.getBlock(x + dx, y + 1, z + dz) != BlockType.AIR:
                rightBlocks += 1
        rightAO = max(0.4, 1.0 - rightBlocks * 0.075)
        
        return (topAO, leftAO, rightAO)
    
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
        # Cached zoom-scaled tile dimensions (updated in setZoom)
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


# ============================================================================
# MAIN GAME CLASS
# ============================================================================

class BlocFantome:
    """
    Main application class for Bloc Fantome.
    
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
        self.hoveredFace: Optional[str] = None  # 'top', 'left', 'right', or None for ground placement
        self.panelHovered = False
        
        # Brush size (1x1, 2x2, 3x3)
        self.brushSize = 1  # 1, 2, or 3
        self.brushSizes = [1, 2, 3]
        
        # Inventory scroll state
        self.inventoryScroll = 0
        self.maxScroll = 0
        
        # Hotkeys expand state
        self.hotkeysExpanded = False
        self.hotkeysExpandBtnRect = None
        
        # Font
        self.font = pygame.font.Font(None, 26)  # Slightly larger for better readability
        self.smallFont = pygame.font.Font(None, 20)  # Slightly larger for better readability
        
        # Panning state
        self.panning = False
        self.panStartX = 0
        self.panStartY = 0
        self.panOffsetX = 0
        self.panOffsetY = 0
        
        # Structure placement mode
        self.structurePlacementMode = False
        self.selectedStructure: Optional[str] = None
        
        # Structure preview thumbnails (pre-rendered at startup)
        self.structurePreviews: Dict[str, pygame.Surface] = {}
        self.hoveredStructure: Optional[str] = None  # For tooltip display
        self.structureThumbnailBg: Optional[pygame.Surface] = None  # Cached cobblestone bg
        
        # Liquid flow timing and optimization
        self.waterFlowDelay = WATER_FLOW_DELAY
        self.lavaFlowDelay = LAVA_FLOW_DELAY
        self.lastWaterFlowTime = 0
        self.lastLavaFlowTime = 0
        self.liquidFlowEnabled = True  # Toggle liquid simulation
        self.liquidUpdatesPerTick = 8  # Increased from 3 for faster flow
        
        # Rain system state
        self.rainEnabled = False
        self.rainDrops: List[Dict] = []  # {x, y, speed, length, angle}
        self.rainSplashes: List[Dict] = []  # {x, y, life, size}
        self.rainTimer = 0
        self.thunderTimer = 0
        self.nextThunderTime = 0
        self.skyDarkness = 0  # 0-150 for fade effect
        self.splashSpawnTimer = 0
        self.lightningFlash = 0  # Flash brightness (fades out)
        self.lightningBolt: List[Tuple[int, int]] = []  # List of (x, y) points for bolt
        self.lightningBoltTimer = 0  # How long bolt is visible
        self.rainIntensity = 1.0  # 0.5 to 1.5 multiplier
        self.rainIntensityTimer = 0
        self.rainIntensityTarget = 1.0
        # Multiple rain sound channels for layered ambient effect (Minecraft-style)
        self.rainSoundChannels: List[Dict] = []  # {channel, sound, timer, nextSwitch, volume, targetVolume}
        
        # Horror rain state (black rain)
        self.horrorRainDrops: List[Dict] = []
        self.horrorRainSplashParticles: List[Dict] = []  # 3D splash particles
        self.horrorRainSplashes: List[Dict] = []  # 2D droplet effects like normal rain
        self.horrorLightningBolts: List[List[Tuple[int, int]]] = []  # Multiple red bolts
        self.horrorLightningTimer = 0
        self.horrorLightningFlash = 0
        self.nextHorrorLightningTime = 0
        
        # Subtle whispers during rain (horror feature)
        self.rainWhisperChannel = None
        self.rainWhisperTimer = 0
        self.nextRainWhisperTime = 0
        self.rainWhisperSound = None
        
        # Sun/Moon cycle system
        self.celestialEnabled = False
        self.celestialAngle = 0.0  # 0-360 degrees for full sun rotation, then 360-720 for moon
        self.celestialSpeed = 0.5  # Degrees per frame (adjustable)
        self.celestialSize = 96  # Size of sun/moon textures
        self.dayBrightness = 1.0  # 0.0 (night) to 1.0 (day)
        self.sunTexture = None
        self.moonTexture = None
        self.moonPhase = 0  # 0-7 for 8 moon phases
        
        # Snow system state
        self.snowEnabled = False
        self.snowFlakes: List[Dict] = []  # {x, y, speed, size, drift}
        self.snowSkyDarkness = 0  # Separate from rain
        self.snowLayers: Dict[Tuple[int, int, int], int] = {}  # {(x, y, z): height} thin snow layers
        self.snowAccumulateTimer = 0
        
        # Thunder ambient background system (separate from lightning strikes)
        self.thunderAmbientChannel = None
        self.thunderAmbientTimer = 0
        self.nextThunderAmbientTime = 0
        
        # Stars system (shown at night)
        self.stars: List[Dict] = []  # {x, y, brightness, twinkleSpeed, twinklePhase}
        self._generateStars()
        
        # Clouds system
        self.cloudsEnabled = False
        self.clouds: List[Dict] = []  # {x, y, speed, scale, alpha}
        self.cloudTexture = None
        
        # Block breaking particles
        self.blockParticles: List[Dict] = []  # {x, y, vx, vy, color, life, maxLife}
        
        # Block highlighting (hovered block outline)
        self.highlightedBlock: Optional[Tuple[int, int, int]] = None
        
        # Ghost block preview (semi-transparent preview of block to be placed)
        self.showGhostPreview = True  # Can be toggled
        self.ghostPreviewAlpha = 100  # Transparency level
        
        # Volume controls (0.0 to 1.0)
        self.musicVolume = 0.3
        self.ambientVolume = 0.5
        self.effectsVolume = 0.7
        
        # Mute toggles
        self.musicMuted = False
        self.ambientMuted = False
        self.effectsMuted = False
        
        # Slider dragging state
        self.draggingSlider = None  # "music", "ambient", "effects", or None
        
        # Keyboard shortcuts panel
        self.showShortcutsPanel = False
        
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
        
        # Tutorial system
        self.tutorialScreen = TutorialScreen(WINDOW_WIDTH, WINDOW_HEIGHT)
        
        # Experimental lighting system
        self.lightingEnabled = False
        self.lightMap: Dict[Tuple[int, int, int], int] = {}
        self.lightingDirty = True  # Flag to recalculate lighting
        self.litBlockCache: Dict[Tuple[BlockType, int, float, float, float], pygame.Surface] = {}  # Cache lit sprites
        self.litBlockCacheMaxSize = 500  # LRU cache limit to prevent memory bloat
        self.litBlockCacheOrder = []  # Track access order for LRU eviction
        
        # ============ NEW FEATURES ============
        
        # Undo/Redo system
        from engine.undo import UndoManager
        self.undoManager = UndoManager(max_history=100)
        
        # Zoom system
        self.zoomLevel = 1.0
        self.zoomMin = 0.5
        self.zoomMax = 2.0
        self.zoomStep = 0.1
        
        # Quick save slots (F5-F8)
        self.quickSaveSlots: Dict[int, str] = {}  # slot number -> filepath
        
        # Block tooltip
        self.showBlockTooltip = True
        
        # Height indicator
        self.currentBuildHeight = 0  # Tracks highest Z being built at
        
        # Selection system
        self.selectionStart: Optional[Tuple[int, int, int]] = None
        self.selectionEnd: Optional[Tuple[int, int, int]] = None
        self.selectionActive = False
        self.clipboard: List[Tuple[Tuple[int, int, int], BlockType, Optional[Dict]]] = []
        self.clipboardSize: Tuple[int, int, int] = (0, 0, 0)
        
        # Block preview rotation (for stairs/slabs before placing)
        self.previewFacing: Facing = Facing.SOUTH
        self.previewSlabPosition: SlabPosition = SlabPosition.BOTTOM
        
        # Screenshots directory
        import os
        self.screenshotsDir = os.path.join(BASE_DIR, "screenshots")
        os.makedirs(self.screenshotsDir, exist_ok=True)
        
        # ============ QOL FEATURES ============
        
        # Hotbar system (9 slots, keys 1-9)
        self.hotbar: List[BlockType] = [
            BlockType.GRASS, BlockType.DIRT, BlockType.STONE,
            BlockType.OAK_PLANKS, BlockType.COBBLESTONE, BlockType.BRICKS,
            BlockType.GLASS, BlockType.OAK_LOG, BlockType.WATER
        ]
        self.hotbarSelectedSlot = 0
        
        # Second hotbar row (Shift+1-9)
        self.hotbar2: List[BlockType] = [
            BlockType.IRON_BLOCK, BlockType.GOLD_BLOCK, BlockType.DIAMOND_BLOCK,
            BlockType.GLOWSTONE, BlockType.SEA_LANTERN, BlockType.QUARTZ_BLOCK,
            BlockType.LAVA, BlockType.TNT, BlockType.OBSIDIAN
        ]
        
        # Recent blocks (last 10 placed)
        self.recentBlocks: List[BlockType] = []
        self.maxRecentBlocks = 10
        
        # Favorites bar (persistent across sessions)
        self.favoriteBlocks: List[BlockType] = []
        self.maxFavorites = 9  # Same as hotbar
        
        # Block search
        self.searchQuery = ""
        self.searchActive = False
        self.searchResults: List[BlockType] = []
        self.searchHistory: List[str] = []  # Remember recent search queries
        self.maxSearchHistory = 10
        
        # Auto-save system
        self.autoSaveEnabled = True
        self.autoSaveInterval = 300000  # 5 minutes in ms
        self.lastAutoSaveTime = pygame.time.get_ticks()
        self.autoSavePath = os.path.join(SAVES_DIR, "_autosave.json.gz")
        self.autoSaveFlashTimer = 0  # Frames to show "Saved" indicator
        
        # Auto-backup system (keeps rolling backups)
        self.autoBackupEnabled = True
        self.maxBackups = 5  # Keep 5 rolling backups
        self.backupDir = os.path.join(SAVES_DIR, "_backups")
        
        # Build statistics
        self.blocksPlaced = 0
        self.blocksRemoved = 0
        self.sessionStartTime = pygame.time.get_ticks()
        self.blockUsageStats: Dict[BlockType, int] = {}  # Track most used blocks
        
        # Coordinate display
        self.showCoordinates = True
        
        # Grid toggle
        self.showGrid = False
        
        # Smooth camera (lerp-based)
        self.targetOffsetX = self.renderer.offsetX
        self.targetOffsetY = self.renderer.offsetY
        self.cameraSmoothing = 0.15  # Lerp factor (0-1, higher = faster)
        self.smoothCameraEnabled = True
        
        # Eyedropper mode
        self.eyedropperMode = False
        
        # Fill tool
        self.fillToolActive = False
        self.fillStart: Optional[Tuple[int, int, int]] = None
        
        # Mirror mode
        self.mirrorModeX = False
        self.mirrorModeY = False
        
        # Layer view
        self.layerViewEnabled = False
        self.currentViewLayer = 0
        
        # Measurement tool
        self.measurementMode = False
        self.measurePoint1: Optional[Tuple[int, int, int]] = None
        self.measurePoint2: Optional[Tuple[int, int, int]] = None
        
        # Minimap
        self.showMinimap = True
        self.minimapSize = 100  # Size of minimap in pixels
        self.minimapMargin = 10  # Margin from screen edge
        
        # Replace mode (replace all blocks of type A with type B)
        self.replaceMode = False
        self.replaceSourceBlock: Optional[BlockType] = None
        
        # Radial symmetry mode (4-way or 8-way)
        self.radialSymmetry = 0  # 0=off, 4=4-way, 8=8-way
        
        # Magic wand selection
        self.magicWandMode = False
        self.magicWandSelection: Set[Tuple[int, int, int]] = set()
        
        # Clone/Stamp Tool - click repeatedly to place copied selection
        self.stampMode = False
        self.stampData: Dict[Tuple[int, int, int], BlockType] = {}  # Relative positions -> block type
        self.stampOrigin: Optional[Tuple[int, int, int]] = None  # Origin point for stamp
        
        # X-Ray mode (make solid blocks semi-transparent)
        self.xrayEnabled = False
        self.xrayAlpha = 80  # Transparency level (0-255, lower = more transparent)
        self.xrayBlocks: Set[BlockType] = {
            BlockType.STONE, BlockType.COBBLESTONE, BlockType.DIRT, BlockType.GRASS,
            BlockType.SAND, BlockType.SANDSTONE, BlockType.GRAVEL, BlockType.CLAY,
            BlockType.BRICKS, BlockType.STONE_BRICKS, BlockType.NETHERRACK,
            BlockType.END_STONE, BlockType.OBSIDIAN, BlockType.PRISMARINE,
        }  # Default: common solid blocks
        
        # Blueprint mode
        self.blueprintMode = False
        self.blueprintBlocks: Dict[Tuple[int, int, int], BlockType] = {}
        
        # Settings menu
        self.settingsMenuOpen = False
        
        # Undo history panel
        self.historyPanelOpen = False
        self.historyPanelScroll = 0
        self.historyHoveredIndex = -1
        self.historyHoveredIsRedo = False
        
        # Block outline on hover
        self.showBlockOutline = True
        
        # Placement animation particles
        self.placementParticles: List[Dict] = []
        
        # Tooltips
        self.tooltipText = ""
        self.tooltipTimer = 0
        self.tooltipDelay = 500  # ms before showing tooltip
        
        # Panel hover tracking
        self.hoveredPanelBlock: Optional[BlockType] = None
        self.panelHoverTime = 0
        
        # Music continuous playback
        self.musicFiles: List[str] = []
        self.currentMusicIndex = 0
        self.musicFadingIn = False
        self.musicFadingOut = False
        self.musicFadeTimer = 0
        self.musicFadeDuration = 2500  # 2.5 second fade
        self.pendingDimensionMusic = None  # Dimension to switch to after fade-out
        
        # ============ BLOCK PREVIEW GHOST ============
        self.showBlockPreview = True  # Show semi-transparent preview before placement
        self.previewAlpha = 120  # Transparency level for preview (0-255)
        
        # ============ HORROR SYSTEM ============
        self.horrorEnabled = True  # Master toggle for all horror features
        self.horrorRainEnabled = False  # Black rain with reversed sounds
        self.horrorRainSound = None  # Reversed/pitched rain sound
        self.horrorRainSoundChannel = None
        self.horrorSounds: Dict[str, List[pygame.mixer.Sound]] = {}  # Horror ambient sounds
        self.lastHorrorSoundTime = 0
        self.horrorSoundMinDelay = 300000  # Minimum 5 minutes between horror sounds (ms)
        self.horrorSoundMaxDelay = 1800000  # Maximum 30 minutes between horror sounds (ms)
        self.nextHorrorSoundTime = random.randint(self.horrorSoundMinDelay, self.horrorSoundMaxDelay)
        self.totalBlocksPlacedAllTime = 0  # Persistent counter for progression-based horror
        self.horrorIntensity = 0  # 0-3, increases with blocks placed
        self.lastVisualGlitchTime = 0
        self.visualGlitchChance = 0.0001  # Very rare visual glitches
        self.herobrineSpotted = 0  # Counter for Herobrine sightings
        self.sessionPlayTime = 0  # Total play time this session in ms
        
        # Horror event flags
        self.screenTearActive = False
        self.screenTearFrames = 0
        self.blockFlickerPos: Optional[Tuple[int, int, int]] = None
        self.blockFlickerTimer = 0
        self.shadowFigureActive = False
        self.shadowFigurePos: Optional[Tuple[int, int]] = None
        self.shadowFigureFadeTimer = 0
        self.ghostCursorActive = False
        self.ghostCursorPositions: List[Tuple[int, int]] = []  # Trail of past mouse positions
        self.blockCounterGlitch = False  # Show count off by 1
        self.subliminalMessageTimer = 0
        self.subliminalMessage = ""
        
        # Herobrine Easter Egg
        self.herobrineActive = False
        self.herobrinePos: Optional[Tuple[int, int]] = None  # Screen position
        self.herobrineFadeTimer = 0
        self.herobrineTriggered = False  # Has Herobrine appeared this session?
        
        # Collapse button tracking for categories
        self.collapseBtnRects: Dict[str, pygame.Rect] = {}  # category -> rect
        
        # Initialize HorrorManager (consolidates all horror features)
        self.horrorManager = HorrorManager(self)
        # Alias for backward compatibility
        self.panelWidth = PANEL_WIDTH
        
        # Load user preferences from config file
        self._loadAppConfig()
    
    def _setAppIconEarly(self):
        """Set app icon BEFORE display is created (critical for Windows taskbar)"""
        iconSize = 32
        icon = pygame.Surface((iconSize, iconSize), pygame.SRCALPHA)
        
        # Load textures directly (before AssetManager is created)
        # Use end_stone.png for the app icon with proper texture mapping
        # Note: Don't use convert_alpha() before display is set
        texPath = os.path.join(TEXTURES_DIR, "end_stone.png")
        
        if os.path.exists(texPath):
            tex = pygame.image.load(texPath)
            
            # Scale texture to a reasonable sampling size
            texSize = 16
            tex = pygame.transform.scale(tex, (texSize, texSize))
            
            W = iconSize
            H = iconSize
            halfW = W // 2
            halfH = W // 4  # Tile height for isometric
            blockH = W * 5 // 8  # Block height for proper proportions
            
            # TOP FACE - isometric diamond with texture mapping
            for py in range(halfH * 2):
                if py <= halfH:
                    spanRatio = py / halfH if halfH > 0 else 0
                else:
                    spanRatio = (halfH * 2 - py) / halfH if halfH > 0 else 0
                
                span = int(halfW * spanRatio)
                if span <= 0:
                    continue
                
                startX = halfW - span
                endX = halfW + span
                
                for px in range(startX, endX):
                    relX = px - halfW
                    relY = py - halfH
                    
                    # Inverse isometric projection to get UV coords
                    u = (relX / halfW + relY / halfH) * 0.5 + 0.5 if halfW > 0 and halfH > 0 else 0.5
                    v = (-relX / halfW + relY / halfH) * 0.5 + 0.5 if halfW > 0 and halfH > 0 else 0.5
                    
                    texX = int(u * (texSize - 1))
                    texY = int(v * (texSize - 1))
                    texX = max(0, min(texSize - 1, texX))
                    texY = max(0, min(texSize - 1, texY))
                    
                    pixel = tex.get_at((texX, texY))
                    icon.set_at((px, py), pixel)
            
            # LEFT FACE - darker
            for px in range(halfW):
                topY = halfH + int((px / halfW) * halfH) if halfW > 0 else halfH
                bottomY = topY + blockH
                
                for py in range(topY, min(bottomY, H)):
                    u = px / halfW if halfW > 0 else 0
                    v = (py - topY) / blockH if blockH > 0 else 0
                    
                    texX = int(u * (texSize - 1))
                    texY = int(v * (texSize - 1))
                    texX = max(0, min(texSize - 1, texX))
                    texY = max(0, min(texSize - 1, texY))
                    
                    pixel = tex.get_at((texX, texY))
                    # Darken for left face
                    r = int(pixel.r * 0.6)
                    g = int(pixel.g * 0.6)
                    b = int(pixel.b * 0.6)
                    icon.set_at((px, py), (r, g, b, pixel.a))
            
            # RIGHT FACE - medium brightness
            for px in range(halfW, W):
                relX = px - halfW
                topY = halfH * 2 - 1 - int((relX / halfW) * halfH) if halfW > 0 else halfH
                bottomY = topY + blockH
                
                for py in range(max(0, topY), min(bottomY, H)):
                    u = relX / halfW if halfW > 0 else 0
                    v = (py - topY) / blockH if blockH > 0 else 0
                    
                    texX = int(u * (texSize - 1))
                    texY = int(v * (texSize - 1))
                    texX = max(0, min(texSize - 1, texX))
                    texY = max(0, min(texSize - 1, texY))
                    
                    pixel = tex.get_at((texX, texY))
                    # Slightly darken for right face
                    r = int(pixel.r * 0.8)
                    g = int(pixel.g * 0.8)
                    b = int(pixel.b * 0.8)
                    icon.set_at((px, py), (r, g, b, pixel.a))
            
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
        
        # Use end_stone texture with proper texture mapping
        tex = self.assetManager.textures.get("end_stone")
        
        if tex:
            texSize = 16
            tex = pygame.transform.scale(tex, (texSize, texSize))
            
            W = iconSize
            H = iconSize
            halfW = W // 2
            halfH = W // 4  # Tile height for isometric
            blockH = W * 5 // 8  # Block height for proper proportions
            
            # TOP FACE - isometric diamond with texture mapping
            for py in range(halfH * 2):
                if py <= halfH:
                    spanRatio = py / halfH if halfH > 0 else 0
                else:
                    spanRatio = (halfH * 2 - py) / halfH if halfH > 0 else 0
                
                span = int(halfW * spanRatio)
                if span <= 0:
                    continue
                
                startX = halfW - span
                endX = halfW + span
                
                for px in range(startX, endX):
                    relX = px - halfW
                    relY = py - halfH
                    
                    # Inverse isometric projection to get UV coords
                    u = (relX / halfW + relY / halfH) * 0.5 + 0.5 if halfW > 0 and halfH > 0 else 0.5
                    v = (-relX / halfW + relY / halfH) * 0.5 + 0.5 if halfW > 0 and halfH > 0 else 0.5
                    
                    texX = int(u * (texSize - 1))
                    texY = int(v * (texSize - 1))
                    texX = max(0, min(texSize - 1, texX))
                    texY = max(0, min(texSize - 1, texY))
                    
                    pixel = tex.get_at((texX, texY))
                    icon.set_at((px, py), pixel)
            
            # LEFT FACE - darker
            for px in range(halfW):
                topY = halfH + int((px / halfW) * halfH) if halfW > 0 else halfH
                bottomY = topY + blockH
                
                for py in range(topY, min(bottomY, H)):
                    u = px / halfW if halfW > 0 else 0
                    v = (py - topY) / blockH if blockH > 0 else 0
                    
                    texX = int(u * (texSize - 1))
                    texY = int(v * (texSize - 1))
                    texX = max(0, min(texSize - 1, texX))
                    texY = max(0, min(texSize - 1, texY))
                    
                    pixel = tex.get_at((texX, texY))
                    # Darken for left face
                    r = int(pixel.r * 0.6)
                    g = int(pixel.g * 0.6)
                    b = int(pixel.b * 0.6)
                    icon.set_at((px, py), (r, g, b, pixel.a))
            
            # RIGHT FACE - medium brightness
            for px in range(halfW, W):
                relX = px - halfW
                topY = halfH * 2 - 1 - int((relX / halfW) * halfH) if halfW > 0 else halfH
                bottomY = topY + blockH
                
                for py in range(max(0, topY), min(bottomY, H)):
                    u = relX / halfW if halfW > 0 else 0
                    v = (py - topY) / blockH if blockH > 0 else 0
                    
                    texX = int(u * (texSize - 1))
                    texY = int(v * (texSize - 1))
                    texX = max(0, min(texSize - 1, texX))
                    texY = max(0, min(texSize - 1, texY))
                    
                    pixel = tex.get_at((texX, texY))
                    # Slightly darken for right face
                    r = int(pixel.r * 0.8)
                    g = int(pixel.g * 0.8)
                    b = int(pixel.b * 0.8)
                    icon.set_at((px, py), (r, g, b, pixel.a))
            
            pygame.display.set_icon(icon)
    
    def _loadAppConfig(self) -> None:
        """Load app preferences from config file (expanded categories, hotbar, etc.)"""
        try:
            if os.path.exists(APP_CONFIG_FILE):
                with open(APP_CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    
                    # NOTE: Menu state (expanded categories, etc.) is NOT restored on launch
                    # This ensures a clean slate each session per user request
                    # The following states are intentionally reset to defaults:
                    # - expandedCategories: all False
                    # - blocksExpanded: False
                    # - problemsExpanded: False
                    # - experimentalExpanded: False
                    # - structuresExpanded: False
                    # - hotkeysExpanded: False
                    # - inventoryScroll: 0
                    # - searchQuery: ""
                    
                    # Restore other preferences (these are useful to persist)
                    self.showGrid = config.get("showGrid", True)
                    self.lightingEnabled = config.get("lightingEnabled", False)
                    self.showBlockTooltip = config.get("showBlockTooltip", True)
                    
                    # Restore favorites (by block name)
                    savedFavorites = config.get("favoriteBlocks", [])
                    self.favoriteBlocks = []
                    for blockName in savedFavorites:
                        try:
                            blockType = BlockType[blockName]
                            self.favoriteBlocks.append(blockType)
                        except KeyError:
                            pass  # Ignore unknown block types
                    
                    # Restore hotbar (by block name)
                    savedHotbar = config.get("hotbar", [])
                    if savedHotbar:
                        for i, blockName in enumerate(savedHotbar[:9]):
                            try:
                                self.hotbar[i] = BlockType[blockName]
                            except KeyError:
                                pass
                    
                    # Restore search history
                    self.searchHistory = config.get("searchHistory", [])[:self.maxSearchHistory]
                    
        except Exception as e:
            print(f"Could not load app config: {e}")
    
    def _saveAppConfig(self) -> None:
        """Save app preferences to config file"""
        try:
            config = {
                "expandedCategories": self.expandedCategories,
                "blocksExpanded": self.blocksExpanded,
                "problemsExpanded": self.problemsExpanded,
                "experimentalExpanded": self.experimentalExpanded,
                "structuresExpanded": self.structuresExpanded,
                "showGrid": self.showGrid,
                "lightingEnabled": self.lightingEnabled,
                "showBlockTooltip": self.showBlockTooltip,
                "favoriteBlocks": [b.name for b in self.favoriteBlocks],
                "hotbar": [b.name for b in self.hotbar],
                "searchHistory": self.searchHistory,
            }
            with open(APP_CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Could not save app config: {e}")
    
    def _showSplashScreen(self):
        """
        Display a splash screen with the app icon and title.
        Uses the new splash.py module for high-resolution rendering.
        """
        # Define pre-render callback for smooth transition
        def pre_render_game():
            self._render()
            return self.screen.copy()
        
        try:
            # Use the new splash module
            splash = SplashScreen(
                self.screen, 
                self.clock, 
                TEXTURES_DIR, 
                FONTS_DIR, 
                ICONS_DIR
            )
            splash.show(pre_render_callback=pre_render_game)
            return True
        except Exception as e:
            print(f"Splash screen error: {e}")
            # Fallback: just return True to continue
            return True

    def run(self) -> None:
        """Main application loop"""
        # Load assets
        if not self.assetManager.loadAllAssets():
            print("Failed to load assets!")
            return
        
        # Start music immediately after assets load
        self._playMenuMusic()
        
        # Set 3D app icon (after assets loaded)
        self._setAppIcon()
        
        # Generate structure preview thumbnails (after assets loaded)
        self._generateStructurePreviews()
        
        # Initialize tutorial with assets
        self.tutorialScreen.setAssets(
            self.assetManager.buttonNormal,
            self.assetManager.buttonHover,
            self.assetManager.checkboxTexture,
            self.assetManager.checkboxSelectedTexture,
            self.assetManager.clickSound,
            self.assetManager  # Pass assetManager for block icons
        )
        # Set callback for tutorial demo loading
        self.tutorialScreen.onStepChange = self._onTutorialStepChange
        # Set callback for when tutorial ends (return to overworld)
        self.tutorialScreen.onTutorialEnd = self._onTutorialEnd
        
        # Create initial floor (needed for splash screen fade)
        self._createInitialFloor()
        
        # Show splash screen (also starts music during fade)
        if not self._showSplashScreen():
            return  # User quit during splash
        
        # Show tutorial on startup if enabled
        if self.tutorialScreen.shouldShowOnStartup():
            self.tutorialScreen.show()
        
        print("\n=== Bloc Fantome Started ===")
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
        
        # Save user preferences before quitting
        self._saveAppConfig()
        
        # Clean up
        if self.rainEnabled:
            self._stopRain()
        pygame.mixer.music.stop()
        pygame.quit()
    
    def _rotateViewAndRecenter(self, direction: int):
        """Rotate view and recenter on the grid at a lower position"""
        self.renderer.rotateView(direction)
        
        # Recenter the view on the middle of the grid - position lower on screen
        centerX = (WINDOW_WIDTH - PANEL_WIDTH) // 2
        centerY = WINDOW_HEIGHT // 2 + 50  # Lower position (was // 3)
        
        # Calculate where the grid center should be in screen coords
        gridCenterX = GRID_WIDTH // 2
        gridCenterY = GRID_DEPTH // 2
        
        # Get screen position of grid center with new rotation
        self.renderer.offsetX = centerX
        self.renderer.offsetY = centerY
        screenX, screenY = self.renderer.worldToScreen(gridCenterX, gridCenterY, 0)
        
        # Adjust offset so grid center is at screen center
        self.renderer.offsetX = centerX - (screenX - centerX)
        self.renderer.offsetY = centerY - (screenY - centerY)
        
        # Update smooth camera targets
        self.targetOffsetX = self.renderer.offsetX
        self.targetOffsetY = self.renderer.offsetY
        
        print(f"View rotated: {self.renderer.viewRotation * 90}°")
    
    def _centerOnCell(self, worldX: int, worldY: int, worldZ: int):
        """Center the view on a specific world cell"""
        centerX = (WINDOW_WIDTH - PANEL_WIDTH) // 2
        centerY = WINDOW_HEIGHT // 2
        
        # Get current screen position of the target cell
        screenX, screenY = self.renderer.worldToScreen(worldX, worldY, worldZ)
        
        # Calculate offset needed to center that cell on screen
        targetOffsetX = self.renderer.offsetX + (centerX - screenX)
        targetOffsetY = self.renderer.offsetY + (centerY - screenY)
        
        # Update smooth camera targets for smooth transition
        if self.smoothCameraEnabled:
            self.targetOffsetX = targetOffsetX
            self.targetOffsetY = targetOffsetY
        else:
            self.renderer.offsetX = targetOffsetX
            self.renderer.offsetY = targetOffsetY
            self.targetOffsetX = targetOffsetX
            self.targetOffsetY = targetOffsetY
    
    def _centerOnHoveredOrGrid(self):
        """Center view on hovered cell, selection, or grid center"""
        if self.hoveredCell:
            # Center on hovered cell
            x, y, z = self.hoveredCell
            self._centerOnCell(x, y, z)
            self.tooltipText = f"Centered on ({x}, {y}, {z})"
            self.tooltipTimer = 1000
        elif self.selectionStart and self.selectionEnd:
            # Center on middle of selection
            midX = (self.selectionStart[0] + self.selectionEnd[0]) // 2
            midY = (self.selectionStart[1] + self.selectionEnd[1]) // 2
            midZ = (self.selectionStart[2] + self.selectionEnd[2]) // 2
            self._centerOnCell(midX, midY, midZ)
            self.tooltipText = "Centered on selection"
            self.tooltipTimer = 1000
        else:
            # Center on grid center
            self._centerOnCell(GRID_WIDTH // 2, GRID_DEPTH // 2, 0)
            self.tooltipText = "Centered on grid"
            self.tooltipTimer = 1000
    
    def _playMenuMusic(self, dimension: str = None):
        """Play a random song based on dimension with crossfade transition"""
        if dimension is None:
            dimension = self.currentDimension
        
        # If music is playing, start fade-out and queue the new dimension
        if pygame.mixer.music.get_busy() and not self.musicFadingOut:
            self.pendingDimensionMusic = dimension
            self.musicFadingOut = True
            self.musicFadingIn = False
            self.musicFadeTimer = 0
            return
        
        # Choose music directory based on dimension
        if dimension == DIMENSION_NETHER:
            musicDir = MUSIC_DIR_NETHER
        elif dimension == DIMENSION_END:
            musicDir = MUSIC_DIR_END
        else:
            musicDir = MUSIC_DIR
        
        # Collect all ogg files recursively (for nether subdirectories)
        self.musicFiles = []
        if os.path.exists(musicDir):
            for root, dirs, files in os.walk(musicDir):
                for f in files:
                    if f.endswith('.ogg'):
                        self.musicFiles.append(os.path.join(root, f))
        
        # Also include custom user music (.ogg and .mp3 files)
        if os.path.exists(CUSTOM_MUSIC_DIR):
            for f in os.listdir(CUSTOM_MUSIC_DIR):
                if f.lower().endswith(('.ogg', '.mp3', '.wav')):
                    self.musicFiles.append(os.path.join(CUSTOM_MUSIC_DIR, f))
            customCount = len([f for f in os.listdir(CUSTOM_MUSIC_DIR) if f.lower().endswith(('.ogg', '.mp3', '.wav'))])
            if customCount > 0:
                print(f"  Added {customCount} custom music track(s) from saves/custom_music")
        
        if self.musicFiles:
            # Shuffle playlist
            random.shuffle(self.musicFiles)
            self.currentMusicIndex = 0
            self._playNextSong()
            
            # Set up end event for continuous playback
            pygame.mixer.music.set_endevent(pygame.USEREVENT + 1)
    
    def _playNextSong(self):
        """Play the next song in the playlist with fade"""
        if not hasattr(self, 'musicFiles') or not self.musicFiles:
            return
        
        # Get next song
        selectedPath = self.musicFiles[self.currentMusicIndex]
        selectedName = os.path.basename(selectedPath)
        
        try:
            pygame.mixer.music.load(selectedPath)
            pygame.mixer.music.set_volume(0)  # Start silent for fade-in
            pygame.mixer.music.play()
            
            # Start fade-in (faster fade so music is heard sooner)
            self.musicFadingIn = True
            self.musicFadeTimer = 0
            self.musicFadeDuration = 1500  # 1.5 second fade (was 3s)
            
            print(f"Now playing: {selectedName}")
            
            # Move to next song (loop around)
            self.currentMusicIndex = (self.currentMusicIndex + 1) % len(self.musicFiles)
        except Exception as e:
            print(f"Could not play music: {e}")
            # Try next song
            self.currentMusicIndex = (self.currentMusicIndex + 1) % len(self.musicFiles)
    
    def _generateStructurePreviews(self):
        """
        Pre-render isometric thumbnail previews for all structures.
        Creates 115x75 thumbnails with the same isometric view as the main grid.
        """
        PREVIEW_WIDTH = 115
        PREVIEW_HEIGHT = 75
        
        for structName, structData in PREMADE_STRUCTURES.items():
            # Create transparent surface for preview
            preview = pygame.Surface((PREVIEW_WIDTH, PREVIEW_HEIGHT), pygame.SRCALPHA)
            preview.fill((0, 0, 0, 0))
            
            blocks = structData.get("blocks", [])
            if not blocks:
                self.structurePreviews[structName] = preview
                continue
            
            # Find bounding box of structure
            minX = min(b[0] for b in blocks)
            maxX = max(b[0] for b in blocks)
            minY = min(b[1] for b in blocks)
            maxY = max(b[1] for b in blocks)
            minZ = min(b[2] for b in blocks)
            maxZ = max(b[2] for b in blocks)
            
            structWidth = maxX - minX + 1
            structDepth = maxY - minY + 1
            structHeight = maxZ - minZ + 1
            
            # Calculate the approximate rendered size of the structure
            # Using the main isometric constants as reference
            approxWidth = (structWidth + structDepth) * (TILE_WIDTH // 2)
            approxHeight = (structWidth + structDepth) * (TILE_HEIGHT // 2) + structHeight * BLOCK_HEIGHT
            
            # Calculate scale to fit in preview with padding
            padding = 6
            scaleX = (PREVIEW_WIDTH - padding * 2) / max(approxWidth, 1)
            scaleY = (PREVIEW_HEIGHT - padding * 2) / max(approxHeight, 1)
            scale = min(scaleX, scaleY)
            
            # Center offset for the preview - horizontal center
            centerOffsetX = PREVIEW_WIDTH // 2
            
            # Calculate actual rendered bounds to center vertically
            # First pass: find the actual screen Y range after scaling
            allScreenY = []
            for bx, by, bz, blockType in blocks:
                nx = bx - minX
                ny = by - minY
                nz = bz - minZ
                screenY = (nx + ny) * (TILE_HEIGHT // 2) * scale - nz * BLOCK_HEIGHT * scale
                # Account for block sprite height
                sprite = self.assetManager.getBlockSprite(blockType)
                if sprite:
                    scaledHeight = max(4, int(sprite.get_height() * scale))
                    allScreenY.append(screenY)
                    allScreenY.append(screenY + scaledHeight)
            
            if allScreenY:
                actualMinY = min(allScreenY)
                actualMaxY = max(allScreenY)
                actualHeight = actualMaxY - actualMinY
                # Center vertically with the actual rendered height
                centerOffsetY = (PREVIEW_HEIGHT - actualHeight) // 2 - actualMinY
            else:
                centerOffsetY = PREVIEW_HEIGHT // 2
            
            # Sort blocks by depth (painter's algorithm)
            sortedBlocks = sorted(blocks, key=lambda b: b[0] + b[1] + b[2])
            
            # Draw each block
            for bx, by, bz, blockType in sortedBlocks:
                # Normalize coordinates relative to structure min
                nx = bx - minX
                ny = by - minY
                nz = bz - minZ
                
                # Convert to screen position using same formula as main renderer, then scale
                screenX = (nx - ny) * (TILE_WIDTH // 2) * scale + centerOffsetX
                screenY = (nx + ny) * (TILE_HEIGHT // 2) * scale - nz * BLOCK_HEIGHT * scale + centerOffsetY
                
                # Get block sprite and scale it down
                sprite = self.assetManager.getBlockSprite(blockType)
                if sprite:
                    # Scale sprite to fit the preview
                    origWidth = sprite.get_width()
                    origHeight = sprite.get_height()
                    scaledWidth = max(4, int(origWidth * scale))
                    scaledHeight = max(4, int(origHeight * scale))
                    
                    # Scale the sprite
                    scaledSprite = pygame.transform.smoothscale(sprite, (scaledWidth, scaledHeight))
                    
                    # Position to align sprite's top vertex with tile position
                    drawX = int(screenX - scaledWidth // 2)
                    drawY = int(screenY)
                    
                    preview.blit(scaledSprite, (drawX, drawY))
            
            self.structurePreviews[structName] = preview
        
        print(f"  Generated {len(self.structurePreviews)} structure previews")
    
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
        
        # Stop rain if leaving Overworld
        if self.rainEnabled and newDimension != DIMENSION_OVERWORLD:
            self.rainEnabled = False
            self._stopRain()
        
        # Stop snow if leaving Overworld
        if self.snowEnabled and newDimension != DIMENSION_OVERWORLD:
            self.snowEnabled = False
            self._stopSnow()
        
        # Clear snow layers when switching dimensions
        self._clearSnowLayers()
        
        # Stop celestial cycle if leaving Overworld
        if self.celestialEnabled and newDimension != DIMENSION_OVERWORLD:
            self.celestialEnabled = False
            self._stopCelestial()
        
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
    
    def _onTutorialStepChange(self, stepIndex: int) -> None:
        """Handle tutorial step change - load demo structure for the step"""
        if stepIndex < 0 or stepIndex >= len(TutorialScreen.TUTORIAL_STEPS):
            return
        
        step = TutorialScreen.TUTORIAL_STEPS[stepIndex]
        demo = step.get("demo")
        title = step.get("title", "")
        is_horror = step.get("is_horror", False)
        
        # First, always unpause music to ensure clean state for dimension switches
        pygame.mixer.music.unpause()
        
        # ===== Determine required dimension for this step =====
        # Default to Overworld unless specified otherwise
        requiredDimension = DIMENSION_OVERWORLD
        if "Nether" in title:
            requiredDimension = DIMENSION_NETHER
        elif "End" in title:
            requiredDimension = DIMENSION_END
        # Note: Horror stays in overworld but with special effects
        
        # Switch dimension if needed (BEFORE loading demo, so floor is correct)
        # Skip for save: demos as they handle their own dimension
        if not (demo and demo.startswith("save:")):
            if self.currentDimension != requiredDimension:
                self._switchDimension(requiredDimension)
                print(f"Tutorial: Switched to {requiredDimension} dimension")
        
        # ===== Reset modes when switching panels =====
        # Turn off mirror mode when navigating tutorial
        if self.mirrorModeX or self.mirrorModeY:
            self.mirrorModeX = False
            self.mirrorModeY = False
            print("Tutorial: Reset mirror mode")
        
        # ===== Override hotbar for specific tutorial panels =====
        step = TutorialScreen.TUTORIAL_STEPS[stepIndex]
        icons = step.get("icons", [])
        
        # Map icon names to BlockTypes for hotbar - every panel gets appropriate blocks
        iconToBlock = {
            # Basic blocks
            "grass_block": BlockType.GRASS, "grass": BlockType.GRASS,
            "dirt": BlockType.DIRT, "stone": BlockType.STONE,
            "oak_planks": BlockType.OAK_PLANKS, "cobblestone": BlockType.COBBLESTONE,
            "bricks": BlockType.BRICKS, "glass": BlockType.GLASS,
            "oak_log": BlockType.OAK_LOG, "spruce_log": BlockType.SPRUCE_LOG,
            "birch_log": BlockType.BIRCH_LOG, "jungle_log": BlockType.JUNGLE_LOG,
            "dark_oak_log": BlockType.DARK_OAK_LOG,
            # Wool colors
            "red_wool": BlockType.RED_WOOL, "blue_wool": BlockType.BLUE_WOOL,
            "yellow_wool": BlockType.YELLOW_WOOL, "green_wool": BlockType.GREEN_WOOL,
            "white_wool": BlockType.WHITE_WOOL, "purple_wool": BlockType.PURPLE_WOOL,
            # Stone variants
            "stone_bricks": BlockType.STONE_BRICKS, "mossy_cobblestone": BlockType.MOSSY_COBBLESTONE,
            "andesite": BlockType.ANDESITE, "diorite": BlockType.DIORITE, "granite": BlockType.GRANITE,
            "smooth_stone": BlockType.SMOOTH_STONE, "quartz_block": BlockType.QUARTZ_BLOCK,
            "sandstone": BlockType.SANDSTONE, "prismarine": BlockType.PRISMARINE,
            # Liquids and ice
            "water": BlockType.WATER, "lava": BlockType.LAVA,
            "ice": BlockType.ICE, "packed_ice": BlockType.PACKED_ICE,
            "obsidian": BlockType.OBSIDIAN, "snow": BlockType.SNOW, "snow_block": BlockType.SNOW,
            # Light sources
            "glowstone": BlockType.GLOWSTONE, "sea_lantern": BlockType.SEA_LANTERN,
            "jack_o_lantern": BlockType.JACK_O_LANTERN, "shroomlight": BlockType.SHROOMLIGHT,
            "magma_block": BlockType.MAGMA_BLOCK,
            # Nether blocks
            "netherrack": BlockType.NETHERRACK, "soul_sand": BlockType.SOUL_SAND,
            "nether_bricks": BlockType.NETHER_BRICKS, "crying_obsidian": BlockType.CRYING_OBSIDIAN,
            "bone_block": BlockType.BONE_BLOCK,
            # End blocks
            "end_stone": BlockType.END_STONE, "purpur_block": BlockType.PURPUR_BLOCK,
            "bedrock": BlockType.BEDROCK,
            # Functional blocks
            "bookshelf": BlockType.BOOKSHELF, "crafting_table": BlockType.CRAFTING_TABLE,
            "furnace": BlockType.FURNACE, "chest": BlockType.CHEST,
            "enchanting_table": BlockType.ENCHANTING_TABLE, "ender_chest": BlockType.ENDER_CHEST,
            "jukebox": BlockType.JUKEBOX,
            # Ore/mineral blocks
            "diamond_block": BlockType.DIAMOND_BLOCK, "emerald_block": BlockType.EMERALD_BLOCK,
            "gold_block": BlockType.GOLD_BLOCK, "iron_block": BlockType.IRON_BLOCK,
            "lapis_block": BlockType.LAPIS_BLOCK, "redstone_block": BlockType.REDSTONE_BLOCK,
            # Clay
            "clay": BlockType.CLAY, "white_concrete": BlockType.WHITE_CONCRETE,
        }
        
        # Build hotbar from panel icons + fill remaining with relevant blocks
        tutorialBlocks = []
        for iconName in icons:
            if iconName in iconToBlock:
                tutorialBlocks.append(iconToBlock[iconName])
        
        # Fill to 9 slots with contextually relevant blocks
        if "Welcome" in title or "Camera" in title:
            fillBlocks = [BlockType.GRASS, BlockType.DIRT, BlockType.STONE, BlockType.OAK_PLANKS, 
                         BlockType.COBBLESTONE, BlockType.BRICKS, BlockType.GLASS, BlockType.OAK_LOG, BlockType.WATER]
        elif "Block Selection" in title or "Mirror" in title:
            fillBlocks = [BlockType.RED_WOOL, BlockType.BLUE_WOOL, BlockType.YELLOW_WOOL, BlockType.GREEN_WOOL,
                         BlockType.WHITE_WOOL, BlockType.PURPLE_WOOL, BlockType.ORANGE_WOOL, BlockType.CYAN_WOOL, BlockType.PINK_WOOL]
        elif "Fill" in title:
            fillBlocks = [BlockType.STONE_BRICKS, BlockType.QUARTZ_BLOCK, BlockType.SANDSTONE, BlockType.SMOOTH_STONE,
                         BlockType.PRISMARINE, BlockType.BRICKS, BlockType.COBBLESTONE, BlockType.STONE, BlockType.DIRT]
        elif "Brush" in title:
            fillBlocks = [BlockType.OAK_LOG, BlockType.SPRUCE_LOG, BlockType.BIRCH_LOG, BlockType.JUNGLE_LOG,
                         BlockType.DARK_OAK_LOG, BlockType.ACACIA_LOG, BlockType.STONE, BlockType.COBBLESTONE, BlockType.BRICKS]
        elif "Undo" in title:
            fillBlocks = [BlockType.STONE, BlockType.COBBLESTONE, BlockType.MOSSY_COBBLESTONE, BlockType.ANDESITE,
                         BlockType.DIORITE, BlockType.GRANITE, BlockType.STONE_BRICKS, BlockType.DIRT, BlockType.GRAVEL]
        elif "Rotate" in title:
            fillBlocks = [BlockType.STONE_BRICKS, BlockType.OAK_PLANKS, BlockType.STONE, BlockType.OAK_LOG,
                         BlockType.GLASS, BlockType.QUARTZ_BLOCK, BlockType.COBBLESTONE, BlockType.BRICKS, BlockType.GLOWSTONE]
        elif "Liquid" in title:
            fillBlocks = [BlockType.WATER, BlockType.LAVA, BlockType.ICE, BlockType.PACKED_ICE,
                         BlockType.OBSIDIAN, BlockType.SNOW, BlockType.PRISMARINE, BlockType.CLAY, BlockType.SAND]
        elif "Structures" in title:
            fillBlocks = [BlockType.OAK_PLANKS, BlockType.COBBLESTONE, BlockType.STONE_BRICKS, BlockType.OAK_LOG,
                         BlockType.GLASS, BlockType.BOOKSHELF, BlockType.CHEST, BlockType.CRAFTING_TABLE, BlockType.FURNACE]
        elif "Nether" in title:
            fillBlocks = [BlockType.NETHERRACK, BlockType.SOUL_SAND, BlockType.NETHER_BRICKS, BlockType.GLOWSTONE,
                         BlockType.MAGMA_BLOCK, BlockType.OBSIDIAN, BlockType.QUARTZ_BLOCK, BlockType.LAVA, BlockType.CRYING_OBSIDIAN]
        elif "End" in title:
            fillBlocks = [BlockType.END_STONE, BlockType.PURPUR_BLOCK, BlockType.OBSIDIAN, BlockType.BEDROCK,
                         BlockType.END_STONE, BlockType.PURPUR_PILLAR, BlockType.PURPUR_BLOCK, BlockType.STONE, BlockType.GLASS]
        elif "Weather" in title:
            fillBlocks = [BlockType.SNOW, BlockType.ICE, BlockType.PACKED_ICE, BlockType.WHITE_WOOL,
                         BlockType.WHITE_CONCRETE, BlockType.QUARTZ_BLOCK, BlockType.GLASS, BlockType.CLAY, BlockType.BONE_BLOCK]
        elif "Lighting" in title:
            fillBlocks = [BlockType.GLOWSTONE, BlockType.SEA_LANTERN, BlockType.JACK_O_LANTERN, BlockType.SHROOMLIGHT,
                         BlockType.MAGMA_BLOCK, BlockType.LAVA, BlockType.CRYING_OBSIDIAN, BlockType.REDSTONE_BLOCK, BlockType.GOLD_BLOCK]
        elif "Save" in title:
            fillBlocks = [BlockType.CHEST, BlockType.ENDER_CHEST, BlockType.BOOKSHELF, BlockType.JUKEBOX,
                         BlockType.CRAFTING_TABLE, BlockType.QUARTZ_BLOCK, BlockType.STONE_BRICKS, BlockType.GLOWSTONE, BlockType.OAK_PLANKS]
        elif "Hidden" in title or is_horror:
            fillBlocks = [BlockType.CRYING_OBSIDIAN, BlockType.OBSIDIAN, BlockType.BONE_BLOCK, BlockType.NETHERRACK,
                         BlockType.SOUL_SAND, BlockType.MAGMA_BLOCK, BlockType.COAL_BLOCK, BlockType.BLACKSTONE, BlockType.BASALT]
        elif "Ready" in title:
            fillBlocks = [BlockType.DIAMOND_BLOCK, BlockType.EMERALD_BLOCK, BlockType.GOLD_BLOCK, BlockType.IRON_BLOCK,
                         BlockType.LAPIS_BLOCK, BlockType.REDSTONE_BLOCK, BlockType.COPPER_BLOCK, BlockType.COAL_BLOCK, BlockType.NETHERITE_BLOCK]
        else:
            # Default fallback
            fillBlocks = [BlockType.GRASS, BlockType.DIRT, BlockType.STONE, BlockType.OAK_PLANKS,
                         BlockType.COBBLESTONE, BlockType.BRICKS, BlockType.GLASS, BlockType.OAK_LOG, BlockType.WATER]
        
        # Use fillBlocks if tutorialBlocks is empty or incomplete
        if not tutorialBlocks:
            tutorialBlocks = fillBlocks[:9]
        else:
            # Fill remaining slots
            while len(tutorialBlocks) < 9:
                for block in fillBlocks:
                    if block not in tutorialBlocks and len(tutorialBlocks) < 9:
                        tutorialBlocks.append(block)
                if len(tutorialBlocks) < 9:
                    break  # Prevent infinite loop
        
        # Apply to hotbar
        for i, block in enumerate(tutorialBlocks[:9]):
            self.hotbar[i] = block
        self.selectedBlock = tutorialBlocks[0] if tutorialBlocks else BlockType.GRASS
        
        # ===== Showcase features based on step =====
        # Toggle rain on weather panel, off otherwise
        if "Weather" in title:
            if not self.rainEnabled:
                self.rainEnabled = True
                print("Tutorial: Enabled rain for weather showcase")
        else:
            if self.rainEnabled and not is_horror:
                self.rainEnabled = False
        
        # Toggle lighting: ON for Lighting panel and Nether pages, OFF otherwise
        isNetherPage = "Nether" in title or demo == "save:warped_forest_accurate"
        if "Lighting" in title or isNetherPage:
            if not self.lightingEnabled:
                self.lightingEnabled = True
                self.lightingDirty = True
                print(f"Tutorial: Enabled lighting for {'Nether' if isNetherPage else 'Lighting'} showcase")
        else:
            # Reset lighting for all other tutorial pages
            if self.lightingEnabled:
                self.lightingEnabled = False
                print("Tutorial: Disabled lighting")
        
        # Turn off horror rain when not in horror
        if is_horror:
            if not self.horrorRainEnabled:
                self.horrorRainEnabled = True
                self._startHorrorRain()
                print("Tutorial: Enabled horror rain")
        else:
            if self.horrorRainEnabled:
                self.horrorRainEnabled = False
                self._stopHorrorRain()
        
        if demo == "clear":
            # Clear the world and create floor
            self.world.clear()
            self._createInitialFloor()
            print(f"Tutorial step {stepIndex + 1}: Cleared world")
        elif demo and demo.startswith("save:"):
            # Load a save file using _loadBuilding
            saveName = demo[5:]  # Remove "save:" prefix
            saveFilename = f"{saveName}.json"
            try:
                success = self._loadBuilding(saveFilename, silent=True)
                if success:
                    pass  # Silent load for tutorial
                else:
                    # Fallback to empty world
                    self.world.clear()
                    self._createInitialFloor()
            except Exception as e:
                print(f"Tutorial: Could not load save '{saveName}': {e}")
                self.world.clear()
                self._createInitialFloor()
        elif demo and demo in PREMADE_STRUCTURES:
            # Clear and load the demo structure
            self.world.clear()
            
            # Place the structure centered in the world
            structure = PREMADE_STRUCTURES[demo]
            # Calculate structure bounds to center it
            if structure["blocks"]:
                minX = min(b[0] for b in structure["blocks"])
                maxX = max(b[0] for b in structure["blocks"])
                minY = min(b[1] for b in structure["blocks"])
                maxY = max(b[1] for b in structure["blocks"])
                minZ = min(b[2] for b in structure["blocks"])
                
                # Center at grid center (around middle of grid)
                centerX = GRID_WIDTH // 2 - (maxX + minX) // 2
                centerY = GRID_DEPTH // 2 - (maxY + minY) // 2
                
                # Only for Structures Library panel (empty_platform): don't create floor since it has its own
                # All other panels: create floor and place structure on top
                if demo == "empty_platform":
                    # Structure has its own floor, place at z=0
                    centerZ = 0
                else:
                    # Create floor for other panels and place structure on top
                    self._createInitialFloor()
                    centerZ = 1
                
                for x, y, z, blockType in structure["blocks"]:
                    placeX = x + centerX
                    placeY = y + centerY
                    placeZ = z + centerZ
                    if 0 <= placeX < GRID_WIDTH and 0 <= placeY < GRID_DEPTH and 0 <= placeZ < GRID_HEIGHT:
                        self.world.setBlock(placeX, placeY, placeZ, blockType)
                
                print(f"Tutorial step {stepIndex + 1}: Loaded '{demo}' structure")
                
                # For Undo tutorial panel (step 5): pre-populate undo history with "mistake" blocks
                # so the user can immediately test Ctrl+Z
                if stepIndex == 5 and demo == "undo_demo":
                    # Clear undo history first
                    self.undoManager.clear()
                    
                    # Place "mistake" blocks through the undo system at visible locations
                    # These will appear on the structure and user can undo them
                    mistakeBlocks = [
                        (centerX + 4, centerY + 4, centerZ + 1, BlockType.DIRT),
                        (centerX + 6, centerY + 3, centerZ + 1, BlockType.COBBLESTONE),
                        (centerX + 3, centerY + 6, centerZ + 2, BlockType.GRAVEL),
                        (centerX + 5, centerY + 5, centerZ + 2, BlockType.SAND),
                        (centerX + 7, centerY + 4, centerZ + 1, BlockType.NETHERRACK),
                    ]
                    
                    for mx, my, mz, mBlockType in mistakeBlocks:
                        if 0 <= mx < GRID_WIDTH and 0 <= my < GRID_DEPTH and 0 <= mz < GRID_HEIGHT:
                            self._placeBlockWithUndo(mx, my, mz, mBlockType)
                    
                    print(f"Tutorial: Pre-placed {len(mistakeBlocks)} undoable 'mistake' blocks")
        elif demo is None:
            # Don't clear - let user keep their work
            pass
        
        # Horror mode: pause music AFTER demo is loaded (so dimension music starts first)
        if is_horror:
            # Give music a moment to start, then pause for eerie effect
            pygame.mixer.music.pause()
            print("Tutorial: Paused music for horror effect")
    
    def _onTutorialEnd(self) -> None:
        """Handle tutorial ending - return to overworld and resume music"""
        # Switch back to overworld dimension
        if self.currentDimension != DIMENSION_OVERWORLD:
            self._switchDimension(DIMENSION_OVERWORLD)
        
        # Make sure music is unpaused (in case horror mode paused it)
        pygame.mixer.music.unpause()
        
        # Reset lighting when tutorial ends
        if self.lightingEnabled:
            self.lightingEnabled = False
            print("Tutorial: Disabled lighting on exit")
        
        # Reset any tutorial-specific weather effects
        if self.rainEnabled:
            self.rainEnabled = False
        if self.horrorRainEnabled:
            self.horrorRainEnabled = False
        
        # Restore default hotbar
        self.hotbar = [
            BlockType.GRASS, BlockType.DIRT, BlockType.STONE,
            BlockType.OAK_PLANKS, BlockType.COBBLESTONE, BlockType.BRICKS,
            BlockType.GLASS, BlockType.OAK_LOG, BlockType.WATER
        ]
        self.selectedBlock = BlockType.GRASS
        
        # Clear world for fresh start
        self.world.clear()
        self._createInitialFloor()
        
        print("Tutorial ended - returned to Overworld")
    
    def _handleEvents(self) -> None:
        """Handle pygame events"""
        for event in pygame.event.get():
            # Let tutorial handle events first if visible
            if self.tutorialScreen.handleEvent(event):
                continue
            
            if event.type == pygame.QUIT:
                self.running = False
            
            elif event.type == pygame.USEREVENT + 1:
                # Music ended event - play next song
                self._playNextSong()
            
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
        """Handle mouse wheel scrolling for zoom (world) or inventory (panel)"""
        mouseX, mouseY = pygame.mouse.get_pos()
        
        # Check if mouse is over the panel - scroll inventory
        if mouseX > WINDOW_WIDTH - PANEL_WIDTH:
            # Scroll speed
            scrollAmount = 30
            
            # event.y is positive when scrolling up, negative when scrolling down
            self.inventoryScroll -= event.y * scrollAmount
            
            # Clamp scroll to valid range
            self.inventoryScroll = max(0, min(self.inventoryScroll, self.maxScroll))
        else:
            # Mouse is over the world area - handle zoom toward cursor
            # event.y is positive when scrolling up (zoom in), negative when scrolling down (zoom out)
            self._handleZoom(event.y * self.zoomStep, mouseX, mouseY)
    
    def _handleMouseDown(self, event):
        """Handle mouse button press"""
        mouseX, mouseY = event.pos
        mods = pygame.key.get_mods()
        
        # If history panel is open, handle clicks
        if self.historyPanelOpen:
            if hasattr(self, 'historyPanelRect') and self.historyPanelRect.collidepoint(mouseX, mouseY):
                self._handleHistoryPanelClick(mouseX, mouseY)
            else:
                self.historyPanelOpen = False
            return
        
        # If settings menu is open, handle settings clicks
        if self.settingsMenuOpen:
            self._handleSettingsClick(mouseX, mouseY)
            return
        
        # Check if clicking on hotbar
        if self._handleHotbarClick(mouseX, mouseY, event.button):
            return
        
        # Check if clicking on panel
        if mouseX > WINDOW_WIDTH - PANEL_WIDTH:
            if event.button == 1:  # Left click
                self._handlePanelClick(mouseX, mouseY)
                self.assetManager.playClickSound()
            return
        
        if event.button == 1:  # Left click - place block
            # Alt+Click for eyedropper
            if mods & pygame.KMOD_ALT:
                self._eyedropperBlock(mouseX, mouseY)
                return
            
            # Measurement tool mode
            if self.measurementMode and self.hoveredCell:
                self._handleMeasurementClick()
                return
            
            # Replace mode - click to select source block, then it replaces all
            if self.replaceMode and self.hoveredCell:
                self._handleReplaceModeClick()
                return
            
            # Magic wand mode - select connected blocks of same type
            if self.magicWandMode and self.hoveredCell:
                self._handleMagicWandClick()
                return
            
            # Stamp/Clone mode - place stamp at click location
            if self.stampMode and self.hoveredCell:
                self._handleStampClick()
                return
            
            # Shift+Click for quick swap (replace block at position)
            if mods & pygame.KMOD_SHIFT:
                self._quickSwapBlock(mouseX, mouseY)
                return
            
            # Fill tool - Ctrl+Click for fill start/end
            if self.fillToolActive:
                self._handleFillToolClick(mouseX, mouseY)
                return
            
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
        if event.button == 1:  # Left click release
            self.draggingSlider = None  # Stop slider dragging
        if event.button == 2:  # Middle click release
            self.panning = False
    
    def _handleMouseMotion(self, event):
        """Handle mouse movement"""
        mouseX, mouseY = event.pos
        
        # Handle slider dragging
        if self.draggingSlider and pygame.mouse.get_pressed()[0]:
            # Calculate slider position
            panelX = WINDOW_WIDTH - PANEL_WIDTH
            sliderWidth = PANEL_WIDTH - 2 * ICON_MARGIN - 30
            labelWidth = 55
            trackWidth = sliderWidth - labelWidth - 50
            trackX = panelX + ICON_MARGIN + 10 + labelWidth
            
            # Calculate new volume from mouse X position
            relX = mouseX - trackX
            newVolume = max(0.0, min(1.0, relX / trackWidth))
            self._setVolume(self.draggingSlider, newVolume)
            return
        
        # Check panel hover
        self.panelHovered = mouseX > WINDOW_WIDTH - PANEL_WIDTH
        
        # Handle panning
        if self.panning:
            dx = mouseX - self.panStartX
            dy = mouseY - self.panStartY
            if self.smoothCameraEnabled:
                # Update target offset for smooth following
                self.targetOffsetX += dx
                self.targetOffsetY += dy
            else:
                # Direct camera movement
                self.renderer.offsetX += dx
                self.renderer.offsetY += dy
            self.panStartX = mouseX
            self.panStartY = mouseY
            return
        
        # Update hovered cell
        if not self.panelHovered:
            self._updateHoveredCell(mouseX, mouseY)
            self.hoveredPanelBlock = None
        else:
            self.hoveredCell = None
            self.hoveredFace = None
            # Update panel hover
            self._updatePanelHover(mouseX, mouseY)
    
    def _handleKeyDown(self, event):
        """Handle keyboard input"""
        mods = pygame.key.get_mods()
        
        # If search is active, handle text input
        if self.searchActive:
            if event.key == pygame.K_ESCAPE:
                self.searchActive = False
                self.searchQuery = ""
                self.searchResults = []
                return
            elif event.key == pygame.K_RETURN:
                # Select first search result if any
                if self.searchResults:
                    self.selectedBlock = self.searchResults[0]
                    self._addToRecentBlocks(self.selectedBlock)
                    # Add to search history
                    if self.searchQuery and self.searchQuery not in self.searchHistory:
                        self.searchHistory.insert(0, self.searchQuery)
                        self.searchHistory = self.searchHistory[:self.maxSearchHistory]
                    # Auto-scroll panel to show selected block
                    self._scrollToBlock(self.selectedBlock)
                self.searchActive = False
                self.searchQuery = ""
                self.searchResults = []
                return
            elif event.key == pygame.K_BACKSPACE:
                self.searchQuery = self.searchQuery[:-1]
                self._updateSearchResults()
                return
            elif event.unicode and event.unicode.isprintable():
                self.searchQuery += event.unicode.lower()
                self._updateSearchResults()
                return
        
        if event.key == pygame.K_ESCAPE:
            # Close menus in order
            if self.historyPanelOpen:
                self.historyPanelOpen = False
            elif self.settingsMenuOpen:
                self.settingsMenuOpen = False
            elif self.showShortcutsPanel:
                self.showShortcutsPanel = False
            elif self.blueprintMode:
                self.blueprintMode = False
                self.blueprintBlocks.clear()
            elif self.fillToolActive:
                self.fillToolActive = False
                self.fillStart = None
            else:
                self.running = False
        
        # Hotbar selection (1-9 for primary, Shift+1-9 for secondary)
        elif event.key in [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5, 
                           pygame.K_6, pygame.K_7, pygame.K_8, pygame.K_9]:
            slot = event.key - pygame.K_1  # 0-8
            if mods & pygame.KMOD_SHIFT:
                # Secondary hotbar (Shift+1-9)
                if slot < len(self.hotbar2):
                    self.selectedBlock = self.hotbar2[slot]
                    self.assetManager.playClickSound()
            else:
                # Primary hotbar (1-9)
                self.hotbarSelectedSlot = slot
                if slot < len(self.hotbar):
                    self.selectedBlock = self.hotbar[slot]
                    self.assetManager.playClickSound()
        
        # Search (Ctrl+F)
        elif event.key == pygame.K_f and mods & pygame.KMOD_CTRL and not (mods & pygame.KMOD_SHIFT):
            self.searchActive = True
            self.searchQuery = ""
            self.searchResults = []
        
        # 3D Flood Fill (Ctrl+Shift+F) - fill enclosed air space
        elif event.key == pygame.K_f and mods & pygame.KMOD_CTRL and mods & pygame.KMOD_SHIFT:
            if self.hoveredCell:
                x, y, z = self.hoveredCell
                # Fill at hover position (air block)
                if self.world.getBlock(x, y, z) == BlockType.AIR:
                    filled = self._floodFill3D(x, y, z, self.selectedBlock)
                    self.tooltipText = f"Filled {filled} blocks with {self.selectedBlock.name}"
                    self.tooltipTimer = 2000
                    self.assetManager.playPlaceSound()
                else:
                    self.tooltipText = "Point at empty space to flood fill"
                    self.tooltipTimer = 1500
        
        # Settings menu (Ctrl+,)
        elif event.key == pygame.K_COMMA and mods & pygame.KMOD_CTRL:
            self.settingsMenuOpen = not self.settingsMenuOpen
        
        # Undo history panel (Ctrl+H)
        elif event.key == pygame.K_h and mods & pygame.KMOD_CTRL:
            self.historyPanelOpen = not self.historyPanelOpen
        
        # Toggle coordinates display
        elif event.key == pygame.K_F3:
            self.showCoordinates = not self.showCoordinates
        
        # Toggle grid (F4 or G)
        elif event.key == pygame.K_F4 or event.key == pygame.K_g:
            self.showGrid = not self.showGrid
        
        # Mirror mode toggle
        elif event.key == pygame.K_m:
            if mods & pygame.KMOD_SHIFT:
                self.mirrorModeY = not self.mirrorModeY
                print(f"Mirror Y: {'ON' if self.mirrorModeY else 'OFF'}")
            else:
                self.mirrorModeX = not self.mirrorModeX
                print(f"Mirror X: {'ON' if self.mirrorModeX else 'OFF'}")
        
        # Layer view toggle
        elif event.key == pygame.K_PERIOD:  # > key (without shift is .)
            if self.layerViewEnabled:
                self.currentViewLayer = min(self.currentViewLayer + 1, GRID_HEIGHT - 1)
        elif event.key == pygame.K_COMMA:  # < key (without shift is ,)
            if self.layerViewEnabled and not (mods & pygame.KMOD_CTRL):  # Not Ctrl+, for settings
                self.currentViewLayer = max(self.currentViewLayer - 1, 0)
        elif event.key == pygame.K_SLASH:  # / key - toggle layer view
            self.layerViewEnabled = not self.layerViewEnabled
            if self.layerViewEnabled:
                self.currentViewLayer = self.currentBuildHeight
        
        # View rotation (Q/E keys)
        elif event.key == pygame.K_q:
            # Rotate view counter-clockwise
            self._rotateViewAndRecenter(-1)
        elif event.key == pygame.K_e:
            # Rotate view clockwise
            self._rotateViewAndRecenter(1)
        
        # Fill tool (F key, without ctrl)
        elif event.key == pygame.K_f and not (mods & pygame.KMOD_CTRL):
            self.fillToolActive = not self.fillToolActive
            if self.fillToolActive:
                self.fillStart = None
                self.tooltipText = "Fill Tool: Click start point"
                self.tooltipTimer = 2000
            else:
                self.fillStart = None
        
        # Replace tool (Ctrl+R)
        elif event.key == pygame.K_r and mods & pygame.KMOD_CTRL:
            if self.hoveredCell:
                x, y, z = self.hoveredCell
                # Find the block at or below hover
                for checkZ in range(z, -1, -1):
                    blockType = self.world.getBlock(x, y, checkZ)
                    if blockType != BlockType.AIR:
                        # Replace all blocks of this type with selected block
                        self._replaceBlocks(blockType, self.selectedBlock)
                        break
        
        # Blueprint mode
        elif event.key == pygame.K_b and mods & pygame.KMOD_CTRL:
            self.blueprintMode = not self.blueprintMode
            if not self.blueprintMode:
                # Apply blueprint
                for pos, blockType in self.blueprintBlocks.items():
                    self._placeBlockWithUndo(pos[0], pos[1], pos[2], blockType)
                self.blueprintBlocks.clear()
        
        elif event.key == pygame.K_h:
            self.structurePlacementMode = True
            self.selectedStructure = "house"
            print("House placement mode - click to place")
        
        elif event.key == pygame.K_t:
            # If tutorial is visible and on Structures panel, place a demo structure
            if self.tutorialScreen.visible:
                step = TutorialScreen.TUTORIAL_STEPS[self.tutorialScreen.currentStep]
                if "Structures" in step.get("title", ""):
                    # Place a watchtower at center of world
                    structure = PREMADE_STRUCTURES.get("watch_tower")
                    if structure and structure.get("blocks"):
                        centerX = GRID_WIDTH // 2 - 3
                        centerY = GRID_DEPTH // 2 - 3
                        centerZ = 3  # Place on elevated terrain
                        for x, y, z, blockType in structure["blocks"]:
                            placeX = x + centerX
                            placeY = y + centerY
                            placeZ = z + centerZ
                            if 0 <= placeX < GRID_WIDTH and 0 <= placeY < GRID_DEPTH and 0 <= placeZ < GRID_HEIGHT:
                                self.world.setBlock(placeX, placeY, placeZ, blockType)
                        self.assetManager.playSound("stone")
                        print("Tutorial: Placed watchtower structure")
                    return
            # Normal tree placement mode
            self.structurePlacementMode = True
            self.selectedStructure = "tree"
            print("Tree placement mode - click to place")
        
        elif event.key == pygame.K_c:
            if not (mods & pygame.KMOD_CTRL):  # Plain C to clear
                self.world.clear()
                if hasattr(self, 'liquidSpriteCache'):
                    self.liquidSpriteCache.clear()
                self._createInitialFloor()
                self.assetManager.playSound("stone")
                print("World cleared")
        
        elif event.key == pygame.K_l:
            # Toggle liquid flow simulation
            self.liquidFlowEnabled = not self.liquidFlowEnabled
            state = "enabled" if self.liquidFlowEnabled else "disabled"
            print(f"Liquid flow {state}")
        
        elif event.key == pygame.K_k:
            # Clear all liquids (water and lava) from the world
            self._clearAllLiquids()
        
        elif event.key == pygame.K_r:
            if not (mods & pygame.KMOD_CTRL):
                # Rotate preview or hovered block
                blockDef = BLOCK_DEFINITIONS.get(self.selectedBlock)
                if blockDef and (blockDef.isStair or blockDef.isDoor):
                    self.previewFacing = Facing((self.previewFacing.value + 1) % 4)
                    print(f"Preview facing: {self.previewFacing.name}")
                else:
                    self._rotateHoveredBlock()
        
        elif event.key == pygame.K_f:
            # Toggle slab position (top/bottom) for preview or existing block
            blockDef = BLOCK_DEFINITIONS.get(self.selectedBlock)
            if blockDef and blockDef.isSlab:
                # Toggle preview slab position
                if self.previewSlabPosition == SlabPosition.BOTTOM:
                    self.previewSlabPosition = SlabPosition.TOP
                else:
                    self.previewSlabPosition = SlabPosition.BOTTOM
                print(f"Preview slab: {self.previewSlabPosition.name}")
            else:
                # Try to toggle existing slab
                self._toggleSlabPosition()
        
        elif event.key == pygame.K_s and mods & pygame.KMOD_CTRL:
            # Save build (Ctrl+S)
            self._saveBuilding()
            self.assetManager.playClickSound()
        
        elif event.key == pygame.K_o and mods & pygame.KMOD_CTRL:
            # Load build (Ctrl+O) - loads most recent save
            saveFiles = self._getSaveFiles()
            if saveFiles:
                self._loadBuilding(saveFiles[0])
                self.assetManager.playClickSound()
            else:
                print("No saved builds found")
        
        elif event.key == pygame.K_SLASH and mods & pygame.KMOD_SHIFT:
            # Toggle shortcuts panel (? key = Shift+/)
            self.showShortcutsPanel = not self.showShortcutsPanel
            self.assetManager.playClickSound()
        
        # Center view on hovered cell/selection (Home key)
        elif event.key == pygame.K_HOME:
            self._centerOnHoveredOrGrid()
            self.assetManager.playClickSound()
        
        # X-Ray mode toggle (X key)
        elif event.key == pygame.K_x and not (mods & pygame.KMOD_CTRL):
            self.xrayEnabled = not self.xrayEnabled
            state = "ON" if self.xrayEnabled else "OFF"
            self.tooltipText = f"X-Ray Mode: {state}"
            self.tooltipTimer = 1500
        
        # Brush size cycle (B key)
        elif event.key == pygame.K_b and not (mods & pygame.KMOD_CTRL):
            currentIdx = self.brushSizes.index(self.brushSize)
            self.brushSize = self.brushSizes[(currentIdx + 1) % len(self.brushSizes)]
            self.tooltipText = f"Brush Size: {self.brushSize}x{self.brushSize}"
            self.tooltipTimer = 1500
            self.assetManager.playClickSound()
            self.assetManager.playClickSound()
        
        # Measurement tool toggle (M key)
        elif event.key == pygame.K_m and not (mods & pygame.KMOD_CTRL):
            self.measurementMode = not self.measurementMode
            if self.measurementMode:
                self.measurePoint1 = None
                self.measurePoint2 = None
                self.tooltipText = "Measurement Mode: Click two points to measure"
            else:
                self.measurePoint1 = None
                self.measurePoint2 = None
                self.tooltipText = "Measurement Mode: OFF"
            self.tooltipTimer = 1500
            self.assetManager.playClickSound()
        
        # Toggle favorite for selected block (Ctrl+D)
        elif event.key == pygame.K_d and mods & pygame.KMOD_CTRL:
            if self.selectedBlock != BlockType.AIR:
                self._toggleFavorite(self.selectedBlock)
                self.assetManager.playClickSound()
        
        # Toggle minimap (Tab key)
        elif event.key == pygame.K_TAB and not (mods & pygame.KMOD_CTRL):
            self.showMinimap = not self.showMinimap
            state = "ON" if self.showMinimap else "OFF"
            self.tooltipText = f"Minimap: {state}"
            self.tooltipTimer = 1500
        
        # Replace mode (Ctrl+R)
        elif event.key == pygame.K_r and mods & pygame.KMOD_CTRL:
            self.replaceMode = not self.replaceMode
            if self.replaceMode:
                self.replaceSourceBlock = None
                self.tooltipText = "Replace Mode: Click source block to replace"
            else:
                self.replaceSourceBlock = None
                self.tooltipText = "Replace Mode: OFF"
            self.tooltipTimer = 2000
            self.assetManager.playClickSound()
        
        # Radial symmetry cycle (Ctrl+Y cycles 0->4->8->0)
        elif event.key == pygame.K_t and mods & pygame.KMOD_CTRL:
            if self.radialSymmetry == 0:
                self.radialSymmetry = 4
                self.tooltipText = "Radial Symmetry: 4-way"
            elif self.radialSymmetry == 4:
                self.radialSymmetry = 8
                self.tooltipText = "Radial Symmetry: 8-way"
            else:
                self.radialSymmetry = 0
                self.tooltipText = "Radial Symmetry: OFF"
            self.tooltipTimer = 1500
            self.assetManager.playClickSound()
        
        # Magic Wand tool (W key)
        elif event.key == pygame.K_w and not (mods & pygame.KMOD_CTRL):
            self.magicWandMode = not self.magicWandMode
            if self.magicWandMode:
                self.magicWandSelection.clear()
                self.tooltipText = "Magic Wand: Click a block to select connected"
            else:
                self.magicWandSelection.clear()
                self.tooltipText = "Magic Wand: OFF"
            self.tooltipTimer = 1500
            self.assetManager.playClickSound()
        
        # Clone/Stamp tool (P key) - use clipboard content as stamp
        elif event.key == pygame.K_p and not (mods & pygame.KMOD_CTRL):
            self._toggleStampMode()
        
        # ============ NEW KEYBINDINGS ============
        
        elif event.key == pygame.K_z and mods & pygame.KMOD_CTRL:
            # Undo (Ctrl+Z)
            if self.undoManager.can_undo():
                cmd = self.undoManager.undo()
                if cmd:
                    print(f"Undo: {cmd.get_description()}")
                    self.assetManager.playClickSound()
        
        elif event.key == pygame.K_y and mods & pygame.KMOD_CTRL:
            # Redo (Ctrl+Y)
            if self.undoManager.can_redo():
                cmd = self.undoManager.redo()
                if cmd:
                    print(f"Redo: {cmd.get_description()}")
                    self.assetManager.playClickSound()
        
        elif event.key == pygame.K_F2:
            # Screenshot
            self._takeScreenshot()
        
        elif event.key == pygame.K_F5:
            # Quick Save Slot 1
            self._quickSave(1)
        elif event.key == pygame.K_F6:
            # Quick Save Slot 2
            self._quickSave(2)
        elif event.key == pygame.K_F7:
            # Quick Save Slot 3
            self._quickSave(3)
        elif event.key == pygame.K_F8:
            # Quick Save Slot 4
            self._quickSave(4)
        
        elif event.key == pygame.K_F9:
            # Quick Load Slot 1
            self._quickLoad(1)
        elif event.key == pygame.K_F10:
            # Quick Load Slot 2
            self._quickLoad(2)
        elif event.key == pygame.K_F11:
            # Quick Load Slot 3
            self._quickLoad(3)
        elif event.key == pygame.K_F12:
            # Quick Load Slot 4
            self._quickLoad(4)
        
        # Selection box tool
        elif event.key == pygame.K_b and mods & pygame.KMOD_CTRL:
            # Start selection mode (Ctrl+B)
            self._startSelection()
        
        elif event.key == pygame.K_ESCAPE and self.selectionActive:
            # Cancel selection
            self._clearSelection()
        
        elif event.key == pygame.K_DELETE and self.selectionActive:
            # Delete selected blocks
            self._deleteSelection()
        
        elif event.key == pygame.K_DELETE and self.magicWandSelection:
            # Delete magic wand selected blocks
            self._deleteMagicWandSelection()
        
        elif event.key == pygame.K_c and mods & pygame.KMOD_CTRL and self.selectionActive:
            # Copy selection (Ctrl+C)
            self._copySelection()
        
        elif event.key == pygame.K_v and mods & pygame.KMOD_CTRL:
            # Paste clipboard (Ctrl+V)
            self._pasteSelection()
        
        elif event.key == pygame.K_a and mods & pygame.KMOD_CTRL:
            # Fill selection with current block (Ctrl+A)
            if self.selectionActive:
                self._fillSelection(self.selectedBlock)
        
        elif event.key == pygame.K_h and mods & pygame.KMOD_CTRL:
            # Hollow selection with current block (Ctrl+H)
            if self.selectionActive:
                self._hollowSelection(self.selectedBlock)
        
        elif event.key == pygame.K_LEFTBRACKET:
            # Rotate clipboard counter-clockwise ([)
            self._rotateClipboard(clockwise=False)
        
        elif event.key == pygame.K_RIGHTBRACKET:
            # Rotate clipboard clockwise (])
            self._rotateClipboard(clockwise=True)
    
    def _handlePanelClick(self, mouseX: int, mouseY: int):
        """Handle click on the inventory panel with three main dropdown buttons"""
        # Check settings gear button first (fixed position at top right)
        if hasattr(self, 'settingsGearRect') and self.settingsGearRect.collidepoint(mouseX, mouseY):
            self.settingsMenuOpen = not self.settingsMenuOpen
            return
        
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
                if category == "Problematic" or category == "Experimental":
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
                    
                    # Check collapse button click
                    collapseBtnWidth = PANEL_WIDTH - 2 * ICON_MARGIN - 30
                    collapseBtnHeight = 22
                    collapseBtnX = ICON_MARGIN + 15
                    collapseBtnY = currentY
                    
                    if (collapseBtnX <= panelX <= collapseBtnX + collapseBtnWidth and 
                        collapseBtnY <= panelY <= collapseBtnY + collapseBtnHeight):
                        self.expandedCategories[category] = False
                        return
                    
                    currentY += collapseBtnHeight + 5
            
            currentY += 5
        
        # ===== CHECK PROBLEMS MAIN BUTTON =====
        problemsTop = currentY
        problemsBottom = currentY + mainButtonHeight
        
        if problemsTop <= panelY <= problemsBottom and ICON_MARGIN <= panelX <= PANEL_WIDTH - ICON_MARGIN:
            self.problemsExpanded = not self.problemsExpanded
            return
        
        currentY += mainButtonHeight + 5
        
        # Check experimental blocks if expanded
        if self.problemsExpanded:
            experimentalBlocks = BLOCK_CATEGORIES.get("Experimental", [])
            blocksStartY = currentY + 2
            
            for i, blockType in enumerate(experimentalBlocks):
                row = i // ICONS_PER_ROW
                col = i % ICONS_PER_ROW
                
                btnX = ICON_MARGIN + col * (slotSize + 4)
                btnY = blocksStartY + row * (slotSize + 4)
                
                if btnX <= panelX <= btnX + slotSize and btnY <= panelY <= btnY + slotSize:
                    self.selectedBlock = blockType
                    return
            
            numRows = (len(experimentalBlocks) + ICONS_PER_ROW - 1) // ICONS_PER_ROW
            currentY += numRows * (slotSize + 4) + 10
        
        # ===== CHECK FEATURES MAIN BUTTON =====
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
            
            # Check Show Tutorial button
            if dimY <= panelY <= dimY + 30 and ICON_MARGIN + 10 <= panelX <= PANEL_WIDTH - ICON_MARGIN - 10:
                self.tutorialScreen.show()
                return
            dimY += 35
            
            # Check Rain toggle button (only in Overworld)
            if dimY <= panelY <= dimY + 30 and ICON_MARGIN + 10 <= panelX <= PANEL_WIDTH - ICON_MARGIN - 10:
                self._toggleRain()
                return
            dimY += 35
            
            # Check Snow toggle button (only in Overworld)
            if dimY <= panelY <= dimY + 30 and ICON_MARGIN + 10 <= panelX <= PANEL_WIDTH - ICON_MARGIN - 10:
                self._toggleSnow()
                return
            dimY += 35
            
            # Check Sun/Moon toggle button (only in Overworld)
            if dimY <= panelY <= dimY + 30 and ICON_MARGIN + 10 <= panelX <= PANEL_WIDTH - ICON_MARGIN - 10:
                self._toggleCelestial()
                return
            dimY += 35
            
            # Check Clouds toggle button
            if dimY <= panelY <= dimY + 30 and ICON_MARGIN + 10 <= panelX <= PANEL_WIDTH - ICON_MARGIN - 10:
                self._toggleClouds()
                return
            dimY += 35
            
            # Check Lighting toggle button
            if dimY <= panelY <= dimY + 30 and ICON_MARGIN + 10 <= panelX <= PANEL_WIDTH - ICON_MARGIN - 10:
                self._toggleLighting()
                return
            dimY += 35
            
            # Check Horror Rain button (black button at end)
            if dimY <= panelY <= dimY + 30 and ICON_MARGIN + 10 <= panelX <= PANEL_WIDTH - ICON_MARGIN - 10:
                self._toggleHorrorRain()
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
        
        # Check structure thumbnail grid if expanded
        if self.structuresExpanded:
            PREVIEW_WIDTH = 115
            PREVIEW_HEIGHT = 75
            PREVIEWS_PER_ROW = 2
            PREVIEW_MARGIN = 6
            PREVIEW_PADDING = 8
            
            structureY = currentY + 2
            structureList = list(PREMADE_STRUCTURES.items())
            
            for idx, (structName, structData) in enumerate(structureList):
                row = idx // PREVIEWS_PER_ROW
                col = idx % PREVIEWS_PER_ROW
                
                # Calculate thumbnail position
                thumbX = PREVIEW_PADDING + col * (PREVIEW_WIDTH + PREVIEW_MARGIN)
                thumbY = structureY + row * (PREVIEW_HEIGHT + PREVIEW_MARGIN)
                
                # Check if click is within this thumbnail
                if (thumbX <= panelX <= thumbX + PREVIEW_WIDTH and 
                    thumbY <= panelY <= thumbY + PREVIEW_HEIGHT):
                    self.structurePlacementMode = True
                    self.selectedStructure = structName
                    print(f"{structData['name']} placement mode - click to place")
                    return
            
            # Calculate total height of structure grid
            numRows = (len(structureList) + PREVIEWS_PER_ROW - 1) // PREVIEWS_PER_ROW
            currentY = structureY + numRows * (PREVIEW_HEIGHT + PREVIEW_MARGIN) + 5
        
        # ===== CHECK SAVE/LOAD BUTTONS (using stored rects from render) =====
        if hasattr(self, 'saveBtnRect') and self.saveBtnRect.collidepoint(mouseX, mouseY):
            self._saveBuilding()
            self.assetManager.playClickSound()
            return
        if hasattr(self, 'loadBtnRect') and self.loadBtnRect.collidepoint(mouseX, mouseY):
            self._openLoadDialog()
            self.assetManager.playClickSound()
            return
        
        # ===== VIEW INDICATOR (no buttons - use Q/E hotkeys) =====
        currentY += 25
        
        # Skip volume header
        currentY += 22
        
        # Volume slider click handling using stored Y positions from render
        sliderWidth = PANEL_WIDTH - 2 * ICON_MARGIN - 30
        labelWidth = 55
        trackWidth = sliderWidth - labelWidth - 50
        relTrackX = ICON_MARGIN + 10 + labelWidth  # Relative to panel left
        relMuteX = relTrackX + trackWidth + 30
        muteSize = 16
        
        # Check Music volume slider (use stored Y from render)
        if hasattr(self, 'musicSliderY'):
            sliderY = self.musicSliderY
            # Music mute button
            if relMuteX <= panelX <= relMuteX + muteSize and sliderY <= mouseY <= sliderY + 20:
                self.musicMuted = not getattr(self, 'musicMuted', False)
                if self.musicMuted:
                    pygame.mixer.music.set_volume(0)
                else:
                    pygame.mixer.music.set_volume(self.musicVolume)
                self.assetManager.playClickSound()
                return
            # Music slider track - start dragging
            if relTrackX <= panelX <= relTrackX + trackWidth and sliderY <= mouseY <= sliderY + 20:
                self.draggingSlider = "music"
                clickX = panelX - relTrackX
                newVolume = max(0.0, min(1.0, clickX / trackWidth))
                self._setVolume("music", newVolume)
                return
        
        # Check Ambient volume slider
        if hasattr(self, 'ambientSliderY'):
            sliderY = self.ambientSliderY
            # Ambient mute button
            if relMuteX <= panelX <= relMuteX + muteSize and sliderY <= mouseY <= sliderY + 20:
                self.ambientMuted = not getattr(self, 'ambientMuted', False)
                self.assetManager.playClickSound()
                return
            # Ambient slider track - start dragging
            if relTrackX <= panelX <= relTrackX + trackWidth and sliderY <= mouseY <= sliderY + 20:
                self.draggingSlider = "ambient"
                clickX = panelX - relTrackX
                newVolume = max(0.0, min(1.0, clickX / trackWidth))
                self._setVolume("ambient", newVolume)
                return
        
        # Check Effects volume slider
        if hasattr(self, 'effectsSliderY'):
            sliderY = self.effectsSliderY
            # Effects mute button
            if relMuteX <= panelX <= relMuteX + muteSize and sliderY <= mouseY <= sliderY + 20:
                self.effectsMuted = not getattr(self, 'effectsMuted', False)
                self.assetManager.playClickSound()
                return
            # Effects slider track - start dragging
            if relTrackX <= panelX <= relTrackX + trackWidth and sliderY <= mouseY <= sliderY + 20:
                self.draggingSlider = "effects"
                clickX = panelX - relTrackX
                newVolume = max(0.0, min(1.0, clickX / trackWidth))
                self._setVolume("effects", newVolume)
                return
        
        # Check hotkeys expand button
        if hasattr(self, 'hotkeysExpandBtnRect') and self.hotkeysExpandBtnRect:
            if self.hotkeysExpandBtnRect.collidepoint(mouseX, mouseY):
                self.hotkeysExpanded = not self.hotkeysExpanded
                self.assetManager.playClickSound()
                return
    
    def _detectBlockFace(self, mouseX: int, mouseY: int, blockX: int, blockY: int, blockZ: int) -> Optional[str]:
        """
        Detect which face of an isometric block was clicked.
        
        The sprite is drawn with top-left at (screenX - 32, screenY).
        The top vertex of the diamond is at (screenX, screenY).
        
        Face polygons (relative to top vertex at 0,0):
        - TOP: (0, 0) → (32, 16) → (0, 32) → (-32, 16)
        - LEFT: (-32, 16) → (0, 32) → (0, 70) → (-32, 54)
        - RIGHT: (0, 32) → (32, 16) → (32, 54) → (0, 70)
        
        Returns:
            'top', 'left', 'right', or None if not on this block
        """
        # Get screen position of the block (top vertex of the isometric tile)
        screenX, screenY = self.renderer.worldToScreen(blockX, blockY, blockZ)
        
        # Calculate relative position from the top vertex
        relX = mouseX - screenX
        relY = mouseY - screenY
        
        halfW = TILE_WIDTH // 2  # 32
        halfH = TILE_HEIGHT // 2  # 16
        totalH = TILE_HEIGHT + BLOCK_HEIGHT  # 70
        
        # Small tolerance for edge detection (makes clicking more forgiving)
        tolerance = 2
        
        # Check bounds first with tolerance
        if relX < -halfW - tolerance or relX > halfW + tolerance:
            return None
        if relY < -tolerance or relY > totalH + tolerance:
            return None
        
        # Check if in TOP face (diamond region, y from 0 to TILE_HEIGHT)
        if relY < TILE_HEIGHT:
            # Diamond test with tolerance
            if relY < halfH:
                edgeLimit = relY * 2 + tolerance
            else:
                edgeLimit = (TILE_HEIGHT - relY) * 2 + tolerance
            
            if -edgeLimit <= relX <= edgeLimit:
                return 'top'
            return None
        
        # Below the top diamond - in the side faces region
        # relY is now between TILE_HEIGHT (32) and totalH (70)
        sideY = relY - TILE_HEIGHT  # 0 to BLOCK_HEIGHT (38)
        
        # For the side faces, check with tolerance
        if relX < tolerance:  # Left side (including small tolerance on the dividing line)
            # Potentially on left face
            # Left face top edge: from (-32, 16) to (0, 32)
            topEdgeY = halfH + (relX + halfW) * 0.5 - tolerance
            # Bottom edge: from (-32, 54) to (0, 70)
            bottomEdgeY = (halfH + BLOCK_HEIGHT) + (relX + halfW) * 0.5 + tolerance
            
            if topEdgeY <= relY <= bottomEdgeY:
                return 'left'
        
        if relX > -tolerance:  # Right side (including small tolerance on the dividing line)
            # Potentially on right face
            # Right face top edge: from (0, 32) to (32, 16)
            topEdgeY = TILE_HEIGHT - relX * 0.5 - tolerance
            # Bottom edge: from (0, 70) to (32, 54)
            bottomEdgeY = totalH - relX * 0.5 + tolerance
            
            if topEdgeY <= relY <= bottomEdgeY:
                return 'right'
        
        return None
    
    def _updateHoveredCell(self, mouseX: int, mouseY: int):
        """Update the currently hovered cell based on face detection for 3D building"""
        # We need to find which block face the mouse is over
        # The challenge: side faces of blocks behind can overlap with top faces in front
        # Strategy: check blocks in painter's order (furthest first) and find the first hit
        
        bestHit = None  # (sortKey, blockX, blockY, blockZ, face, distance)
        viewRot = self.renderer.viewRotation
        
        # Check blocks at each Z level, using screenToWorld at that level for accuracy
        # Increased search range for better accuracy at edges
        searchRange = 3
        for z in range(GRID_HEIGHT - 1, -1, -1):
            # Get approximate world position at this Z level
            baseX, baseY = self.renderer.screenToWorld(mouseX, mouseY, z)
            
            # Check blocks in a region around this position
            for dx in range(-searchRange, searchRange + 1):
                for dy in range(-searchRange, searchRange + 1):
                    bx = baseX + dx
                    by = baseY + dy
                    
                    if not self.world.isInBounds(bx, by, z):
                        continue
                    if self.world.getBlock(bx, by, z) == BlockType.AIR:
                        continue
                    
                    # Check if mouse is on this block's face
                    face = self._detectBlockFace(mouseX, mouseY, bx, by, z)
                    if face is None:
                        continue
                    
                    # Calculate screen distance from mouse to block center for tie-breaking
                    blockScreenX, blockScreenY = self.renderer.worldToScreen(bx, by, z)
                    # Adjust to center of block face
                    if face == 'top':
                        centerY = blockScreenY + TILE_HEIGHT // 2
                    else:
                        centerY = blockScreenY + TILE_HEIGHT + BLOCK_HEIGHT // 2
                    dist = ((mouseX - blockScreenX) ** 2 + (mouseY - centerY) ** 2) ** 0.5
                    
                    # Use painter's algorithm sort key (higher = in front)
                    # Must match _renderWorld sort key for correct detection
                    if viewRot == 0:
                        sortKey = bx + by + z
                    elif viewRot == 1:
                        sortKey = -by + bx + z
                    elif viewRot == 2:
                        sortKey = -bx - by + z
                    elif viewRot == 3:
                        sortKey = by - bx + z
                    else:
                        sortKey = bx + by + z
                    
                    # Prefer blocks that are in front (higher sortKey)
                    # For ties, prefer blocks closer to mouse
                    if bestHit is None:
                        bestHit = (sortKey, bx, by, z, face, dist)
                    elif sortKey > bestHit[0]:
                        bestHit = (sortKey, bx, by, z, face, dist)
                    elif sortKey == bestHit[0] and dist < bestHit[5]:
                        # Same depth - prefer closer to mouse
                        bestHit = (sortKey, bx, by, z, face, dist)
        
        if bestHit:
            _, bx, by, bz, face, _ = bestHit
            self.hoveredFace = face
            
            # Remap face directions based on view rotation
            # In default view (0): left=+Y, right=+X
            # The visual "left" and "right" sides change as we rotate
            if face == 'top':
                # Place block on top of this block
                if bz + 1 < GRID_HEIGHT:
                    self.hoveredCell = (bx, by, bz + 1)
                else:
                    self.hoveredCell = (bx, by, bz)
            elif face == 'left':
                # "Left" face placement direction changes with view rotation
                if viewRot == 0:
                    newX, newY = bx, by + 1
                elif viewRot == 1:
                    newX, newY = bx - 1, by
                elif viewRot == 2:
                    newX, newY = bx, by - 1
                elif viewRot == 3:
                    newX, newY = bx + 1, by
                else:
                    newX, newY = bx, by + 1
                    
                if self.world.isInBounds(newX, newY, bz) and self.world.getBlock(newX, newY, bz) == BlockType.AIR:
                    self.hoveredCell = (newX, newY, bz)
                else:
                    # Fallback to top
                    if bz + 1 < GRID_HEIGHT:
                        self.hoveredCell = (bx, by, bz + 1)
                    else:
                        self.hoveredCell = (bx, by, bz)
            elif face == 'right':
                # "Right" face placement direction changes with view rotation
                if viewRot == 0:
                    newX, newY = bx + 1, by
                elif viewRot == 1:
                    newX, newY = bx, by + 1
                elif viewRot == 2:
                    newX, newY = bx - 1, by
                elif viewRot == 3:
                    newX, newY = bx, by - 1
                else:
                    newX, newY = bx + 1, by
                    
                if self.world.isInBounds(newX, newY, bz) and self.world.getBlock(newX, newY, bz) == BlockType.AIR:
                    self.hoveredCell = (newX, newY, bz)
                else:
                    # Fallback to top
                    if bz + 1 < GRID_HEIGHT:
                        self.hoveredCell = (bx, by, bz + 1)
                    else:
                        self.hoveredCell = (bx, by, bz)
            return
        
        # No block found - default to ground level placement
        self.hoveredFace = None
        worldX, worldY = self.renderer.screenToWorld(mouseX, mouseY, 0)
        if self.world.isInBounds(worldX, worldY, 0):
            highestZ = self.world.getHighestBlock(worldX, worldY)
            targetZ = min(highestZ + 1, GRID_HEIGHT - 1)
            self.hoveredCell = (worldX, worldY, targetZ)
        else:
            self.hoveredCell = None
            self.hoveredFace = None
    
    def _placeBlockAtMouse(self, mouseX: int, mouseY: int):
        """Place a block at the mouse position with undo support"""
        if self.hoveredCell:
            x, y, z = self.hoveredCell
            
            # Check if in selection mode
            if self.selectionActive:
                if self._handleSelectionClick(x, y, z):
                    return  # Handled as selection click
            
            # Check layer view restriction
            if self.layerViewEnabled and z != self.currentViewLayer:
                return  # Don't place blocks outside current layer view
            
            # Calculate brush offset to center the brush on the clicked cell
            brushOffset = (self.brushSize - 1) // 2
            
            # Place blocks in brush area
            blocksPlacedCount = 0
            for bx in range(self.brushSize):
                for by in range(self.brushSize):
                    placeX = x - brushOffset + bx
                    placeY = y - brushOffset + by
                    
                    # Check bounds
                    if not (0 <= placeX < GRID_WIDTH and 0 <= placeY < GRID_DEPTH):
                        continue
                    
                    # For brush sizes > 1, find the appropriate Z level for each cell
                    if self.brushSize > 1:
                        placeZ = self.world.getHighestBlock(placeX, placeY) + 1
                        placeZ = min(placeZ, GRID_HEIGHT - 1)
                    else:
                        placeZ = z
                    
                    # Use undo-enabled placement
                    if self._placeBlockWithUndo(placeX, placeY, placeZ, self.selectedBlock):
                        blocksPlacedCount += 1
                        
                        # Mirror mode placement
                        if self.mirrorModeX or self.mirrorModeY:
                            self._placeWithMirror(placeX, placeY, placeZ, self.selectedBlock)
                        
                        # Radial symmetry placement
                        if self.radialSymmetry > 0:
                            self._placeWithRadialSymmetry(placeX, placeY, placeZ, self.selectedBlock)
                        
                        # Set properties for special blocks
                        blockDef = BLOCK_DEFINITIONS.get(self.selectedBlock)
                        if blockDef:
                            if blockDef.isDoor or blockDef.isStair or blockDef.isSlab:
                                props = BlockProperties(
                                    facing=self.previewFacing,
                                    isOpen=False,
                                    slabPosition=self.previewSlabPosition
                                )
                                self.world.setBlockProperties(placeX, placeY, placeZ, props)
            
            if blocksPlacedCount > 0:
                # Friday 13th horror - 13% chance blocks make no sound
                shouldPlaySound = True
                if self.horrorEnabled and hasattr(self, '_friday13th') and self._friday13th:
                    if random.random() < 0.13:
                        shouldPlaySound = False
                
                if shouldPlaySound:
                    self.assetManager.playBlockSound(self.selectedBlock, isPlace=True, worldPos=(x, y, z), effectsVolume=self.effectsVolume)
                self.blocksPlaced += blocksPlacedCount
                self._addToRecentBlocks(self.selectedBlock)
                self._trackBlockUsage(self.selectedBlock)  # Track usage statistics
                self._spawnPlacementParticles(x, y, z, self.selectedBlock)
                self.lightingDirty = True
    
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
        """Remove a block at the mouse position with undo support"""
        # First, try the hoveredCell approach - it already found the block
        if self.hoveredCell:
            x, y, z = self.hoveredCell
            # The hovered cell points to where we'd place a new block (one above the existing)
            # So check the block at z-1 first
            for checkZ in range(z, -1, -1):
                blockType = self.world.getBlock(x, y, checkZ)
                if blockType != BlockType.AIR:
                    # Get screen position for particles before removing
                    screenX, screenY = self.renderer.worldToScreen(x, y, checkZ)
                    
                    # Use undo-enabled removal
                    if self._removeBlockWithUndo(x, y, checkZ):
                        # Clean up liquid sprite cache
                        if hasattr(self, 'liquidSpriteCache') and (x, y, checkZ) in self.liquidSpriteCache:
                            del self.liquidSpriteCache[(x, y, checkZ)]
                        self.assetManager.playBlockSound(blockType, isPlace=False, worldPos=(x, y, checkZ), effectsVolume=self.effectsVolume)
                        
                        # Track statistics
                        self.blocksRemoved += 1
                        
                        # Mark lighting as dirty for recalculation
                        self.lightingDirty = True
                        
                        # Spawn breaking particles
                        self._spawnBlockParticles(screenX, screenY + TILE_HEIGHT // 2, blockType)
                        
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
                                self.blocksRemoved += 1
                                # Clean up liquid sprite cache
                                if hasattr(self, 'liquidSpriteCache') and (checkX, checkY, z) in self.liquidSpriteCache:
                                    del self.liquidSpriteCache[(checkX, checkY, z)]
                                self.assetManager.playBlockSound(blockType, isPlace=False, worldPos=(checkX, checkY, z), effectsVolume=self.effectsVolume)
                                
                                # Mark lighting as dirty for recalculation
                                self.lightingDirty = True
                                
                                # Spawn breaking particles
                                self._spawnBlockParticles(blockScreenX, blockScreenY + TILE_HEIGHT // 2, blockType)
                                
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
                    # Play the portal complete sound (endportal.ogg)
                    if "end_portal" in self.assetManager.sounds and self.assetManager.sounds["end_portal"]:
                        self.assetManager.sounds["end_portal"][0].play()
                    else:
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
        
        # Update fire ambient sound (crackling every ~5 seconds)
        self._updateFireAmbient(dt)
        
        # Update spawner particles
        self._updateSpawnerParticles(dt)
        
        # Update rain effects
        self._updateRain(dt)
        
        # Update horror rain effects
        self._updateHorrorRain(dt)
        
        # Update snow effects
        self._updateSnow(dt)
        
        # Update celestial cycle (sun/moon)
        self._updateCelestial(dt)
        
        # Update clouds
        self._updateClouds(dt)
        
        # Update block breaking particles
        self._updateBlockParticles(dt)
        
        # Update smooth camera movement
        self._updateSmoothCamera()
        
        # Update placement particles
        self._updatePlacementParticles()
        
        # Auto-save check
        self._autoSave()
        
        # Update tooltip timer
        if self.tooltipTimer > 0:
            self.tooltipTimer -= dt
        
        # Update music fade-in
        self._updateMusicFade(dt)
        
        # Update horror ambient system
        self._updateHorrorSystem(dt)
    
    def _updateLiquidFlow(self) -> None:
        """Process liquid flow updates with separate timing for water and lava"""
        # Skip if liquid flow is disabled
        if not self.liquidFlowEnabled:
            return
        
        currentTime = pygame.time.get_ticks()
        allChanges = []
        
        # Update water if enough time has passed
        if currentTime - self.lastWaterFlowTime >= self.waterFlowDelay:
            waterChanges = self.world.updateLiquids(BlockType.WATER, self.liquidUpdatesPerTick)
            allChanges.extend(waterChanges)
            self.lastWaterFlowTime = currentTime
        
        # Update lava if enough time has passed (slower)
        if currentTime - self.lastLavaFlowTime >= self.lavaFlowDelay:
            lavaChanges = self.world.updateLiquids(BlockType.LAVA, self.liquidUpdatesPerTick)
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
    
    def _updatePortalSound(self) -> None:
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
    
    def _updateFireAmbient(self, dt: int) -> None:
        """Play fire crackling sound every ~5 seconds if fire blocks exist"""
        import random
        
        # Update timer
        self.assetManager.fireAmbientTimer += dt
        
        if self.assetManager.fireAmbientTimer >= self.assetManager.fireAmbientInterval:
            self.assetManager.fireAmbientTimer = 0
            
            # Check if any fire blocks exist (FIRE or SOUL_FIRE)
            fireBlocks = []
            for (x, y, z), blockType in self.world.blocks.items():
                if blockType in (BlockType.FIRE, BlockType.SOUL_FIRE):
                    fireBlocks.append((x, y, z))
            
            if fireBlocks and "fire" in self.assetManager.sounds and self.assetManager.sounds["fire"]:
                # Pick a random fire block to be the sound source
                firePos = random.choice(fireBlocks)
                # Play fire crackling sound from that position
                self.assetManager.playSound("fire", firePos, self.effectsVolume)
    
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
                    # Spawn 4-8 particles per mob spawner
                    for _ in range(random.randint(4, 8)):
                        # Random position around the spawner
                        px = x + random.uniform(-0.4, 0.4)
                        py = y + random.uniform(-0.4, 0.4)
                        pz = z + random.uniform(0, 0.6)
                        
                        # Particle properties - orange/red flames
                        particle = {
                            "x": x, "y": y, "z": z,  # Block position for sorting
                            "px": px, "py": py, "pz": pz,  # Actual position
                            "vx": random.uniform(-0.02, 0.02),
                            "vy": random.uniform(-0.02, 0.02),
                            "vz": random.uniform(0.01, 0.04),  # Float upward
                            "life": random.randint(20, 40),
                            "color": random.choice([
                                (255, 80, 30),    # Deep orange flame
                                (255, 120, 50),   # Orange flame
                                (255, 180, 80),   # Yellow-orange
                                (255, 50, 20),    # Red-orange
                            ])
                        }
                        self.spawnerParticleList.append(particle)
                
                elif blockType == BlockType.TRIAL_SPAWNER:
                    # Spawn 4-8 particles per trial spawner - blue particles
                    for _ in range(random.randint(4, 8)):
                        # Random position around the spawner
                        px = x + random.uniform(-0.4, 0.4)
                        py = y + random.uniform(-0.4, 0.4)
                        pz = z + random.uniform(0, 0.6)
                        
                        # Particle properties - blue/cyan flames
                        particle = {
                            "x": x, "y": y, "z": z,  # Block position for sorting
                            "px": px, "py": py, "pz": pz,  # Actual position
                            "vx": random.uniform(-0.02, 0.02),
                            "vy": random.uniform(-0.02, 0.02),
                            "vz": random.uniform(0.01, 0.04),  # Float upward
                            "life": random.randint(20, 40),
                            "color": random.choice([
                                (50, 150, 255),   # Bright blue
                                (80, 200, 255),   # Cyan-blue
                                (100, 180, 255),  # Light blue
                                (30, 120, 220),   # Deep blue
                            ])
                        }
                        self.spawnerParticleList.append(particle)
        
        # Update existing particles
        for particle in self.spawnerParticleList:
            particle["life"] -= 1
            particle["px"] += particle["vx"]
            particle["py"] += particle["vy"]
            particle["pz"] += particle["vz"]
        # Remove dead particles efficiently
        self.spawnerParticleList = [p for p in self.spawnerParticleList if p["life"] > 0]
    
    def _clearAllLiquids(self):
        """Clear all water and lava blocks from the world to reduce lag"""
        removed = self.world.clearLiquids()
        
        # Clear liquid sprite cache
        if hasattr(self, 'liquidSpriteCache'):
            self.liquidSpriteCache.clear()
        
        # Play a satisfying water drain sound
        self.assetManager.playSound("water", effectsVolume=self.effectsVolume)
        
        print(f"Cleared {removed} liquid blocks")
    
    def _toggleRain(self):
        """Toggle rain on/off (only works in Overworld)"""
        if self.currentDimension != DIMENSION_OVERWORLD:
            return  # Rain only in Overworld
        
        # If snow is on, turn it off first
        if self.snowEnabled:
            self.snowEnabled = False
            self._stopSnow()
        
        self.rainEnabled = not self.rainEnabled
        
        if self.rainEnabled:
            # Start rain
            self._startRain()
        else:
            # Stop rain
            self._stopRain()
    
    def _startRain(self):
        """Initialize rain effects"""
        self.rainDrops = []
        self.rainSplashes = []
        self.thunderTimer = 0
        self.nextThunderTime = random.randint(5000, 15000)  # 5-15 seconds for first thunder
        self.lightningFlash = 0
        self.lightningBolt = []
        self.lightningBoltTimer = 0
        self.rainIntensity = 1.0
        self.rainIntensityTimer = 0
        self.rainIntensityTarget = 1.0
        
        # Create initial rain drops with slight angle
        for _ in range(150):  # 150 rain drops
            self.rainDrops.append({
                "x": random.randint(0, WINDOW_WIDTH),
                "y": random.randint(-WINDOW_HEIGHT, 0),
                "speed": random.randint(15, 25),
                "length": random.randint(10, 20),
                "angle": random.uniform(0.08, 0.15)  # Slight wind angle
            })
        
        # Rain sound: Use pre-loaded Sound (avoids loading stutter)
        self.rainSoundChannel = None
        if self.assetManager.relaxingRainSound:
            try:
                # Use pre-loaded Sound object to avoid loading delay/stutter
                self.rainSound = self.assetManager.relaxingRainSound
                self.rainSoundChannel = self.rainSound.play(loops=-1)  # Loop forever
                print("    Playing relaxing rain track (on sound channel)")
            except Exception as e:
                print(f"    Could not play rain track: {e}")
        
        # Thunder ambient: Use a dedicated channel that we control
        self.thunderAmbientChannel = None
        self.thunderAmbientTimer = 0
        self.nextThunderAmbientTime = random.randint(3000, 8000)  # First ambient 3-8 sec
    
    def _stopRain(self):
        """Stop rain effects"""
        self.rainDrops = []
        self.rainSplashes = []
        self.skyDarkness = 0
        self.lightningFlash = 0
        self.lightningBolt = []
        self.lightningBoltTimer = 0
        
        # Stop rain sound channel (not music)
        if self.rainSoundChannel:
            self.rainSoundChannel.stop()
            self.rainSoundChannel = None
        if hasattr(self, 'rainSound'):
            self.rainSound.stop()
        
        # Stop thunder ambient
        if self.thunderAmbientChannel:
            self.thunderAmbientChannel.stop()
            self.thunderAmbientChannel = None
    
    def _toggleHorrorRain(self):
        """Toggle horror rain (black rain with reversed/pitched sounds)"""
        # Stop normal rain/snow if active
        if self.rainEnabled:
            self.rainEnabled = False
            self._stopRain()
        if self.snowEnabled:
            self.snowEnabled = False
            self._stopSnow()
        
        self.horrorRainEnabled = not self.horrorRainEnabled
        
        if self.horrorRainEnabled:
            self._startHorrorRain()
        else:
            self._stopHorrorRain()
    
    def _startHorrorRain(self):
        """Initialize horror rain effects (black rain)"""
        self.horrorRainDrops = []
        self.skyDarkness = 180  # Very dark sky
        self.horrorLightningBolts = []
        self.horrorLightningTimer = 0
        self.horrorLightningFlash = 0
        self.nextHorrorLightningTime = random.randint(5000, 12000)  # First lightning 5-12 sec
        self.horrorBrightness = 100  # Screen gets brighter instead of darker
        
        # Create initial black rain drops
        for _ in range(200):  # More drops for ominous feel
            self.horrorRainDrops.append({
                "x": random.randint(0, WINDOW_WIDTH),
                "y": random.randint(-WINDOW_HEIGHT, 0),
                "speed": random.randint(8, 15),  # Slower, more ominous
                "length": random.randint(15, 30),  # Longer streaks
                "angle": random.uniform(-0.05, 0.05)  # Subtle angle variation
            })
        
        # Create creepy distorted rain sound
        if self.assetManager.relaxingRainSound and not self.horrorRainSound:
            try:
                import numpy as np
                # Get the sound data
                soundArray = pygame.sndarray.array(self.assetManager.relaxingRainSound)
                # Pitch down by taking every 2nd sample and repeating for creepy low pitch
                pitchedDown = np.repeat(soundArray[::2], 2, axis=0)[:len(soundArray)]
                # Bitcrush effect - reduce bit depth for harsh digital distortion
                bitcrushed = (pitchedDown // 512) * 512  # Reduce to ~6 bit for crunchier sound
                # Add warble by modulating with low frequency
                length = len(bitcrushed)
                warble = np.sin(np.linspace(0, 30 * np.pi, length)).reshape(-1, 1) * 3000
                warbled = np.clip(bitcrushed.astype(np.float32) + warble, -32768, 32767)
                # Add subtle static noise
                noise = np.random.randint(-800, 800, warbled.shape, dtype=np.int16)
                distorted = np.clip(warbled.astype(np.int32) + noise, -32768, 32767)
                # Create new sound from modified array
                self.horrorRainSound = pygame.sndarray.make_sound(distorted.astype(np.int16))
                self.horrorRainSound.set_volume(0.5)  # Quieter - was 1.0
            except ImportError:
                # numpy not available - use regular rain sound at lower volume as fallback
                self.horrorRainSound = self.assetManager.relaxingRainSound
                if self.horrorRainSound:
                    self.horrorRainSound.set_volume(0.3)
            except Exception as e:
                print(f"Could not create horror rain sound: {e}")
                # Fallback to regular rain sound
                self.horrorRainSound = self.assetManager.relaxingRainSound
                if self.horrorRainSound:
                    self.horrorRainSound.set_volume(0.3)
        
        # Play the horror rain sound
        if self.horrorRainSound:
            try:
                self.horrorRainSoundChannel = self.horrorRainSound.play(loops=-1)
            except Exception as e:
                print(f"Could not play horror rain sound: {e}")
    
    def _stopHorrorRain(self):
        """Stop horror rain effects"""
        self.horrorRainDrops = []
        self.horrorRainSplashParticles = []
        self.horrorRainSplashes = []  # Clear 2D droplet effects
        self.skyDarkness = 0
        self.horrorBrightness = 0
        self.horrorLightningBolts = []
        self.horrorLightningFlash = 0
        
        # Stop horror rain sound
        if self.horrorRainSoundChannel:
            self.horrorRainSoundChannel.stop()
            self.horrorRainSoundChannel = None
    
    def _updateHorrorRain(self, dt: int):
        """Update horror rain animation"""
        if not self.horrorRainEnabled:
            return
        
        panelLeft = WINDOW_WIDTH - PANEL_WIDTH
        dtSec = dt / 1000.0
        
        # Update existing rain drops (just for visuals, no terrain collision)
        for drop in self.horrorRainDrops:
            drop["y"] += drop["speed"]
            drop["x"] += drop["angle"] * drop["speed"]
            
            # Reset when off screen
            if drop["y"] > WINDOW_HEIGHT:
                drop["y"] = random.randint(-50, 0)
                drop["x"] = random.randint(0, WINDOW_WIDTH)
        
        # Spawn splashes directly on top blocks (like normal rain does)
        # This ensures splashes appear on actual block surfaces
        self._spawnHorrorSplashesOnBlocks()
        
        # Update 2D droplet splashes (same as normal rain)
        for splash in self.horrorRainSplashes:
            splash["life"] -= 1
        self.horrorRainSplashes = [s for s in self.horrorRainSplashes if s["life"] > 0]
        
        # Update splash particles (3D physics)
        gravity = 0.2
        for particle in self.horrorRainSplashParticles:
            particle["x"] += particle["vx"]
            particle["y"] += particle["vy"]
            particle["vy"] += gravity
            particle["life"] -= dtSec / particle["maxLife"]
        self.horrorRainSplashParticles = [p for p in self.horrorRainSplashParticles if p["life"] > 0]
        
        # Horror lightning timing - chance for red lightning
        self.horrorLightningTimer += dt
        if self.horrorLightningTimer >= self.nextHorrorLightningTime:
            # 60% chance to trigger horror lightning (more common)
            if random.random() < 0.6:
                self._triggerHorrorLightning()
            self.horrorLightningTimer = 0
            self.nextHorrorLightningTime = random.randint(4000, 10000)  # 4-10 seconds (more frequent)
        
        # Fade horror lightning flash
        if self.horrorLightningFlash > 0:
            self.horrorLightningFlash = max(0, self.horrorLightningFlash - 5)
        
        # Clear lightning bolts when flash is gone
        if self.horrorLightningFlash <= 0:
            self.horrorLightningBolts = []
    
    def _spawnHorrorSplashesOnBlocks(self):
        """Spawn horror splash effects directly on random blocks in the world (like normal rain)"""
        # Find the highest block at each (x, y) position
        topBlocks = {}  # (x, y) -> z
        for (x, y, z), blockType in self.world.blocks.items():
            if (x, y) not in topBlocks or z > topBlocks[(x, y)]:
                topBlocks[(x, y)] = z
        
        if not topBlocks:
            return
        
        # Spawn 3-5 splashes per update on random top blocks
        blockList = list(topBlocks.items())
        numSplashes = min(len(blockList), random.randint(3, 5))
        
        for _ in range(numSplashes):
            (x, y), z = random.choice(blockList)
            
            # worldToScreen returns the TOP VERTEX (apex) of the tile diamond
            screenX, screenY = self.renderer.worldToScreen(x, y, z)
            
            # Keep offsets small to stay within the visible block top
            offsetX = random.randint(-6, 6)
            offsetY = random.randint(-3, 3)
            
            # Add panning offset
            splashX = screenX + self.panOffsetX + offsetX
            splashY = screenY + self.panOffsetY + TILE_HEIGHT // 4 + offsetY
            
            # Add 2D droplet splash (like normal rain)
            self.horrorRainSplashes.append({
                "x": splashX,
                "y": splashY,
                "life": 12,
                "size": random.randint(2, 5)
            })
            
            # Also spawn 3D particles occasionally
            if random.random() < 0.3:
                self._spawnHorrorSplash(splashX, splashY)
    
    def _spawnHorrorSplash(self, x: float, y: float):
        """Spawn 3D splash particles for horror rain"""
        # Dark colors for horror splash
        colors = [(10, 5, 15), (20, 10, 25), (5, 0, 10), (30, 15, 35), (15, 5, 20)]
        
        # Spawn 8-12 particles per splash
        numParticles = random.randint(8, 12)
        for _ in range(numParticles):
            self.horrorRainSplashParticles.append({
                "x": x + random.randint(-8, 8),
                "y": y + random.randint(-5, 5),
                "vx": random.uniform(-3, 3),
                "vy": random.uniform(-4, -1),  # Upward burst
                "color": random.choice(colors),
                "life": 1.0,
                "maxLife": random.uniform(0.4, 0.8),
                "size": random.randint(3, 6)
            })
    
    def _triggerHorrorLightning(self):
        """Trigger 3 red lightning bolts with horror sound"""
        self.horrorLightningBolts = []
        self.horrorLightningFlash = 150  # Bright red flash
        
        panelLeft = WINDOW_WIDTH - PANEL_WIDTH
        
        # Create 3 red lightning bolts
        for _ in range(3):
            bolt = []
            startX = random.randint(50, panelLeft - 50)
            startY = 0
            endX = startX + random.randint(-150, 150)
            endX = max(50, min(panelLeft - 50, endX))
            endY = random.randint(WINDOW_HEIGHT // 2, WINDOW_HEIGHT - 50)
            
            bolt.append((startX, startY))
            currentX, currentY = startX, startY
            
            while currentY < endY - 20:
                currentY += random.randint(30, 60)
                directionBias = (endX - currentX) * 0.15
                currentX += random.randint(-40, 40) + int(directionBias)
                currentX = max(50, min(panelLeft - 50, currentX))
                bolt.append((currentX, min(currentY, endY)))
            
            self.horrorLightningBolts.append(bolt)
        
        # Play horror sound (use thunder but louder and lower)
        if self.assetManager.thunderSounds:
            thunderSound = random.choice(self.assetManager.thunderSounds)
            # Play multiple times slightly offset for chaotic effect
            for i in range(3):
                channel = pygame.mixer.find_channel()
                if channel:
                    channel.play(thunderSound)
                    channel.set_volume(1.0)  # Full volume for horror effect
    
    def _renderHorrorRain(self):
        """Render horror rain (dark drops with subtle blue glow, splash particles, fog, and red lightning)"""
        if not self.horrorRainEnabled:
            return
        
        panelLeft = WINDOW_WIDTH - PANEL_WIDTH
        
        # Draw fog effect across the terrain (3 block height layers)
        self._renderHorrorFog()
        
        # NO brightness overlay - removed white filter for cleaner look
        
        # Draw each dark rain drop with subtle blue glow
        for drop in self.horrorRainDrops:
            if drop["x"] > panelLeft:
                continue
            endX = drop["x"] + drop["angle"] * drop["length"]
            endY = drop["y"] + drop["length"]
            
            # Subtle blue glow behind the drop (drawn first)
            glowColor = (40, 80, 140, 30)  # Very subtle light blue with low alpha
            glowSurf = pygame.Surface((8, int(drop["length"]) + 4), pygame.SRCALPHA)
            pygame.draw.line(glowSurf, glowColor, (4, 0), (4, int(drop["length"])), 6)
            self.screen.blit(glowSurf, (int(drop["x"]) - 4, int(drop["y"]) - 2))
            
            # Dark rain drop core
            rainColor = (15, 10, 25)  # Very dark purple
            pygame.draw.line(self.screen, rainColor, 
                           (int(drop["x"]), int(drop["y"])),
                           (int(endX), int(endY)), 2)
        
        # Draw 3D splash particles
        for particle in self.horrorRainSplashParticles:
            if particle["x"] > panelLeft:
                continue
            alpha = int(particle["life"] * 255)
            color = (*particle["color"], alpha)
            size = max(2, int(particle["size"] * (0.5 + particle["life"] * 0.5)))
            if size > 0:
                particleSurf = pygame.Surface((size, size), pygame.SRCALPHA)
                particleSurf.fill(color)
                # Add darker outline for 3D effect
                if size > 2:
                    darker = (max(0, particle["color"][0] - 5), max(0, particle["color"][1] - 5), max(0, particle["color"][2] - 5), alpha)
                    pygame.draw.rect(particleSurf, darker, (0, 0, size, size), 1)
                self.screen.blit(particleSurf, (int(particle["x"]), int(particle["y"])))
        
        # Draw 2D droplet splash effects (dark version of normal rain splashes)
        for splash in getattr(self, 'horrorRainSplashes', []):
            if splash["x"] > panelLeft:
                continue
            alpha = int(180 * (splash["life"] / 12))
            # Draw expanding ring splash effect - dark purple
            expansion = (12 - splash["life"]) * 0.5
            size = splash["size"] + expansion
            
            # Outer ring - dark purple
            splashSurf = pygame.Surface((int(size * 3), int(size * 1.5)), pygame.SRCALPHA)
            splashColor = (40, 20, 60, alpha)
            pygame.draw.ellipse(splashSurf, splashColor, splashSurf.get_rect(), 2)
            self.screen.blit(splashSurf, (splash["x"] - size * 1.5, splash["y"] - size * 0.75))
            
            # Inner splash dot
            if splash["life"] > 6:
                dotSize = max(2, splash["size"] - 1)
                dotSurf = pygame.Surface((dotSize * 2, dotSize), pygame.SRCALPHA)
                dotColor = (20, 10, 30, alpha)
                pygame.draw.ellipse(dotSurf, dotColor, dotSurf.get_rect())
                self.screen.blit(dotSurf, (splash["x"] - dotSize, splash["y"] - dotSize // 2))
        
        # Draw red lightning bolts
        for bolt in self.horrorLightningBolts:
            if len(bolt) >= 2:
                for i in range(len(bolt) - 1):
                    start = bolt[i]
                    end = bolt[i + 1]
                    # Outer glow - thick and dark red
                    pygame.draw.line(self.screen, (100, 0, 0), start, end, 9)
                    pygame.draw.line(self.screen, (150, 0, 0), start, end, 6)
                    # Core - bright red
                    pygame.draw.line(self.screen, (255, 50, 50), start, end, 3)
                    pygame.draw.line(self.screen, (255, 100, 100), start, end, 2)
        
        # Draw red lightning flash overlay
        if self.horrorLightningFlash > 0:
            flashOverlay = pygame.Surface((panelLeft, WINDOW_HEIGHT), pygame.SRCALPHA)
            flashOverlay.fill((255, 0, 0, min(100, self.horrorLightningFlash)))  # Red flash
            self.screen.blit(flashOverlay, (0, 0))
    
    def _renderHorrorFog(self):
        """Render semi-transparent fog blocks across the terrain during horror rain"""
        panelLeft = WINDOW_WIDTH - PANEL_WIDTH
        
        # Get all unique x,y positions in the world
        uniquePositions = set()
        for (x, y, z), blockType in self.world.blocks.items():
            uniquePositions.add((x, y))
        
        # Also add positions within the grid even if empty
        for x in range(GRID_WIDTH):
            for y in range(GRID_DEPTH):
                uniquePositions.add((x, y))
        
        # Sort positions for proper isometric rendering (back to front)
        sortedPositions = sorted(uniquePositions, key=lambda pos: pos[0] + pos[1])
        
        # Create fog surface
        fogColor = (40, 30, 50)  # Dark purple fog
        fogAlpha = 60  # Semi-transparent
        
        # Draw fog at z levels 1, 2, 3 (3 blocks height)
        for fogZ in range(1, 4):
            for (x, y) in sortedPositions:
                # Get screen position for this fog block
                screenX, screenY = self.renderer.worldToScreen(x, y, fogZ)
                screenX += self.panOffsetX
                screenY += self.panOffsetY
                
                # Skip if off-screen or in panel area
                if screenX > panelLeft + TILE_WIDTH or screenX < -TILE_WIDTH:
                    continue
                if screenY > WINDOW_HEIGHT + TILE_HEIGHT or screenY < -TILE_HEIGHT * 2:
                    continue
                
                # Draw fog as a diamond-shaped block top (only top face for fog)
                # Create the isometric diamond points for fog
                points = [
                    (screenX, screenY),  # Top
                    (screenX + TILE_WIDTH // 2, screenY + TILE_HEIGHT // 4),  # Right
                    (screenX, screenY + TILE_HEIGHT // 2),  # Bottom
                    (screenX - TILE_WIDTH // 2, screenY + TILE_HEIGHT // 4)  # Left
                ]
                
                # Draw semi-transparent fog diamond
                fogSurf = pygame.Surface((TILE_WIDTH, TILE_HEIGHT), pygame.SRCALPHA)
                localPoints = [
                    (TILE_WIDTH // 2, 0),  # Top
                    (TILE_WIDTH, TILE_HEIGHT // 4),  # Right
                    (TILE_WIDTH // 2, TILE_HEIGHT // 2),  # Bottom
                    (0, TILE_HEIGHT // 4)  # Left
                ]
                pygame.draw.polygon(fogSurf, (*fogColor, fogAlpha), localPoints)
                self.screen.blit(fogSurf, (screenX - TILE_WIDTH // 2, screenY))
    
    def _toggleSnow(self):
        """Toggle snow on/off (only works in Overworld)"""
        if self.currentDimension != DIMENSION_OVERWORLD:
            return  # Snow only in Overworld
        
        # If rain is on, turn it off first
        if self.rainEnabled:
            self.rainEnabled = False
            self._stopRain()
        
        self.snowEnabled = not self.snowEnabled
        
        if self.snowEnabled:
            self._startSnow()
        else:
            self._stopSnow()
    
    def _startSnow(self):
        """Initialize snow effects"""
        self.snowFlakes = []
        self.snowSkyDarkness = 0
        
        # Calculate platform screen bounds for constraining snow
        self._updatePlatformBounds()
        
        # Create initial snowflakes within platform bounds
        for _ in range(80):  # Fewer particles than rain
            x = self._getRandomSnowPosition()
            self.snowFlakes.append({
                "x": x,
                "y": random.randint(-50, WINDOW_HEIGHT),
                "speed": random.uniform(1.5, 3.5),  # Much slower than rain
                "size": random.randint(2, 4),
                "drift": random.uniform(-0.5, 0.5),  # Horizontal drift
                "driftSpeed": random.uniform(0.01, 0.03),
                "driftPhase": random.uniform(0, 6.28)  # Random starting phase
            })
    
    def _updatePlatformBounds(self):
        """Calculate the screen bounds of the platform for weather effects"""
        # Get the four corners of the platform at z=0 in isometric view
        # In initial perspective (rotation 0), the platform is a diamond:
        #   - Top corner is at world (0, 0) - this is the BACK
        #   - Right corner is at world (GRID_WIDTH-1, 0)
        #   - Bottom corner is at world (GRID_WIDTH-1, GRID_DEPTH-1) - this is the FRONT
        #   - Left corner is at world (0, GRID_DEPTH-1)
        
        # Get screen positions of platform corners at z=0 (ground level)
        backCorner = self.renderer.worldToScreen(0, 0, 0)  # Back (top-center visually)
        rightCorner = self.renderer.worldToScreen(GRID_WIDTH - 1, 0, 0)  # Right
        frontCorner = self.renderer.worldToScreen(GRID_WIDTH - 1, GRID_DEPTH - 1, 0)  # Front (bottom visually)
        leftCorner = self.renderer.worldToScreen(0, GRID_DEPTH - 1, 0)  # Left
        
        # Store corners for isometric bounds checking
        self.platformCorners = [backCorner, rightCorner, frontCorner, leftCorner]
        
        # Calculate bounding box with some padding
        padding = 30
        self.platformMinX = min(backCorner[0], leftCorner[0], frontCorner[0], rightCorner[0]) - padding
        self.platformMaxX = min(max(backCorner[0], leftCorner[0], frontCorner[0], rightCorner[0]) + padding, WINDOW_WIDTH - PANEL_WIDTH)
        self.platformMinY = min(backCorner[1], leftCorner[1], frontCorner[1], rightCorner[1]) - padding
        self.platformMaxY = max(backCorner[1], leftCorner[1], frontCorner[1], rightCorner[1]) + padding
    
    def _isPointInPlatformDiamond(self, x, y):
        """Check if a screen point is within the isometric platform diamond"""
        if not hasattr(self, 'platformCorners') or len(self.platformCorners) != 4:
            return True  # Default to allowing if not calculated
        
        # Use cross product to check if point is inside the diamond
        # Diamond vertices: back (top), right, front (bottom), left
        back, right, front, left = self.platformCorners
        
        def sign(p1, p2, p3):
            return (p1[0] - p3[0]) * (p2[1] - p3[1]) - (p2[0] - p3[0]) * (p1[1] - p3[1])
        
        # Check if point is on the correct side of each edge
        # With some tolerance for the borders
        tolerance = 20
        
        # Check against all four edges of the diamond
        # back-right edge (top-right)
        # right-front edge (bottom-right)  
        # front-left edge (bottom-left)
        # left-back edge (top-left)
        
        d1 = sign((x, y), back, right)
        d2 = sign((x, y), right, front)
        d3 = sign((x, y), front, left)
        d4 = sign((x, y), left, back)
        
        has_neg = (d1 < -tolerance) or (d2 < -tolerance) or (d3 < -tolerance) or (d4 < -tolerance)
        has_pos = (d1 > tolerance) or (d2 > tolerance) or (d3 > tolerance) or (d4 > tolerance)
        
        return not (has_neg and has_pos)
    
    def _getRandomSnowPosition(self):
        """Get a random X position within the platform bounds"""
        if hasattr(self, 'platformMinX') and hasattr(self, 'platformMaxX'):
            return random.randint(int(self.platformMinX), int(self.platformMaxX))
        else:
            return random.randint(0, WINDOW_WIDTH - PANEL_WIDTH)
    
    def _stopSnow(self):
        """Stop snow effects and clear accumulated snow"""
        self.snowFlakes = []
        self.snowSkyDarkness = 0
        self.snowLayers = {}  # Clear accumulated snow when turned off
    
    def _clearSnowLayers(self):
        """Clear all accumulated snow layers"""
        self.snowLayers = {}
    
    def _updateSnow(self, dt: int):
        """Update snow particle positions and accumulation"""
        if not self.snowEnabled:
            # Fade out sky darkness
            if self.snowSkyDarkness > 0:
                self.snowSkyDarkness = max(0, self.snowSkyDarkness - 2)
            return
        
        # Update platform bounds periodically (every few frames) for panning support
        if not hasattr(self, '_snowBoundsTimer'):
            self._snowBoundsTimer = 0
        self._snowBoundsTimer += dt
        if self._snowBoundsTimer > 500:  # Update every 500ms
            self._snowBoundsTimer = 0
            self._updatePlatformBounds()
        
        # Fade in sky darkness (lighter than rain - around 80)
        if self.snowSkyDarkness < 80:
            self.snowSkyDarkness = min(80, self.snowSkyDarkness + 1)
        
        panelLeft = WINDOW_WIDTH - PANEL_WIDTH
        
        # Update snowflakes with gentle drifting motion
        for flake in self.snowFlakes:
            flake["y"] += flake["speed"]
            
            # Sinusoidal horizontal drift (like real snowflakes)
            flake["driftPhase"] += flake["driftSpeed"]
            flake["x"] += math.sin(flake["driftPhase"]) * flake["drift"]
            
            # Update platform bounds periodically (in case of panning)
            if not hasattr(self, 'platformMinX'):
                self._updatePlatformBounds()
            
            # If flake goes off platform bounds or screen, reset to top within bounds
            minX = getattr(self, 'platformMinX', 0)
            maxX = getattr(self, 'platformMaxX', panelLeft)
            maxY = getattr(self, 'platformMaxY', WINDOW_HEIGHT)
            
            if flake["y"] > maxY or flake["x"] < minX - 20 or flake["x"] > maxX + 20:
                flake["y"] = random.randint(-30, -5)
                flake["x"] = self._getRandomSnowPosition()
                flake["speed"] = random.uniform(1.5, 3.5)
                flake["size"] = random.randint(2, 4)
                flake["drift"] = random.uniform(-0.5, 0.5)
                flake["driftPhase"] = random.uniform(0, 6.28)
        
        # Snow accumulation on blocks (like Minecraft)
        self.snowAccumulateTimer += dt
        if self.snowAccumulateTimer >= 1500:  # Every 1.5 seconds
            self.snowAccumulateTimer = 0
            self._accumulateSnowOnBlocks()
    
    def _accumulateSnowOnBlocks(self):
        """Add thin snow layer on top of random exposed blocks (only within platform bounds)"""
        # Find all top blocks (exposed to sky) that are within platform bounds
        topBlocks = {}
        for (x, y, z), blockType in self.world.blocks.items():
            # Skip if outside platform bounds
            if x < 0 or x >= self.world.width or y < 0 or y >= self.world.depth:
                continue
            # Skip if there's already a block above (not exposed)
            if (x, y, z + 1) in self.world.blocks:
                continue
            if (x, y) not in topBlocks or z > topBlocks[(x, y)]:
                topBlocks[(x, y)] = z
        
        if not topBlocks:
            return
        
        # Add snow to 1-3 random exposed blocks
        numToSnow = random.randint(1, 3)
        candidates = list(topBlocks.items())
        random.shuffle(candidates)
        
        for (x, y), z in candidates[:numToSnow]:
            snowPos = (x, y, z + 1)  # Snow layer goes on top
            
            # Skip if already has snow layer or a real block
            if snowPos in self.snowLayers or snowPos in self.world.blocks:
                continue
            
            # Add thin snow layer (height 1-3, representing 1/16 to 3/16 of a block)
            currentHeight = self.snowLayers.get(snowPos, 0)
            if currentHeight < 8:  # Max 8 layers (half a block)
                self.snowLayers[snowPos] = min(8, currentHeight + random.randint(1, 2))
    
    def _renderSnow(self) -> None:
        """Render snow overlay effects and accumulated snow layers"""
        # Calculate panel boundary
        panelLeft = WINDOW_WIDTH - PANEL_WIDTH
        
        # Draw snow darkening overlay (lighter than rain)
        if self.snowSkyDarkness > 0:
            darkOverlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
            # Blueish-gray tint for snowy atmosphere
            darkOverlay.fill((40, 50, 70, self.snowSkyDarkness))
            self.screen.blit(darkOverlay, (0, 0))
        
        # Draw accumulated snow layers on blocks (thin white layer covering block top)
        if self.snowLayers:
            # Sort snow layers by depth for proper rendering (same as blocks)
            sortedLayers = sorted(self.snowLayers.items(), key=lambda item: item[0][0] + item[0][1] + item[0][2])
            
            for (x, y, z), height in sortedLayers:
                # Get screen position at the snow's Z level (on top of block at z-1)
                # worldToScreen returns the TOP VERTEX of the isometric tile
                screenX, screenY = self.renderer.worldToScreen(x, y, z)
                
                # Skip if off screen
                if screenX < -50 or screenX > panelLeft + 50:
                    continue
                
                # Snow layer thickness (2-5 pixels based on accumulation)
                layerThickness = max(2, min(5, height))
                
                # The top face diamond matches _createIsometricBlock exactly:
                # topPoints = [(halfW, 0), (W-1, halfH), (halfW, TILE_HEIGHT-1), (0, halfH)]
                # Where halfW = TILE_WIDTH//2 = 32, halfH = TILE_HEIGHT//2 = 16
                # screenX,screenY is the top vertex (center top of diamond)
                
                halfW = TILE_WIDTH // 2  # 32
                halfH = TILE_HEIGHT // 2  # 16
                
                # Top surface diamond - matches block top face exactly
                topPoints = [
                    (screenX, screenY),                      # Top vertex (0, 0 in local)
                    (screenX + halfW, screenY + halfH),      # Right vertex (32, 16)
                    (screenX, screenY + TILE_HEIGHT),        # Bottom vertex (0, 32)
                    (screenX - halfW, screenY + halfH)       # Left vertex (-32, 16)
                ]
                
                # Bottom of snow layer (offset down by thickness)
                bottomOffset = layerThickness
                
                # Left side face - thin edge matching isometric projection
                leftSidePoints = [
                    (screenX - halfW, screenY + halfH),
                    (screenX, screenY + TILE_HEIGHT),
                    (screenX, screenY + TILE_HEIGHT + bottomOffset),
                    (screenX - halfW, screenY + halfH + bottomOffset),
                ]
                
                # Right side face - thin edge matching isometric projection
                rightSidePoints = [
                    (screenX, screenY + TILE_HEIGHT),
                    (screenX + halfW, screenY + halfH),
                    (screenX + halfW, screenY + halfH + bottomOffset),
                    (screenX, screenY + TILE_HEIGHT + bottomOffset),
                ]
                
                # Snow colors (white with slight blue tint)
                topColor = (250, 252, 255)  # Bright white top
                leftColor = (200, 210, 225)  # Shaded left
                rightColor = (225, 235, 245)  # Medium shaded right
                
                # Draw sides first, then top (proper painter's algorithm)
                pygame.draw.polygon(self.screen, leftColor, leftSidePoints)
                pygame.draw.polygon(self.screen, rightColor, rightSidePoints)
                pygame.draw.polygon(self.screen, topColor, topPoints)
        
        # Draw falling snowflakes as small white circles/dots
        if self.snowEnabled or self.snowFlakes:
            for flake in self.snowFlakes:
                # Skip flakes over the UI panel
                if flake["x"] > panelLeft:
                    continue
                
                # Skip flakes outside the isometric platform diamond (prevents floating appearance)
                if not self._isPointInPlatformDiamond(flake["x"], flake["y"]):
                    continue
                
                # Draw snowflake as small white circle
                color = (255, 255, 255, 200)
                snowSurf = pygame.Surface((flake["size"] * 2, flake["size"] * 2), pygame.SRCALPHA)
                pygame.draw.circle(snowSurf, color, (flake["size"], flake["size"]), flake["size"])
                self.screen.blit(snowSurf, (int(flake["x"]), int(flake["y"])))
    
    def _generateStars(self):
        """Generate random star positions for night sky"""
        self.stars = []
        panelLeft = WINDOW_WIDTH - PANEL_WIDTH
        for _ in range(300):  # 300 stars for denser sky
            self.stars.append({
                "x": random.randint(0, panelLeft),
                "y": random.randint(0, int(WINDOW_HEIGHT * 0.7)),  # Upper 70% of screen
                "brightness": random.uniform(0.5, 1.0),  # Brighter minimum
                "twinkleSpeed": random.uniform(0.003, 0.012),  # Faster twinkle
                "twinklePhase": random.uniform(0, math.pi * 2),
                "size": random.choice([1, 2, 2, 3, 3, 4])  # Bigger stars
            })
    
    def _renderStars(self) -> None:
        """Render twinkling stars during night"""
        if not self.celestialEnabled:
            return
        
        # Stars only visible during night (celestialAngle 360-720)
        if self.celestialAngle < 360:
            return
        
        # Calculate star visibility based on time of night
        # Full visibility during deep night (angle 450-630), fading at dusk/dawn
        if self.celestialAngle < 420:
            starAlpha = (self.celestialAngle - 360) / 60  # Fade in
        elif self.celestialAngle > 660:
            starAlpha = (720 - self.celestialAngle) / 60  # Fade out
        else:
            starAlpha = 1.0
        
        panelLeft = WINDOW_WIDTH - PANEL_WIDTH
        currentTime = pygame.time.get_ticks() / 1000.0
        
        for star in self.stars:
            if star["x"] >= panelLeft:
                continue
            
            # Twinkle effect using sine wave
            twinkle = math.sin(currentTime * star["twinkleSpeed"] * 100 + star["twinklePhase"])
            brightness = star["brightness"] * (0.6 + 0.4 * twinkle) * starAlpha
            
            if brightness > 0.1:
                alpha = int(brightness * 255)
                color = (255, 255, 220, alpha)  # Warm white/yellow tint
                size = star["size"]
                
                if size == 1:
                    # Small star - 2x2 with center bright
                    starSurf = pygame.Surface((2, 2), pygame.SRCALPHA)
                    starSurf.fill(color)
                elif size == 2:
                    # Medium star - cross pattern
                    starSurf = pygame.Surface((5, 5), pygame.SRCALPHA)
                    dimColor = (255, 255, 220, alpha // 2)
                    starSurf.set_at((2, 2), color)  # Center
                    starSurf.set_at((1, 2), dimColor)
                    starSurf.set_at((3, 2), dimColor)
                    starSurf.set_at((2, 1), dimColor)
                    starSurf.set_at((2, 3), dimColor)
                elif size == 3:
                    # Larger star with glow
                    starSurf = pygame.Surface((7, 7), pygame.SRCALPHA)
                    dimColor = (255, 255, 220, alpha // 2)
                    faintColor = (255, 255, 220, alpha // 4)
                    pygame.draw.circle(starSurf, color, (3, 3), 2)
                    starSurf.set_at((0, 3), faintColor)
                    starSurf.set_at((6, 3), faintColor)
                    starSurf.set_at((3, 0), faintColor)
                    starSurf.set_at((3, 6), faintColor)
                else:
                    # Biggest star - bright with cross rays
                    starSurf = pygame.Surface((9, 9), pygame.SRCALPHA)
                    dimColor = (255, 255, 220, alpha // 2)
                    pygame.draw.circle(starSurf, color, (4, 4), 3)
                    pygame.draw.line(starSurf, dimColor, (0, 4), (8, 4), 1)
                    pygame.draw.line(starSurf, dimColor, (4, 0), (4, 8), 1)
                
                self.screen.blit(starSurf, (star["x"], star["y"]))
    
    def _loadCloudTexture(self):
        """Load the cloud texture"""
        if self.cloudTexture is None:
            try:
                cloudPath = os.path.join("Assets", "Texture Hub", "environment", "clouds.png")
                if os.path.exists(cloudPath):
                    self.cloudTexture = pygame.image.load(cloudPath).convert_alpha()
                    print("Loaded cloud texture")
            except Exception as e:
                print(f"Could not load cloud texture: {e}")
    
    def _generateClouds(self):
        """Generate Minecraft-style clouds - large flat connected blocks"""
        self.clouds = []
        self._loadCloudTexture()
        
        panelLeft = WINDOW_WIDTH - PANEL_WIDTH
        
        # Generate 10-15 cloud formations (was 4-6)
        for i in range(random.randint(10, 15)):
            # Minecraft clouds are flat (thin), wide rectangular prisms
            # They connect horizontally to form larger shapes
            numBlocks = random.randint(5, 12)  # 5-12 connected blocks per cloud (was 3-8)
            blocks = []
            
            # Start with a base block
            baseX = 0
            baseY = 0
            
            for b in range(numBlocks):
                if b == 0:
                    # First block at origin - much larger
                    blocks.append({
                        "offsetX": 0,
                        "offsetY": 0,
                        "width": random.randint(150, 280),   # Was 80-140
                        "height": 30,  # Was 20 - slightly taller
                        "depth": random.randint(100, 180)   # Was 60-100
                    })
                else:
                    # Connect to a random existing block
                    connectTo = random.choice(blocks)
                    # Extend in a random direction (mostly horizontal)
                    direction = random.choice(["left", "right", "front", "back"])
                    newWidth = random.randint(120, 220)   # Was 60-120
                    newDepth = random.randint(90, 160)    # Was 50-90
                    
                    if direction == "right":
                        newX = connectTo["offsetX"] + connectTo["width"] - 10
                        newY = connectTo["offsetY"] + random.randint(-20, 20)
                    elif direction == "left":
                        newX = connectTo["offsetX"] - newWidth + 10
                        newY = connectTo["offsetY"] + random.randint(-20, 20)
                    elif direction == "front":
                        newX = connectTo["offsetX"] + random.randint(-20, 20)
                        newY = connectTo["offsetY"] + connectTo["depth"] - 10
                    else:  # back
                        newX = connectTo["offsetX"] + random.randint(-20, 20)
                        newY = connectTo["offsetY"] - newDepth + 10
                    
                    blocks.append({
                        "offsetX": newX,
                        "offsetY": newY,
                        "width": newWidth,
                        "height": 30,  # Keep flat but taller (was 20)
                        "depth": newDepth
                    })
            
            self.clouds.append({
                "x": random.randint(-400, panelLeft + 200),  # Wider spread (was -200 to panelLeft)
                "y": random.randint(30, WINDOW_HEIGHT // 4),  # Higher clouds
                "speed": random.uniform(0.08, 0.20),  # Slower movement (was 0.12-0.28)
                "blocks": blocks,
                "alpha": random.randint(180, 230)
            })
    
    def _updateClouds(self, dt: int):
        """Update cloud positions"""
        if not self.cloudsEnabled:
            return
        
        panelLeft = WINDOW_WIDTH - PANEL_WIDTH
        for cloud in self.clouds:
            cloud["x"] += cloud["speed"]
            # Wrap around when cloud goes off screen
            if cloud["x"] > panelLeft + 200:
                cloud["x"] = -250
                cloud["y"] = random.randint(30, WINDOW_HEIGHT // 4)
                cloud["speed"] = random.uniform(0.15, 0.35)
    
    def _renderClouds(self) -> None:
        """Render Minecraft-style flat clouds as connected isometric blocks"""
        if not self.cloudsEnabled:
            return
        
        panelLeft = WINDOW_WIDTH - PANEL_WIDTH
        
        for cloud in self.clouds:
            if cloud["x"] < -400 or cloud["x"] > panelLeft + 200:
                continue
            
            # Sort blocks by depth for proper rendering
            blocks = cloud.get("blocks", [])
            sortedBlocks = sorted(blocks, key=lambda b: b["offsetX"] + b["offsetY"])
            
            for block in sortedBlocks:
                blockX = cloud["x"] + block["offsetX"]
                blockY = cloud["y"] + block["offsetY"]
                
                width = block["width"]
                height = block["height"]  # This is the vertical thickness (small for flat clouds)
                depth = block["depth"]
                
                # Isometric projection for flat rectangular cloud blocks
                # Half-width and half-depth for isometric diamond
                halfW = width // 4
                halfD = depth // 4
                
                alpha = cloud["alpha"]
                
                # Cloud colors (pure white like Minecraft)
                topColor = (255, 255, 255, alpha)
                leftColor = (230, 230, 235, alpha)  # Slight shadow
                rightColor = (245, 245, 250, alpha)  # Slight shadow
                
                # Top face - flat isometric diamond
                topPoints = [
                    (blockX, blockY),                          # Back corner
                    (blockX + halfW, blockY + halfW // 2),     # Right corner
                    (blockX + halfW - halfD, blockY + halfW // 2 + halfD // 2),  # Front corner
                    (blockX - halfD, blockY + halfD // 2)      # Left corner
                ]
                
                # Left face (depth side) - thin because clouds are flat
                leftPoints = [
                    (blockX - halfD, blockY + halfD // 2),
                    (blockX + halfW - halfD, blockY + halfW // 2 + halfD // 2),
                    (blockX + halfW - halfD, blockY + halfW // 2 + halfD // 2 + height),
                    (blockX - halfD, blockY + halfD // 2 + height)
                ]
                
                # Right face (width side) - thin because clouds are flat
                rightPoints = [
                    (blockX + halfW - halfD, blockY + halfW // 2 + halfD // 2),
                    (blockX + halfW, blockY + halfW // 2),
                    (blockX + halfW, blockY + halfW // 2 + height),
                    (blockX + halfW - halfD, blockY + halfW // 2 + halfD // 2 + height)
                ]
                
                # Calculate surface size needed
                maxSize = max(width, depth) + height + 50
                
                # Draw with alpha blending
                cloudSurf = pygame.Surface((maxSize, maxSize), pygame.SRCALPHA)
                centerX = maxSize // 4
                centerY = maxSize // 4
                offsetPts = lambda pts: [(int(p[0] - blockX + centerX), int(p[1] - blockY + centerY)) for p in pts]
                
                pygame.draw.polygon(cloudSurf, leftColor, offsetPts(leftPoints))
                pygame.draw.polygon(cloudSurf, rightColor, offsetPts(rightPoints))
                pygame.draw.polygon(cloudSurf, topColor, offsetPts(topPoints))
                
                self.screen.blit(cloudSurf, (int(blockX - centerX), int(blockY - centerY)))
    
    def _toggleClouds(self):
        """Toggle clouds on/off"""
        self.cloudsEnabled = not self.cloudsEnabled
        if self.cloudsEnabled and not self.clouds:
            self._generateClouds()
    
    def _spawnBlockParticles(self, screenX: int, screenY: int, blockType: BlockType):
        """Spawn particles when breaking a block using the block's colors"""
        # Get the block's sprite for color sampling
        sprite = self.assetManager.getBlockSprite(blockType)
        if not sprite:
            return
        
        # Sample colors from the sprite
        colors = []
        spriteWidth = sprite.get_width()
        spriteHeight = sprite.get_height()
        for _ in range(5):
            px = random.randint(0, spriteWidth - 1)
            py = random.randint(0, spriteHeight - 1)
            color = sprite.get_at((px, py))
            if color.a > 50:  # Only use non-transparent pixels
                colors.append((color.r, color.g, color.b))
        
        if not colors:
            colors = [(128, 128, 128)]  # Fallback gray
        
        # Spawn 20-30 particles for more noticeable effect
        numParticles = random.randint(20, 30)
        for _ in range(numParticles):
            self.blockParticles.append({
                "x": screenX + random.randint(-15, 15),
                "y": screenY + random.randint(-15, 15),
                "vx": random.uniform(-4, 4),  # Faster spread
                "vy": random.uniform(-5, -1),  # Bigger upward burst
                "color": random.choice(colors),
                "life": 1.0,
                "maxLife": random.uniform(0.6, 1.2),  # Longer lasting
                "size": random.randint(4, 8)  # Bigger particles
            })
    
    def _updateBlockParticles(self, dt: int):
        """Update block breaking particles"""
        gravity = 0.15
        dtSec = dt / 1000.0
        
        for particle in self.blockParticles:
            particle["x"] += particle["vx"]
            particle["y"] += particle["vy"]
            particle["vy"] += gravity  # Gravity
            particle["life"] -= dtSec / particle["maxLife"]
        # Remove dead particles efficiently
        self.blockParticles = [p for p in self.blockParticles if p["life"] > 0]
    
    def _renderBlockParticles(self) -> None:
        """Render block breaking particles"""
        for particle in self.blockParticles:
            alpha = int(particle["life"] * 255)
            color = (*particle["color"], alpha)
            # Keep size larger for longer, minimum size of 2
            size = max(2, int(particle["size"] * (0.5 + particle["life"] * 0.5)))
            if size > 0:
                particleSurf = pygame.Surface((size, size), pygame.SRCALPHA)
                particleSurf.fill(color)
                # Add slight outline for visibility
                if size > 3:
                    darker = (max(0, particle["color"][0] - 40), max(0, particle["color"][1] - 40), max(0, particle["color"][2] - 40), alpha)
                    pygame.draw.rect(particleSurf, darker, (0, 0, size, size), 1)
                self.screen.blit(particleSurf, (int(particle["x"]), int(particle["y"])))
    
    def _renderGrid(self) -> None:
        """Render isometric grid lines over the platform when grid is enabled"""
        if not self.showGrid:
            return
        
        # Grid line color - semi-transparent white for visibility on any block
        gridColor = (255, 255, 255, 80)
        
        halfW = TILE_WIDTH // 2
        halfH = TILE_HEIGHT // 2
        
        # Create a surface for the grid lines with alpha
        gridSurface = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        
        # Draw lines along the X axis (constant Y values)
        for y in range(GRID_DEPTH + 1):
            # Line from (0, y, 1) to (GRID_WIDTH, y, 1) at z=1 (top of floor blocks)
            startX, startY = self.renderer.worldToScreen(0, y, 1)
            endX, endY = self.renderer.worldToScreen(GRID_WIDTH, y, 1)
            # Adjust to draw on top face of blocks
            startY -= BLOCK_HEIGHT
            endY -= BLOCK_HEIGHT
            pygame.draw.line(gridSurface, gridColor, (startX, startY), (endX, endY), 1)
        
        # Draw lines along the Y axis (constant X values)
        for x in range(GRID_WIDTH + 1):
            # Line from (x, 0, 1) to (x, GRID_DEPTH, 1) at z=1 (top of floor blocks)
            startX, startY = self.renderer.worldToScreen(x, 0, 1)
            endX, endY = self.renderer.worldToScreen(x, GRID_DEPTH, 1)
            # Adjust to draw on top face of blocks
            startY -= BLOCK_HEIGHT
            endY -= BLOCK_HEIGHT
            pygame.draw.line(gridSurface, gridColor, (startX, startY), (endX, endY), 1)
        
        self.screen.blit(gridSurface, (0, 0))
    
    def _renderBlockHighlight(self) -> None:
        """Render outline around the brush area (all blocks that would be placed)"""
        if not self.hoveredCell or self.panelHovered:
            return
        
        baseX, baseY, baseZ = self.hoveredCell
        brushSize = self.brushSize
        
        # Scale dimensions with zoom level to match zoomed blocks
        scaledTileWidth = int(TILE_WIDTH * self.zoomLevel)
        scaledTileHeight = int(TILE_HEIGHT * self.zoomLevel)
        scaledBlockHeight = int(BLOCK_HEIGHT * self.zoomLevel)
        halfW = scaledTileWidth // 2
        halfH = scaledTileHeight // 2
        
        # Check if we need to flip for rotated views
        viewRot = self.renderer.viewRotation
        flipFaces = (viewRot == 1 or viewRot == 3)
        
        # For brush size > 1, draw one outline around the entire brush area
        # Calculate the corners of the brush area in world space
        # Top-left corner is baseX, baseY
        # Bottom-right corner is baseX + brushSize - 1, baseY + brushSize - 1
        
        # Get screen positions for the 4 corners of the brush area
        # In isometric view, we need the outermost points
        
        # For the outline, we need:
        # - Top point: corner at (baseX, baseY) - top vertex
        # - Right point: corner at (baseX + brushSize - 1, baseY) - right vertex  
        # - Bottom point: corner at (baseX + brushSize - 1, baseY + brushSize - 1) - bottom vertex
        # - Left point: corner at (baseX, baseY + brushSize - 1) - left vertex
        
        topCornerX, topCornerY = baseX, baseY
        rightCornerX, rightCornerY = baseX + brushSize - 1, baseY
        bottomCornerX, bottomCornerY = baseX + brushSize - 1, baseY + brushSize - 1
        leftCornerX, leftCornerY = baseX, baseY + brushSize - 1
        
        # Get screen positions
        topScreen = self.renderer.worldToScreen(topCornerX, topCornerY, baseZ)
        rightScreen = self.renderer.worldToScreen(rightCornerX, rightCornerY, baseZ)
        bottomScreen = self.renderer.worldToScreen(bottomCornerX, bottomCornerY, baseZ)
        leftScreen = self.renderer.worldToScreen(leftCornerX, leftCornerY, baseZ)
        
        # Top face diamond - outer bounds of brush area
        topPoints = [
            (topScreen[0], topScreen[1]),  # Top vertex
            (rightScreen[0] + halfW, rightScreen[1] + halfH),  # Right vertex
            (bottomScreen[0], bottomScreen[1] + scaledTileHeight),  # Bottom vertex
            (leftScreen[0] - halfW, leftScreen[1] + halfH)  # Left vertex
        ]
        
        # Side faces - we need the vertical edges
        if flipFaces:
            # Left face (actually right side visually when flipped)
            leftPoints = [
                (rightScreen[0] + halfW, rightScreen[1] + halfH),
                (bottomScreen[0], bottomScreen[1] + scaledTileHeight),
                (bottomScreen[0], bottomScreen[1] + scaledTileHeight + scaledBlockHeight),
                (rightScreen[0] + halfW, rightScreen[1] + halfH + scaledBlockHeight)
            ]
            # Right face (actually left side visually when flipped)
            rightPoints = [
                (bottomScreen[0], bottomScreen[1] + scaledTileHeight),
                (leftScreen[0] - halfW, leftScreen[1] + halfH),
                (leftScreen[0] - halfW, leftScreen[1] + halfH + scaledBlockHeight),
                (bottomScreen[0], bottomScreen[1] + scaledTileHeight + scaledBlockHeight)
            ]
        else:
            # Left face vertices
            leftPoints = [
                (leftScreen[0] - halfW, leftScreen[1] + halfH),
                (bottomScreen[0], bottomScreen[1] + scaledTileHeight),
                (bottomScreen[0], bottomScreen[1] + scaledTileHeight + scaledBlockHeight),
                (leftScreen[0] - halfW, leftScreen[1] + halfH + scaledBlockHeight)
            ]
            # Right face vertices
            rightPoints = [
                (bottomScreen[0], bottomScreen[1] + scaledTileHeight),
                (rightScreen[0] + halfW, rightScreen[1] + halfH),
                (rightScreen[0] + halfW, rightScreen[1] + halfH + scaledBlockHeight),
                (bottomScreen[0], bottomScreen[1] + scaledTileHeight + scaledBlockHeight)
            ]
        
        # Draw highlight outline (white with some transparency)
        highlightColor = (255, 255, 255, 180)
        
        # Draw outlines
        pygame.draw.polygon(self.screen, highlightColor, topPoints, 2)
        pygame.draw.polygon(self.screen, highlightColor, leftPoints, 2)
        pygame.draw.polygon(self.screen, highlightColor, rightPoints, 2)
        
        self.highlightedBlock = (baseX, baseY, baseZ)

    def _saveBuilding(self, filename: str = None, silent: bool = False):
        """Save the current building to a compressed JSON file (gzip) with atomic write"""
        import json
        import gzip
        from datetime import datetime
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"build_{timestamp}.json.gz"
        
        # Ensure filename has .gz extension for new saves
        if not filename.endswith('.gz'):
            filename = filename + '.gz'
        
        # Create saves directory if it doesn't exist
        os.makedirs(SAVES_DIR, exist_ok=True)
        
        filepath = os.path.join(SAVES_DIR, filename)
        tempPath = filepath + '.tmp'
        
        # Collect block data with proper enum serialization
        blocks = []
        for (x, y, z), blockType in self.world.blocks.items():
            blockData = {
                "x": x, "y": y, "z": z,
                "type": blockType.name
            }
            # Include properties if present - serialize enums as names
            props = self.world.getBlockProperties(x, y, z)
            if props:
                if props.facing:
                    blockData["facing"] = props.facing.name if hasattr(props.facing, 'name') else str(props.facing)
                if props.isOpen:
                    blockData["isOpen"] = props.isOpen
                if props.slabPosition:
                    blockData["slabPosition"] = props.slabPosition.name if hasattr(props.slabPosition, 'name') else str(props.slabPosition)
            blocks.append(blockData)
        
        saveData = {
            "version": 3,  # Version 3 = atomic writes + proper enum serialization
            "dimension": self.currentDimension,
            "blocks": blocks
        }
        
        try:
            # Atomic write: write to temp file first, then rename
            jsonStr = json.dumps(saveData, separators=(',', ':'))  # Compact JSON
            with gzip.open(tempPath, 'wt', encoding='utf-8') as f:
                f.write(jsonStr)
            # Atomic rename - prevents corruption if write fails mid-way
            os.replace(tempPath, filepath)
            if not silent:
                print(f"Build saved to {filepath} (compressed)")
                self.tooltipText = "Build saved!"
                self.tooltipTimer = 1500
            return True
        except Exception as e:
            if not silent:
                print(f"Error saving build: {e}")
                self.tooltipText = f"Save failed: {e}"
                self.tooltipTimer = 3000
            # Clean up temp file if it exists
            if os.path.exists(tempPath):
                try:
                    os.remove(tempPath)
                except OSError:
                    pass
            return False
    
    def _loadBuilding(self, filename: str, silent: bool = False):
        """Load a building from a JSON file (supports both compressed .gz and plain .json)"""
        import json
        import gzip
        
        filepath = os.path.join(SAVES_DIR, filename)
        
        if not os.path.exists(filepath):
            if not silent:
                print(f"Save file not found: {filepath}")
            self.tooltipText = f"File not found: {filename}"
            self.tooltipTimer = 2000
            return False
        
        try:
            # Try to load as gzip first, fall back to plain JSON
            try:
                with gzip.open(filepath, 'rt', encoding='utf-8') as f:
                    saveData = json.load(f)
            except (gzip.BadGzipFile, OSError):
                # Not a gzip file, try plain JSON
                with open(filepath, 'r') as f:
                    saveData = json.load(f)
            
            # Validate save file structure
            if not isinstance(saveData, dict) or "blocks" not in saveData:
                raise ValueError("Invalid save file format")
            
            # Clear current world (except floor)
            self.world.clear()
            if hasattr(self, 'liquidSpriteCache'):
                self.liquidSpriteCache.clear()
            
            # Set dimension if present
            if "dimension" in saveData:
                self._switchDimension(saveData["dimension"])
            
            # Track loading statistics
            loadedCount = 0
            skippedCount = 0
            
            # Load blocks with proper enum deserialization
            for blockData in saveData.get("blocks", []):
                try:
                    # Validate required fields
                    if not all(k in blockData for k in ("x", "y", "z", "type")):
                        skippedCount += 1
                        continue
                    
                    blockType = BlockType[blockData["type"]]
                    x, y, z = int(blockData["x"]), int(blockData["y"]), int(blockData["z"])
                    self.world.setBlock(x, y, z, blockType)
                    loadedCount += 1
                    
                    # Restore properties if present - properly deserialize enums
                    if "facing" in blockData or "isOpen" in blockData or "slabPosition" in blockData:
                        props = BlockProperties()
                        if "facing" in blockData:
                            facing = blockData["facing"]
                            # Handle both enum name strings and legacy raw values
                            if isinstance(facing, str):
                                try:
                                    props.facing = Facing[facing]
                                except KeyError:
                                    props.facing = Facing.SOUTH  # Default fallback
                            else:
                                props.facing = Facing.SOUTH
                        if "isOpen" in blockData:
                            props.isOpen = bool(blockData["isOpen"])
                        if "slabPosition" in blockData:
                            slabPos = blockData["slabPosition"]
                            # Handle both enum name strings and legacy raw values
                            if isinstance(slabPos, str):
                                try:
                                    props.slabPosition = SlabPosition[slabPos]
                                except KeyError:
                                    props.slabPosition = SlabPosition.BOTTOM
                            else:
                                props.slabPosition = SlabPosition.BOTTOM
                        self.world.setBlockProperties(x, y, z, props)
                except (KeyError, ValueError, TypeError) as e:
                    skippedCount += 1
                    if not silent:
                        print(f"Skipping invalid block: {e}")
            
            # Mark lighting as dirty for recalculation
            self.lightingDirty = True
            
            if not silent:
                print(f"Build loaded from {filepath} ({loadedCount} blocks, {skippedCount} skipped)")
                self.tooltipText = f"Loaded {loadedCount} blocks"
                self.tooltipTimer = 2000
            return True
        except json.JSONDecodeError as e:
            print(f"Error: Corrupted save file: {e}")
            self.tooltipText = "Error: Corrupted save file"
            self.tooltipTimer = 3000
            return False
        except Exception as e:
            print(f"Error loading build: {e}")
            self.tooltipText = f"Load failed: {e}"
            self.tooltipTimer = 3000
            return False
    
    def _openLoadDialog(self):
        """Open a file dialog to select and load a save file"""
        try:
            import tkinter as tk
            from tkinter import filedialog
            
            # Create a hidden root window
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)  # Bring dialog to front
            
            # Set the initial directory to saves folder
            os.makedirs(SAVES_DIR, exist_ok=True)
            
            # Open file dialog
            filepath = filedialog.askopenfilename(
                title="Load Build",
                initialdir=SAVES_DIR,
                filetypes=[("Build files", "*.json *.json.gz"), ("JSON files", "*.json"), ("Compressed", "*.json.gz"), ("All files", "*.*")]
            )
            
            root.destroy()
            
            # Load the selected file
            if filepath:
                filename = os.path.basename(filepath)
                # If the file is in the saves directory, just use the filename
                if os.path.dirname(filepath) == SAVES_DIR:
                    self._loadBuilding(filename)
                else:
                    # If it's from elsewhere, load directly from the full path
                    self._loadBuildingFromPath(filepath)
        except Exception as e:
            print(f"Error opening load dialog: {e}")
            # Fallback: try to load most recent save from saves folder
            saveFiles = self._getSaveFiles()
            if saveFiles:
                print(f"Loading most recent save: {saveFiles[0]}")
                self._loadBuilding(saveFiles[0])
            else:
                print("No save files found in saves folder")
    
    def _loadBuildingFromPath(self, filepath: str):
        """Load a building from a full file path with proper enum deserialization"""
        if not os.path.exists(filepath):
            print(f"Save file not found: {filepath}")
            self.tooltipText = "File not found"
            self.tooltipTimer = 2000
            return False
        
        try:
            # Try to load as gzip first, fall back to plain JSON
            import gzip
            try:
                with gzip.open(filepath, 'rt', encoding='utf-8') as f:
                    saveData = json.load(f)
            except (gzip.BadGzipFile, OSError):
                # Not a gzip file, try plain JSON
                with open(filepath, 'r') as f:
                    saveData = json.load(f)
            
            # Validate save file structure
            if not isinstance(saveData, dict) or "blocks" not in saveData:
                raise ValueError("Invalid save file format")
            
            # Clear current world (except floor)
            self.world.clear()
            if hasattr(self, 'liquidSpriteCache'):
                self.liquidSpriteCache.clear()
            
            # Set dimension if present
            if "dimension" in saveData:
                self._switchDimension(saveData["dimension"])
            
            loadedCount = 0
            
            # Load blocks with proper enum deserialization
            for blockData in saveData.get("blocks", []):
                try:
                    blockType = BlockType[blockData["type"]]
                    x, y, z = int(blockData["x"]), int(blockData["y"]), int(blockData["z"])
                    self.world.setBlock(x, y, z, blockType)
                    loadedCount += 1
                    
                    # Restore properties if present - properly deserialize enums
                    if "facing" in blockData or "isOpen" in blockData or "slabPosition" in blockData:
                        props = BlockProperties()
                        if "facing" in blockData:
                            facing = blockData["facing"]
                            if isinstance(facing, str):
                                try:
                                    props.facing = Facing[facing]
                                except KeyError:
                                    props.facing = Facing.SOUTH
                            else:
                                props.facing = Facing.SOUTH
                        if "isOpen" in blockData:
                            props.isOpen = bool(blockData["isOpen"])
                        if "slabPosition" in blockData:
                            slabPos = blockData["slabPosition"]
                            if isinstance(slabPos, str):
                                try:
                                    props.slabPosition = SlabPosition[slabPos]
                                except KeyError:
                                    props.slabPosition = SlabPosition.BOTTOM
                            else:
                                props.slabPosition = SlabPosition.BOTTOM
                        self.world.setBlockProperties(x, y, z, props)
                except (KeyError, ValueError, TypeError) as e:
                    print(f"Skipping invalid block: {e}")
            
            # Mark lighting as dirty for recalculation
            self.lightingDirty = True
            
            # Only show tooltip for user-initiated loads, not internal/tutorial loads
            # self.tooltipText = f"Loaded {loadedCount} blocks"
            # self.tooltipTimer = 2000
            return True
        except json.JSONDecodeError as e:
            print(f"Error: Corrupted save file: {e}")
            self.tooltipText = "Error: Corrupted save file"
            self.tooltipTimer = 3000
            return False
        except Exception as e:
            print(f"Error loading build: {e}")
            self.tooltipText = f"Load failed: {e}"
            self.tooltipTimer = 3000
            return False
    
    def _getSaveFiles(self) -> List[str]:
        """Get list of saved build files (both .json and .json.gz)"""
        if not os.path.exists(SAVES_DIR):
            return []
        
        files = [f for f in os.listdir(SAVES_DIR) if f.endswith('.json') or f.endswith('.json.gz')]
        files.sort(reverse=True)  # Most recent first
        return files
    
    # ============ NEW FEATURE METHODS ============
    
    def _takeScreenshot(self):
        """Take a screenshot and save it to the screenshots folder"""
        from datetime import datetime
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.png"
        filepath = os.path.join(self.screenshotsDir, filename)
        
        try:
            pygame.image.save(self.screen, filepath)
            print(f"Screenshot saved: {filepath}")
            self.assetManager.playClickSound()
        except Exception as e:
            print(f"Error saving screenshot: {e}")
    
    def _quickSave(self, slot: int):
        """Quick save to a numbered slot"""
        filename = f"quicksave_{slot}.json"
        if self._saveBuilding(filename):
            self.quickSaveSlots[slot] = filename
            print(f"Quick saved to slot {slot}")
    
    def _quickLoad(self, slot: int):
        """Quick load from a numbered slot"""
        filename = f"quicksave_{slot}.json"
        filepath = os.path.join(SAVES_DIR, filename)
        
        if os.path.exists(filepath):
            self._loadBuilding(filename)
            print(f"Quick loaded from slot {slot}")
        else:
            print(f"No quick save in slot {slot}")
    
    def _placeBlockWithUndo(self, x: int, y: int, z: int, blockType: BlockType):
        """Place a block with undo support"""
        from engine.undo import PlaceBlockCommand
        
        # Create and execute command through undo manager
        cmd = PlaceBlockCommand(
            world=self.world,
            x=x, y=y, z=z,
            block_type=blockType,
            properties=BlockProperties() if self._isSpecialBlock(blockType) else None
        )
        
        if self.undoManager.execute(cmd):
            # Update build height tracker
            self.currentBuildHeight = max(self.currentBuildHeight, z)
            return True
        return False
    
    def _removeBlockWithUndo(self, x: int, y: int, z: int):
        """Remove a block with undo support"""
        from engine.undo import RemoveBlockCommand
        
        cmd = RemoveBlockCommand(world=self.world, x=x, y=y, z=z)
        return self.undoManager.execute(cmd)
    
    def _isSpecialBlock(self, blockType: BlockType) -> bool:
        """Check if a block type needs special properties"""
        definition = BLOCK_DEFINITIONS.get(blockType)
        if definition:
            return definition.isStair or definition.isSlab or definition.isDoor
        return False
    
    def _renderBlockTooltip(self) -> None:
        """Render tooltip showing block name when hovering over a placed block"""
        if not self.showBlockTooltip or self.panelHovered:
            return
        
        if self.hoveredCell is None:
            return
        
        x, y, z = self.hoveredCell
        blockType = self.world.getBlock(x, y, z)
        
        # Horror: Rare glitch where AIR shows "???" tooltip (0.01% chance)
        if blockType == BlockType.AIR:
            if self.horrorEnabled and random.random() < 0.0001:
                # Show glitched tooltip for empty space
                blockName = "???"
            else:
                return
        else:
            # Get block name
            definition = BLOCK_DEFINITIONS.get(blockType)
            if definition:
                blockName = definition.name
            else:
                blockName = blockType.name.replace('_', ' ').title()
            
            # Horror: Rare "HELP" tooltip glitch (0.1% chance)
            if self.horrorEnabled and random.random() < 0.001:
                blockName = random.choice(["HELP", "???", blockName, "WATCHING"])
        
        # Get mouse position
        mouseX, mouseY = pygame.mouse.get_pos()
        
        # Render tooltip
        text = self.smallFont.render(blockName, True, (255, 255, 255))
        textWidth = text.get_width()
        textHeight = text.get_height()
        
        padding = 6
        tooltipWidth = textWidth + padding * 2
        tooltipHeight = textHeight + padding * 2
        
        tooltipX = mouseX + 15
        tooltipY = mouseY - tooltipHeight - 5
        
        # Keep on screen
        if tooltipX + tooltipWidth > WINDOW_WIDTH:
            tooltipX = mouseX - tooltipWidth - 5
        if tooltipY < 0:
            tooltipY = mouseY + 20
        
        # Draw background
        tooltipBg = pygame.Surface((tooltipWidth, tooltipHeight), pygame.SRCALPHA)
        tooltipBg.fill((30, 30, 40, 230))
        self.screen.blit(tooltipBg, (tooltipX, tooltipY))
        
        # Border
        pygame.draw.rect(self.screen, (100, 100, 120),
                        (tooltipX, tooltipY, tooltipWidth, tooltipHeight), 1)
        
        # Text
        self.screen.blit(text, (tooltipX + padding, tooltipY + padding))
    
    def _renderHeightIndicator(self) -> None:
        """Render current building height indicator"""
        if self.hoveredCell is None:
            return
        
        _, _, z = self.hoveredCell
        
        # Draw compact height indicator near cursor
        text = f"Z: {z}"
        textSurf = self.font.render(text, True, (100, 200, 100))
        
        # Position at top-left of screen
        padding = 4
        bgRect = pygame.Rect(10 - padding, 10 - padding,
                            textSurf.get_width() + padding * 2,
                            textSurf.get_height() + padding * 2)
        
        bgSurf = pygame.Surface((bgRect.width, bgRect.height), pygame.SRCALPHA)
        bgSurf.fill((30, 30, 40, 180))
        self.screen.blit(bgSurf, bgRect.topleft)
        
        self.screen.blit(textSurf, (10, 10))
    
    # ==================== QOL FEATURE METHODS ====================
    
    def _scrollToBlock(self, blockType: BlockType):
        """Auto-scroll panel to show a specific block"""
        # Find which category contains this block
        targetCategory = None
        for category, blocks in BLOCK_CATEGORIES.items():
            if blockType in blocks:
                targetCategory = category
                break
        
        if not targetCategory:
            return
        
        # Expand the category if collapsed
        self.expandedCategories[targetCategory] = True
        
        # Calculate approximate Y position of block in panel
        mainButtonHeight = 35
        subCategoryHeight = 24
        slotSize = ICON_SIZE + 8
        headerHeight = 10
        slotsPerRow = (PANEL_WIDTH - 20) // slotSize
        
        yPos = headerHeight + mainButtonHeight + 5  # After main blocks button
        
        for category in CATEGORY_ORDER:
            if category == "Problematic" or category == "Experimental":
                continue
            
            blocks = BLOCK_CATEGORIES.get(category, [])
            isExpanded = self.expandedCategories.get(category, False)
            
            yPos += subCategoryHeight  # Category header
            
            if category == targetCategory:
                # Found the category, now find block position within it
                if blockType in blocks:
                    blockIdx = blocks.index(blockType)
                    row = blockIdx // slotsPerRow
                    yPos += row * slotSize + slotSize // 2
                break
            
            if isExpanded:
                rows = (len(blocks) + slotsPerRow - 1) // slotsPerRow
                yPos += rows * slotSize + 5
        
        # Scroll to center the block in view
        targetScroll = max(0, yPos - WINDOW_HEIGHT // 2)
        self.inventoryScroll = targetScroll
    
    def _updateSearchResults(self):
        """Update search results based on current query"""
        if not self.searchQuery:
            self.searchResults = []
            return
        
        self.searchResults = []
        query = self.searchQuery.lower()
        
        for blockType in BlockType:
            blockDef = BLOCK_DEFINITIONS.get(blockType)
            if blockDef:
                name = blockDef.name.lower()
            else:
                name = blockType.name.replace('_', ' ').lower()
            
            if query in name:
                self.searchResults.append(blockType)
        
        # Limit to first 20 results
        self.searchResults = self.searchResults[:20]
    
    def _updatePanelHover(self, mouseX: int, mouseY: int):
        """Update which block in the panel is being hovered"""
        oldHovered = self.hoveredPanelBlock
        self.hoveredPanelBlock = None
        
        panelX = mouseX - (WINDOW_WIDTH - PANEL_WIDTH)
        panelY = mouseY
        
        # Match panel layout
        mainButtonHeight = 35
        subCategoryHeight = 24
        slotSize = ICON_SIZE + 8
        headerHeight = 10
        currentY = headerHeight - self.inventoryScroll
        
        # Skip main blocks button
        currentY += mainButtonHeight + 5
        
        if not self.blocksExpanded:
            return
        
        # Check block categories
        for category in CATEGORY_ORDER:
            if category == "Problematic" or category == "Experimental":
                continue
            
            blocks = BLOCK_CATEGORIES.get(category, [])
            isExpanded = self.expandedCategories.get(category, False)
            
            currentY += subCategoryHeight
            
            if isExpanded:
                blocksStartY = currentY + 2
                
                for i, blockType in enumerate(blocks):
                    row = i // ICONS_PER_ROW
                    col = i % ICONS_PER_ROW
                    
                    btnX = ICON_MARGIN + col * (slotSize + 4)
                    btnY = blocksStartY + row * (slotSize + 4)
                    
                    if btnX <= panelX <= btnX + slotSize and btnY <= panelY <= btnY + slotSize:
                        self.hoveredPanelBlock = blockType
                        if oldHovered != blockType:
                            self.panelHoverTime = pygame.time.get_ticks()
                        return
                
                numRows = (len(blocks) + ICONS_PER_ROW - 1) // ICONS_PER_ROW
                currentY += numRows * (slotSize + 4) + 5
        
        # Reset hover time if nothing hovered
        if self.hoveredPanelBlock is None:
            self.panelHoverTime = 0
    
    def _renderPanelBlockTooltip(self):
        """Render tooltip for hovered block in panel"""
        if not self.hoveredPanelBlock:
            return
        
        # Only show after delay
        if pygame.time.get_ticks() - self.panelHoverTime < self.tooltipDelay:
            return
        
        # Get block name
        blockDef = BLOCK_DEFINITIONS.get(self.hoveredPanelBlock)
        if blockDef:
            blockName = blockDef.name
        else:
            blockName = self.hoveredPanelBlock.name.replace('_', ' ').title()
        
        mouseX, mouseY = pygame.mouse.get_pos()
        
        textSurf = self.smallFont.render(blockName, True, (255, 255, 255))
        padding = 6
        tooltipWidth = textSurf.get_width() + padding * 2
        tooltipHeight = textSurf.get_height() + padding * 2
        
        # Position to left of cursor (since panel is on right)
        tooltipX = mouseX - tooltipWidth - 10
        tooltipY = mouseY - tooltipHeight // 2
        
        # Keep on screen
        if tooltipX < 0:
            tooltipX = mouseX + 15
        if tooltipY < 0:
            tooltipY = 5
        
        # Background
        bgSurf = pygame.Surface((tooltipWidth, tooltipHeight), pygame.SRCALPHA)
        bgSurf.fill((30, 30, 40, 230))
        self.screen.blit(bgSurf, (tooltipX, tooltipY))
        pygame.draw.rect(self.screen, (100, 100, 120), (tooltipX, tooltipY, tooltipWidth, tooltipHeight), 1)
        
        # Text
        self.screen.blit(textSurf, (tooltipX + padding, tooltipY + padding))

    def _addToRecentBlocks(self, blockType: BlockType):
        """Add a block to recent blocks list"""
        if blockType in self.recentBlocks:
            self.recentBlocks.remove(blockType)
        self.recentBlocks.insert(0, blockType)
        if len(self.recentBlocks) > self.maxRecentBlocks:
            self.recentBlocks = self.recentBlocks[:self.maxRecentBlocks]
    
    def _toggleFavorite(self, blockType: BlockType):
        """Toggle a block in/out of favorites list"""
        if blockType in self.favoriteBlocks:
            self.favoriteBlocks.remove(blockType)
            self.tooltipText = f"Removed {blockType.name} from favorites"
        else:
            if len(self.favoriteBlocks) < self.maxFavorites:
                self.favoriteBlocks.append(blockType)
                self.tooltipText = f"Added {blockType.name} to favorites"
            else:
                self.tooltipText = "Favorites full! (max 9)"
        self.tooltipTimer = 1500
        self._saveAppConfig()  # Save immediately
    
    def _updateHotbarSlot(self, slot: int, blockType: BlockType):
        """Update a hotbar slot with a new block type"""
        if 0 <= slot < len(self.hotbar):
            self.hotbar[slot] = blockType
    
    def _eyedropperBlock(self, mouseX: int, mouseY: int):
        """Pick block type from world at mouse position (eyedropper tool)"""
        if not self.hoveredCell:
            return False
        
        x, y, z = self.hoveredCell
        # Find the top-most block at this position
        for checkZ in range(z, -1, -1):
            blockType = self.world.getBlock(x, y, checkZ)
            if blockType != BlockType.AIR:
                self.selectedBlock = blockType
                self._addToRecentBlocks(blockType)
                # Also update current hotbar slot
                self.hotbar[self.hotbarSelectedSlot] = blockType
                self.assetManager.playClickSound()
                self.tooltipText = f"Picked: {blockType.name}"
                self.tooltipTimer = 1500
                return True
        return False
    
    def _quickSwapBlock(self, mouseX: int, mouseY: int):
        """Replace block at mouse position with selected block (quick swap tool)"""
        if not self.hoveredCell:
            return False
        
        x, y, z = self.hoveredCell
        # Find the top-most block at this position to replace
        for checkZ in range(z, -1, -1):
            existingBlock = self.world.getBlock(x, y, checkZ)
            if existingBlock != BlockType.AIR:
                # Don't swap if it's the same block type
                if existingBlock == self.selectedBlock:
                    return False
                
                # Record undo action (old block -> new block)
                self.undoManager.recordPlacement(x, y, checkZ, existingBlock, self.selectedBlock)
                
                # Replace with selected block
                self.world.setBlock(x, y, checkZ, self.selectedBlock)
                
                # Handle block properties if needed (e.g., doors)
                blockDef = BLOCK_DEFINITIONS.get(self.selectedBlock)
                if blockDef and blockDef.isDoor:
                    # Set default facing and closed state
                    self.world.setBlockProperties(x, y, checkZ, BlockProperties(facing="south", isOpen=False))
                
                # Visual feedback
                self.assetManager.playPlaceSound()
                self._addToRecentBlocks(self.selectedBlock)
                self.tooltipText = f"Swapped: {existingBlock.name} -> {self.selectedBlock.name}"
                self.tooltipTimer = 1500
                return True
        return False
    
    def _handleMeasurementClick(self):
        """Handle click in measurement mode to set points"""
        if not self.hoveredCell:
            return
        
        x, y, z = self.hoveredCell
        
        if self.measurePoint1 is None:
            # Set first point
            self.measurePoint1 = (x, y, z)
            self.tooltipText = f"Point 1: ({x}, {y}, {z}) - Click second point"
            self.tooltipTimer = 2000
            self.assetManager.playClickSound()
        else:
            # Set second point and calculate distance
            self.measurePoint2 = (x, y, z)
            
            # Calculate 3D distance
            dx = self.measurePoint2[0] - self.measurePoint1[0]
            dy = self.measurePoint2[1] - self.measurePoint1[1]
            dz = self.measurePoint2[2] - self.measurePoint1[2]
            
            distance = (dx**2 + dy**2 + dz**2) ** 0.5
            
            # Calculate manhattan distance (block distance)
            blockDist = abs(dx) + abs(dy) + abs(dz)
            
            self.tooltipText = f"Distance: {distance:.1f} blocks (X:{abs(dx)} Y:{abs(dy)} Z:{abs(dz)} = {blockDist} blocks)"
            self.tooltipTimer = 5000
            self.assetManager.playClickSound()
    
    def _handleReplaceModeClick(self):
        """Handle click in replace mode - select source block type then replace all with selected"""
        if not self.hoveredCell:
            return
        
        x, y, z = self.hoveredCell
        
        # Find the block at hover position
        for checkZ in range(z, -1, -1):
            blockType = self.world.getBlock(x, y, checkZ)
            if blockType != BlockType.AIR:
                if self.replaceSourceBlock is None:
                    # First click - select source block type
                    self.replaceSourceBlock = blockType
                    self.tooltipText = f"Replace all {blockType.name} with {self.selectedBlock.name}? Click again to confirm"
                    self.tooltipTimer = 3000
                    self.assetManager.playClickSound()
                else:
                    # Second click - perform replacement
                    if blockType == self.replaceSourceBlock:
                        replaced = self._replaceAllBlocks(self.replaceSourceBlock, self.selectedBlock)
                        self.tooltipText = f"Replaced {replaced} blocks: {self.replaceSourceBlock.name} -> {self.selectedBlock.name}"
                        self.tooltipTimer = 2000
                        self.replaceSourceBlock = None
                        self.replaceMode = False
                        self.assetManager.playPlaceSound()
                    else:
                        # Clicked different block, start over
                        self.replaceSourceBlock = blockType
                        self.tooltipText = f"Replace all {blockType.name} with {self.selectedBlock.name}? Click again to confirm"
                        self.tooltipTimer = 3000
                        self.assetManager.playClickSound()
                return
        
        # Clicked on air
        self.tooltipText = "Click on a block to replace"
        self.tooltipTimer = 1500
    
    def _replaceAllBlocks(self, sourceType: BlockType, targetType: BlockType) -> int:
        """Replace all blocks of sourceType with targetType"""
        count = 0
        positions = list(self.world.blocks.keys())
        
        for pos in positions:
            if self.world.blocks[pos] == sourceType:
                x, y, z = pos
                # Record for undo
                self.undoManager.recordPlacement(x, y, z, sourceType, targetType)
                self.world.setBlock(x, y, z, targetType)
                count += 1
        
        self.lightingDirty = True
        return count
    
    def _handleMagicWandClick(self):
        """Handle click in magic wand mode - select all connected blocks of same type"""
        if not self.hoveredCell:
            return
        
        x, y, z = self.hoveredCell
        
        # Find the block at hover position
        for checkZ in range(z, -1, -1):
            blockType = self.world.getBlock(x, y, checkZ)
            if blockType != BlockType.AIR:
                # Flood fill to find all connected blocks of same type
                self.magicWandSelection = self._floodFillSelect(x, y, checkZ, blockType)
                count = len(self.magicWandSelection)
                self.tooltipText = f"Selected {count} connected {blockType.name} blocks. Press Del to remove or click to place"
                self.tooltipTimer = 3000
                self.assetManager.playClickSound()
                return
        
        # Clicked on air - clear selection
        self.magicWandSelection.clear()
        self.tooltipText = "Click on a block to select connected"
        self.tooltipTimer = 1500
    
    def _floodFillSelect(self, startX: int, startY: int, startZ: int, blockType: BlockType) -> Set[Tuple[int, int, int]]:
        """Flood fill to select all connected blocks of the same type"""
        selected = set()
        toCheck = [(startX, startY, startZ)]
        checked = set()
        
        while toCheck:
            x, y, z = toCheck.pop()
            if (x, y, z) in checked:
                continue
            checked.add((x, y, z))
            
            # Check bounds
            if not (0 <= x < GRID_WIDTH and 0 <= y < GRID_DEPTH and 0 <= z < GRID_HEIGHT):
                continue
            
            # Check if same block type
            if self.world.getBlock(x, y, z) == blockType:
                selected.add((x, y, z))
                
                # Add neighbors (6-connected)
                for dx, dy, dz in [(1,0,0), (-1,0,0), (0,1,0), (0,-1,0), (0,0,1), (0,0,-1)]:
                    neighbor = (x + dx, y + dy, z + dz)
                    if neighbor not in checked:
                        toCheck.append(neighbor)
        
        return selected
    
    def _floodFill3D(self, startX: int, startY: int, startZ: int, fillBlockType: BlockType, maxFill: int = 1000) -> int:
        """Flood fill empty space with a block type (fill enclosed spaces)"""
        toFill = []
        toCheck = [(startX, startY, startZ)]
        checked = set()
        
        while toCheck and len(toFill) < maxFill:
            x, y, z = toCheck.pop()
            if (x, y, z) in checked:
                continue
            checked.add((x, y, z))
            
            # Check bounds
            if not (0 <= x < GRID_WIDTH and 0 <= y < GRID_DEPTH and 0 <= z < GRID_HEIGHT):
                continue
            
            # Only fill AIR blocks
            if self.world.getBlock(x, y, z) == BlockType.AIR:
                toFill.append((x, y, z))
                
                # Add neighbors (6-connected)
                for dx, dy, dz in [(1,0,0), (-1,0,0), (0,1,0), (0,-1,0), (0,0,1), (0,0,-1)]:
                    neighbor = (x + dx, y + dy, z + dz)
                    if neighbor not in checked:
                        toCheck.append(neighbor)
        
        # Fill all positions found
        from engine.undo import BatchCommand, PlaceBlockCommand
        commands = []
        
        for x, y, z in toFill:
            cmd = PlaceBlockCommand(self.world, x, y, z, fillBlockType, None)
            commands.append(cmd)
        
        if commands:
            batch = BatchCommand(commands)
            self.undoManager.execute(batch)
        
        self.lightingDirty = True
        return len(toFill)
    
    def _deleteMagicWandSelection(self):
        """Delete all blocks in magic wand selection"""
        if not self.magicWandSelection:
            return
        
        count = 0
        for x, y, z in self.magicWandSelection:
            blockType = self.world.getBlock(x, y, z)
            if blockType != BlockType.AIR:
                # Record for undo
                self.undoManager.recordPlacement(x, y, z, blockType, BlockType.AIR)
                self.world.setBlock(x, y, z, BlockType.AIR)
                count += 1
        
        # Clear selection
        self.magicWandSelection.clear()
        self.lightingDirty = True
        
        self.tooltipText = f"Deleted {count} blocks"
        self.tooltipTimer = 2000
        self.assetManager.playClickSound()
    
    def _toggleStampMode(self):
        """Toggle stamp/clone tool mode using clipboard content"""
        if not self.clipboard:
            self.tooltipText = "Copy a selection first (Ctrl+B, Ctrl+C)"
            self.tooltipTimer = 2000
            return
        
        self.stampMode = not self.stampMode
        
        if self.stampMode:
            # Convert clipboard to stamp data (relative positions)
            self._loadStampFromClipboard()
            count = len(self.stampData)
            self.tooltipText = f"Stamp Mode: Click to place ({count} blocks). Press P to exit"
        else:
            self.stampData.clear()
            self.stampOrigin = None
            self.tooltipText = "Stamp Mode: OFF"
        
        self.tooltipTimer = 2000
        self.assetManager.playClickSound()
    
    def _loadStampFromClipboard(self):
        """Load clipboard content into stamp data with relative positions"""
        if not self.clipboard:
            return
        
        self.stampData.clear()
        
        # Clipboard is a list of (relPos, blockType, props)
        for relPos, blockType, props in self.clipboard:
            self.stampData[relPos] = blockType
    
    def _handleStampClick(self):
        """Handle click in stamp mode - place stamp at click location"""
        if not self.hoveredCell or not self.stampData:
            return
        
        baseX, baseY, baseZ = self.hoveredCell
        count = 0
        
        for (relX, relY, relZ), blockType in self.stampData.items():
            x = baseX + relX
            y = baseY + relY
            z = baseZ + relZ
            
            # Check bounds
            if not (0 <= x < GRID_WIDTH and 0 <= y < GRID_DEPTH and 0 <= z < GRID_HEIGHT):
                continue
            
            # Record for undo and place
            oldBlock = self.world.getBlock(x, y, z)
            self.undoManager.recordPlacement(x, y, z, oldBlock, blockType)
            self.world.setBlock(x, y, z, blockType)
            count += 1
        
        self.lightingDirty = True
        self.tooltipText = f"Stamped {count} blocks"
        self.tooltipTimer = 1000
        self.assetManager.playClickSound()

    def _renderMeasurementLine(self):
        """Render measurement line and distance between two points"""
        if not self.measurementMode:
            return
        
        # Draw point 1 marker
        if self.measurePoint1:
            x1, y1, z1 = self.measurePoint1
            screenX1, screenY1 = self.renderer.worldToScreen(x1, y1, z1)
            
            # Draw a marker at point 1
            markerSurf = pygame.Surface((20, 20), pygame.SRCALPHA)
            pygame.draw.circle(markerSurf, (0, 255, 0, 180), (10, 10), 8, 3)
            pygame.draw.circle(markerSurf, (0, 255, 0, 100), (10, 10), 5)
            self.screen.blit(markerSurf, (screenX1 - 10, screenY1 + TILE_HEIGHT // 2 - 10))
            
            # Label
            label1 = self.smallFont.render("1", True, (0, 255, 0))
            self.screen.blit(label1, (screenX1 + 10, screenY1 + TILE_HEIGHT // 2 - 8))
        
        # Draw point 2 marker and line if both points set
        if self.measurePoint1 and self.measurePoint2:
            x2, y2, z2 = self.measurePoint2
            screenX2, screenY2 = self.renderer.worldToScreen(x2, y2, z2)
            
            # Draw a marker at point 2
            markerSurf = pygame.Surface((20, 20), pygame.SRCALPHA)
            pygame.draw.circle(markerSurf, (255, 100, 0, 180), (10, 10), 8, 3)
            pygame.draw.circle(markerSurf, (255, 100, 0, 100), (10, 10), 5)
            self.screen.blit(markerSurf, (screenX2 - 10, screenY2 + TILE_HEIGHT // 2 - 10))
            
            # Label
            label2 = self.smallFont.render("2", True, (255, 100, 0))
            self.screen.blit(label2, (screenX2 + 10, screenY2 + TILE_HEIGHT // 2 - 8))
            
            # Draw dashed line between points
            x1, y1, z1 = self.measurePoint1
            screenX1, screenY1 = self.renderer.worldToScreen(x1, y1, z1)
            
            # Adjust to center of tiles
            p1 = (screenX1, screenY1 + TILE_HEIGHT // 2)
            p2 = (screenX2, screenY2 + TILE_HEIGHT // 2)
            
            # Draw dashed line
            dashLen = 8
            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            dist = max(1, (dx**2 + dy**2) ** 0.5)
            numDashes = int(dist / dashLen)
            
            for i in range(0, numDashes, 2):
                startRatio = i / numDashes
                endRatio = min((i + 1) / numDashes, 1)
                startP = (int(p1[0] + dx * startRatio), int(p1[1] + dy * startRatio))
                endP = (int(p1[0] + dx * endRatio), int(p1[1] + dy * endRatio))
                pygame.draw.line(self.screen, (255, 255, 0), startP, endP, 2)
            
            # Draw distance label at midpoint
            midX = (p1[0] + p2[0]) // 2
            midY = (p1[1] + p2[1]) // 2
            
            dx_blocks = abs(self.measurePoint2[0] - self.measurePoint1[0])
            dy_blocks = abs(self.measurePoint2[1] - self.measurePoint1[1])
            dz_blocks = abs(self.measurePoint2[2] - self.measurePoint1[2])
            distance = ((dx_blocks**2 + dy_blocks**2 + dz_blocks**2) ** 0.5)
            
            distText = f"{distance:.1f}"
            distSurf = self.font.render(distText, True, (255, 255, 0))
            
            # Background for readability
            bgSurf = pygame.Surface((distSurf.get_width() + 8, distSurf.get_height() + 4), pygame.SRCALPHA)
            bgSurf.fill((0, 0, 0, 160))
            self.screen.blit(bgSurf, (midX - distSurf.get_width() // 2 - 4, midY - distSurf.get_height() // 2 - 2))
            self.screen.blit(distSurf, (midX - distSurf.get_width() // 2, midY - distSurf.get_height() // 2))

    def _autoSave(self):
        """Perform auto-save if enabled and interval has passed"""
        if not self.autoSaveEnabled:
            return
        
        currentTime = pygame.time.get_ticks()
        if currentTime - self.lastAutoSaveTime >= self.autoSaveInterval:
            # Create rolling backup before auto-save
            if self.autoBackupEnabled:
                self._createRollingBackup()
            
            self._saveBuilding(os.path.basename(self.autoSavePath), silent=True)
            self.lastAutoSaveTime = currentTime
            
            # Show "Saved" indicator for ~1 second (60 frames at 60fps)
            self.autoSaveFlashTimer = 60
            
            # Horror: Rare creepy autosave message (0.5% chance)
            if self.horrorEnabled and random.random() < 0.005:
                creepyMessages = [
                    "Saving... someone is watching",
                    "Saving... you are not alone",
                    "Saving... it remembers",
                    "Saving... we see you building",
                    "Saving..."  # Normal but the others are rare
                ]
                self.tooltipText = random.choice(creepyMessages)
                self.tooltipTimer = 2000
    
    def _createRollingBackup(self):
        """Create a rolling backup, maintaining only the last N backups"""
        import shutil
        from datetime import datetime
        
        try:
            os.makedirs(self.backupDir, exist_ok=True)
            
            # Get existing backups sorted by modification time
            backups = []
            if os.path.exists(self.backupDir):
                for f in os.listdir(self.backupDir):
                    if f.startswith("backup_") and (f.endswith(".json.gz") or f.endswith(".json")):
                        fpath = os.path.join(self.backupDir, f)
                        backups.append((fpath, os.path.getmtime(fpath)))
            
            # Sort by time (oldest first)
            backups.sort(key=lambda x: x[1])
            
            # Delete oldest backups if we have too many
            while len(backups) >= self.maxBackups:
                oldest = backups.pop(0)
                try:
                    os.remove(oldest[0])
                except OSError as e:
                    print(f"Warning: Could not remove old backup: {e}")
            
            # Create new backup with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backupFilename = f"backup_{timestamp}.json.gz"
            backupPath = os.path.join(self.backupDir, backupFilename)
            
            # Save current world as backup
            self._saveBackup(backupPath)
            
        except Exception as e:
            print(f"Backup error: {e}")
    
    def _saveBackup(self, filepath: str):
        """Save a backup to specified path (compressed) with atomic write"""
        import json
        import gzip
        
        blocks = []
        for (x, y, z), blockType in self.world.blocks.items():
            blockData = {"x": x, "y": y, "z": z, "type": blockType.name}
            props = self.world.getBlockProperties(x, y, z)
            if props:
                if props.facing:
                    blockData["facing"] = props.facing.name if hasattr(props.facing, 'name') else str(props.facing)
                if props.isOpen:
                    blockData["isOpen"] = props.isOpen
                if props.slabPosition:
                    blockData["slabPosition"] = props.slabPosition.name if hasattr(props.slabPosition, 'name') else str(props.slabPosition)
            blocks.append(blockData)
        
        saveData = {
            "version": 3,  # Version 3 = atomic writes + proper enum serialization
            "dimension": self.currentDimension,
            "blocks": blocks
        }
        
        try:
            # Atomic write: write to temp file, then rename
            tempPath = filepath + '.tmp'
            jsonStr = json.dumps(saveData, separators=(',', ':'))
            with gzip.open(tempPath, 'wt', encoding='utf-8') as f:
                f.write(jsonStr)
            # Atomic rename (prevents corruption if write fails mid-way)
            os.replace(tempPath, filepath)
        except (OSError, IOError) as e:
            print(f"Warning: Backup save failed: {e}")
            # Clean up temp file if it exists
            if os.path.exists(tempPath):
                try:
                    os.remove(tempPath)
                except OSError:
                    pass
    
    def _getBackupFiles(self) -> List[Tuple[str, str]]:
        """Get list of backup files with their timestamps"""
        from datetime import datetime
        
        backups = []
        if os.path.exists(self.backupDir):
            for f in os.listdir(self.backupDir):
                if f.startswith("backup_") and (f.endswith(".json.gz") or f.endswith(".json")):
                    fpath = os.path.join(self.backupDir, f)
                    mtime = os.path.getmtime(fpath)
                    timeStr = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
                    backups.append((f, timeStr))
        
        # Sort by name descending (newest first due to timestamp naming)
        backups.sort(reverse=True)
        return backups
    
    def _restoreBackup(self, filename: str) -> bool:
        """Restore world from a backup file"""
        filepath = os.path.join(self.backupDir, filename)
        if os.path.exists(filepath):
            return self._loadBuildingFromPath(filepath)
        return False
    
    def _updateMusicFade(self, dt: float):
        """Update music crossfade effect (fade-in and fade-out)"""
        targetVolume = self.musicVolume if hasattr(self, 'musicVolume') else 0.3
        
        # Handle fade-out (when switching dimensions)
        if hasattr(self, 'musicFadingOut') and self.musicFadingOut:
            self.musicFadeTimer += dt
            progress = min(1.0, self.musicFadeTimer / self.musicFadeDuration)
            
            # Fade out current track
            currentVolume = targetVolume * (1.0 - progress)
            pygame.mixer.music.set_volume(currentVolume)
            
            if progress >= 1.0:
                self.musicFadingOut = False
                pygame.mixer.music.stop()
                
                # Start the new dimension's music if pending
                if hasattr(self, 'pendingDimensionMusic') and self.pendingDimensionMusic:
                    dimension = self.pendingDimensionMusic
                    self.pendingDimensionMusic = None
                    
                    # Choose music directory based on dimension
                    if dimension == DIMENSION_NETHER:
                        musicDir = MUSIC_DIR_NETHER
                    elif dimension == DIMENSION_END:
                        musicDir = MUSIC_DIR_END
                    else:
                        musicDir = MUSIC_DIR
                    
                    # Collect all ogg files
                    self.musicFiles = []
                    if os.path.exists(musicDir):
                        for root, dirs, files in os.walk(musicDir):
                            for f in files:
                                if f.endswith('.ogg'):
                                    self.musicFiles.append(os.path.join(root, f))
                    
                    if self.musicFiles:
                        random.shuffle(self.musicFiles)
                        self.currentMusicIndex = 0
                        self._playNextSong()
            return
        
        # Handle fade-in
        if not hasattr(self, 'musicFadingIn') or not self.musicFadingIn:
            return
        
        self.musicFadeTimer += dt
        progress = min(1.0, self.musicFadeTimer / self.musicFadeDuration)
        
        # Apply eased volume (quadratic ease-in for smoother fade)
        easedProgress = progress * progress
        pygame.mixer.music.set_volume(targetVolume * easedProgress)
        
        if progress >= 1.0:
            self.musicFadingIn = False
            pygame.mixer.music.set_volume(targetVolume)
    
    def _updateHorrorSystem(self, dt: float):
        """Update horror ambient system - plays random cave sounds and visual glitches"""
        if not self.horrorEnabled:
            return
        
        currentTime = pygame.time.get_ticks()
        self.sessionPlayTime += dt
        
        # Check if it's time to play a horror ambient sound
        if currentTime >= self.lastHorrorSoundTime + self.nextHorrorSoundTime:
            self._playRandomHorrorSound()
            self.lastHorrorSoundTime = currentTime
            # Schedule next horror sound
            self.nextHorrorSoundTime = random.randint(
                self.horrorSoundMinDelay, self.horrorSoundMaxDelay
            )
        
        # Update visual glitch timers
        if self.screenTearActive:
            self.screenTearFrames -= 1
            if self.screenTearFrames <= 0:
                self.screenTearActive = False
        
        if self.blockFlickerPos:
            self.blockFlickerTimer -= dt
            if self.blockFlickerTimer <= 0:
                self.blockFlickerPos = None
        
        if self.shadowFigureActive:
            self.shadowFigureFadeTimer -= dt
            if self.shadowFigureFadeTimer <= 0:
                self.shadowFigureActive = False
                self.shadowFigurePos = None
        
        # Update ghost cursor trail
        mouseX, mouseY = pygame.mouse.get_pos()
        self.ghostCursorPositions.append((mouseX, mouseY))
        if len(self.ghostCursorPositions) > 20:  # Keep last 20 positions
            self.ghostCursorPositions.pop(0)
        
        # Ghost cursor occasionally appears (0.01% chance per frame)
        if not self.ghostCursorActive and random.random() < 0.0001:
            self.ghostCursorActive = True
        elif self.ghostCursorActive and random.random() < 0.01:  # 1% chance to deactivate
            self.ghostCursorActive = False
        
        # Block counter glitch (very rare)
        if random.random() < 0.00005:  # 0.005% chance
            self.blockCounterGlitch = not self.blockCounterGlitch
        
        # Phantom footsteps - very rare distant footsteps
        if hasattr(self.assetManager, 'phantomFootsteps') and self.assetManager.phantomFootsteps:
            # 0.0005% chance per frame (~once per 30 minutes at 60fps)
            if random.random() < 0.000005 * (1 + self.horrorIntensity * 0.3):
                sound = random.choice(self.assetManager.phantomFootsteps)
                sound.play()
        
        # Distant knock sound - very rare
        if hasattr(self.assetManager, 'knockSound') and self.assetManager.knockSound:
            # 0.0002% chance per frame (~once per hour)
            if random.random() < 0.000002 * (1 + self.horrorIntensity * 0.2):
                self.assetManager.knockSound.play()
        
        # Breathing sound - extremely rare
        if hasattr(self.assetManager, 'breathSound') and self.assetManager.breathSound:
            # 0.0001% chance per frame (~once per 2 hours)
            if random.random() < 0.000001 * (1 + self.horrorIntensity * 0.3):
                self.assetManager.breathSound.play()
        
        # Subliminal message timer
        if self.subliminalMessageTimer > 0:
            self.subliminalMessageTimer -= dt
        elif random.random() < 0.00001:  # Very rare subliminal message
            self.subliminalMessage = random.choice([
                "WATCHING", "IT SEES", "NOT ALONE", "BEHIND YOU", "WE WAIT"
            ])
            self.subliminalMessageTimer = 16  # ~1 frame
        
        # Progression-based horror intensity
        totalBlocks = self.blocksPlaced + self.totalBlocksPlacedAllTime
        if totalBlocks >= 10000:
            self.horrorIntensity = 3
        elif totalBlocks >= 5000:
            self.horrorIntensity = 2
        elif totalBlocks >= 1000:
            self.horrorIntensity = 1
        
        # Very rare chance for visual glitches (1/10000 per frame at intensity 0)
        glitchChance = self.visualGlitchChance * (1 + self.horrorIntensity * 0.5)
        if random.random() < glitchChance:
            self._triggerRandomVisualGlitch()
        
        # Herobrine Easter Egg - appears after 30+ minutes of play
        # 0.01% chance per minute (checked every frame)
        if self.herobrineFadeTimer > 0:
            self.herobrineFadeTimer -= dt
            if self.herobrineFadeTimer <= 0:
                self.herobrineActive = False
                self.herobrinePos = None
        elif self.sessionPlayTime >= 1800000:  # 30 minutes in ms
            # Very rare chance: 0.0001% per frame (~0.01% per minute at 60fps)
            if random.random() < 0.000001 * (1 + self.herobrineSpotted * 0.5):
                self._triggerHerobrine()
        
        # Time-based horror events
        self._checkTimeBasedHorror()

    def _checkTimeBasedHorror(self):
        """Check for time-based horror events (3 AM, Halloween, etc.)"""
        from datetime import datetime
        now = datetime.now()
        
        # 3:00 AM event - all lights flicker, brief silence
        if now.hour == 3 and now.minute == 0 and now.second < 5:
            if not hasattr(self, '_3amTriggered') or not self._3amTriggered:
                self._3amTriggered = True
                # Trigger screen flicker
                self.screenTearActive = True
                self.screenTearFrames = 10
                # Brief pause in music (if playing)
                pygame.mixer.music.pause()
                # Schedule music resume after 3 seconds
                pygame.time.set_timer(pygame.USEREVENT + 10, 3000, loops=1)
        elif now.hour != 3 or now.minute != 0:
            self._3amTriggered = False
        
        # Halloween (October 31) - spookier ambiance
        if now.month == 10 and now.day == 31:
            # More frequent horror sounds
            if not hasattr(self, '_halloweenBoost'):
                self._halloweenBoost = True
                self.horrorSoundMinDelay = 150000  # 2.5 minutes instead of 5
                self.horrorSoundMaxDelay = 600000  # 10 minutes instead of 30
        else:
            if hasattr(self, '_halloweenBoost') and self._halloweenBoost:
                self._halloweenBoost = False
                self.horrorSoundMinDelay = 300000
                self.horrorSoundMaxDelay = 1800000
        
        # Friday the 13th - world slightly darker, 13% chance blocks make no sound
        if now.weekday() == 4 and now.day == 13:  # Friday = 4
            if not hasattr(self, '_friday13th'):
                self._friday13th = True
        else:
            self._friday13th = False

    def _triggerHerobrine(self):
        """Trigger a Herobrine sighting at the edge of the screen"""
        if self.herobrineActive:
            return
        
        self.herobrineActive = True
        self.herobrineTriggered = True
        self.herobrineSpotted += 1
        
        # Position at world edge (far from camera)
        edge = random.choice(["left", "right", "top"])
        if edge == "left":
            self.herobrinePos = (30, random.randint(200, WINDOW_HEIGHT - 200))
        elif edge == "right":
            self.herobrinePos = (WINDOW_WIDTH - PANEL_WIDTH - 50, random.randint(200, WINDOW_HEIGHT - 200))
        else:  # top
            self.herobrinePos = (random.randint(100, WINDOW_WIDTH - PANEL_WIDTH - 100), 50)
        
        self.herobrineFadeTimer = 150  # About 2.5 seconds at 60fps (but despawns if camera moves)

    def _playRandomHorrorSound(self):
        """Play a random horror ambient sound based on current dimension"""
        sounds = []
        
        if self.currentDimension == DIMENSION_NETHER:
            # In Nether, use nether ambient sounds
            if hasattr(self.assetManager, 'netherAmbientSounds') and self.assetManager.netherAmbientSounds:
                sounds = self.assetManager.netherAmbientSounds
            # Rare chance to also play distant ghast moan
            if hasattr(self.assetManager, 'ghastMoans') and self.assetManager.ghastMoans:
                if random.random() < 0.15:  # 15% chance in Nether
                    ghast = random.choice(self.assetManager.ghastMoans)
                    ghast.play()
        elif self.currentDimension == DIMENSION_END:
            # In End, use enderman sounds and cave sounds
            if hasattr(self.assetManager, 'endermanSounds') and self.assetManager.endermanSounds:
                if random.random() < 0.3:  # 30% chance for enderman sound in End
                    enderman = random.choice(self.assetManager.endermanSounds)
                    enderman.play()
            if hasattr(self.assetManager, 'caveSounds') and self.assetManager.caveSounds:
                sounds = self.assetManager.caveSounds
        else:
            # In Overworld, use cave sounds
            if hasattr(self.assetManager, 'caveSounds') and self.assetManager.caveSounds:
                sounds = self.assetManager.caveSounds
        
        if sounds:
            sound = random.choice(sounds)
            sound.play()
    
    def _triggerRandomVisualGlitch(self):
        """Trigger a random visual glitch effect"""
        glitchType = random.choice(["screen_tear", "block_flicker", "shadow_figure"])
        
        if glitchType == "screen_tear":
            self.screenTearActive = True
            self.screenTearFrames = random.randint(1, 3)  # Very brief
        
        elif glitchType == "block_flicker" and self.world.blocks:
            # Pick a random placed block to briefly show wrong texture
            positions = list(self.world.blocks.keys())
            self.blockFlickerPos = random.choice(positions)
            self.blockFlickerTimer = 16  # ~1 frame at 60fps
        
        elif glitchType == "shadow_figure":
            # Create a shadow figure at edge of screen
            self.shadowFigureActive = True
            edge = random.choice(["left", "right"])
            if edge == "left":
                self.shadowFigurePos = (20, random.randint(100, WINDOW_HEIGHT - 200))
            else:
                self.shadowFigurePos = (WINDOW_WIDTH - PANEL_WIDTH - 50, random.randint(100, WINDOW_HEIGHT - 200))
            self.shadowFigureFadeTimer = 150  # Very brief appearance
    
    def _loadAutoSave(self):
        """Load auto-save if it exists (crash recovery)"""
        if os.path.exists(self.autoSavePath):
            try:
                self._loadBuilding(os.path.basename(self.autoSavePath))
                print("Recovered from auto-save")
                return True
            except Exception as e:
                print(f"Warning: Could not recover from auto-save: {e}")
        return False
    
    def _getBuildStatistics(self) -> Dict:
        """Get current build statistics"""
        sessionTime = (pygame.time.get_ticks() - self.sessionStartTime) // 1000
        
        # Get most used blocks
        sortedBlocks = sorted(self.blockUsageStats.items(), key=lambda x: x[1], reverse=True)
        topBlocks = [(block.name, count) for block, count in sortedBlocks[:5]]
        
        return {
            "blocks_placed": self.blocksPlaced,
            "blocks_removed": self.blocksRemoved,
            "session_time_seconds": sessionTime,
            "total_blocks": len(self.world.blocks),
            "most_used_blocks": topBlocks,
        }
    
    def _trackBlockUsage(self, blockType: BlockType):
        """Track which blocks are used most often"""
        if blockType == BlockType.AIR:
            return
        self.blockUsageStats[blockType] = self.blockUsageStats.get(blockType, 0) + 1
    
    def _updateSmoothCamera(self):
        """Update smooth camera interpolation"""
        if not self.smoothCameraEnabled:
            return
        
        # Lerp toward target
        dx = self.targetOffsetX - self.renderer.offsetX
        dy = self.targetOffsetY - self.renderer.offsetY
        
        if abs(dx) > 0.5 or abs(dy) > 0.5:
            self.renderer.offsetX += dx * self.cameraSmoothing
            self.renderer.offsetY += dy * self.cameraSmoothing
    
    def _fillRegion(self, start: Tuple[int, int, int], end: Tuple[int, int, int], blockType: BlockType):
        """Fill a region with blocks"""
        x1, y1, z1 = start
        x2, y2, z2 = end
        
        minX, maxX = min(x1, x2), max(x1, x2)
        minY, maxY = min(y1, y2), max(y1, y2)
        minZ, maxZ = min(z1, z2), max(z1, z2)
        
        from engine.undo import BatchCommand, PlaceBlockCommand
        commands = []
        
        for x in range(minX, maxX + 1):
            for y in range(minY, maxY + 1):
                for z in range(minZ, maxZ + 1):
                    if self.world.isInBounds(x, y, z):
                        cmd = PlaceBlockCommand(self.world, x, y, z, blockType, None)
                        commands.append(cmd)
        
        if commands:
            batch = BatchCommand(commands)
            self.undoManager.execute(batch)
            self.blocksPlaced += len(commands)
    
    def _replaceBlocks(self, oldType: BlockType, newType: BlockType):
        """Replace all blocks of one type with another"""
        from engine.undo import BatchCommand, PlaceBlockCommand
        commands = []
        
        for pos, blockType in list(self.world.blocks.items()):
            if blockType == oldType:
                x, y, z = pos
                cmd = PlaceBlockCommand(self.world, x, y, z, newType, None)
                commands.append(cmd)
        
        if commands:
            batch = BatchCommand(commands)
            self.undoManager.execute(batch)
            print(f"Replaced {len(commands)} blocks")
    
    def _placeWithMirror(self, x: int, y: int, z: int, blockType: BlockType):
        """Place block with optional mirroring"""
        # Place original
        if self._placeBlockWithUndo(x, y, z, blockType):
            self.blocksPlaced += 1
            self._addToRecentBlocks(blockType)
            self._spawnPlacementParticles(x, y, z, blockType)
            
            # Mirror X
            if self.mirrorModeX:
                mirrorX = GRID_WIDTH - 1 - x
                if self.world.isInBounds(mirrorX, y, z):
                    self._placeBlockWithUndo(mirrorX, y, z, blockType)
                    self.blocksPlaced += 1
            
            # Mirror Y
            if self.mirrorModeY:
                mirrorY = GRID_DEPTH - 1 - y
                if self.world.isInBounds(x, mirrorY, z):
                    self._placeBlockWithUndo(x, mirrorY, z, blockType)
                    self.blocksPlaced += 1
            
            # Mirror both (diagonal)
            if self.mirrorModeX and self.mirrorModeY:
                mirrorX = GRID_WIDTH - 1 - x
                mirrorY = GRID_DEPTH - 1 - y
                if self.world.isInBounds(mirrorX, mirrorY, z):
                    self._placeBlockWithUndo(mirrorX, mirrorY, z, blockType)
                    self.blocksPlaced += 1
            
            return True
        return False
    
    def _placeWithRadialSymmetry(self, x: int, y: int, z: int, blockType: BlockType):
        """Place blocks with radial symmetry (4-way or 8-way)"""
        import math
        
        # Calculate center of grid
        centerX = GRID_WIDTH / 2
        centerY = GRID_DEPTH / 2
        
        # Calculate position relative to center
        relX = x - centerX
        relY = y - centerY
        
        # Calculate angle and distance from center
        angle = math.atan2(relY, relX)
        distance = math.sqrt(relX**2 + relY**2)
        
        # Calculate rotation step based on symmetry mode
        numRotations = self.radialSymmetry
        angleStep = 2 * math.pi / numRotations
        
        # Place blocks at rotated positions
        for i in range(1, numRotations):  # Skip 0 (original position already placed)
            newAngle = angle + angleStep * i
            newX = int(centerX + distance * math.cos(newAngle))
            newY = int(centerY + distance * math.sin(newAngle))
            
            # Check bounds and place
            if self.world.isInBounds(newX, newY, z):
                if self._placeBlockWithUndo(newX, newY, z, blockType):
                    self.blocksPlaced += 1

    def _spawnPlacementParticles(self, x: int, y: int, z: int, blockType: BlockType):
        """Spawn visual particles when placing a block"""
        # Get screen position for block
        screenX, screenY = self.renderer.worldToScreen(x, y, z)
        
        # Get block color for particles
        blockDef = BLOCK_DEFINITIONS.get(blockType)
        if blockDef:
            # Default particle color based on block category
            baseColor = (150, 150, 150)
            if "stone" in blockDef.name.lower():
                baseColor = (128, 128, 128)
            elif "wood" in blockDef.name.lower() or "log" in blockDef.name.lower():
                baseColor = (139, 90, 43)
            elif "grass" in blockDef.name.lower():
                baseColor = (100, 180, 100)
        else:
            baseColor = (150, 150, 150)
        
        # Spawn 5-8 particles
        import random
        for _ in range(random.randint(5, 8)):
            self.placementParticles.append({
                "x": screenX + random.randint(-10, 10),
                "y": screenY + random.randint(-10, 10),
                "vx": random.uniform(-2, 2),
                "vy": random.uniform(-3, -1),
                "color": baseColor,
                "life": 20,
                "maxLife": 20
            })
    
    def _updatePlacementParticles(self):
        """Update placement animation particles"""
        for p in self.placementParticles[:]:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["vy"] += 0.2  # Gravity
            p["life"] -= 1
            if p["life"] <= 0:
                self.placementParticles.remove(p)
    
    def _renderPlacementParticles(self):
        """Render placement animation particles"""
        for p in self.placementParticles:
            alpha = int(255 * (p["life"] / p["maxLife"]))
            size = max(2, int(4 * (p["life"] / p["maxLife"])))
            
            surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            color = (*p["color"], alpha)
            pygame.draw.circle(surf, color, (size, size), size)
            self.screen.blit(surf, (int(p["x"]) - size, int(p["y"]) - size))
    
    def _handleHotbarClick(self, mouseX: int, mouseY: int, button: int) -> bool:
        """Handle clicks on the hotbar. Returns True if click was on hotbar."""
        slotSize = 50
        padding = 4
        hotbarWidth = len(self.hotbar) * (slotSize + padding) + padding
        hotbarHeight = slotSize + padding * 2
        
        startX = (WINDOW_WIDTH - PANEL_WIDTH - hotbarWidth) // 2
        startY = WINDOW_HEIGHT - hotbarHeight - 10
        
        # Check if click is within hotbar bounds
        if not (startX <= mouseX <= startX + hotbarWidth and 
                startY <= mouseY <= startY + hotbarHeight):
            return False
        
        # Calculate which slot was clicked
        relX = mouseX - startX - padding
        slotIndex = relX // (slotSize + padding)
        
        if 0 <= slotIndex < len(self.hotbar):
            if button == 1:  # Left click - select slot
                self.hotbarSelectedSlot = slotIndex
                if self.hotbar[slotIndex]:
                    self.selectedBlock = self.hotbar[slotIndex]
                self.assetManager.playClickSound()
            elif button == 3:  # Right click - assign current block to slot
                self.hotbar[slotIndex] = self.selectedBlock
                self.assetManager.playClickSound()
            return True
        return False
    
    def _handleSettingsClick(self, mouseX: int, mouseY: int):
        """Handle clicks on the settings menu"""
        menuWidth = 400
        menuHeight = 450
        menuX = (WINDOW_WIDTH - menuWidth) // 2
        menuY = (WINDOW_HEIGHT - menuHeight) // 2
        
        # Close button (top right)
        closeX = menuX + menuWidth - 30
        closeY = menuY + 10
        if closeX <= mouseX <= closeX + 20 and closeY <= mouseY <= closeY + 20:
            self.settingsMenuOpen = False
            self.assetManager.playClickSound()
            return
        
        # Check if click is outside menu (close it)
        if not (menuX <= mouseX <= menuX + menuWidth and 
                menuY <= mouseY <= menuY + menuHeight):
            self.settingsMenuOpen = False
            return
        
        # Volume sliders - match render layout
        y = menuY + 60
        sliderY = y + 20  # Label is at y, track is at y+20
        sliderHeight = 8
        sliderX = menuX + 20
        sliderWidth = menuWidth - 40
        
        # Music volume slider
        if sliderX <= mouseX <= sliderX + sliderWidth and sliderY <= mouseY <= sliderY + sliderHeight + 8:
            newVol = (mouseX - sliderX) / sliderWidth
            self.musicVolume = max(0, min(1, newVol))
            pygame.mixer.music.set_volume(self.musicVolume)
        
        # Ambient volume slider (y + 50)
        y += 50
        sliderY = y + 20
        if sliderX <= mouseX <= sliderX + sliderWidth and sliderY <= mouseY <= sliderY + sliderHeight + 8:
            newVol = (mouseX - sliderX) / sliderWidth
            self.ambientVolume = max(0, min(1, newVol))
        
        # Effects volume slider (y + 50)
        y += 50
        sliderY = y + 20
        if sliderX <= mouseX <= sliderX + sliderWidth and sliderY <= mouseY <= sliderY + sliderHeight + 8:
            newVol = (mouseX - sliderX) / sliderWidth
            self.effectsVolume = max(0, min(1, newVol))
        
        # Toggle options - match render layout (y + 60 after effects)
        y += 60
        toggleSize = 20
        toggleX = sliderX + sliderWidth - toggleSize
        
        # Toggle attributes in order
        toggles = [
            "autoSaveEnabled",
            "smoothCameraEnabled", 
            "showCoordinates",
            "showGrid",
            "showBlockOutline",
            "showBlockTooltip",
        ]
        
        for attr in toggles:
            if toggleX <= mouseX <= toggleX + toggleSize and y <= mouseY <= y + toggleSize:
                currentVal = getattr(self, attr)
                setattr(self, attr, not currentVal)
                self.assetManager.playClickSound()
                return
            y += 35
    
    def _handleFillToolClick(self, mouseX: int, mouseY: int):
        """Handle clicks when fill tool is active"""
        if not self.hoveredCell:
            return
        
        if self.fillStart is None:
            # First click - set start point
            self.fillStart = self.hoveredCell
            self.tooltipText = "Fill start set. Click end point."
            self.tooltipTimer = 2000
        else:
            # Second click - perform fill
            self._fillRegion(self.fillStart, self.hoveredCell, self.selectedBlock)
            self.fillStart = None
            self.fillToolActive = False
            self.tooltipText = "Fill complete!"
            self.tooltipTimer = 1500

    def _renderHotbar(self):
        """Render the hotbar at bottom of screen"""
        slotSize = 50
        padding = 4
        hotbarWidth = len(self.hotbar) * (slotSize + padding) + padding
        hotbarHeight = slotSize + padding * 2
        
        startX = (WINDOW_WIDTH - PANEL_WIDTH - hotbarWidth) // 2
        startY = WINDOW_HEIGHT - hotbarHeight - 10
        
        # Background
        bgSurf = pygame.Surface((hotbarWidth, hotbarHeight), pygame.SRCALPHA)
        bgSurf.fill((30, 30, 40, 200))
        self.screen.blit(bgSurf, (startX, startY))
        pygame.draw.rect(self.screen, (80, 80, 100), (startX, startY, hotbarWidth, hotbarHeight), 2)
        
        # Slots
        for i, blockType in enumerate(self.hotbar):
            slotX = startX + padding + i * (slotSize + padding)
            slotY = startY + padding
            
            # Slot background
            if i == self.hotbarSelectedSlot:
                pygame.draw.rect(self.screen, (100, 200, 100), (slotX, slotY, slotSize, slotSize), 2)
            else:
                pygame.draw.rect(self.screen, (60, 60, 70), (slotX, slotY, slotSize, slotSize))
            
            # Block icon - use the full isometric block sprite like placed/right panel blocks
            sprite = self.assetManager.getBlockSprite(blockType)
            if sprite:
                # Scale the sprite to fit the slot while preserving aspect ratio
                spriteW, spriteH = sprite.get_size()
                # Calculate scale to fit within slot with some padding
                maxSize = slotSize - 6
                scale = min(maxSize / spriteW, maxSize / spriteH)
                newW = int(spriteW * scale)
                newH = int(spriteH * scale)
                
                # Use smoothscale for better quality
                scaled = pygame.transform.smoothscale(sprite, (newW, newH))
                
                # Center the sprite in the slot
                offsetX = slotX + (slotSize - newW) // 2
                offsetY = slotY + (slotSize - newH) // 2
                self.screen.blit(scaled, (offsetX, offsetY))
            
            # Slot number
            numText = self.smallFont.render(str(i + 1), True, (200, 200, 200))
            self.screen.blit(numText, (slotX + 2, slotY + 2))
    
    def _renderSearchBox(self):
        """Render search box when active"""
        if not self.searchActive:
            return
        
        boxWidth = 300
        boxHeight = 30
        boxX = (WINDOW_WIDTH - PANEL_WIDTH - boxWidth) // 2
        boxY = 50
        
        # Background
        pygame.draw.rect(self.screen, (40, 40, 50), (boxX, boxY, boxWidth, boxHeight))
        pygame.draw.rect(self.screen, (100, 200, 100), (boxX, boxY, boxWidth, boxHeight), 2)
        
        # Search text
        displayText = self.searchQuery if self.searchQuery else "Type to search blocks..."
        color = (220, 220, 220) if self.searchQuery else (150, 150, 150)
        textSurf = self.font.render(displayText, True, color)
        self.screen.blit(textSurf, (boxX + 10, boxY + 5))
        
        # Cursor blink
        if self.searchQuery and pygame.time.get_ticks() % 1000 < 500:
            cursorX = boxX + 10 + textSurf.get_width() + 2
            pygame.draw.line(self.screen, (220, 220, 220), (cursorX, boxY + 5), (cursorX, boxY + 25), 2)
        
        # Search results dropdown
        if self.searchResults:
            resultHeight = min(len(self.searchResults), 8) * 25
            pygame.draw.rect(self.screen, (40, 40, 50), (boxX, boxY + boxHeight, boxWidth, resultHeight))
            pygame.draw.rect(self.screen, (80, 80, 100), (boxX, boxY + boxHeight, boxWidth, resultHeight), 1)
            
            for i, blockType in enumerate(self.searchResults[:8]):
                resultY = boxY + boxHeight + i * 25
                
                # Highlight first result
                if i == 0:
                    pygame.draw.rect(self.screen, (60, 100, 60), (boxX + 1, resultY, boxWidth - 2, 24))
                
                blockDef = BLOCK_DEFINITIONS.get(blockType)
                name = blockDef.name if blockDef else blockType.name.replace('_', ' ').title()
                textSurf = self.smallFont.render(name, True, (220, 220, 220))
                self.screen.blit(textSurf, (boxX + 10, resultY + 4))
    
    def _renderCoordinates(self):
        """Render coordinate display"""
        if not self.showCoordinates or self.hoveredCell is None:
            return
        
        x, y, z = self.hoveredCell
        
        # Horror: Coordinate anomaly - rarely show impossible/glitched values
        if self.horrorEnabled and random.random() < 0.0002:  # 0.02% chance
            glitchType = random.choice(["negative", "huge", "symbols", "shift"])
            if glitchType == "negative":
                x, y, z = -x - 1, -y - 1, -z - 1
            elif glitchType == "huge":
                x = random.randint(99999, 999999)
            elif glitchType == "symbols":
                text = f"X: ??  Y: ??  Z: ??"
            elif glitchType == "shift":
                x, y, z = z, x, y  # Coordinates shifted around
        
        if 'text' not in dir():
            text = f"X: {x}  Y: {y}  Z: {z}"
        
        textSurf = self.smallFont.render(text, True, (200, 200, 200))
        
        # Position at top left
        padding = 4
        bgWidth = textSurf.get_width() + padding * 2
        bgHeight = textSurf.get_height() + padding * 2
        
        bgSurf = pygame.Surface((bgWidth, bgHeight), pygame.SRCALPHA)
        bgSurf.fill((30, 30, 40, 180))
        self.screen.blit(bgSurf, (10, 35))
        self.screen.blit(textSurf, (10 + padding, 35 + padding))
    
    def _renderDimensionIndicator(self):
        """Render current dimension name with small block icon"""
        # Get dimension name and icon texture
        if self.currentDimension == DIMENSION_OVERWORLD:
            dimName = "Overworld"
            dimColor = (124, 189, 107)  # Grass green
            iconTexture = "grass_block_side.png"
        elif self.currentDimension == DIMENSION_NETHER:
            dimName = "Nether"
            dimColor = (140, 60, 60)  # Netherrack red
            iconTexture = "netherrack.png"
        else:  # DIMENSION_END
            dimName = "The End"
            dimColor = (219, 222, 158)  # End stone yellow
            iconTexture = "end_stone.png"
        
        # Render text
        textSurf = self.smallFont.render(dimName, True, dimColor)
        
        # Get icon (16x16)
        iconSize = 16
        iconSurf = None
        if iconTexture in self.assetManager.textures:
            tex = self.assetManager.textures[iconTexture]
            iconSurf = pygame.transform.smoothscale(tex, (iconSize, iconSize))
        
        # Calculate position - top left at y=10
        x = 10
        y = 10
        padding = 4
        
        totalWidth = textSurf.get_width() + padding * 2
        if iconSurf:
            totalWidth += iconSize + 4  # icon + spacing
        
        # Background
        bgHeight = max(textSurf.get_height(), iconSize) + padding * 2
        bgSurf = pygame.Surface((totalWidth, bgHeight), pygame.SRCALPHA)
        bgSurf.fill((30, 30, 40, 180))
        self.screen.blit(bgSurf, (x - padding, y - padding))
        
        # Draw icon first
        drawX = x
        if iconSurf:
            iconY = y + (textSurf.get_height() - iconSize) // 2
            self.screen.blit(iconSurf, (drawX, iconY))
            drawX += iconSize + 4
        
        # Draw text
        self.screen.blit(textSurf, (drawX, y))
    
    def _renderMirrorIndicator(self):
        """Render mirror mode indicators"""
        if not self.mirrorModeX and not self.mirrorModeY:
            return
        
        indicators = []
        if self.mirrorModeX:
            indicators.append("Mirror X")
        if self.mirrorModeY:
            indicators.append("Mirror Y")
        
        text = " | ".join(indicators)
        textSurf = self.smallFont.render(text, True, (100, 200, 255))
        
        x = 10
        y = 60 if self.showCoordinates else 35
        
        padding = 4
        bgSurf = pygame.Surface((textSurf.get_width() + padding * 2, textSurf.get_height() + padding * 2), pygame.SRCALPHA)
        bgSurf.fill((30, 60, 80, 180))
        self.screen.blit(bgSurf, (x - padding, y - padding))
        self.screen.blit(textSurf, (x, y))
    
    def _renderModeIndicators(self):
        """Render indicators for active modes (radial symmetry, replace, magic wand, stamp)"""
        indicators = []
        colors = []
        
        if self.radialSymmetry > 0:
            indicators.append(f"Radial {self.radialSymmetry}x")
            colors.append((255, 150, 100))  # Orange
        
        if self.replaceMode:
            if self.replaceSourceBlock:
                indicators.append(f"Replace: {self.replaceSourceBlock.name}")
            else:
                indicators.append("Replace: Click source")
            colors.append((255, 100, 100))  # Red
        
        if self.magicWandMode:
            count = len(self.magicWandSelection) if self.magicWandSelection else 0
            indicators.append(f"Magic Wand ({count})")
            colors.append((255, 100, 255))  # Magenta
        
        if self.stampMode:
            count = len(self.stampData) if self.stampData else 0
            indicators.append(f"Stamp ({count} blocks)")
            colors.append((100, 255, 150))  # Green
        
        if not indicators:
            return
        
        # Calculate Y position below other indicators
        y = 60 if self.showCoordinates else 35
        if self.mirrorModeX or self.mirrorModeY:
            y += 25
        if self.layerViewEnabled:
            y += 25
        
        for i, (text, color) in enumerate(zip(indicators, colors)):
            textSurf = self.smallFont.render(text, True, color)
            x = 10
            
            padding = 4
            bgSurf = pygame.Surface((textSurf.get_width() + padding * 2, textSurf.get_height() + padding * 2), pygame.SRCALPHA)
            bgSurf.fill((60, 40, 40, 180))
            self.screen.blit(bgSurf, (x - padding, y - padding))
            self.screen.blit(textSurf, (x, y))
            y += 25
    
    def _renderLayerIndicator(self):
        """Render layer view indicator"""
        if not self.layerViewEnabled:
            return
        
        text = f"Layer: {self.currentViewLayer} / {GRID_HEIGHT - 1}"
        textSurf = self.smallFont.render(text, True, (255, 200, 100))
        
        x = 10
        y = 85 if self.showCoordinates else 60
        if self.mirrorModeX or self.mirrorModeY:
            y += 25
        
        padding = 4
        bgSurf = pygame.Surface((textSurf.get_width() + padding * 2, textSurf.get_height() + padding * 2), pygame.SRCALPHA)
        bgSurf.fill((80, 60, 30, 180))
        self.screen.blit(bgSurf, (x - padding, y - padding))
        self.screen.blit(textSurf, (x, y))
    
    def _renderMinimap(self):
        """Render a small top-down view minimap of the build"""
        if not self.showMinimap:
            return
        
        # Position in bottom-left corner
        mapX = self.minimapMargin
        mapY = WINDOW_HEIGHT - self.minimapSize - self.minimapMargin - 30  # Above stats
        
        # Create minimap surface with dimension-appropriate background color
        mapSurf = pygame.Surface((self.minimapSize, self.minimapSize), pygame.SRCALPHA)
        
        # Background color based on current dimension
        if self.currentDimension == DIMENSION_END:
            # End stone yellowish color
            mapBgColor = (219, 222, 158, 200)
        elif self.currentDimension == DIMENSION_NETHER:
            # Netherrack reddish color
            mapBgColor = (111, 54, 52, 200)
        else:
            # Overworld - grass greenish (tinted)
            mapBgColor = (60, 90, 50, 200)
        
        mapSurf.fill(mapBgColor)
        
        # Calculate scale (grid to minimap)
        scaleX = self.minimapSize / GRID_WIDTH
        scaleY = self.minimapSize / GRID_DEPTH
        pixelSize = max(1, int(min(scaleX, scaleY)))
        
        # Draw blocks (top-down view - highest Z at each X,Y)
        for x in range(GRID_WIDTH):
            for y in range(GRID_DEPTH):
                # Find the highest block at this position
                for z in range(GRID_HEIGHT - 1, -1, -1):
                    blockType = self.world.getBlock(x, y, z)
                    if blockType != BlockType.AIR:
                        # Get color from block definition or use default
                        blockDef = BLOCK_DEFINITIONS.get(blockType)
                        mapColor = getattr(blockDef, 'mapColor', None) if blockDef else None
                        if mapColor:
                            color = mapColor
                        else:
                            # Fallback: extract dominant color from name
                            name = blockType.name.lower()
                            if 'grass' in name:
                                color = (100, 180, 80)
                            elif 'dirt' in name:
                                color = (130, 90, 60)
                            elif 'end_stone' in name or 'end' in name:
                                # Check end_stone BEFORE generic stone to avoid grey
                                color = (219, 222, 158)  # End stone yellowish
                            elif 'stone' in name or 'cobble' in name:
                                color = (120, 120, 120)
                            elif 'water' in name:
                                color = (50, 100, 200)
                            elif 'lava' in name:
                                color = (255, 100, 0)
                            elif 'wood' in name or 'log' in name or 'plank' in name:
                                color = (150, 100, 50)
                            elif 'sand' in name:
                                color = (220, 200, 150)
                            elif 'glass' in name:
                                color = (200, 220, 255)
                            elif 'iron' in name:
                                color = (200, 200, 200)
                            elif 'gold' in name:
                                color = (255, 215, 0)
                            elif 'diamond' in name:
                                color = (100, 220, 255)
                            elif 'netherrack' in name or 'nether' in name:
                                color = (120, 50, 50)
                            else:
                                color = (100, 100, 100)
                        
                        # Darken based on depth (lower Z = darker)
                        darken = 1.0 - (z / GRID_HEIGHT) * 0.3
                        color = (int(color[0] * darken), int(color[1] * darken), int(color[2] * darken))
                        
                        # Draw pixel on minimap
                        px = int(x * scaleX)
                        py = int(y * scaleY)
                        pygame.draw.rect(mapSurf, color, (px, py, pixelSize, pixelSize))
                        break
        
        # Draw hovered cell indicator
        if self.hoveredCell:
            hx, hy, hz = self.hoveredCell
            px = int(hx * scaleX)
            py = int(hy * scaleY)
            pygame.draw.rect(mapSurf, (255, 255, 255), (px - 1, py - 1, pixelSize + 2, pixelSize + 2), 1)
        
        # Draw border
        pygame.draw.rect(mapSurf, (100, 100, 120), (0, 0, self.minimapSize, self.minimapSize), 2)
        
        # Blit to screen
        self.screen.blit(mapSurf, (mapX, mapY))
        
        # Label
        labelText = self.smallFont.render("Minimap", True, (150, 150, 150))
        self.screen.blit(labelText, (mapX, mapY - 15))

    def _renderViewRotationIndicator(self):
        """Render view rotation indicator when view is rotated"""
        if self.renderer.viewRotation == 0:
            return  # Don't show at default view
        
        # Direction names for each rotation
        directions = ["NE (default)", "SE", "SW", "NW"]
        angle = self.renderer.viewRotation * 90
        text = f"View: {directions[self.renderer.viewRotation]} ({angle}°)"
        textSurf = self.smallFont.render(text, True, (100, 255, 100))
        
        # Position below other indicators
        x = 10
        y = 85 if self.showCoordinates else 60
        if self.mirrorModeX or self.mirrorModeY:
            y += 25
        if self.layerViewEnabled:
            y += 25
        
        padding = 4
        bgSurf = pygame.Surface((textSurf.get_width() + padding * 2, textSurf.get_height() + padding * 2), pygame.SRCALPHA)
        bgSurf.fill((30, 80, 30, 180))
        self.screen.blit(bgSurf, (x - padding, y - padding))
        self.screen.blit(textSurf, (x, y))
    
    def _renderSettingsMenu(self):
        """Render settings menu overlay"""
        if not self.settingsMenuOpen:
            return
        
        menuWidth = 400
        menuHeight = 500
        menuX = (WINDOW_WIDTH - menuWidth) // 2
        menuY = (WINDOW_HEIGHT - menuHeight) // 2
        
        # Overlay
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))
        
        # Menu background
        pygame.draw.rect(self.screen, (40, 40, 50), (menuX, menuY, menuWidth, menuHeight))
        pygame.draw.rect(self.screen, (100, 100, 120), (menuX, menuY, menuWidth, menuHeight), 3)
        
        # Title
        title = self.font.render("Settings", True, (255, 255, 255))
        self.screen.blit(title, (menuX + menuWidth // 2 - title.get_width() // 2, menuY + 20))
        
        y = menuY + 60
        
        # Volume controls
        self._renderSettingsVolumeSlider("Music Volume", self.musicVolume, menuX + 20, y, menuWidth - 40)
        y += 50
        self._renderSettingsVolumeSlider("Ambient Volume", self.ambientVolume, menuX + 20, y, menuWidth - 40)
        y += 50
        self._renderSettingsVolumeSlider("Effects Volume", self.effectsVolume, menuX + 20, y, menuWidth - 40)
        y += 60
        
        # Toggle options
        toggles = [
            ("Auto-Save (5 min)", self.autoSaveEnabled, "autoSaveEnabled"),
            ("Smooth Camera", self.smoothCameraEnabled, "smoothCameraEnabled"),
            ("Show Coordinates", self.showCoordinates, "showCoordinates"),
            ("Show Grid", self.showGrid, "showGrid"),
            ("Show Block Outline", self.showBlockOutline, "showBlockOutline"),
            ("Show Block Tooltip", self.showBlockTooltip, "showBlockTooltip"),
        ]
        
        for label, value, attr in toggles:
            self._renderToggle(label, value, menuX + 20, y, menuWidth - 40)
            y += 35
        
        # Close hint
        hint = self.smallFont.render("Press Ctrl+, or ESC to close", True, (150, 150, 150))
        self.screen.blit(hint, (menuX + menuWidth // 2 - hint.get_width() // 2, menuY + menuHeight - 30))
    
    def _drawRotationArrow(self, rect: pygame.Rect, clockwise: bool, centered: bool = False):
        """Draw a clean curved rotation arrow icon on a button"""
        import math
        
        centerX = rect.centerx
        centerY = rect.centery
        radius = 10  # Slightly smaller for cleaner look
        
        # High contrast colors for visibility
        arrowColor = (255, 255, 255)  # Bright white for visibility
        shadowColor = (40, 40, 50)
        
        # Many segments for smooth curve
        numSegments = 24
        
        # Center position
        cx = centerX
        cy = centerY
        
        if clockwise:
            # CW arrow - arc from ~10 o'clock to ~5 o'clock (about 210 degrees)
            startAngle = -math.pi * 0.6   # Start around 10 o'clock
            endAngle = math.pi * 0.55     # End around 5 o'clock
        else:
            # CCW arrow - mirror of CW
            startAngle = math.pi * 0.6    # Start around 2 o'clock
            endAngle = -math.pi * 0.55    # End around 7 o'clock
        
        # Generate arc points
        points = []
        for i in range(numSegments + 1):
            t = i / numSegments
            angle = startAngle + t * (endAngle - startAngle)
            px = cx + radius * math.cos(angle)
            py = cy + radius * math.sin(angle)
            points.append((px, py))
        
        if len(points) > 1:
            # Draw shadow for depth
            shadowPoints = [(p[0] + 1, p[1] + 1) for p in points]
            pygame.draw.lines(self.screen, shadowColor, False, shadowPoints, 4)
            
            # Draw main arc
            pygame.draw.lines(self.screen, arrowColor, False, points, 3)
        
        # Draw arrowhead at end of arc - using explicit direction for clean look
        if len(points) >= 2:
            endX, endY = points[-1]
            prevX, prevY = points[-2]
            
            # Calculate tangent direction
            tangentAngle = math.atan2(endY - prevY, endX - prevX)
            
            # Arrowhead parameters
            arrowLen = 7
            arrowWidth = math.pi / 5  # ~36 degree spread
            
            # Arrow tip is at the end of the arc
            tip = (endX, endY)
            
            # Calculate the two back points of the arrowhead
            backLeft = (endX - arrowLen * math.cos(tangentAngle - arrowWidth),
                       endY - arrowLen * math.sin(tangentAngle - arrowWidth))
            backRight = (endX - arrowLen * math.cos(tangentAngle + arrowWidth),
                        endY - arrowLen * math.sin(tangentAngle + arrowWidth))
            
            # Draw arrowhead shadow
            shadowOffset = 1
            shadowTip = (tip[0] + shadowOffset, tip[1] + shadowOffset)
            shadowLeft = (backLeft[0] + shadowOffset, backLeft[1] + shadowOffset)
            shadowRight = (backRight[0] + shadowOffset, backRight[1] + shadowOffset)
            pygame.draw.polygon(self.screen, shadowColor, [shadowTip, shadowLeft, shadowRight])
            
            # Draw main arrowhead (filled triangle)
            pygame.draw.polygon(self.screen, arrowColor, [tip, backLeft, backRight])
    
    def _renderSettingsVolumeSlider(self, label: str, value: float, x: int, y: int, width: int):
        """Render a volume slider for settings menu"""
        # Label
        labelSurf = self.smallFont.render(label, True, (200, 200, 200))
        self.screen.blit(labelSurf, (x, y))
        
        # Slider track
        trackY = y + 20
        trackHeight = 8
        pygame.draw.rect(self.screen, (60, 60, 70), (x, trackY, width, trackHeight))
        
        # Filled portion
        fillWidth = int(width * value)
        pygame.draw.rect(self.screen, (100, 180, 100), (x, trackY, fillWidth, trackHeight))
        
        # Handle
        handleX = x + fillWidth
        pygame.draw.circle(self.screen, (200, 200, 200), (handleX, trackY + trackHeight // 2), 8)
        
        # Value text
        valueText = self.smallFont.render(f"{int(value * 100)}%", True, (150, 150, 150))
        self.screen.blit(valueText, (x + width + 10, y))
    
    def _renderToggle(self, label: str, value: bool, x: int, y: int, width: int):
        """Render a toggle option"""
        # Label
        labelSurf = self.smallFont.render(label, True, (200, 200, 200))
        self.screen.blit(labelSurf, (x, y + 2))
        
        # Toggle box
        boxSize = 20
        boxX = x + width - boxSize
        
        if value:
            pygame.draw.rect(self.screen, (100, 180, 100), (boxX, y, boxSize, boxSize))
            # Checkmark
            pygame.draw.line(self.screen, (255, 255, 255), (boxX + 4, y + 10), (boxX + 8, y + 14), 2)
            pygame.draw.line(self.screen, (255, 255, 255), (boxX + 8, y + 14), (boxX + 16, y + 6), 2)
        else:
            pygame.draw.rect(self.screen, (60, 60, 70), (boxX, y, boxSize, boxSize))
        
        pygame.draw.rect(self.screen, (100, 100, 120), (boxX, y, boxSize, boxSize), 1)
    
    def _renderHistoryPanel(self):
        """Render the undo/redo history panel overlay"""
        if not self.historyPanelOpen:
            return
        
        panelWidth = 320
        panelHeight = 450
        panelX = (WINDOW_WIDTH - panelWidth) // 2
        panelY = (WINDOW_HEIGHT - panelHeight) // 2
        
        # Overlay
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))
        
        # Panel background
        pygame.draw.rect(self.screen, (40, 40, 50), (panelX, panelY, panelWidth, panelHeight))
        pygame.draw.rect(self.screen, (100, 100, 120), (panelX, panelY, panelWidth, panelHeight), 3)
        
        # Title
        title = self.font.render("Undo History", True, (255, 255, 255))
        self.screen.blit(title, (panelX + panelWidth // 2 - title.get_width() // 2, panelY + 15))
        
        # Counts
        undoCount, redoCount = self.undoManager.get_history_count()
        countText = self.smallFont.render(f"Undo: {undoCount}  |  Redo: {redoCount}", True, (150, 150, 150))
        self.screen.blit(countText, (panelX + panelWidth // 2 - countText.get_width() // 2, panelY + 45))
        
        mouseX, mouseY = pygame.mouse.get_pos()
        y = panelY + 75
        itemHeight = 28
        maxVisible = 12
        
        # Get history
        undoHistory = self.undoManager.get_undo_history(max_items=50)
        redoHistory = self.undoManager.get_redo_history(max_items=50)
        
        # Reset hover
        self.historyHoveredIndex = -1
        
        # Draw undo section header
        undoHeader = self.smallFont.render("v UNDO STACK (click to jump)", True, (100, 180, 100))
        self.screen.blit(undoHeader, (panelX + 15, y))
        y += 25
        
        # Draw undo items (scrollable)
        visibleUndoStart = min(self.historyPanelScroll, max(0, len(undoHistory) - maxVisible // 2))
        visibleUndo = undoHistory[visibleUndoStart:visibleUndoStart + maxVisible // 2]
        
        for idx, (cmdIndex, desc) in enumerate(visibleUndo):
            itemRect = pygame.Rect(panelX + 10, y, panelWidth - 20, itemHeight - 2)
            isHovered = itemRect.collidepoint(mouseX, mouseY)
            
            if isHovered:
                self.historyHoveredIndex = cmdIndex
                self.historyHoveredIsRedo = False
                pygame.draw.rect(self.screen, (70, 100, 70), itemRect)
            else:
                pygame.draw.rect(self.screen, (50, 55, 60), itemRect)
            
            # Truncate description if too long
            displayDesc = desc if len(desc) < 35 else desc[:32] + "..."
            
            # Index badge
            indexText = self.smallFont.render(f"#{cmdIndex + 1}", True, (120, 120, 130))
            self.screen.blit(indexText, (panelX + 15, y + 5))
            
            # Description
            descText = self.smallFont.render(displayDesc, True, (200, 200, 200))
            self.screen.blit(descText, (panelX + 55, y + 5))
            
            y += itemHeight
        
        # Separator
        y += 10
        pygame.draw.line(self.screen, (80, 80, 90), (panelX + 20, y), (panelX + panelWidth - 20, y), 1)
        y += 15
        
        # Draw redo section header
        redoHeader = self.smallFont.render("^ REDO STACK (click to jump)", True, (180, 130, 100))
        self.screen.blit(redoHeader, (panelX + 15, y))
        y += 25
        
        # Draw redo items
        visibleRedo = redoHistory[:maxVisible // 2]
        
        for idx, (cmdIndex, desc) in enumerate(visibleRedo):
            itemRect = pygame.Rect(panelX + 10, y, panelWidth - 20, itemHeight - 2)
            isHovered = itemRect.collidepoint(mouseX, mouseY)
            
            if isHovered:
                self.historyHoveredIndex = cmdIndex
                self.historyHoveredIsRedo = True
                pygame.draw.rect(self.screen, (100, 70, 60), itemRect)
            else:
                pygame.draw.rect(self.screen, (55, 50, 50), itemRect)
            
            # Truncate description if too long
            displayDesc = desc if len(desc) < 35 else desc[:32] + "..."
            
            # Index badge
            indexText = self.smallFont.render(f"#{cmdIndex + 1}", True, (130, 120, 120))
            self.screen.blit(indexText, (panelX + 15, y + 5))
            
            # Description
            descText = self.smallFont.render(displayDesc, True, (200, 200, 200))
            self.screen.blit(descText, (panelX + 55, y + 5))
            
            y += itemHeight
        
        # If both lists are empty
        if not undoHistory and not redoHistory:
            emptyText = self.smallFont.render("No history yet - start building!", True, (120, 120, 130))
            self.screen.blit(emptyText, (panelX + panelWidth // 2 - emptyText.get_width() // 2, panelY + 180))
        
        # Close hint
        hint = self.smallFont.render("Press H or ESC to close  |  Click item to jump", True, (150, 150, 150))
        self.screen.blit(hint, (panelX + panelWidth // 2 - hint.get_width() // 2, panelY + panelHeight - 30))
        
        # Store panel rect for click detection
        self.historyPanelRect = pygame.Rect(panelX, panelY, panelWidth, panelHeight)
    
    def _handleHistoryPanelClick(self, mouseX: int, mouseY: int):
        """Handle click on the history panel"""
        if self.historyHoveredIndex >= 0:
            if self.historyHoveredIsRedo:
                # Redo to this index
                count = self.undoManager.redo_to_index(self.historyHoveredIndex)
                if count > 0:
                    self._showNotification(f"Redid {count} action{'s' if count > 1 else ''}")
            else:
                # Undo to this index
                count = self.undoManager.undo_to_index(self.historyHoveredIndex)
                if count > 0:
                    self._showNotification(f"Undid {count} action{'s' if count > 1 else ''}")
            self.assetManager.playClickSound()
    
    def _renderHorrorEffects(self):
        """Render horror visual effects - screen tear, shadow figures, etc."""
        if not self.horrorEnabled:
            return
        
        # Progression-based screen darkening (subtle)
        # Intensity 1 (1000 blocks): 2% darker
        # Intensity 2 (5000 blocks): 4% darker (shadows appear longer)
        # Intensity 3 (10000 blocks): 6% darker
        if self.horrorIntensity > 0:
            darkenAlpha = self.horrorIntensity * 5  # 5, 10, or 15 alpha
            darkenOverlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
            darkenOverlay.fill((0, 0, 0, darkenAlpha))
            self.screen.blit(darkenOverlay, (0, 0))
        
        # Screen tear effect - horizontal displacement for 1-3 frames
        if self.screenTearActive:
            tearY = random.randint(50, WINDOW_HEIGHT - 100)
            tearHeight = random.randint(2, 8)
            displacement = random.choice([-3, -2, -1, 1, 2, 3])
            
            # Copy a horizontal strip and displace it
            try:
                strip = self.screen.subsurface((0, tearY, WINDOW_WIDTH, tearHeight)).copy()
                self.screen.blit(strip, (displacement, tearY))
            except ValueError:
                pass  # Ignore if subsurface fails
        
        # Shadow figure effect - barely visible dark shape at edge
        if self.shadowFigureActive and self.shadowFigurePos:
            figX, figY = self.shadowFigurePos
            figWidth = 20
            figHeight = 60
            
            # Create a very faint dark figure
            alpha = max(5, min(25, int(self.shadowFigureFadeTimer / 6)))  # Very faint
            figureSurf = pygame.Surface((figWidth, figHeight), pygame.SRCALPHA)
            
            # Draw simple humanoid silhouette
            # Head
            pygame.draw.ellipse(figureSurf, (10, 10, 15, alpha), (5, 0, 10, 12))
            # Body  
            pygame.draw.rect(figureSurf, (10, 10, 15, alpha), (6, 12, 8, 25))
            # Legs
            pygame.draw.rect(figureSurf, (10, 10, 15, alpha), (6, 37, 3, 20))
            pygame.draw.rect(figureSurf, (10, 10, 15, alpha), (11, 37, 3, 20))
            
            self.screen.blit(figureSurf, (figX, figY))
        
        # Ghost cursor effect - faint trail that follows cursor
        if self.ghostCursorActive and len(self.ghostCursorPositions) > 3:
            for i, (gx, gy) in enumerate(self.ghostCursorPositions[:-1]):
                # Older positions are more faint
                alpha = int((i / len(self.ghostCursorPositions)) * 15) + 3
                ghostSurf = pygame.Surface((8, 8), pygame.SRCALPHA)
                pygame.draw.circle(ghostSurf, (100, 100, 120, alpha), (4, 4), 4)
                self.screen.blit(ghostSurf, (gx - 4, gy - 4))
        
        # Subliminal message - brief flash in corner
        if self.subliminalMessageTimer > 0 and self.subliminalMessage:
            msgSurf = self.smallFont.render(self.subliminalMessage, True, (80, 0, 0))
            msgSurf.set_alpha(30)  # Very faint
            corner = random.choice([(10, 10), (WINDOW_WIDTH - 100, 10), 
                                    (10, WINDOW_HEIGHT - 30), (WINDOW_WIDTH - 100, WINDOW_HEIGHT - 30)])
            self.screen.blit(msgSurf, corner)
        
        # Herobrine Easter Egg - appears at edge of screen
        if self.herobrineActive and self.herobrinePos:
            hbX, hbY = self.herobrinePos
            
            # Calculate alpha based on fade timer (appears, then fades)
            if self.herobrineFadeTimer > 100:
                alpha = min(40, int((150 - self.herobrineFadeTimer) * 0.8))  # Fade in
            else:
                alpha = min(40, int(self.herobrineFadeTimer * 0.4))  # Fade out
            
            # Create Herobrine figure (white head + blue shirt, very faint)
            hbWidth = 12
            hbHeight = 28
            hbSurf = pygame.Surface((hbWidth, hbHeight), pygame.SRCALPHA)
            
            # Head (white wool block style)
            headColor = (230, 230, 230, alpha)
            pygame.draw.rect(hbSurf, headColor, (2, 0, 8, 8))
            
            # Glowing white eyes (slightly brighter)
            eyeAlpha = min(80, alpha * 2)
            pygame.draw.rect(hbSurf, (255, 255, 255, eyeAlpha), (3, 2, 2, 2))
            pygame.draw.rect(hbSurf, (255, 255, 255, eyeAlpha), (7, 2, 2, 2))
            
            # Body (cyan/teal shirt)
            shirtColor = (0, 170, 170, alpha)
            pygame.draw.rect(hbSurf, shirtColor, (2, 8, 8, 10))
            
            # Legs (dark blue pants)
            pantsColor = (30, 30, 100, alpha)
            pygame.draw.rect(hbSurf, pantsColor, (2, 18, 3, 10))
            pygame.draw.rect(hbSurf, pantsColor, (7, 18, 3, 10))
            
            self.screen.blit(hbSurf, (hbX, hbY))
            
            # Check if player moved camera toward Herobrine - despawn
            mouseX, mouseY = pygame.mouse.get_pos()
            distToHB = ((mouseX - hbX) ** 2 + (mouseY - hbY) ** 2) ** 0.5
            if distToHB < 150:  # If cursor gets close, Herobrine disappears
                self.herobrineActive = False
                self.herobrinePos = None
        
        # Subliminal red pixel (extremely rare, single frame)
        if random.random() < 0.0001:  # 1/10000 chance per frame
            redX = random.randint(100, WINDOW_WIDTH - PANEL_WIDTH - 100)
            redY = random.randint(100, WINDOW_HEIGHT - 100)
            self.screen.set_at((redX, redY), (255, 0, 0))
        
        # Hidden eyes in Nether blocks - barely visible watching eyes
        if self.currentDimension == DIMENSION_NETHER and random.random() < 0.0003:
            self._drawHiddenNetherEyes()
    
    def _drawHiddenNetherEyes(self):
        """Draw barely-visible eyes somewhere in the nether scene for 1 frame"""
        # Pick a random position in the world area (not panel)
        eyeX = random.randint(50, WINDOW_WIDTH - PANEL_WIDTH - 50)
        eyeY = random.randint(100, WINDOW_HEIGHT - 100)
        
        # Create very faint eyes
        eyeSurf = pygame.Surface((16, 8), pygame.SRCALPHA)
        eyeAlpha = random.randint(8, 18)  # Very very faint
        
        # Two small glowing eyes
        eyeColor = (180, 20, 20, eyeAlpha)  # Dim red for nether
        pupilColor = (0, 0, 0, eyeAlpha + 5)
        
        # Left eye
        pygame.draw.ellipse(eyeSurf, eyeColor, (0, 0, 6, 6))
        pygame.draw.circle(eyeSurf, pupilColor, (3, 3), 1)
        
        # Right eye
        pygame.draw.ellipse(eyeSurf, eyeColor, (10, 0, 6, 6))
        pygame.draw.circle(eyeSurf, pupilColor, (13, 3), 1)
        
        self.screen.blit(eyeSurf, (eyeX, eyeY))
    
    def _renderBuildStats(self):
        """Render build statistics in corner"""
        stats = self._getBuildStatistics()
        minutes = stats["session_time_seconds"] // 60
        seconds = stats["session_time_seconds"] % 60
        
        # Get block counts (no random glitching)
        blocksPlaced = stats['blocks_placed']
        totalBlocks = stats['total_blocks']
        
        text = f"Placed: {blocksPlaced} | Total: {totalBlocks} | Time: {minutes}:{seconds:02d}"
        textSurf = self.smallFont.render(text, True, (150, 150, 150))
        
        x = WINDOW_WIDTH - PANEL_WIDTH - textSurf.get_width() - 10
        y = WINDOW_HEIGHT - 25
        self.screen.blit(textSurf, (x, y))
    
    def _renderAutoSaveIndicator(self):
        """Render brief 'Saved' indicator when auto-save occurs"""
        if self.autoSaveFlashTimer <= 0:
            return
        
        # Decrement timer
        self.autoSaveFlashTimer -= 1
        
        # Calculate alpha for fade out (fade in last 20 frames)
        if self.autoSaveFlashTimer < 20:
            alpha = int(255 * self.autoSaveFlashTimer / 20)
        else:
            alpha = 255
        
        # Render "Saved" text in green
        textSurf = self.smallFont.render("Saved", True, (100, 255, 100))
        textSurf.set_alpha(alpha)
        
        # Position at top right (above panel)
        x = WINDOW_WIDTH - PANEL_WIDTH - textSurf.get_width() - 10
        y = 10
        
        # Semi-transparent background
        padding = 4
        bgSurf = pygame.Surface((textSurf.get_width() + padding * 2, textSurf.get_height() + padding * 2), pygame.SRCALPHA)
        bgSurf.fill((30, 60, 30, int(alpha * 0.7)))
        self.screen.blit(bgSurf, (x - padding, y - padding))
        self.screen.blit(textSurf, (x, y))
    
    def _renderTooltipNotification(self):
        """Render tooltip notification message at top of screen"""
        if self.tooltipTimer <= 0 or not self.tooltipText:
            return
        
        # Calculate alpha based on remaining time (fade out in last 500ms)
        alpha = min(255, int(255 * self.tooltipTimer / 500)) if self.tooltipTimer < 500 else 255
        
        textSurf = self.font.render(self.tooltipText, True, (255, 255, 255))
        padding = 10
        bgWidth = textSurf.get_width() + padding * 2
        bgHeight = textSurf.get_height() + padding * 2
        
        x = (WINDOW_WIDTH - PANEL_WIDTH - bgWidth) // 2
        y = 80
        
        # Background
        bgSurf = pygame.Surface((bgWidth, bgHeight), pygame.SRCALPHA)
        bgSurf.fill((40, 40, 50, int(alpha * 0.8)))
        self.screen.blit(bgSurf, (x, y))
        pygame.draw.rect(self.screen, (100, 100, 120, alpha), (x, y, bgWidth, bgHeight), 2)
        
        # Text with alpha
        textWithAlpha = textSurf.copy()
        textWithAlpha.set_alpha(alpha)
        self.screen.blit(textWithAlpha, (x + padding, y + padding))

    def _handleZoom(self, delta: float, cursorX: int = None, cursorY: int = None):
        """Handle zoom in/out, centered on cursor position"""
        oldZoom = self.zoomLevel
        self.zoomLevel = max(self.zoomMin, min(self.zoomMax, self.zoomLevel + delta))
        
        if oldZoom != self.zoomLevel:
            # Calculate zoom factor change
            zoomFactor = self.zoomLevel / oldZoom
            
            # If cursor position provided, adjust offset to keep cursor position stationary
            if cursorX is not None and cursorY is not None:
                # To keep the world point under cursor fixed during zoom:
                # worldX = (cursorX - oldOffset) / oldZoom
                # cursorX = worldX * newZoom + newOffset
                # Solving: newOffset = cursorX * (1 - zoomFactor) + oldOffset * zoomFactor
                
                self.renderer.offsetX = int(cursorX * (1 - zoomFactor) + self.renderer.offsetX * zoomFactor)
                self.renderer.offsetY = int(cursorY * (1 - zoomFactor) + self.renderer.offsetY * zoomFactor)
                
                # Update smooth camera targets too
                self.targetOffsetX = self.renderer.offsetX
                self.targetOffsetY = self.renderer.offsetY
            
            # Update renderer zoom level
            self.renderer.setZoom(self.zoomLevel)
            # Clear sprite caches to regenerate at new zoom level
            self.assetManager.clearZoomCache()
    
    def _getUndoRedoStatus(self) -> str:
        """Get status string for undo/redo"""
        undoCount, redoCount = self.undoManager.get_history_count()
        return f"Undo: {undoCount} | Redo: {redoCount}"
    
    # ==================== Selection Box Tool ====================
    
    def _startSelection(self) -> None:
        """Start or continue selection mode"""
        if not self.selectionActive:
            # Start new selection
            self.selectionActive = True
            self.selectionStart = None
            self.selectionEnd = None
            print("Selection mode: Click to set first corner")
        else:
            # Confirm selection if both corners set
            if self.selectionStart and self.selectionEnd:
                self._confirmSelection()
    
    def _clearSelection(self) -> None:
        """Clear current selection"""
        self.selectionActive = False
        self.selectionStart = None
        self.selectionEnd = None
        self.clipboard = None
        print("Selection cleared")
    
    def _handleSelectionClick(self, x: int, y: int, z: int):
        """Handle click in selection mode"""
        if not self.selectionActive:
            return False
        
        if self.selectionStart is None:
            self.selectionStart = (x, y, z)
            print(f"Selection corner 1: ({x}, {y}, {z})")
            return True
        elif self.selectionEnd is None:
            self.selectionEnd = (x, y, z)
            print(f"Selection corner 2: ({x}, {y}, {z})")
            return True
        return False
    
    def _getSelectionBounds(self) -> Optional[Tuple[Tuple[int, int, int], Tuple[int, int, int]]]:
        """Get normalized selection bounds (min, max)"""
        if self.selectionStart is None or self.selectionEnd is None:
            return None
        
        x1, y1, z1 = self.selectionStart
        x2, y2, z2 = self.selectionEnd
        
        minPos = (min(x1, x2), min(y1, y2), min(z1, z2))
        maxPos = (max(x1, x2), max(y1, y2), max(z1, z2))
        
        return (minPos, maxPos)
    
    def _confirmSelection(self) -> None:
        """Confirm and finalize selection"""
        bounds = self._getSelectionBounds()
        if bounds:
            minP, maxP = bounds
            size = (maxP[0] - minP[0] + 1, maxP[1] - minP[1] + 1, maxP[2] - minP[2] + 1)
            print(f"Selection confirmed: {size[0]}x{size[1]}x{size[2]} blocks")
    
    def _deleteSelection(self) -> None:
        """Delete all blocks in selection"""
        bounds = self._getSelectionBounds()
        if not bounds:
            print("No selection to delete")
            return
        
        minP, maxP = bounds
        
        from engine.undo import BatchCommand, RemoveBlockCommand
        commands = []
        
        for x in range(minP[0], maxP[0] + 1):
            for y in range(minP[1], maxP[1] + 1):
                for z in range(minP[2], maxP[2] + 1):
                    if self.world.getBlock(x, y, z) != BlockType.AIR:
                        cmd = RemoveBlockCommand(self.world, x, y, z)
                        commands.append(cmd)
        
        if commands:
            batch = BatchCommand(commands)
            self.undoManager.execute(batch)
            print(f"Deleted {len(commands)} blocks")
        
        self._clearSelection()
    
    def _copySelection(self) -> None:
        """Copy selection to clipboard"""
        bounds = self._getSelectionBounds()
        if not bounds:
            print("No selection to copy")
            return
        
        minP, maxP = bounds
        
        # Create clipboard data: list of (relative_pos, block_type, properties)
        self.clipboard = []
        self.clipboardSize = (
            maxP[0] - minP[0] + 1,
            maxP[1] - minP[1] + 1,
            maxP[2] - minP[2] + 1
        )
        
        for x in range(minP[0], maxP[0] + 1):
            for y in range(minP[1], maxP[1] + 1):
                for z in range(minP[2], maxP[2] + 1):
                    blockType = self.world.getBlock(x, y, z)
                    if blockType != BlockType.AIR:
                        relPos = (x - minP[0], y - minP[1], z - minP[2])
                        props = self.world.getBlockProperties(x, y, z)
                        self.clipboard.append((relPos, blockType, props))
        
        print(f"Copied {len(self.clipboard)} blocks to clipboard")
    
    def _rotateClipboard(self, clockwise: bool = True):
        """Rotate clipboard content 90 degrees around vertical (Z) axis"""
        if not hasattr(self, 'clipboard') or not self.clipboard:
            self.tooltipText = "Nothing in clipboard to rotate"
            self.tooltipTimer = 1500
            return
        
        if not hasattr(self, 'clipboardSize'):
            return
        
        sizeX, sizeY, sizeZ = self.clipboardSize
        newClipboard = []
        
        for relPos, blockType, props in self.clipboard:
            x, y, z = relPos
            if clockwise:
                # Rotate 90° clockwise: (x, y) -> (y, sizeX - 1 - x)
                newX = y
                newY = sizeX - 1 - x
            else:
                # Rotate 90° counter-clockwise: (x, y) -> (sizeY - 1 - y, x)
                newX = sizeY - 1 - y
                newY = x
            newClipboard.append(((newX, newY, z), blockType, props))
        
        self.clipboard = newClipboard
        # Swap X and Y dimensions
        self.clipboardSize = (sizeY, sizeX, sizeZ)
        
        direction = "clockwise" if clockwise else "counter-clockwise"
        self.tooltipText = f"Rotated clipboard {direction}"
        self.tooltipTimer = 1500
        self.assetManager.playClickSound()
        
        # Also rotate stamp data if in stamp mode
        if self.stampMode and self.stampData:
            self._loadStampFromClipboard()
    
    def _pasteSelection(self) -> None:
        """Paste clipboard at current hovered position"""
        if not hasattr(self, 'clipboard') or not self.clipboard:
            print("Nothing in clipboard")
            return
        
        if self.hoveredCell is None:
            print("Hover over a position to paste")
            return
        
        baseX, baseY, baseZ = self.hoveredCell
        
        from engine.undo import BatchCommand, PlaceBlockCommand
        commands = []
        
        for relPos, blockType, props in self.clipboard:
            x = baseX + relPos[0]
            y = baseY + relPos[1]
            z = baseZ + relPos[2]
            
            # Ensure in bounds
            if 0 <= x < GRID_WIDTH and 0 <= y < GRID_DEPTH and 0 <= z < GRID_HEIGHT:
                cmd = PlaceBlockCommand(
                    world=self.world,
                    x=x, y=y, z=z,
                    block_type=blockType
                )
                commands.append(cmd)
        
        if commands:
            batch = BatchCommand(commands)
            self.undoManager.execute(batch)
            print(f"Pasted {len(commands)} blocks")
    
    def _fillSelection(self, blockType: BlockType):
        """Fill selection with a specific block type"""
        bounds = self._getSelectionBounds()
        if not bounds:
            print("No selection to fill")
            return
        
        minP, maxP = bounds
        
        from engine.undo import BatchCommand, PlaceBlockCommand
        commands = []
        
        for x in range(minP[0], maxP[0] + 1):
            for y in range(minP[1], maxP[1] + 1):
                for z in range(minP[2], maxP[2] + 1):
                    cmd = PlaceBlockCommand(
                        world=self.world,
                        x=x, y=y, z=z,
                        block_type=blockType
                    )
                    commands.append(cmd)
        
        if commands:
            batch = BatchCommand(commands)
            self.undoManager.execute(batch)
            print(f"Filled {len(commands)} blocks with {blockType.name}")
        
        self._clearSelection()
    
    def _hollowSelection(self, blockType: BlockType):
        """Create hollow version of selection (edges only)"""
        bounds = self._getSelectionBounds()
        if not bounds:
            print("No selection to hollow")
            return
        
        minP, maxP = bounds
        
        from engine.undo import BatchCommand, PlaceBlockCommand
        commands = []
        
        for x in range(minP[0], maxP[0] + 1):
            for y in range(minP[1], maxP[1] + 1):
                for z in range(minP[2], maxP[2] + 1):
                    # Only place blocks on edges (walls, floor, ceiling)
                    isEdge = (
                        x == minP[0] or x == maxP[0] or
                        y == minP[1] or y == maxP[1] or
                        z == minP[2] or z == maxP[2]
                    )
                    if isEdge:
                        cmd = PlaceBlockCommand(
                            world=self.world,
                            x=x, y=y, z=z,
                            block_type=blockType
                        )
                        commands.append(cmd)
        
        if commands:
            batch = BatchCommand(commands)
            self.undoManager.execute(batch)
            print(f"Created hollow box with {len(commands)} {blockType.name} blocks")
        
        self._clearSelection()
    
    def _renderSelectionBox(self) -> None:
        """Render selection box outline"""
        if not self.selectionActive:
            return
        
        # If only first corner set, show it
        if self.selectionStart and not self.selectionEnd:
            x, y, z = self.selectionStart
            self._renderSelectionMarker(x, y, z, (0, 255, 255))  # Cyan for start
            return
        
        bounds = self._getSelectionBounds()
        if not bounds:
            return
        
        minP, maxP = bounds
        
        # Render outline for all edge blocks
        for x in range(minP[0], maxP[0] + 1):
            for y in range(minP[1], maxP[1] + 1):
                for z in range(minP[2], maxP[2] + 1):
                    # Only render outline for edge blocks
                    isEdge = (
                        x == minP[0] or x == maxP[0] or
                        y == minP[1] or y == maxP[1] or
                        z == minP[2] or z == maxP[2]
                    )
                    if isEdge:
                        self._renderSelectionMarker(x, y, z, (0, 200, 255, 100))
    
    def _renderSelectionMarker(self, x: int, y: int, z: int, color: Tuple[int, ...]):
        """Render a selection marker at the given position"""
        # Convert to screen coordinates
        screenX, screenY = self.renderer.worldToScreen(x, y, z)
        
        # Draw selection outline using isometric shape
        halfW = TILE_WIDTH // 2
        halfH = TILE_HEIGHT // 2
        points = [
            (screenX, screenY),                    # Top
            (screenX + halfW, screenY + halfH),    # Right
            (screenX, screenY + TILE_HEIGHT),      # Bottom  
            (screenX - halfW, screenY + halfH)     # Left
        ]
        
        # Draw outline
        pygame.draw.polygon(self.screen, color[:3], points, 2)
    
    # ==================== End Selection Box Tool ====================
    
    def _renderMagicWandSelection(self) -> None:
        """Render magic wand selected blocks with highlight"""
        if not self.magicWandSelection:
            return
        
        # Draw outline around each selected block
        for x, y, z in self.magicWandSelection:
            # Check if within viewable area
            screenX, screenY = self.renderer.worldToScreen(x, y, z)
            if -100 < screenX < self.width + 100 and -100 < screenY < self.height + 100:
                self._renderSelectionMarker(x, y, z, (255, 100, 255))  # Magenta for magic wand
    
    # ==================== End Magic Wand Tool ====================
    
    def _setVolume(self, volumeType: str, value: float):
        """Set volume for a specific type"""
        value = max(0.0, min(1.0, value))
        
        if volumeType == "music":
            self.musicVolume = value
            pygame.mixer.music.set_volume(value)
        elif volumeType == "ambient":
            self.ambientVolume = value
            # Update ambient sound volumes (portal, rain, etc.)
        elif volumeType == "effects":
            self.effectsVolume = value
    
    def _renderShortcutsPanel(self) -> None:
        """Render keyboard shortcuts help panel"""
        if not self.showShortcutsPanel:
            return
        
        # Semi-transparent overlay
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))
        
        # Panel dimensions
        panelWidth = 500
        panelHeight = 560  # Increased for more shortcuts
        panelX = (WINDOW_WIDTH - panelWidth) // 2
        panelY = (WINDOW_HEIGHT - panelHeight) // 2
        
        # Draw panel background
        panelRect = pygame.Rect(panelX, panelY, panelWidth, panelHeight)
        pygame.draw.rect(self.screen, (40, 40, 50), panelRect, border_radius=10)
        pygame.draw.rect(self.screen, (100, 100, 120), panelRect, 3, border_radius=10)
        
        # Title
        titleText = self.font.render("Keyboard Shortcuts", True, (255, 255, 255))
        titleX = panelX + (panelWidth - titleText.get_width()) // 2
        self.screen.blit(titleText, (titleX, panelY + 15))
        
        # Shortcuts list
        shortcuts = [
            ("Left Click", "Place block"),
            ("Right Click", "Remove block / Toggle doors"),
            ("Middle Click + Drag", "Pan view"),
            ("Scroll Wheel", "Scroll panel / Zoom (Shift)"),
            ("1-9 / Shift+1-9", "Hotbar row 1 / row 2"),
            ("Q / E", "Rotate view left / right"),
            ("R", "Rotate stairs"),
            ("F", "Flip slab / Fill tool"),
            ("G", "Toggle grid"),
            ("X", "X-Ray mode (see through blocks)"),
            ("B", "Cycle brush size (1x1, 2x2, 3x3)"),
            ("M", "Measurement tool"),
            ("W", "Magic wand (select connected)"),
            ("P", "Stamp tool (copy first)"),
            ("[ / ]", "Rotate clipboard"),
            ("Tab", "Toggle minimap"),
            ("Ctrl+D", "Toggle favorite block"),
            ("Ctrl+R", "Replace all blocks mode"),
            ("Ctrl+T", "Cycle radial symmetry"),
            ("Ctrl+H", "Hollow selection"),
            ("Ctrl+Shift+F", "3D flood fill space"),
            ("Shift+M / Ctrl+M", "Mirror X / Y axis"),
            ("/ . ,", "Layer view / Up / Down"),
            ("Ctrl+F", "Search blocks"),
            ("Alt+Click", "Eyedropper (pick block)"),
            ("Ctrl+S / Ctrl+O", "Save / Load build"),
            ("Ctrl+Z / Ctrl+Y", "Undo / Redo"),
            ("Del", "Delete selection"),
            ("?", "Toggle this help"),
            ("ESC", "Close / Cancel / Quit")
        ]
        
        startY = panelY + 50
        leftCol = panelX + 30
        rightCol = panelX + 200
        lineHeight = 22  # Reduced to fit more shortcuts
        
        for i, (key, action) in enumerate(shortcuts):
            y = startY + i * lineHeight
            
            # Key (in a small box)
            keyText = self.smallFont.render(key, True, (255, 220, 100))
            keyBg = pygame.Rect(leftCol - 5, y - 2, keyText.get_width() + 10, 20)
            pygame.draw.rect(self.screen, (60, 60, 70), keyBg, border_radius=3)
            self.screen.blit(keyText, (leftCol, y))
            
            # Action
            actionText = self.smallFont.render(action, True, (200, 200, 200))
            self.screen.blit(actionText, (rightCol, y))
        
        # Close hint
        closeText = self.smallFont.render("Press ? or ESC to close", True, (150, 150, 150))
        closeX = panelX + (panelWidth - closeText.get_width()) // 2
        self.screen.blit(closeText, (closeX, panelY + panelHeight - 30))
    
    def _toggleCelestial(self):
        """Toggle sun/moon cycle on/off (only works in Overworld)"""
        if self.currentDimension != DIMENSION_OVERWORLD:
            return  # Sun/Moon only in Overworld
        
        self.celestialEnabled = not self.celestialEnabled
        
        if self.celestialEnabled:
            self._startCelestial()
        else:
            self._stopCelestial()
    
    def _startCelestial(self):
        """Initialize celestial cycle"""
        self.celestialAngle = 90.0  # Start at noon (sun at top)
        self.dayBrightness = 1.0
        self.moonPhase = random.randint(0, 7)  # Random moon phase
        
        # Celestial body size (smaller for more Minecraft-like appearance)
        self.celestialSize = 48  # Smaller sun/moon
        
        # Load textures if not already loaded
        if self.sunTexture is None:
            try:
                sunPath = os.path.join("Assets", "Texture Hub", "environment", "sun.png")
                if os.path.exists(sunPath):
                    self.sunTexture = pygame.image.load(sunPath).convert_alpha()
                    # Scale to larger size for visibility
                    self.sunTexture = pygame.transform.scale(self.sunTexture, (self.celestialSize, self.celestialSize))
            except Exception as e:
                print(f"Could not load sun texture: {e}")
        
        if self.moonTexture is None:
            try:
                moonPath = os.path.join("Assets", "Texture Hub", "environment", "moon_phases.png")
                if os.path.exists(moonPath):
                    fullMoon = pygame.image.load(moonPath).convert_alpha()
                    # moon_phases.png is a 4x2 grid of phases, each 32x32
                    # Extract current phase
                    phaseX = (self.moonPhase % 4) * 32
                    phaseY = (self.moonPhase // 4) * 32
                    self.moonTexture = fullMoon.subsurface(pygame.Rect(phaseX, phaseY, 32, 32))
                    # Scale to same size as sun
                    self.moonTexture = pygame.transform.scale(self.moonTexture, (self.celestialSize, self.celestialSize))
            except Exception as e:
                print(f"Could not load moon texture: {e}")
    
    def _stopCelestial(self):
        """Stop celestial cycle and reset brightness"""
        self.celestialEnabled = False
        self.dayBrightness = 1.0  # Reset to full brightness
    
    def _updateCelestial(self, dt: int):
        """Update celestial body positions and day/night lighting"""
        if not self.celestialEnabled:
            # Gradually restore brightness when disabled
            if self.dayBrightness < 1.0:
                self.dayBrightness = min(1.0, self.dayBrightness + 0.01)
            return
        
        # Advance celestial angle (full cycle is 720 degrees: 0-360 sun, 360-720 moon)
        # At 0.5 degrees per frame at 60fps, one full day/night cycle takes ~24 seconds
        self.celestialAngle += self.celestialSpeed
        if self.celestialAngle >= 720:
            self.celestialAngle -= 720
            # Advance moon phase at end of night
            self.moonPhase = (self.moonPhase + 1) % 8
            # Reload moon texture with new phase
            try:
                moonPath = os.path.join("Assets", "Texture Hub", "environment", "moon_phases.png")
                if os.path.exists(moonPath):
                    fullMoon = pygame.image.load(moonPath).convert_alpha()
                    phaseX = (self.moonPhase % 4) * 32
                    phaseY = (self.moonPhase // 4) * 32
                    self.moonTexture = fullMoon.subsurface(pygame.Rect(phaseX, phaseY, 32, 32))
                    self.moonTexture = pygame.transform.scale(self.moonTexture, (self.celestialSize, self.celestialSize))
            except (pygame.error, FileNotFoundError) as e:
                print(f"Warning: Could not load moon texture: {e}")
        
        # Calculate brightness based on angle
        # 0-360 is day (sun doing full rotation), 360-720 is night (moon doing full rotation)
        if self.celestialAngle < 30:
            # Sunrise transition (0-30)
            self.dayBrightness = 0.25 + (self.celestialAngle / 30) * 0.75
        elif self.celestialAngle < 330:
            # Full day (30-330)
            self.dayBrightness = 1.0
        elif self.celestialAngle < 360:
            # Sunset transition (330-360)
            self.dayBrightness = 1.0 - ((self.celestialAngle - 330) / 30) * 0.75
        elif self.celestialAngle < 390:
            # Dusk to full night (360-390)
            self.dayBrightness = 0.25 - ((self.celestialAngle - 360) / 30) * 0.20
        elif self.celestialAngle < 690:
            # Full night (390-690) - very dark for stars to be visible
            self.dayBrightness = 0.05
        else:
            # Dawn transition (690-720)
            self.dayBrightness = 0.05 + ((self.celestialAngle - 690) / 30) * 0.20
    
    def _renderCelestial(self) -> None:
        """Render sun and moon as Minecraft-style squares with glow layers and additive blending"""
        if not self.celestialEnabled:
            return
        
        # Calculate panel boundary
        panelLeft = WINDOW_WIDTH - PANEL_WIDTH
        
        # Calculate center of the grass plane (roughly center of playable area)
        centerX = (panelLeft) // 2
        centerY = WINDOW_HEIGHT // 2 - 50  # Slightly above center
        
        # Orbit radius (how far sun/moon travel from center)
        orbitRadiusX = panelLeft // 3  # Horizontal radius
        orbitRadiusY = WINDOW_HEIGHT // 3  # Vertical radius (elliptical orbit)
        
        # Sun is visible during 0-360 (full rotation)
        if self.celestialAngle < 360:
            # Map 0-360 to a full orbit
            sunAngle = self.celestialAngle
            radians = math.radians(sunAngle - 90)  # -90 so 0 degrees = sunrise (right side)
            
            sunX = centerX + int(orbitRadiusX * math.cos(radians))
            sunY = centerY - int(orbitRadiusY * math.sin(radians))  # Negative because Y increases downward
            
            if self.sunTexture and 0 <= sunX < panelLeft:
                texSize = self.celestialSize
                
                # LAYER 3: Outer glow (large, faint) - 20% opacity
                outerGlowSize = texSize * 3
                outerGlow = pygame.Surface((outerGlowSize, outerGlowSize), pygame.SRCALPHA)
                outerGlow.fill((255, 200, 100, 50))  # Faint warm orange
                drawX = sunX - outerGlowSize // 2
                drawY = sunY - outerGlowSize // 2
                self.screen.blit(outerGlow, (drawX, drawY), special_flags=pygame.BLEND_RGBA_ADD)
                
                # LAYER 2: Medium glow (yellow-orange) - 50% opacity
                midGlowSize = texSize * 2
                midGlow = pygame.Surface((midGlowSize, midGlowSize), pygame.SRCALPHA)
                midGlow.fill((255, 220, 80, 80))  # Medium warm yellow
                drawX = sunX - midGlowSize // 2
                drawY = sunY - midGlowSize // 2
                self.screen.blit(midGlow, (drawX, drawY), special_flags=pygame.BLEND_RGBA_ADD)
                
                # LAYER 1: Core texture (square, bright) with additive blending
                # Draw the actual sun texture as a SQUARE (Minecraft style)
                texWidth = self.sunTexture.get_width()
                texHeight = self.sunTexture.get_height()
                drawX = sunX - texWidth // 2
                drawY = sunY - texHeight // 2
                # Use additive blending for that "glowing" look
                self.screen.blit(self.sunTexture, (drawX, drawY), special_flags=pygame.BLEND_RGBA_ADD)
        
        # Moon is visible during 360-720 (full rotation)
        if self.celestialAngle >= 360:
            # Map 360-720 to a full orbit (0-360)
            moonAngle = self.celestialAngle - 360
            radians = math.radians(moonAngle - 90)  # -90 so 0 degrees = moonrise (right side)
            
            moonX = centerX + int(orbitRadiusX * math.cos(radians))
            moonY = centerY - int(orbitRadiusY * math.sin(radians))
            
            if self.moonTexture and 0 <= moonX < panelLeft:
                texSize = self.celestialSize
                
                # LAYER 3: Outer glow (large, faint blue) - 15% opacity
                outerGlowSize = texSize * 2 + 20
                outerGlow = pygame.Surface((outerGlowSize, outerGlowSize), pygame.SRCALPHA)
                outerGlow.fill((150, 180, 220, 35))  # Faint cool blue
                drawX = moonX - outerGlowSize // 2
                drawY = moonY - outerGlowSize // 2
                self.screen.blit(outerGlow, (drawX, drawY), special_flags=pygame.BLEND_RGBA_ADD)
                
                # LAYER 2: Medium glow (silvery) - 30% opacity
                midGlowSize = texSize + texSize // 2
                midGlow = pygame.Surface((midGlowSize, midGlowSize), pygame.SRCALPHA)
                midGlow.fill((200, 210, 230, 50))  # Medium silver-blue
                drawX = moonX - midGlowSize // 2
                drawY = moonY - midGlowSize // 2
                self.screen.blit(midGlow, (drawX, drawY), special_flags=pygame.BLEND_RGBA_ADD)
                
                # LAYER 1: Core texture (square moon) - normal blit for moon (not as bright)
                texWidth = self.moonTexture.get_width()
                texHeight = self.moonTexture.get_height()
                drawX = moonX - texWidth // 2
                drawY = moonY - texHeight // 2
                # Moon uses normal blending (not as glowing as sun)
                self.screen.blit(self.moonTexture, (drawX, drawY))

    def _updateRain(self, dt: int):
        """Update rain particle positions and effects"""
        if not self.rainEnabled:
            # Fade out sky darkness and lightning
            if self.skyDarkness > 0:
                self.skyDarkness = max(0, self.skyDarkness - 2)
            if self.lightningFlash > 0:
                self.lightningFlash = max(0, self.lightningFlash - 15)
            return
        
        # Fade in sky darkness (130 for darker stormy effect)
        if self.skyDarkness < 130:
            self.skyDarkness = min(130, self.skyDarkness + 1)
        
        # Fade out lightning flash
        if self.lightningFlash > 0:
            self.lightningFlash = max(0, self.lightningFlash - 8)
        
        # Update rain intensity over time (creates heavier/lighter rain periods)
        self.rainIntensityTimer += dt
        if self.rainIntensityTimer >= 10000:  # Every 10 seconds, maybe change intensity
            self.rainIntensityTimer = 0
            if random.random() < 0.3:  # 30% chance to change
                self.rainIntensityTarget = random.uniform(0.6, 1.4)
        # Gradually move towards target intensity
        if self.rainIntensity < self.rainIntensityTarget:
            self.rainIntensity = min(self.rainIntensityTarget, self.rainIntensity + 0.005)
        elif self.rainIntensity > self.rainIntensityTarget:
            self.rainIntensity = max(self.rainIntensityTarget, self.rainIntensity - 0.005)
        
        # Rain sound is handled by pygame.mixer.music (single long track)
        # No complex channel management needed
        
        # Update rain drops with wind angle and intensity
        dropSpeed = int(20 * self.rainIntensity)
        for drop in self.rainDrops:
            drop["y"] += drop["speed"] * self.rainIntensity
            drop["x"] += drop["angle"] * drop["speed"]  # Wind drift
            
            # If drop goes off screen, reset to top
            if drop["y"] > WINDOW_HEIGHT or drop["x"] > WINDOW_WIDTH:
                drop["y"] = random.randint(-50, -10)
                drop["x"] = random.randint(-50, WINDOW_WIDTH)
                drop["speed"] = random.randint(15, 25)
                drop["length"] = random.randint(10, 20)
                drop["angle"] = random.uniform(0.08, 0.15)
        
        # Spawn splashes directly on random blocks (scaled by intensity)
        self.splashSpawnTimer += dt
        splashInterval = int(50 / self.rainIntensity)  # More frequent when intense
        if self.splashSpawnTimer >= splashInterval:
            self.splashSpawnTimer = 0
            self._spawnSplashesOnBlocks()
        
        # Update splashes
        for splash in self.rainSplashes:
            splash["life"] -= 1
        self.rainSplashes = [s for s in self.rainSplashes if s["life"] > 0]
        
        # Lightning timing (visual effect with thunder sound)
        self.thunderTimer += dt
        if self.thunderTimer >= self.nextThunderTime:
            self._triggerLightning()  # Now triggers lightning WITH thunder
            self.thunderTimer = 0
            self.nextThunderTime = random.randint(15000, 35000)  # 15-35 seconds between lightning strikes
        
        # Thunder ambient background (distant rumbles, separate from lightning)
        self.thunderAmbientTimer += dt
        if self.thunderAmbientTimer >= self.nextThunderAmbientTime:
            self._playThunderAmbient()
            self.thunderAmbientTimer = 0
            self.nextThunderAmbientTime = random.randint(8000, 18000)  # 8-18 sec between ambient rumbles
        
        # Update lightning bolt visibility
        if self.lightningBoltTimer > 0:
            self.lightningBoltTimer -= dt
            if self.lightningBoltTimer <= 0:
                self.lightningBolt = []
        
        # Subtle whispers during rain (horror feature)
        if self.horrorEnabled:
            self._updateRainWhispers(dt)
    
    def _updateRainWhispers(self, dt: int):
        """Update subtle whisper sounds that play rarely during rain"""
        # Initialize whisper timer if needed
        if self.nextRainWhisperTime == 0:
            self.nextRainWhisperTime = random.randint(120000, 300000)  # 2-5 minutes between whispers
        
        self.rainWhisperTimer += dt
        if self.rainWhisperTimer >= self.nextRainWhisperTime:
            self._playRainWhisper()
            self.rainWhisperTimer = 0
            self.nextRainWhisperTime = random.randint(180000, 420000)  # 3-7 minutes for subsequent
    
    def _playRainWhisper(self):
        """Play a barely audible whisper sound layered under rain"""
        # Try to use cave sounds as whispers (they're creepy enough)
        if self.assetManager.horrorSounds.get('cave'):
            # Use cave ambient sounds as "whispers" - they're eerie
            whisperSound = random.choice(self.assetManager.horrorSounds['cave'])
            channel = pygame.mixer.find_channel()
            if channel:
                channel.play(whisperSound)
                # Very quiet - barely audible under rain
                channel.set_volume(random.uniform(0.03, 0.08) * self.ambientVolume)
    
    def _playThunderAmbient(self):
        """Play distant thunder ambient sound (no lightning flash)"""
        if self.assetManager.thunderAmbientSounds:
            ambientSound = random.choice(self.assetManager.thunderAmbientSounds)
            # Play on a channel if available
            channel = pygame.mixer.find_channel()
            if channel:
                channel.play(ambientSound)
                channel.set_volume(random.uniform(0.15, 0.3))  # Quieter distant rumble
    
    def _triggerLightning(self):
        """Trigger lightning flash with bolt and play thunder sound"""
        if self.assetManager.thunderSounds:
            thunderSound = random.choice(self.assetManager.thunderSounds)
            thunderSound.play()
        # Trigger lightning flash
        self.lightningFlash = 100  # Moderate flash that will fade out
        
        # Find a random block on the platform to strike
        panelLeft = WINDOW_WIDTH - PANEL_WIDTH
        
        # Get all top blocks to choose a target
        topBlocks = {}
        for (x, y, z), blockType in self.world.blocks.items():
            if (x, y) not in topBlocks or z > topBlocks[(x, y)]:
                topBlocks[(x, y)] = z
        
        if topBlocks:
            # Pick a random block to strike
            targetPos = random.choice(list(topBlocks.keys()))
            targetX, targetY = targetPos
            targetZ = topBlocks[targetPos]
            
            # Convert to screen coordinates
            screenX, screenY = self.renderer.worldToScreen(targetX, targetY, targetZ)
            
            # Make sure target is within visible area
            if 50 <= screenX <= panelLeft - 50:
                endX = screenX
                endY = screenY
            else:
                # Fallback to random position on screen
                endX = random.randint(100, panelLeft - 100)
                endY = random.randint(WINDOW_HEIGHT // 2, WINDOW_HEIGHT - 50)
        else:
            # No blocks, strike random position
            endX = random.randint(100, panelLeft - 100)
            endY = random.randint(WINDOW_HEIGHT // 2, WINDOW_HEIGHT - 50)
        
        # Start from top of screen, slightly offset from target
        startX = endX + random.randint(-50, 50)
        startY = 0
        
        # Build bolt with jagged segments going towards target
        self.lightningBolt = [(startX, startY)]
        currentX, currentY = startX, startY
        segmentLength = random.randint(25, 40)
        
        while currentY < endY - 20:
            # Move down with random horizontal jag, but bias towards target
            currentY += segmentLength
            # Bias horizontal movement towards target
            directionBias = (endX - currentX) * 0.1
            currentX += random.randint(-25, 25) + int(directionBias)
            # Keep bolt within reasonable bounds
            currentX = max(50, min(panelLeft - 50, currentX))
            self.lightningBolt.append((currentX, min(currentY, endY)))
            segmentLength = random.randint(20, 45)
        
        # Final segment goes to target
        self.lightningBolt.append((endX, endY))
        
        # Sometimes add a branch
        if random.random() < 0.6 and len(self.lightningBolt) > 3:
            branchStart = random.randint(1, len(self.lightningBolt) - 2)
            branchX, branchY = self.lightningBolt[branchStart]
            branchDir = random.choice([-1, 1])
            for _ in range(random.randint(2, 4)):
                branchX += branchDir * random.randint(20, 40)
                branchY += random.randint(20, 35)
                self.lightningBolt.append((branchX, branchY))
                self.lightningBolt.append(self.lightningBolt[branchStart])  # Connect back for drawing
        
        self.lightningBoltTimer = 150  # Visible for 150ms
    
    def _spawnSplashesOnBlocks(self):
        """Spawn splash effects directly on random blocks in the world"""
        # Find the highest block at each (x, y) position
        topBlocks = {}  # (x, y) -> z
        for (x, y, z), blockType in self.world.blocks.items():
            if (x, y) not in topBlocks or z > topBlocks[(x, y)]:
                topBlocks[(x, y)] = z
        
        if not topBlocks:
            return
        
        # Spawn 3-6 splashes per update on random top blocks (scaled by intensity)
        blockList = list(topBlocks.items())
        numSplashes = min(len(blockList), int(random.randint(3, 6) * self.rainIntensity))
        
        for _ in range(numSplashes):
            (x, y), z = random.choice(blockList)
            
            # worldToScreen returns the TOP VERTEX (apex) of the tile diamond
            # This is already the center X position of the block
            screenX, screenY = self.renderer.worldToScreen(x, y, z)
            
            # screenX is the center X of the diamond's top vertex
            # screenY is the Y of the top vertex
            # The diamond center (middle of top face) is at screenY + TILE_HEIGHT/2
            # Keep offsets very small to stay within the visible block top
            offsetX = random.randint(-6, 6)
            offsetY = random.randint(-3, 3)
            
            # Add panning offset - screenX is already the center
            splashX = screenX + self.panOffsetX + offsetX
            splashY = screenY + self.panOffsetY + TILE_HEIGHT // 4 + offsetY  # Move down to center of top face
            
            self.rainSplashes.append({
                "x": splashX,
                "y": splashY,
                "life": 12,  # Longer life for more visible splashes
                "size": random.randint(3, 6)  # Larger splashes
            })
    
    def _renderRain(self) -> None:
        """Render rain overlay effects"""
        if not self.rainEnabled and not self.rainDrops:
            return
        
        # Calculate panel boundary (don't render rain on UI panel)
        panelLeft = WINDOW_WIDTH - PANEL_WIDTH
        
        # Draw rain drops with visible blue glow
        for drop in self.rainDrops:
            # Skip drops over the UI panel
            if drop["x"] > panelLeft:
                continue
            
            # Calculate angled end position
            angle = drop.get("angle", 0.1)
            endX = drop["x"] + int(drop["length"] * angle)
            endY = drop["y"] + drop["length"]
            
            # Blue glow effect (drawn first, behind the drop)
            # Glow is more visible when lighting is enabled
            glowIntensity = 60 if self.lightingEnabled else 40
            glowWidth = 6 if self.lightingEnabled else 4
            glowSurf = pygame.Surface((12, int(drop["length"]) + 8), pygame.SRCALPHA)
            glowColor = (80, 140, 255, glowIntensity)  # Bright blue glow
            pygame.draw.line(glowSurf, glowColor, (6, 0), (6, int(drop["length"])), glowWidth)
            self.screen.blit(glowSurf, (int(drop["x"]) - 6, int(drop["y"]) - 4))
            
            # Rain streak color (blue-gray)
            color = (70, 100, 140, 220)
            pygame.draw.line(
                self.screen,
                color,
                (int(drop["x"]), int(drop["y"])),
                (int(endX), int(endY)),
                1
            )
        
        # Draw splash particles (more pronounced)
        for splash in self.rainSplashes:
            # Skip splashes over the UI panel
            if splash["x"] > panelLeft:
                continue
                
            alpha = int(220 * (splash["life"] / 12))
            # Draw expanding ring splash effect
            expansion = (12 - splash["life"]) * 0.5  # Expand as life decreases
            size = splash["size"] + expansion
            
            # Outer ring
            splashSurf = pygame.Surface((int(size * 3), int(size * 1.5)), pygame.SRCALPHA)
            splashColor = (180, 200, 240, alpha)
            pygame.draw.ellipse(splashSurf, splashColor, splashSurf.get_rect(), 2)  # Ring, not filled
            self.screen.blit(splashSurf, (splash["x"] - size * 1.5, splash["y"] - size * 0.75))
            
            # Inner splash dot
            if splash["life"] > 6:
                dotSize = max(2, splash["size"] - 1)
                dotSurf = pygame.Surface((dotSize * 2, dotSize), pygame.SRCALPHA)
                dotColor = (200, 220, 255, alpha)
                pygame.draw.ellipse(dotSurf, dotColor, dotSurf.get_rect())
                self.screen.blit(dotSurf, (splash["x"] - dotSize, splash["y"] - dotSize // 2))
        
        # Draw lightning bolt (Minecraft-style jagged white line)
        if self.lightningBolt and self.lightningBoltTimer > 0:
            # Draw thick white bolt with glow effect
            # Outer glow (purple-blue tint like Minecraft)
            if len(self.lightningBolt) >= 2:
                for i in range(len(self.lightningBolt) - 1):
                    # Check if this is a branch return point (same as previous)
                    if self.lightningBolt[i] == self.lightningBolt[i-1] if i > 0 else False:
                        continue
                    start = self.lightningBolt[i]
                    end = self.lightningBolt[i + 1]
                    # Outer glow - thick and blue-purple
                    pygame.draw.line(self.screen, (150, 150, 255), start, end, 7)
                    pygame.draw.line(self.screen, (200, 200, 255), start, end, 5)
                    # Core - bright white
                    pygame.draw.line(self.screen, (255, 255, 255), start, end, 3)
                    pygame.draw.line(self.screen, (255, 255, 255), start, end, 2)
        
        # Draw lightning flash overlay
        if self.lightningFlash > 0:
            flashOverlay = pygame.Surface((WINDOW_WIDTH - PANEL_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
            flashOverlay.fill((255, 255, 255, self.lightningFlash))
            self.screen.blit(flashOverlay, (0, 0))

    def _render(self) -> None:
        """Render the game"""
        # Draw tiled dirt background
        self.assetManager.drawBackground(self.screen)
        
        # Draw clouds (behind celestial bodies, before darkness)
        self._renderClouds()
        
        # Draw celestial bodies (sun/moon) behind everything else
        self._renderCelestial()
        
        # Draw day/night darkness overlay (based on celestial cycle)
        # At full night (moon at top), background should be nearly black
        if self.celestialEnabled and self.dayBrightness < 1.0:
            # Use much darker overlay - closer to 250 for near-black at night
            nightDarkness = int((1.0 - self.dayBrightness) * 250)  # Max darkness of 250 (almost black)
            darkOverlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
            # Very dark blue-black for night
            darkOverlay.fill((2, 5, 15, nightDarkness))
            self.screen.blit(darkOverlay, (0, 0))
        
        # Draw stars AFTER darkness overlay so they stay bright on top of the dark sky
        self._renderStars()
        
        # Draw rain darkening overlay (behind world but on background)
        if self.skyDarkness > 0:
            darkOverlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
            darkOverlay.fill((20, 30, 50, self.skyDarkness))
            self.screen.blit(darkOverlay, (0, 0))
        
        # Draw grid and blocks
        self._renderWorld()
        
        # Draw grid overlay if enabled
        self._renderGrid()
        
        # Draw block highlight (outline around hovered block)
        self._renderBlockHighlight()
        
        # Draw ghost block preview
        if self.hoveredCell and not self.panelHovered and not self.structurePlacementMode:
            self._renderGhostBlock()
        
        # Draw block breaking particles
        self._renderBlockParticles()
        
        # Draw rain effects (on top of world, but under UI)
        self._renderRain()
        
        # Draw horror rain effects (black rain)
        self._renderHorrorRain()
        
        # Draw snow effects (on top of world, but under UI)
        self._renderSnow()
        
        # Draw selection box (if in selection mode)
        self._renderSelectionBox()
        
        # Draw magic wand selection
        self._renderMagicWandSelection()
        
        # Draw measurement line (if in measurement mode)
        self._renderMeasurementLine()
        
        # Draw block tooltip (world blocks)
        self._renderBlockTooltip()
        
        # Draw height indicator
        self._renderHeightIndicator()
        
        # Draw placement particles
        self._renderPlacementParticles()
        
        # Draw UI panel
        self._renderPanel()
        
        # Draw panel block tooltip (after panel is rendered)
        self._renderPanelBlockTooltip()
        
        # Draw hotbar at bottom
        self._renderHotbar()
        
        # Draw search box if active
        self._renderSearchBox()
        
        # Draw coordinate display
        self._renderCoordinates()
        
        # Draw dimension indicator (top left)
        self._renderDimensionIndicator()
        
        # Draw mirror mode indicator
        self._renderMirrorIndicator()
        
        # Draw layer view indicator
        self._renderLayerIndicator()
        
        # Draw mode indicators (radial, replace, magic wand)
        self._renderModeIndicators()
        
        # Draw view rotation indicator
        self._renderViewRotationIndicator()
        
        # Draw minimap
        self._renderMinimap()
        
        # Draw build statistics
        self._renderBuildStats()
        
        # Draw auto-save indicator
        self._renderAutoSaveIndicator()
        
        # Draw structure thumbnail tooltip (on top of panel)
        self._renderStructureTooltip()
        
        # Draw status text
        self._renderStatus()
        
        # Draw keyboard shortcuts panel (on top of everything)
        self._renderShortcutsPanel()
        
        # Draw tooltip notifications
        self._renderTooltipNotification()
        
        # Draw settings menu if open
        self._renderSettingsMenu()
        
        # Draw history panel if open
        self._renderHistoryPanel()
        
        # Draw tutorial overlay (on top of everything)
        self.tutorialScreen.render(self.screen)
        
        # Draw horror visual effects (very last, for maximum creepiness)
        self._renderHorrorEffects()
        
        # Update display
        pygame.display.flip()
    
    def _applyLighting(self, sprite: pygame.Surface, x: int, y: int, z: int, blockType: BlockType) -> pygame.Surface:
        """
        Apply Minecraft-style lighting to a sprite.
        Combines block light level with ambient occlusion and colored light tint.
        """
        # Get light level and color at this position
        blockDef = BLOCK_DEFINITIONS.get(blockType)
        
        # Light sources emit their own light - they're always fully lit
        # Also skip ambient occlusion for light sources to prevent flat appearance
        if blockDef and blockDef.lightLevel > 0:
            # Return original sprite for light sources (no darkening/AO)
            return sprite
        else:
            # Get light from the lightmap (now stores (level, color) tuples)
            lightData = self.lightMap.get((x, y, z), None)
            if lightData:
                lightLevel, lightColor = lightData
            else:
                lightLevel = 0
                lightColor = (255, 200, 150)  # Default warm light
            
            # Also check neighboring positions for light bleeding through
            for dx, dy, dz in [(1,0,0), (-1,0,0), (0,1,0), (0,-1,0), (0,0,1), (0,0,-1)]:
                neighborData = self.lightMap.get((x+dx, y+dy, z+dz), None)
                if neighborData:
                    neighborLight, neighborColor = neighborData
                    if neighborLight > lightLevel:
                        lightLevel = max(lightLevel, neighborLight - 1)
                        lightColor = neighborColor
        
        # Calculate ambient occlusion
        topAO, leftAO, rightAO = self.world.calculateAmbientOcclusion(x, y, z)
        
        # Create cache key with rounded AO values and light color for better cache hits
        aoKey = (round(topAO, 1), round(leftAO, 1), round(rightAO, 1))
        cacheKey = (blockType, lightLevel, lightColor, aoKey[0], aoKey[1], aoKey[2])
        
        # Check cache first (LRU cache)
        if cacheKey in self.litBlockCache:
            # Move to end (most recently used)
            if cacheKey in self.litBlockCacheOrder:
                self.litBlockCacheOrder.remove(cacheKey)
            self.litBlockCacheOrder.append(cacheKey)
            return self.litBlockCache[cacheKey]
        
        # Calculate brightness (0.0 to 1.0)
        # Minecraft uses exponential falloff: each level is ~80% of the previous
        # Level 15 = 100%, Level 0 = ~5%
        baseBrightness = 0.05 + (lightLevel / 15.0) * 0.95
        
        # Apply AO by averaging (simplified - real MC does per-vertex)
        avgAO = (topAO + leftAO + rightAO) / 3.0
        finalBrightness = baseBrightness * avgAO
        
        # Clamp brightness
        finalBrightness = max(0.15, min(1.0, finalBrightness))
        
        # Create new surface with lighting applied
        litSprite = sprite.copy()
        
        # Calculate color tint intensity (stronger tint at moderate light levels)
        # At full brightness, less tint; at low brightness, tint is dimmed anyway
        tintStrength = min(1.0, lightLevel / 15.0) * 0.4 if lightLevel > 0 else 0
        
        # Normalize light color to tint values (-1 to 1 range for each channel)
        lr, lg, lb = lightColor
        tintR = (lr - 200) / 100.0 * tintStrength  # How much to shift red
        tintG = (lg - 200) / 100.0 * tintStrength  # How much to shift green
        tintB = (lb - 200) / 100.0 * tintStrength  # How much to shift blue
        
        # Apply lighting as a color overlay
        w, h = litSprite.get_size()
        for py in range(h):
            for px in range(w):
                color = litSprite.get_at((px, py))
                if color.a > 0:  # Only modify non-transparent pixels
                    r, g, b, a = color
                    
                    # Apply brightness
                    r = int(r * finalBrightness)
                    g = int(g * finalBrightness)
                    b = int(b * finalBrightness)
                    
                    # Apply colored light tint
                    if lightLevel > 0:
                        r = max(0, min(255, int(r + tintR * 60)))
                        g = max(0, min(255, int(g + tintG * 40)))
                        b = max(0, min(255, int(b + tintB * 60)))
                    
                    litSprite.set_at((px, py), (r, g, b, a))
        
        # Cache the result with LRU eviction
        self.litBlockCache[cacheKey] = litSprite
        self.litBlockCacheOrder.append(cacheKey)
        
        # Evict oldest entries if cache is full
        while len(self.litBlockCacheOrder) > self.litBlockCacheMaxSize:
            oldestKey = self.litBlockCacheOrder.pop(0)
            if oldestKey in self.litBlockCache:
                del self.litBlockCache[oldestKey]
        
        return litSprite
    
    def _toggleLighting(self):
        """Toggle experimental lighting on/off"""
        self.lightingEnabled = not self.lightingEnabled
        self.lightingDirty = True
        self.litBlockCache.clear()
        self.litBlockCacheOrder.clear()
        if self.lightingEnabled:
            print("Lighting: ON (experimental)")
        else:
            print("Lighting: OFF")

    def _renderWorld(self) -> None:
        """Render the world blocks in correct order"""
        # Update lighting if needed
        if self.lightingEnabled and self.lightingDirty:
            self.lightMap = self.world.calculateLighting()
            self.lightingDirty = False
            # Clear lit sprite cache when lighting changes
            self.litBlockCache.clear()
            self.litBlockCacheOrder.clear()
        
        # Collect all blocks with their sort keys
        blocksToDraw = []
        
        # Sort key depends on view rotation for correct painter's algorithm
        viewRot = self.renderer.viewRotation
        
        for (x, y, z), blockType in self.world.blocks.items():
            # Calculate sort key based on view rotation
            # For each view, we need to sort from back to front
            if viewRot == 0:
                sortKey = x + y + z  # Default: back-left is far
            elif viewRot == 1:
                sortKey = -y + x + z  # Rotated 90° CW
            elif viewRot == 2:
                sortKey = -x - y + z  # Rotated 180°
            elif viewRot == 3:
                sortKey = y - x + z  # Rotated 270° CW
            else:
                sortKey = x + y + z
            blocksToDraw.append((sortKey, x, y, z, blockType))
        
        # Sort by depth (furthest first)
        blocksToDraw.sort(key=lambda b: b[0])
        
        # Draw blocks
        for _, x, y, z, blockType in blocksToDraw:
            screenX, screenY = self.renderer.worldToScreen(x, y, z)
            
            # Horror: Block texture flicker - briefly show wrong texture
            displayBlockType = blockType
            if self.horrorEnabled and self.blockFlickerPos == (x, y, z):
                # Show a random different block type for this frame
                allBlocks = list(BlockType)
                wrongBlocks = [b for b in allBlocks if b != blockType and b != BlockType.AIR]
                if wrongBlocks:
                    displayBlockType = random.choice(wrongBlocks)
            
            # Check if this is a liquid with a specific level
            if displayBlockType in (BlockType.WATER, BlockType.LAVA):
                level = self.world.getLiquidLevel(x, y, z)
                if level < 8 and level > 0:
                    # Use cached level sprite or generate one
                    if hasattr(self, 'liquidSpriteCache') and (x, y, z) in self.liquidSpriteCache:
                        sprite = self.liquidSpriteCache[(x, y, z)]
                    else:
                        isWater = displayBlockType == BlockType.WATER
                        sprite = self.assetManager.createLiquidAtLevel(isWater, level)
                        if not hasattr(self, 'liquidSpriteCache'):
                            self.liquidSpriteCache = {}
                        self.liquidSpriteCache[(x, y, z)] = sprite
                else:
                    sprite = self.assetManager.getBlockSprite(displayBlockType)
            else:
                # Check for special blocks with properties
                blockDef = BLOCK_DEFINITIONS.get(displayBlockType)
                props = self.world.getBlockProperties(x, y, z)
                
                if blockDef and blockDef.isDoor and props:
                    # Door - use open/closed state only
                    key = (displayBlockType, props.isOpen)
                    sprite = self.assetManager.doorSprites.get(key)
                    if not sprite:
                        sprite = self.assetManager.getBlockSprite(displayBlockType)
                elif blockDef and blockDef.isStair and props:
                    # Stair - use facing
                    key = (displayBlockType, props.facing)
                    sprite = self.assetManager.stairSprites.get(key)
                    if not sprite:
                        sprite = self.assetManager.getBlockSprite(displayBlockType)
                elif blockDef and blockDef.isSlab and props:
                    # Slab - use position
                    key = (displayBlockType, props.slabPosition)
                    sprite = self.assetManager.slabSprites.get(key)
                    if not sprite:
                        sprite = self.assetManager.getBlockSprite(displayBlockType)
                else:
                    sprite = self.assetManager.getBlockSprite(displayBlockType)
            
            if sprite:
                # Apply view rotation flip (views 1 and 3 need horizontal flip)
                viewRot = self.renderer.viewRotation
                if viewRot == 1 or viewRot == 3:
                    sprite = pygame.transform.flip(sprite, True, False)
                
                # Apply lighting if enabled
                if self.lightingEnabled:
                    sprite = self._applyLighting(sprite, x, y, z, blockType)
                
                # Apply zoom scaling if not at default zoom
                if self.zoomLevel != 1.0:
                    newW = int(sprite.get_width() * self.zoomLevel)
                    newH = int(sprite.get_height() * self.zoomLevel)
                    # Use smoothscale for better quality when zooming in
                    if self.zoomLevel > 1.0:
                        sprite = pygame.transform.smoothscale(sprite, (newW, newH))
                    else:
                        sprite = pygame.transform.scale(sprite, (newW, newH))
                
                # worldToScreen returns the TOP vertex of the tile diamond
                # Sprite's top vertex is at (TILE_WIDTH // 2, 0), so offset to align
                scaledTileWidth = int(TILE_WIDTH * self.zoomLevel)
                scaledBlockHeight = int(BLOCK_HEIGHT * self.zoomLevel)
                drawX = screenX - scaledTileWidth // 2
                drawY = screenY
                
                # Doors are 2 blocks tall - shift up by one block height
                blockDef = BLOCK_DEFINITIONS.get(blockType)
                if blockDef and blockDef.isDoor:
                    drawY -= scaledBlockHeight
                
                # Apply X-Ray transparency for solid blocks
                if self.xrayEnabled and blockType in self.xrayBlocks:
                    sprite = sprite.copy()
                    sprite.set_alpha(self.xrayAlpha)
                
                self.screen.blit(sprite, (drawX, drawY))
        
        # Render spawner particles
        self._renderSpawnerParticles()
    
    def _renderSpawnerParticles(self) -> None:
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
    
    def _renderGhostBlock(self) -> None:
        """Render a transparent preview of the block(s) to be placed based on brush size"""
        if not self.showGhostPreview:
            return
        
        # In stamp mode, render stamp preview instead
        if self.stampMode and self.stampData and self.hoveredCell:
            self._renderStampPreview()
            return
        
        baseX, baseY, baseZ = self.hoveredCell
        
        # Get sprite and prepare it
        sprite = self.assetManager.getBlockSprite(self.selectedBlock)
        if not sprite:
            return
        
        # Create transparent copy
        ghostSprite = sprite.copy()
        ghostSprite.set_alpha(self.ghostPreviewAlpha)
        
        # Apply view rotation flip (views 1 and 3 need horizontal flip)
        viewRot = self.renderer.viewRotation
        if viewRot == 1 or viewRot == 3:
            ghostSprite = pygame.transform.flip(ghostSprite, True, False)
        
        # Apply zoom scaling
        if self.zoomLevel != 1.0:
            newW = int(ghostSprite.get_width() * self.zoomLevel)
            newH = int(ghostSprite.get_height() * self.zoomLevel)
            ghostSprite = pygame.transform.scale(ghostSprite, (newW, newH))
        
        scaledTileWidth = int(TILE_WIDTH * self.zoomLevel)
        scaledBlockHeight = int(BLOCK_HEIGHT * self.zoomLevel)
        
        # Check if block is a door (2 blocks tall)
        blockDef = BLOCK_DEFINITIONS.get(self.selectedBlock)
        isDoor = blockDef and blockDef.isDoor
        
        # Render ghost for each block in brush area
        brushSize = self.brushSize
        for dx in range(brushSize):
            for dy in range(brushSize):
                x = baseX + dx
                y = baseY + dy
                z = baseZ
                
                # Check bounds
                if not (0 <= x < GRID_WIDTH and 0 <= y < GRID_DEPTH and 0 <= z < GRID_HEIGHT):
                    continue
                
                # Don't show ghost over existing solid blocks
                existingBlock = self.world.getBlock(x, y, z)
                if existingBlock != BlockType.AIR:
                    continue
                
                screenX, screenY = self.renderer.worldToScreen(x, y, z)
                drawX = screenX - scaledTileWidth // 2
                drawY = screenY
                
                # Doors are 2 blocks tall - shift up
                if isDoor:
                    drawY -= scaledBlockHeight
                
                self.screen.blit(ghostSprite, (drawX, drawY))
    
    def _renderStampPreview(self) -> None:
        """Render a transparent preview of the stamp to be placed"""
        if not self.stampData or not self.hoveredCell:
            return
        
        baseX, baseY, baseZ = self.hoveredCell
        
        for (relX, relY, relZ), blockType in self.stampData.items():
            x = baseX + relX
            y = baseY + relY
            z = baseZ + relZ
            
            # Check bounds
            if not (0 <= x < GRID_WIDTH and 0 <= y < GRID_DEPTH and 0 <= z < GRID_HEIGHT):
                continue
            
            screenX, screenY = self.renderer.worldToScreen(x, y, z)
            
            sprite = self.assetManager.getBlockSprite(blockType)
            if sprite:
                # Create transparent copy
                ghostSprite = sprite.copy()
                ghostSprite.set_alpha(80)  # More transparent for stamp preview
                
                # Apply view rotation flip (views 1 and 3 need horizontal flip)
                viewRot = self.renderer.viewRotation
                if viewRot == 1 or viewRot == 3:
                    ghostSprite = pygame.transform.flip(ghostSprite, True, False)
                
                # Apply zoom scaling
                if self.zoomLevel != 1.0:
                    newW = int(ghostSprite.get_width() * self.zoomLevel)
                    newH = int(ghostSprite.get_height() * self.zoomLevel)
                    ghostSprite = pygame.transform.scale(ghostSprite, (newW, newH))
                
                scaledTileWidth = int(TILE_WIDTH * self.zoomLevel)
                drawX = screenX - scaledTileWidth // 2
                drawY = screenY
                
                self.screen.blit(ghostSprite, (drawX, drawY))
    
    def _renderPanel(self) -> None:
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
                if category == "Problematic" or category == "Experimental":
                    continue
                totalHeight += subCategoryHeight
                if self.expandedCategories.get(category, False):
                    blocks = BLOCK_CATEGORIES.get(category, [])
                    numRows = (len(blocks) + ICONS_PER_ROW - 1) // ICONS_PER_ROW
                    totalHeight += numRows * (slotSize + 4) + 5
            totalHeight += 10
        
        # Experimental blocks main button + content
        totalHeight += mainButtonHeight
        if self.problemsExpanded:
            experimentalBlocks = BLOCK_CATEGORIES.get("Experimental", [])
            numRows = (len(experimentalBlocks) + ICONS_PER_ROW - 1) // ICONS_PER_ROW
            totalHeight += numRows * (slotSize + 4) + 15
        
        # Features main button + content (3 dimension buttons + Show Tutorial + Rain + Snow + Sun/Moon + Clouds + Lighting + Horror Rain + Save/Load)
        totalHeight += mainButtonHeight
        if self.experimentalExpanded:
            totalHeight += 9 * 35 + 25 + 3 * 30 + 40 + 15  # 9 buttons + volume header + 3 sliders + save/load row
        
        # Structures main button + content
        totalHeight += mainButtonHeight
        if self.structuresExpanded:
            totalHeight += len(PREMADE_STRUCTURES) * 35 + 15
        
        # Controls section (7 primary + header + expand button always + extra if expanded)
        totalHeight += 22  # Header
        totalHeight += 7 * 18  # Primary controls
        totalHeight += 60  # Expand/collapse button with spacing
        totalHeight += 200  # Volume section + padding
        if self.hotkeysExpanded:
            totalHeight += 16 * 18 + 80  # 16 extra controls + padding
        
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
        # No arrow - just "Blocks" text
        self.assetManager.drawButton(self.screen, blocksRect, "Blocks", self.font, blocksHovered, self.blocksExpanded)
        currentY += mainButtonHeight + 5
        
        # Blocks content (sub-categories) - skip Experimental since it has its own section
        if self.blocksExpanded:
            for category in CATEGORY_ORDER:
                if category == "Problematic" or category == "Experimental":
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
                    
                    # ===== COLLAPSE BUTTON (grey button with up-arrow) =====
                    collapseBtnWidth = PANEL_WIDTH - 2 * ICON_MARGIN - 30
                    collapseBtnHeight = 22
                    collapseBtnX = panelX + ICON_MARGIN + 15
                    collapseBtnY = currentY
                    collapseBtnRect = pygame.Rect(collapseBtnX, collapseBtnY, collapseBtnWidth, collapseBtnHeight)
                    
                    # Store rect for click detection
                    self.collapseBtnRects[category] = collapseBtnRect
                    
                    # Check if hovered
                    isCollapseHovered = collapseBtnRect.collidepoint(mouseX, mouseY)
                    
                    # Draw button background (grey Minecraft-style)
                    btnColor = (75, 75, 85) if isCollapseHovered else (55, 55, 65)
                    pygame.draw.rect(self.screen, btnColor, collapseBtnRect, border_radius=3)
                    pygame.draw.rect(self.screen, (90, 90, 100) if isCollapseHovered else (70, 70, 80), collapseBtnRect, 1, border_radius=3)
                    
                    # Draw filled up-arrow (no tail, just the arrowhead)
                    arrowCenterX = collapseBtnX + collapseBtnWidth // 2
                    arrowCenterY = collapseBtnY + collapseBtnHeight // 2
                    arrowSize = 6
                    # Filled triangle pointing up
                    arrowPoints = [
                        (arrowCenterX, arrowCenterY - arrowSize),           # Top point
                        (arrowCenterX - arrowSize, arrowCenterY + arrowSize // 2),  # Bottom left
                        (arrowCenterX + arrowSize, arrowCenterY + arrowSize // 2),  # Bottom right
                    ]
                    arrowColor = (200, 200, 210) if isCollapseHovered else (150, 150, 160)
                    pygame.draw.polygon(self.screen, arrowColor, arrowPoints)
                    
                    currentY += collapseBtnHeight + 5
            
            currentY += 5
        
        # ===== EXPERIMENTAL MAIN BUTTON =====
        problemsRect = pygame.Rect(panelX + ICON_MARGIN, currentY, PANEL_WIDTH - 2 * ICON_MARGIN, mainButtonHeight)
        problemsHovered = problemsRect.collidepoint(mouseX, mouseY)
        self.assetManager.drawButton(self.screen, problemsRect, "Experimental", self.font, problemsHovered, self.problemsExpanded)
        currentY += mainButtonHeight + 5
        
        # Experimental blocks content
        if self.problemsExpanded:
            experimentalBlocks = BLOCK_CATEGORIES.get("Experimental", [])
            blocksStartY = currentY + 2
            
            for i, blockType in enumerate(experimentalBlocks):
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
            
            numRows = (len(experimentalBlocks) + ICONS_PER_ROW - 1) // ICONS_PER_ROW
            currentY += numRows * (slotSize + 4) + 10
        
        # ===== FEATURES MAIN BUTTON =====
        experimentalRect = pygame.Rect(panelX + ICON_MARGIN, currentY, PANEL_WIDTH - 2 * ICON_MARGIN, mainButtonHeight)
        experimentalHovered = experimentalRect.collidepoint(mouseX, mouseY)
        self.assetManager.drawButton(self.screen, experimentalRect, "Features", self.font, experimentalHovered, self.experimentalExpanded)
        currentY += mainButtonHeight + 5
        
        # Experimental content (dimension buttons + Show Tutorial)
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
                    
                    # Texture and tint based on dimension
                    if dimKey == DIMENSION_OVERWORLD:
                        dimTexture = "grass_block_top.png"  # Use grass texture with tint for overworld
                        dimTint = GRASS_TINT
                    elif dimKey == DIMENSION_NETHER:
                        dimTexture = "netherrack.png"
                        dimTint = None
                    else:  # End
                        dimTexture = "end_stone.png"
                        dimTint = None
                    
                    self.assetManager.drawButton(
                        self.screen, btnRect, dimName, 
                        self.smallFont, isHovered, isSelected, bgTexture=dimTexture, bgTint=dimTint
                    )
                
                dimY += 35
            
            # Show Tutorial button
            tutorialBtnRect = pygame.Rect(panelX + ICON_MARGIN + 10, dimY, PANEL_WIDTH - 2 * ICON_MARGIN - 20, 30)
            if dimY + 30 >= startY and dimY <= startY + availableHeight:
                tutorialHovered = tutorialBtnRect.collidepoint(mouseX, mouseY)
                self.assetManager.drawButton(
                    self.screen, tutorialBtnRect, "Show Tutorial",
                    self.smallFont, tutorialHovered, False, bgTexture="bookshelf.png"
                )
            dimY += 35
            
            # Rain toggle button (with status indicator)
            rainBtnRect = pygame.Rect(panelX + ICON_MARGIN + 10, dimY, PANEL_WIDTH - 2 * ICON_MARGIN - 20, 30)
            if dimY + 30 >= startY and dimY <= startY + availableHeight:
                rainHovered = rainBtnRect.collidepoint(mouseX, mouseY)
                rainLabel = "Rain: ON" if self.rainEnabled else "Rain: OFF"
                # Disable button if not in Overworld
                canRain = self.currentDimension == DIMENSION_OVERWORLD
                if canRain:
                    self.assetManager.drawButton(
                        self.screen, rainBtnRect, rainLabel,
                        self.smallFont, rainHovered, self.rainEnabled, bgTexture="lapis_block.png"
                    )
                else:
                    # Draw disabled button
                    self.assetManager.drawButton(
                        self.screen, rainBtnRect, "Rain (Overworld only)",
                        self.smallFont, False, False
                    )
                    # Darken to show disabled
                    darkOverlay = pygame.Surface((rainBtnRect.width, rainBtnRect.height), pygame.SRCALPHA)
                    darkOverlay.fill((0, 0, 0, 100))
                    self.screen.blit(darkOverlay, rainBtnRect.topleft)
            dimY += 35
            
            # Snow toggle button (with status indicator)
            snowBtnRect = pygame.Rect(panelX + ICON_MARGIN + 10, dimY, PANEL_WIDTH - 2 * ICON_MARGIN - 20, 30)
            if dimY + 30 >= startY and dimY <= startY + availableHeight:
                snowHovered = snowBtnRect.collidepoint(mouseX, mouseY)
                snowLabel = "Snow: ON" if self.snowEnabled else "Snow: OFF"
                # Disable button if not in Overworld
                canSnow = self.currentDimension == DIMENSION_OVERWORLD
                if canSnow:
                    self.assetManager.drawButton(
                        self.screen, snowBtnRect, snowLabel,
                        self.smallFont, snowHovered, self.snowEnabled, bgTexture="snow.png"
                    )
                else:
                    # Draw disabled button
                    self.assetManager.drawButton(
                        self.screen, snowBtnRect, "Snow (Overworld only)",
                        self.smallFont, False, False
                    )
                    # Darken to show disabled
                    darkOverlay = pygame.Surface((snowBtnRect.width, snowBtnRect.height), pygame.SRCALPHA)
                    darkOverlay.fill((0, 0, 0, 100))
                    self.screen.blit(darkOverlay, snowBtnRect.topleft)
            dimY += 35
            
            # Sun/Moon toggle button (with status indicator)
            celestialBtnRect = pygame.Rect(panelX + ICON_MARGIN + 10, dimY, PANEL_WIDTH - 2 * ICON_MARGIN - 20, 30)
            if dimY + 30 >= startY and dimY <= startY + availableHeight:
                celestialHovered = celestialBtnRect.collidepoint(mouseX, mouseY)
                celestialLabel = "Sun/Moon: ON" if self.celestialEnabled else "Sun/Moon: OFF"
                # Disable button if not in Overworld
                canCelestial = self.currentDimension == DIMENSION_OVERWORLD
                if canCelestial:
                    self.assetManager.drawButton(
                        self.screen, celestialBtnRect, celestialLabel,
                        self.smallFont, celestialHovered, self.celestialEnabled, bgTexture="gold_block.png"
                    )
                else:
                    # Draw disabled button
                    self.assetManager.drawButton(
                        self.screen, celestialBtnRect, "Sun/Moon (Overworld)",
                        self.smallFont, False, False
                    )
                    # Darken to show disabled
                    darkOverlay = pygame.Surface((celestialBtnRect.width, celestialBtnRect.height), pygame.SRCALPHA)
                    darkOverlay.fill((0, 0, 0, 100))
                    self.screen.blit(darkOverlay, celestialBtnRect.topleft)
            dimY += 35
            
            # Clouds toggle button
            cloudsBtnRect = pygame.Rect(panelX + ICON_MARGIN + 10, dimY, PANEL_WIDTH - 2 * ICON_MARGIN - 20, 30)
            if dimY + 30 >= startY and dimY <= startY + availableHeight:
                cloudsHovered = cloudsBtnRect.collidepoint(mouseX, mouseY)
                cloudsLabel = "Clouds: ON" if self.cloudsEnabled else "Clouds: OFF"
                self.assetManager.drawButton(
                    self.screen, cloudsBtnRect, cloudsLabel,
                    self.smallFont, cloudsHovered, self.cloudsEnabled, bgTexture="bone_block_side.png"
                )
            dimY += 35
            
            # Lighting toggle button (experimental smooth lighting)
            lightingBtnRect = pygame.Rect(panelX + ICON_MARGIN + 10, dimY, PANEL_WIDTH - 2 * ICON_MARGIN - 20, 30)
            if dimY + 30 >= startY and dimY <= startY + availableHeight:
                lightingHovered = lightingBtnRect.collidepoint(mouseX, mouseY)
                lightingLabel = "Lighting: ON" if self.lightingEnabled else "Lighting: OFF"
                self.assetManager.drawButton(
                    self.screen, lightingBtnRect, lightingLabel,
                    self.smallFont, lightingHovered, self.lightingEnabled, bgTexture="jack_o_lantern.png"
                )
            dimY += 35
            
            # Horror rain button (black button with no text) - at the end
            horrorRainBtnRect = pygame.Rect(panelX + ICON_MARGIN + 10, dimY, PANEL_WIDTH - 2 * ICON_MARGIN - 20, 30)
            if dimY + 30 >= startY and dimY <= startY + availableHeight:
                horrorRainHovered = horrorRainBtnRect.collidepoint(mouseX, mouseY)
                # Draw solid black button
                btnColor = (30, 30, 30) if horrorRainHovered else (5, 5, 5)
                pygame.draw.rect(self.screen, btnColor, horrorRainBtnRect, border_radius=3)
                # Dark border
                borderColor = (60, 60, 60) if horrorRainHovered else (20, 20, 20)
                pygame.draw.rect(self.screen, borderColor, horrorRainBtnRect, 2, border_radius=3)
                # Subtle highlight when active
                if self.horrorRainEnabled:
                    pygame.draw.rect(self.screen, (80, 0, 0), horrorRainBtnRect, 2, border_radius=3)
            dimY += 35
            
            currentY = dimY + 5
        
        # ===== STRUCTURES MAIN BUTTON =====
        structuresRect = pygame.Rect(panelX + ICON_MARGIN, currentY, PANEL_WIDTH - 2 * ICON_MARGIN, mainButtonHeight)
        structuresHovered = structuresRect.collidepoint(mouseX, mouseY)
        self.assetManager.drawButton(self.screen, structuresRect, "Structures", self.font, structuresHovered, self.structuresExpanded)
        currentY += mainButtonHeight + 5
        
        # Structures content - grid of thumbnail previews
        if self.structuresExpanded:
            PREVIEW_WIDTH = 115
            PREVIEW_HEIGHT = 75
            PREVIEWS_PER_ROW = 2
            PREVIEW_MARGIN = 6
            PREVIEW_PADDING = 8
            
            structureY = currentY + 2
            structureList = list(PREMADE_STRUCTURES.items())
            
            # Reset hovered structure
            self.hoveredStructure = None
            
            for idx, (structName, structData) in enumerate(structureList):
                row = idx // PREVIEWS_PER_ROW
                col = idx % PREVIEWS_PER_ROW
                
                # Calculate thumbnail position
                thumbX = panelX + PREVIEW_PADDING + col * (PREVIEW_WIDTH + PREVIEW_MARGIN)
                thumbY = structureY + row * (PREVIEW_HEIGHT + PREVIEW_MARGIN)
                
                thumbRect = pygame.Rect(thumbX, thumbY, PREVIEW_WIDTH, PREVIEW_HEIGHT)
                
                # Only render if visible
                if thumbY + PREVIEW_HEIGHT >= startY and thumbY <= startY + availableHeight:
                    isHovered = thumbRect.collidepoint(mouseX, mouseY)
                    isSelected = self.structurePlacementMode and self.selectedStructure == structName
                    
                    # Track hovered structure for tooltip
                    if isHovered:
                        self.hoveredStructure = structName
                    
                    # Draw thumbnail background (cached for performance)
                    if self.structureThumbnailBg is None:
                        # Create and cache the background once
                        self.structureThumbnailBg = pygame.Surface((PREVIEW_WIDTH, PREVIEW_HEIGHT), pygame.SRCALPHA)
                        cobbleTex = self.assetManager.textures.get("cobblestone.png")
                        if cobbleTex:
                            texW, texH = cobbleTex.get_size()
                            for ty in range(0, PREVIEW_HEIGHT, texH):
                                for tx in range(0, PREVIEW_WIDTH, texW):
                                    clipW = min(texW, PREVIEW_WIDTH - tx)
                                    clipH = min(texH, PREVIEW_HEIGHT - ty)
                                    clippedTex = cobbleTex.subsurface((0, 0, clipW, clipH))
                                    self.structureThumbnailBg.blit(clippedTex, (tx, ty))
                            # Pre-apply darkening
                            darkOverlay = pygame.Surface((PREVIEW_WIDTH, PREVIEW_HEIGHT), pygame.SRCALPHA)
                            darkOverlay.fill((0, 0, 0, 80))
                            self.structureThumbnailBg.blit(darkOverlay, (0, 0))
                        else:
                            self.structureThumbnailBg.fill((50, 50, 60))
                    
                    # Blit cached background
                    self.screen.blit(self.structureThumbnailBg, (thumbX, thumbY))
                    
                    # Brighten on hover
                    if isHovered:
                        brightOverlay = pygame.Surface((PREVIEW_WIDTH, PREVIEW_HEIGHT), pygame.SRCALPHA)
                        brightOverlay.fill((255, 255, 255, 30))
                        self.screen.blit(brightOverlay, (thumbX, thumbY))
                    
                    # Draw structure preview (centered in the slot)
                    preview = self.structurePreviews.get(structName)
                    if preview:
                        # Center the preview in the thumbnail slot
                        previewW = preview.get_width()
                        previewH = preview.get_height()
                        centerX = thumbX + (PREVIEW_WIDTH - previewW) // 2
                        centerY = thumbY + (PREVIEW_HEIGHT - previewH) // 2
                        self.screen.blit(preview, (centerX, centerY))
                    
                    # Draw border (yellow/gold for selected, gray otherwise)
                    if isSelected:
                        borderColor = (255, 200, 50)  # Gold/yellow
                        borderWidth = 3
                    elif isHovered:
                        borderColor = (150, 150, 160)
                        borderWidth = 2
                    else:
                        borderColor = (80, 80, 90)
                        borderWidth = 1
                    
                    pygame.draw.rect(self.screen, borderColor, thumbRect, borderWidth)
            
            # Calculate total height of structure grid
            numRows = (len(structureList) + PREVIEWS_PER_ROW - 1) // PREVIEWS_PER_ROW
            currentY = structureY + numRows * (PREVIEW_HEIGHT + PREVIEW_MARGIN) + 5
        
        # ===== SEPARATOR LINE =====
        sepY = currentY + 10
        pygame.draw.line(
            self.screen, PANEL_BORDER,
            (panelX + 10, sepY),
            (WINDOW_WIDTH - 10, sepY), 1
        )
        currentY = sepY + 10
        
        # ===== SAVE/LOAD BUTTONS =====
        saveLoadY = currentY
        saveBtnRect = pygame.Rect(panelX + ICON_MARGIN + 10, saveLoadY, (PANEL_WIDTH - 2 * ICON_MARGIN - 30) // 2, 30)
        loadBtnRect = pygame.Rect(saveBtnRect.right + 10, saveLoadY, saveBtnRect.width, 30)
        
        # Store button rects for click detection
        self.saveBtnRect = saveBtnRect
        self.loadBtnRect = loadBtnRect
        
        if saveLoadY + 30 >= startY and saveLoadY <= startY + availableHeight:
            saveHovered = saveBtnRect.collidepoint(mouseX, mouseY)
            loadHovered = loadBtnRect.collidepoint(mouseX, mouseY)
            self.assetManager.drawButton(self.screen, saveBtnRect, "Save", self.smallFont, saveHovered, False)
            self.assetManager.drawButton(self.screen, loadBtnRect, "Load", self.smallFont, loadHovered, False)
        currentY += 40
        
        # ===== VIEW INDICATOR (no buttons - use Q/E hotkeys) =====
        viewY = currentY
        if viewY + 20 >= startY and viewY <= startY + availableHeight:
            viewLabels = ["NE (0)", "SE (90)", "SW (180)", "NW (270)"]
            viewText = self.smallFont.render(f"View: {viewLabels[self.renderer.viewRotation]} (Q/E to rotate)", True, (150, 200, 150))
            self.screen.blit(viewText, (panelX + ICON_MARGIN + 10, viewY))
        currentY += 25
        
        # Clear rotation button rects (no longer used)
        self.rotLeftBtnRect = None
        self.rotRightBtnRect = None
        
        # ===== VOLUME SLIDERS SECTION =====
        volHeaderY = currentY
        volHeaderText = self.smallFont.render("Volume Controls", True, (180, 180, 180))
        self.screen.blit(volHeaderText, (panelX + ICON_MARGIN + 10, volHeaderY))
        currentY = volHeaderY + 22
        
        # Music volume slider - store rect for click detection
        musicSliderY = currentY
        self._renderVolumeSlider(panelX + ICON_MARGIN + 10, currentY, "Music", self.musicVolume, mouseX, mouseY)
        self.musicSliderY = musicSliderY
        currentY += 28
        
        # Ambient volume slider - store rect for click detection
        ambientSliderY = currentY
        self._renderVolumeSlider(panelX + ICON_MARGIN + 10, currentY, "Ambient", self.ambientVolume, mouseX, mouseY)
        self.ambientSliderY = ambientSliderY
        currentY += 28
        
        # Effects volume slider - store rect for click detection  
        effectsSliderY = currentY
        self._renderVolumeSlider(panelX + ICON_MARGIN + 10, currentY, "Effects", self.effectsVolume, mouseX, mouseY)
        self.effectsSliderY = effectsSliderY
        currentY += 35
        
        # ===== CONTROLS SECTION (Collapsible) =====
        controlsY = currentY + 10
        
        # Primary controls - Always visible (most important, including Q/E rotation)
        primaryControls = [
            ("Q", "E", "Rotate view"),
            ("C", "Clear world"),
            ("K", "Clear liquids"),
            ("MMB", "Drag", "Pan camera"),
            ("F", "Fill (rectangle)"),
            ("B", "Brush size"),
            ("Ctrl", "Z/Y", "Undo/Redo"),
        ]
        
        # Extra controls - Hidden by default (collapsible section)
        extraControls = [
            ("Ctrl", "C/V", "Copy/Paste"),
            ("L", "Toggle liquid flow"),
            ("MMB", "Pick block"),
            ("Ctrl", "A", "Fill selection"),
            ("Ctrl", "Shift", "F", "Flood fill 3D"),
            ("Ctrl", "B", "Selection box"),
            ("Del", "Clear selection"),
            ("R", "F", "Rotate/Flip"),
            ("X", "X-Ray mode"),
            ("Tab", "Minimap"),
            ("M", "Measure tool"),
            ("W", "Magic wand"),
            ("P", "Stamp tool"),
            ("/", "Layer slice"),
            ("G", "Toggle grid"),
            ("?", "All shortcuts"),
        ]
        
        # Draw section header
        headerText = self.smallFont.render("Hotkeys", True, (120, 120, 140))
        headerX = panelX + (PANEL_WIDTH - headerText.get_width()) // 2
        if controlsY >= startY and controlsY <= startY + availableHeight:
            self.screen.blit(headerText, (headerX, controlsY))
        controlsY += 22
        
        # Always show primary controls
        controls = primaryControls
        
        for item in controls:
            if controlsY >= startY and controlsY <= startY + availableHeight:
                # Minecraft-style pressed button appearance for each key
                keyX = panelX + 8
                
                # Handle multi-key combinations (tuples with more than 2 elements)
                if len(item) == 2:
                    # Single key: (key, action)
                    key, action = item
                    keys = [key]
                else:
                    # Multi-key: keys are all but last element, action is last
                    keys = list(item[:-1])
                    action = item[-1]
                
                # Render each key with Minecraft button style
                for i, key in enumerate(keys):
                    # Draw + separator between keys
                    if i > 0:
                        plusText = self.smallFont.render("+", True, (100, 100, 110))
                        self.screen.blit(plusText, (keyX, controlsY))
                        keyX += plusText.get_width() + 2
                    
                    keyText = self.smallFont.render(key, True, (255, 255, 255))
                    btnWidth = keyText.get_width() + 8
                    btnHeight = 16
                    keyBg = pygame.Rect(keyX, controlsY - 1, btnWidth, btnHeight)
                    
                    # Minecraft pressed button style: darker top, lighter bottom edge
                    # Main button face (dark grey)
                    pygame.draw.rect(self.screen, (55, 55, 55), keyBg)
                    # Top shadow (darker - pressed look)
                    pygame.draw.line(self.screen, (30, 30, 30), (keyBg.left, keyBg.top), (keyBg.right - 1, keyBg.top))
                    pygame.draw.line(self.screen, (30, 30, 30), (keyBg.left, keyBg.top), (keyBg.left, keyBg.bottom - 1))
                    # Bottom highlight (lighter)
                    pygame.draw.line(self.screen, (80, 80, 80), (keyBg.left + 1, keyBg.bottom - 1), (keyBg.right - 1, keyBg.bottom - 1))
                    pygame.draw.line(self.screen, (80, 80, 80), (keyBg.right - 1, keyBg.top + 1), (keyBg.right - 1, keyBg.bottom - 1))
                    
                    self.screen.blit(keyText, (keyX + 4, controlsY))
                    keyX += btnWidth + 3
                
                # Action text
                actionText = self.smallFont.render(action, True, (140, 140, 140))
                self.screen.blit(actionText, (keyX + 4, controlsY))
            controlsY += 18
        
        # Draw extra controls if expanded (BEFORE the collapse button)
        if self.hotkeysExpanded:
            for item in extraControls:
                if controlsY >= startY and controlsY <= startY + availableHeight:
                    keyX = panelX + 8
                    
                    if len(item) == 2:
                        key, action = item
                        keys = [key]
                    else:
                        keys = list(item[:-1])
                        action = item[-1]
                    
                    for i, key in enumerate(keys):
                        if i > 0:
                            plusText = self.smallFont.render("+", True, (100, 100, 110))
                            self.screen.blit(plusText, (keyX, controlsY))
                            keyX += plusText.get_width() + 2
                        
                        keyText = self.smallFont.render(key, True, (255, 255, 255))
                        btnWidth = keyText.get_width() + 8
                        btnHeight = 16
                        keyBg = pygame.Rect(keyX, controlsY - 1, btnWidth, btnHeight)
                        
                        pygame.draw.rect(self.screen, (55, 55, 55), keyBg)
                        pygame.draw.line(self.screen, (30, 30, 30), (keyBg.left, keyBg.top), (keyBg.right - 1, keyBg.top))
                        pygame.draw.line(self.screen, (30, 30, 30), (keyBg.left, keyBg.top), (keyBg.left, keyBg.bottom - 1))
                        pygame.draw.line(self.screen, (80, 80, 80), (keyBg.left + 1, keyBg.bottom - 1), (keyBg.right - 1, keyBg.bottom - 1))
                        pygame.draw.line(self.screen, (80, 80, 80), (keyBg.right - 1, keyBg.top + 1), (keyBg.right - 1, keyBg.bottom - 1))
                        
                        self.screen.blit(keyText, (keyX + 4, controlsY))
                        keyX += btnWidth + 3
                    
                    actionText = self.smallFont.render(action, True, (140, 140, 140))
                    self.screen.blit(actionText, (keyX + 4, controlsY))
                controlsY += 18
        
        # Add spacing before expand button
        controlsY += 8
        
        # Draw expand/collapse button at the END - shorter horizontally
        expandBtnHeight = 24
        expandBtnWidth = 80  # Shorter width
        expandBtnX = panelX + (PANEL_WIDTH - expandBtnWidth) // 2  # Centered
        expandBtnY = controlsY
        self.hotkeysExpandBtnRect = pygame.Rect(expandBtnX, expandBtnY, expandBtnWidth, expandBtnHeight)
        
        # Style like subcategory collapse button (grey box with triangle arrow)
        expandHovered = self.hotkeysExpandBtnRect.collidepoint(mouseX, mouseY)
        subColor = (65, 65, 75) if expandHovered else (50, 50, 60)
        pygame.draw.rect(self.screen, subColor, self.hotkeysExpandBtnRect, border_radius=3)
        pygame.draw.rect(self.screen, (80, 80, 90), self.hotkeysExpandBtnRect, 1, border_radius=3)
        
        # Draw expand/collapse indicator as a triangle - centered in button
        indicatorX = expandBtnX + expandBtnWidth // 2
        indicatorY = expandBtnY + expandBtnHeight // 2
        if self.hotkeysExpanded:
            # Up-pointing triangle (to collapse) - like in the screenshot
            points = [(indicatorX - 5, indicatorY + 2), (indicatorX + 5, indicatorY + 2), (indicatorX, indicatorY - 3)]
        else:
            # Down-pointing triangle (to expand)
            points = [(indicatorX - 5, indicatorY - 2), (indicatorX + 5, indicatorY - 2), (indicatorX, indicatorY + 3)]
        pygame.draw.polygon(self.screen, (180, 180, 180), points)
        
        controlsY += 28
        
        # Reduced padding at bottom
        controlsY += 20
        
        # Reset clipping
        self.screen.set_clip(None)
        
        # ===== SETTINGS GEAR BUTTON (BOTTOM RIGHT - outside scroll area) =====
        gearSize = 32
        gearX = WINDOW_WIDTH - gearSize - 10
        gearY = WINDOW_HEIGHT - gearSize - 10
        gearRect = pygame.Rect(gearX, gearY, gearSize, gearSize)
        gearHovered = gearRect.collidepoint(mouseX, mouseY)
        
        # Draw square gray box
        gearBgColor = (110, 110, 110) if gearHovered else (80, 80, 80)
        pygame.draw.rect(self.screen, gearBgColor, gearRect)
        pygame.draw.rect(self.screen, (60, 60, 60), gearRect, 2)
        
        # Draw proper gear icon with 6 teeth
        import math
        centerX = gearX + gearSize // 2
        centerY = gearY + gearSize // 2
        gearColor = (255, 255, 255)
        
        # Build gear shape as polygon points
        gearPoints = []
        numTeeth = 6
        outerRadius = 11  # Tip of teeth
        innerRadius = 8   # Base of teeth
        toothWidth = 0.35  # Radians - tooth width at tip
        
        for i in range(numTeeth):
            # Angle to center of tooth
            toothAngle = (i * 2 * math.pi / numTeeth) - math.pi / 2
            
            # Valley before tooth (inner radius)
            valleyAngle1 = toothAngle - math.pi / numTeeth + toothWidth / 2
            gearPoints.append((
                centerX + int(math.cos(valleyAngle1) * innerRadius),
                centerY + int(math.sin(valleyAngle1) * innerRadius)
            ))
            
            # Tooth start (outer radius)
            toothStart = toothAngle - toothWidth / 2
            gearPoints.append((
                centerX + int(math.cos(toothStart) * outerRadius),
                centerY + int(math.sin(toothStart) * outerRadius)
            ))
            
            # Tooth end (outer radius)
            toothEnd = toothAngle + toothWidth / 2
            gearPoints.append((
                centerX + int(math.cos(toothEnd) * outerRadius),
                centerY + int(math.sin(toothEnd) * outerRadius)
            ))
            
            # Valley after tooth (inner radius)
            valleyAngle2 = toothAngle + math.pi / numTeeth - toothWidth / 2
            gearPoints.append((
                centerX + int(math.cos(valleyAngle2) * innerRadius),
                centerY + int(math.sin(valleyAngle2) * innerRadius)
            ))
        
        # Draw the gear body
        pygame.draw.polygon(self.screen, gearColor, gearPoints)
        
        # Draw center hole
        holeColor = gearBgColor  # Match background
        pygame.draw.circle(self.screen, holeColor, (centerX, centerY), 4)
        
        # Store gear button rect for click detection
        self.settingsGearRect = gearRect
        
        # Draw scroll indicator if needed
        if self.maxScroll > 0:
            scrollBarHeight = max(20, availableHeight * availableHeight // totalHeight)
            scrollBarY = startY + (self.inventoryScroll * (availableHeight - scrollBarHeight) // self.maxScroll)
            scrollBarRect = pygame.Rect(WINDOW_WIDTH - 8, scrollBarY, 4, scrollBarHeight)
            pygame.draw.rect(self.screen, (150, 150, 150), scrollBarRect)
    
    def _renderStatus(self) -> None:
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
    
    def _renderStructureTooltip(self) -> None:
        """Render tooltip showing structure name when hovering over structure thumbnail"""
        if not self.hoveredStructure or not self.structuresExpanded:
            return
        
        # Get structure display name
        structData = PREMADE_STRUCTURES.get(self.hoveredStructure)
        if not structData:
            return
        
        displayName = structData.get("name", self.hoveredStructure)
        
        # Render tooltip near mouse position
        mouseX, mouseY = pygame.mouse.get_pos()
        
        # Create tooltip text
        tooltipText = self.smallFont.render(displayName, True, (255, 255, 255))
        textWidth = tooltipText.get_width()
        textHeight = tooltipText.get_height()
        
        # Padding around text
        padding = 6
        tooltipWidth = textWidth + padding * 2
        tooltipHeight = textHeight + padding * 2
        
        # Position tooltip near mouse, but offset to not obscure
        tooltipX = mouseX + 15
        tooltipY = mouseY - tooltipHeight - 5
        
        # Keep tooltip on screen
        if tooltipX + tooltipWidth > WINDOW_WIDTH:
            tooltipX = mouseX - tooltipWidth - 5
        if tooltipY < 0:
            tooltipY = mouseY + 20
        
        # Draw tooltip background with border
        tooltipRect = pygame.Rect(tooltipX, tooltipY, tooltipWidth, tooltipHeight)
        
        # Dark semi-transparent background
        tooltipBg = pygame.Surface((tooltipWidth, tooltipHeight), pygame.SRCALPHA)
        tooltipBg.fill((30, 30, 40, 230))
        self.screen.blit(tooltipBg, (tooltipX, tooltipY))
        
        # Border
        pygame.draw.rect(self.screen, (100, 100, 120), tooltipRect, 1)
        
        # Text
        self.screen.blit(tooltipText, (tooltipX + padding, tooltipY + padding))
    
    def _renderVolumeSlider(self, x: int, y: int, label: str, value: float, mouseX: int, mouseY: int):
        """Render a volume slider with mute toggle"""
        sliderWidth = PANEL_WIDTH - 2 * ICON_MARGIN - 30
        sliderHeight = 8
        labelWidth = 55
        trackWidth = sliderWidth - labelWidth - 50  # Leave room for mute button
        
        # Determine mute state based on label
        if label == "Music":
            isMuted = getattr(self, 'musicMuted', False)
        elif label == "Ambient":
            isMuted = getattr(self, 'ambientMuted', False)
        else:
            isMuted = getattr(self, 'effectsMuted', False)
        
        # Draw label
        labelColor = (100, 100, 100) if isMuted else (180, 180, 180)
        labelText = self.smallFont.render(label, True, labelColor)
        self.screen.blit(labelText, (x, y))
        
        # Slider track
        trackX = x + labelWidth
        trackY = y + 5
        trackRect = pygame.Rect(trackX, trackY, trackWidth, sliderHeight)
        trackColor = (40, 40, 45) if isMuted else (50, 50, 60)
        pygame.draw.rect(self.screen, trackColor, trackRect, border_radius=4)
        
        # Filled portion
        filledWidth = int(trackWidth * value)
        if filledWidth > 0:
            filledColor = (60, 90, 60) if isMuted else (80, 150, 80)
            filledRect = pygame.Rect(trackX, trackY, filledWidth, sliderHeight)
            pygame.draw.rect(self.screen, filledColor, filledRect, border_radius=4)
        
        # Slider handle
        handleX = trackX + filledWidth - 4
        handleRect = pygame.Rect(handleX, trackY - 2, 8, sliderHeight + 4)
        handleColor = (200, 200, 200) if trackRect.collidepoint(mouseX, mouseY) else (150, 150, 150)
        if isMuted:
            handleColor = (100, 100, 100)
        pygame.draw.rect(self.screen, handleColor, handleRect, border_radius=2)
        
        # Value percentage
        percentText = self.smallFont.render(f"{int(value * 100)}%", True, (100, 100, 100) if isMuted else (150, 150, 150))
        self.screen.blit(percentText, (trackRect.right + 5, y))
        
        # Mute toggle button (small box with X when muted, empty when not)
        muteX = trackRect.right + 35
        muteY = y
        muteSize = 16
        muteRect = pygame.Rect(muteX, muteY, muteSize, muteSize)
        muteHovered = muteRect.collidepoint(mouseX, mouseY)
        muteBgColor = (70, 50, 50) if isMuted else ((60, 60, 70) if muteHovered else (45, 45, 55))
        pygame.draw.rect(self.screen, muteBgColor, muteRect, border_radius=3)
        pygame.draw.rect(self.screen, (80, 80, 90), muteRect, 1, border_radius=3)
        
        # Draw X when muted, empty when not
        if isMuted:
            # Draw X
            pygame.draw.line(self.screen, (200, 100, 100), (muteX + 4, muteY + 4), (muteX + 12, muteY + 12), 2)
            pygame.draw.line(self.screen, (200, 100, 100), (muteX + 12, muteY + 4), (muteX + 4, muteY + 12), 2)


# ============================================================================
# ENTRY POINT
# ============================================================================

def main():
    """Main entry point for the application"""
    # Set up logging for frozen exe (since console is hidden)
    if getattr(sys, 'frozen', False):
        import logging
        log_path = os.path.join(os.path.dirname(sys.executable), "minecraft_builder.log")
        logging.basicConfig(
            filename=log_path,
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        # Redirect print to logging
        class LoggingPrinter:
            def write(self, msg):
                if msg.strip():
                    logging.info(msg.strip())
            def flush(self):
                pass
        sys.stdout = LoggingPrinter()
        sys.stderr = LoggingPrinter()
    
    print("=" * 50)
    print("  Bloc Fantome Building Simulator")
    print("=" * 50)
    
    try:
        app = BlocFantome()
        app.run()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        if getattr(sys, 'frozen', False):
            import logging
            logging.exception("Fatal error:")
        pygame.quit()
        sys.exit(1)


if __name__ == "__main__":
    main()
