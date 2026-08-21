"""Resolve source and frozen runtime paths without importing the application."""

import os
import sys


if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
    BUNDLED_DATA_DIR = getattr(sys, "_MEIPASS", BASE_DIR)
    ASSETS_DIR = os.path.join(BASE_DIR, "Assets")
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    BUNDLED_DATA_DIR = BASE_DIR
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
BUILTIN_STRUCTURES_DIR = os.path.join(
    BUNDLED_DATA_DIR, "structures" if getattr(sys, "frozen", False) else "saves"
)
WORLDS_DIR = os.path.join(BUNDLED_DATA_DIR, "worlds")
CUSTOM_MUSIC_DIR = os.path.join(SAVES_DIR, "custom_music")
APP_CONFIG_FILE = os.path.join(BASE_DIR, ".app_config.json")
DERIVED_WORLD_CACHE_DIR = os.path.join(
    os.environ.get("LOCALAPPDATA", BASE_DIR), "BlocFantome", "Cache", "worlds"
)
