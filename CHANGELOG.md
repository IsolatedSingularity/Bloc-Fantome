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

## [2.6.4] - 2026-08-27

### Added
- Added an ignored, lossless WorldBuilder reference corpus with the original archives, byte-identical DCR movies, raw ProjectorRays and shockwave-extractor output, searchable Lingo/cast indexes, rebuild tools, and an agent-first entrypoint.
- Added map-specific, texture-derived travelers: villager and bee, strider and blaze, shulker and endermite, and cod and salmon.

### Changed
- Reconstructed the mission question mark, blink, and shadow directly from the Director cast palettes, bit depths, registrations, and two-sprite Lingo behavior, including its idle orbit and 200 ms hover clock.
- Tightened the Nether hub framing around a full-screen five-biome landscape while keeping its bastion and fortress pieces inside the map volume.
- Expanded the End map volume so the complete ship and upper deck remain visible.
- Rebuilt the Deep Ocean hub around a full 58 x 58 monument exterior and replaced decorative water blocks with animated screen-space caustics.
- Made every World Map hub use the complete window viewport for more readable, unzoomed presentation.

### Fixed
- Removed clipped Nether structures, the clipped End ship, guessed marker recoloring, and the undersized handmade Ocean Monument.

## [2.6.3] - 2026-08-26

### Added
- Added ambient WorldBuilder-style travelers to every map hub and an underwater map volume with guardians, light shafts, bubbles, and particles.
- Added source-template warm and cold ruin clusters plus an intact with-mast shipwreck to the Deep Ocean hub and editable ocean world.

### Changed
- Rebuilt the map marker from the recovered native WorldBuilder black silhouette, white detail mask, green rollover rays, mission copy, and selector sounds.
- Expanded the Nether hub to a 92 x 92 irregular generated landscape with distinct warped, crimson, soul-sand, basalt, lava, bastion, and source-generator fortress regions.
- Restyled map and objective navigation with the recovered cyan WorldBuilder panels and orange arrow art.
- Rendered skyboxes as complete camera-locked cubemap enclosures with native-detail 1080p sampling, no panorama scrolling, fog, haze, vignette, or equator seam.
- World Map music now plays its intro once and loops each dimension's score family continuously across hubs and objectives.

### Fixed
- Kept underwater presentation across the complete map viewport and tapered the seabed edge instead of exposing a dry UI-side strip or thick slab.
- Removed the remaining yellow marker tint and low-resolution sky intermediates.

## [2.6.2] - 2026-08-26

### Added
- Added a locked Deep Ocean World Map with a monument, canonical ruin and shipwreck pieces, underwater atmosphere, and source-textured decorative guardians.
- Added editable 256 x 256 Nether Fortress Expanse and Deep Ocean Monument worlds to the Worlds gallery.
- Added the canonical End ship to the End map and a fortress crossing to the Nether map and its second repair route.

### Changed
- Lowered startup music to 40 percent and reduced the mixer buffer for more responsive map sounds.
- Rebuilt WorldBuilder music playback as an ordered predecoded queue with MP3 padding trim for uninterrupted fragment transitions.
- Made skybox turns smooth and camera-linked with perspective cubemap projection, horizon haze, and no autonomous rotation.
- Replaced the black question-mark mask with the recovered WorldBuilder amber/detail composition and restyled all map navigation controls.
- Reworked village paths, Nether biome regions, global plains-house geometry, and canonical stair orientation.

### Fixed
- Removed the startup tutorial pop-in by staging its terrain before the splash fade completes.
- Removed the LEGO badge and prevented locked Ocean routes from opening unfinished objectives.
- Kept all new map and gallery terrain grounded without floating objective grids or redstone levels.

## [2.6.1] - 2026-08-26

### Added
- Java 1.16.1 NBT-derived village, bastion, and End City pieces for every World Map hub and repair route.
- Native 1920x1080 visual and benchmark coverage for fullscreen presentation.

### Changed
- Reworked the splash into a darker generated Deep Dark pattern without translucent circular decoration.
- Replaced scrolling equirectangular sky panoramas with camera-linked cubemap faces and made skyboxes opt-in for every session.
- Isolated World Map objectives from the normal editor panel and adopted the recovered WorldBuilder marker, shadow, rollover, arrow, and translucent grey HUD assets.
- Resizing now increases native block render scale while preserving the world-space camera center.

### Fixed
- Removed the floating objective grid and every redstone requirement from World Map levels.
- Removed the skybox longitude wrap and equator projection seam while keeping the licensed sky choices available.
- Prevented the level return control from overlapping the normal right-side editor UI.

## [2.6.0] - 2026-08-25

### Added
- A dedicated three-dimension World Map with persistent WorldBuilder-style objective markers.
- Builder objectives for the Overworld crossing, Nether redstone gate, and End island beacon.
- Responsive native window resizing with a 960×640 minimum plus F11 and Alt+Enter fullscreen.

### Changed
- World Map sessions now preserve and restore the live build, camera, hotbars, undo history, weather, and display state.
- Release packaging validates and installs the curated local WorldBuilder UI/audio set.
- README media now includes the three map hubs, objective view, and terrain/canvas hover demonstrations.

### Removed
- Redundant tracked `WorldBuilder.zip` and `Black Mesa Skyboxes.zip` archives after validating their extracted payloads.

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
