# Changelog

All notable changes to Bloc Fantôme will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.9.9] - 2026-10-21

### Changed
- Consolidate the Pass A-R placement repair, modern editor controls and generated monochrome icon sets.
- Rename the Library's Worlds tile to Dimensions; add large dimension selectors, two-column galleries, tightly framed previews and reciprocal back navigation.
- Restore the larger held-block preview and colored grow, shrink and terrain-noise hover previews. Canvas shrink is immediate and undoable.
- Keep World controls open after dimension and Horror Rain changes, color the selected dimension, and animate liquid controls with falling drops and ripples.
- Ask for a filename on the first manual save, reuse that path afterward, and keep cancellation harmless.
- Frame World Map landscapes closer, remove the modern editor's floating grid, and refine button corners, spacing and Menu hierarchy.
- Document laptop-reset recovery inputs separately from reproducible caches.

### Known limitations
- Large scenes still have cold camera, loading and save stalls. See the 2.9.9 evidence checkpoint; this release does not imply performance acceptance or promotion of accepted main.
- Borderless presentation, Pass B and original-creature replacement remain deferred.

## [2.9.8] - 2026-10-20

### Changed
- Add connected diagonal vault ribs, clustered shafts and paired clerestory tracery to the open cathedral, informed by architectural references.
- Preserve the player's orbit and zoom at cinematic handoffs and bring the rising cathedral into frame earlier.
- Prepare the lighting tutorial's exact light map off the render thread and retain normal lighting invalidation after edits.
- Frame the lighting lesson around the bastion and hide its surrounding Nether terrain through the existing reversible terrain control.
- Add an audited cleanup tool for untracked generated files, retaining the newest two installers and preserving source assets, saves and visual evidence.

## [2.9.7] - 2026-10-19

### Changed
- Add a 44-second cathedral encounter using the locally supplied articulated Twilight Thorn rig, corrected source animation timing, planted climbing contacts, overturning, recovery, impacts and physical monument consumption.
- Enlarge the cathedral and creature, remove the experimental photographic eye, retain receding monuments, and add deep shrine foundations, sparse flowers and connected undulating ground.
- Replace short repeating movement cues with continuous recorded material processed in SuperCollider and eleven staggered vocal takes, with clearer muffled voices.
- Frame tutorial subjects closer against the full background, keep instructions compact at the lower left, and prepare the next lesson while the current one is explored.

## [2.9.6] - 2026-10-18

### Changed
- Use a continuous, velocity-following orbit sound and a deeper source-driven sanctuary rise, rendered in SuperCollider with reproducible local scores.
- Arrive closer to the cathedral and allow smooth, bounded mouse-wheel zoom within the opening, retaining native rendering and accurate picking.
- Fade bottom presentation controls after three seconds, revealing them on interaction or bottom-edge hover. Preserve the existing editor camera and return behavior.
- Record the approved creature encounter direction and reference/animation review checkpoint for the next chat. The creature is not included in this release.

## [2.9.5] - 2026-10-18

### Added
- Connect the opening shrine to an ascending open sanctuary with repeated pointed arches, a muted blue glass apse and detached architectural echoes in the void.
- Continuous camera orbit, a drag slider, translucent Q/E hints, sparse hover/interaction cues, stone movement rumble and restrained settling tremor. Touch the sanctuary light to reveal Return; the previous world and undo history remain intact.
- Borderless fullscreen presentation with restored editor dimensions on exit. `--opening-windowed` previews in a window; F11 toggles presentation mode independently of the editor.

### Fixed
- Shift the shrine left with a modest pullback on the doorway click, raise the sanctuary through the void at upper right with aligned detached arcades and lantern towers, retract the shrine and glowstone, then approach the visible glass focal point.
- Frame the cottage, village well, outpost and observatory around their actual subject bounds, lifted above the hotbar, on tutorial page changes.
- Preserve the SDL window wrapper across presentation display changes so returning to the editor remains stable.
- Remove the splash title strip, keep the complete painting and place its small title over a subtle lower-edge vignette. Show the version in square brackets in the native window caption.
- Render the presentation at the active display resolution with depth-correct textured geometry. Keep the builder's existing renderer unchanged.

## [2.9.4] - 2026-10-18

