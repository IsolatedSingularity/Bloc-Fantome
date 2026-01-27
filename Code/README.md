# Bite Sized Minecraft - Source Code

This folder contains the Python source code for Bite Sized Minecraft.

## Project Structure

```
Code/
├── minecraftBuilder.py     # Main application (~15,000 lines)
├── splash.py               # Splash screen module
├── horror.py               # Horror system manager
├── constants.py            # Shared constants and types
├── config.json             # Application configuration
├── build_exe.py            # PyInstaller build script
├── downloadAssets.py       # Asset download utility
├── installer.iss           # Inno Setup installer script
│
├── engine/                 # Core game engine modules
│   ├── __init__.py
│   ├── undo.py            # Undo/redo system
│   ├── world.py           # World voxel grid management
│   ├── renderer.py        # Isometric renderer
│   └── performance.py     # Performance optimization utilities
│
├── saves/                  # Example save files and user saves
│   ├── *.json             # Structure save files
│   ├── custom_music/      # User-added music
│   └── _backups/          # Auto-backup folder
│
└── build/                  # PyInstaller build output
    └── MinecraftBuilder.spec
```

## Running from Source

1. Install dependencies:
   ```bash
   pip install pygame
   ```

2. Run the game:
   ```bash
   python minecraftBuilder.py
   ```

## Building Executable

```bash
python build_exe.py
```

The executable will be created in the parent folder.

## Module Overview

### minecraftBuilder.py
The main application file containing:
- `MinecraftBuilder` class - Main game class
- `AssetManager` class - Texture and sound loading
- `TutorialScreen` class - Interactive tutorial
- Block definitions and enums
- UI rendering and input handling

### engine/
Core engine components that can be imported independently:
- `World` - Voxel grid with liquid flow simulation
- `IsometricRenderer` - 2:1 dimetric projection
- `UndoManager` - Command pattern undo system
- Performance utilities:
  - `DirtyRegionTracker` - Track changed regions for partial redraws
  - `ChunkStorage` - Chunk-based sparse block storage
  - `SpriteCache` - LRU cache for transformed sprites
  - `TextureAtlas` - Combine textures into single atlas
  - `RenderBatcher` - Batch draw calls for efficiency
  - `PerformanceMonitor` - Frame time profiling

### horror.py
`HorrorManager` class handling all ambient horror features:
- Cave sounds and visual glitches
- Herobrine Easter egg
- Horror rain system
- Time-based events

### splash.py
`SplashScreen` class for the startup splash screen.

### constants.py
Shared constants, enums, and type definitions.
