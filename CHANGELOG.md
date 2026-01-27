# Changelog

All notable changes to Bloc Fantôme will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Modular architecture: split codebase into core/, engine/, ui/, structures/ modules
- Configuration file system (config.json) for customizable settings
- Undo/Redo system with Ctrl+Z and Ctrl+Y (100-step history)
- Selection box tool for multi-block operations:
  - Ctrl+B to start selection mode
  - Click to set corners
  - Ctrl+C to copy, Ctrl+V to paste
  - Delete to remove selected blocks
  - Ctrl+A to fill selection with current block
  - ESC to cancel selection
- Block preview rotation before placement (R to rotate, F to flip slabs)
- Block tooltip showing block name on hover
- Grid height indicator displaying current Z-level
- Camera zoom with mouse wheel (Shift+Scroll)
- Quick save/load slots (F5-F8 save, F9-F12 load)
- Screenshot feature (F2) - saves to screenshots/ folder
- Event bus system for decoupled architecture
- Portable mode detection (uses local folder if config.json present)
- Version information embedding in executables
- Inno Setup installer script for Windows distribution
- Liquid flow toggle (L key)
- **Compressed save format**: Saves now use gzip compression (.json.gz)
- **Auto-backup system**: Rolling backups (max 5) in _backups folder, created on auto-save
- **3D Positional Audio**: Block sounds now have distance-based volume falloff and stereo panning
- **Custom music support**: Drop .ogg/.mp3/.wav files in saves/custom_music folder
- **Extended sound effects**: Added 30+ block-specific sound categories (snow, coral, wet_grass, amethyst, bamboo, cherry, deepslate, sculk, etc.)
- **Generic placement sound**: playPlaceSound() method for operations without specific block type
- **Quick Keys panel**: Right panel now shows 17 most useful hotkeys sorted by builder usefulness

### Changed
- Saves now stored in user's AppData directory by default
- Optimized liquid flow simulation with configurable batch updates (8 per tick)
- Improved type hints throughout codebase
- Refactored rendering methods with proper return type annotations
- Cached expensive polygon and lighting calculations
- Keyboard shortcuts panel expanded with all new shortcuts
- Preview facing/slab position applies when placing blocks
- Snow blocks now use proper snow sounds instead of cloth
- **Splash screen icon**: Increased quality with 8x supersampling (was 4x)
- **Snow effects**: Now constrained to platform area, doesn't fall across entire screen
- **Block selection accuracy**: Improved with larger search range, tolerance, and distance-based tie-breaking
- **LRU sprite cache**: Lit block sprites now use LRU eviction (max 500 entries) to prevent memory bloat
- **Renderer optimization**: Cached zoom-scaled tile dimensions to reduce redundant calculations in worldToScreen/screenToWorld

### Fixed
- Face-based block placement now works at all heights
- Executable crash on startup (pygame event handling)
- Conda auto-activation terminal error

## [1.0.0] - 2026-01-18

### Added
- Initial release
- Isometric 2.5D block placement system
- 100+ Minecraft block types organized by category
- Pre-made structures (houses, trees, portals, etc.)
- Three dimensions: Overworld, Nether, End
- Animated blocks: water, lava, fire, portals
- Authentic Minecraft sounds and music
- 10-step interactive tutorial
- Rain and snow weather effects
- Day/night cycle with sun and moon
- Block rotation (stairs) and flipping (slabs)
- Door interaction (open/close)
- Liquid flow simulation
- Structure saving and loading (JSON format)

### Technical
- Pure Python implementation with Pygame
- 2:1 dimetric isometric projection
- Sparse dictionary world storage
- Painter's algorithm depth sorting
- Face-based click detection for 3D building