### Added
- An optional, skippable opening: a checker platform, hanging glowstone vein and pale monument in a quiet blue void. One ghost-block placement triggers two coherent moving sections and reveals an interior light.
- A stair-and-lantern shrine, hover-highlighted placement and animated native-size Q/E key buttons after the reveal. Settings reopens the scene and holds the persisted skip-on-launch toggle; leaving preserves the live build, camera and undo history.
- The owner-selected panoir recording, using its complete first chapter with soft fades and bounded predecoded playback.

### Fixed
- Fit the startup window to the full swamp painting and a narrow title strip, then restore the editor size.
- Frame tutorial subjects more closely, reset page cameras, and leave map/lab modes when changing lessons.
- Stage every tutorial page off the input thread; cache hotbar icons and time-slice cold terrain drawing without dropping cells. Finish an in-progress render despite advancing water/fire frames.

## [2.9.3] - 2026-10-18

### Fixed
- Preserve complete v5 world state in backups, retain recovery history on write failure, and report autosave failures truthfully.
- Reject corrupt, all-invalid and unsupported future builds; replace duplicate cells with the complete last valid row.
- Block editing during pending World loads, support Escape cancellation, and discard results belonging to an older canvas or mode.
- Roll back failed undo batches and retain modern block state in derived scene caches, including large canvas bounds.
- Make the structure fingerprint independent of checkout location without dropping content fields.
- Reduce repeated visibility classification and spread large initial renders over frames at unchanged final quality.
- Reserve a separate title area below the full, aspect-preserved swamp painting.

## [2.9.2] - 2026-09-13

### Changed
- Rebuilt the 16-page tutorial around distinct source scenes, dimensions, weather, independently turning skies, the live World Map, and the complete counter lab.
- Expanded all 37 featured biome captures and replaced 13 Java 1.16.1 Worlds with larger source locations. Villages and nearby landmarks retain their original terrain and coordinates.
- Replaced the splash with the supplied swamp artwork, fully visible with a small regular title along the bottom.
- Kept one persistent tutorial question mark beside Settings, the lab above Settings, one coordinate readout, and centered canvas controls.
- Prepack exact source records, stage palettes and camera orders on the loading worker, and reduce overview, minimap, and underwater rendering work for large captures.

### Fixed
- Separate sky rotation from terrain rotation and remove floating sky objects.
- Preserve the original build preferences and autosave during tutorial, map, and lab excursions.
- Reveal submerged source geometry in the ocean cutaway while retaining editable water cells; clear weather particles when changing tutorial demonstrations.

## [Unreleased]

### Engineering review
- Preserve undo/redo history when a command raises, reject stale biome-load results after edits or mode/canvas changes, and release completed/cancelled load ownership references.
- Write application preferences atomically; retain and restore editor sky selections during tutorial, map and lab excursions.
- Validate compact capture payload hashes with exact-source recovery; declare the tested NumPy runtime dependency and separate test/build requirements.
- Version and validate prepared tutorial data, cover its actual source inputs in fingerprints, and preserve valid lessons on partial rebakes.
- Remove shadowed legacy enum/world/renderer definitions and extract asynchronous load ownership without changing public imports.
- Reduce per-cell visibility bookkeeping while preserving exact visibility, painter orders and lighting; measure complete cold surfaces rather than their first rendering batch.
- Archive and independently verify generated QA evidence before untracking it; retain original local copies and source worlds/captures.
- Defer creature replacement to the owner's later art pass. The existing 2.9.8 opening remains active.

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

## [2.6.5] - 2026-08-27

### Added
- Added dense, drifting Overworld selector fog rendered strictly behind the map.
- Added two visible, non-clickable Deep Ocean route placeholders and restored the End ship dragon head as a source-textured landmark.

### Changed
- Replaced the small End tower vignette with the full source-backed End City assembly and moved the second End mission marker onto the ship.
- Gave Nether, End, and Deep Ocean closer authored cameras while locking every selector hub to its fixed perspective.
- Enlarged mission question marks by 25 percent, tinted navigation controls per map, made travelers reverse continuously, and expanded the seabed with deterministic ridges, trenches, sediment, and outcrops.
- Raised both ruin clusters and shifted the sunken ship six blocks away from the Ocean Monument.

### Fixed
- Kept the normal editor's World Map button centered across native fullscreen and responsive window sizes.
- Removed the popping rollover cue, leaving one consistent WorldBuilder toot per marker entry.
- Removed the obsolete Miette Start Menu shortcut during installation upgrades.

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
