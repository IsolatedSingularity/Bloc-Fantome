# Bloc Fantome Modularization and Performance Implementation Plan

Status: execution-ready temporary plan

This file is the source of truth for the refactor. It is intentionally separate from `README.md`, which must remain unchanged. Delete this plan only after every completion gate has passed and the permanent contributor documentation has been updated.

## 1. Objective

Refactor `Code/blocFantome.py` from a 19,399-line monolith into a set of cohesive, interconnected modules while preserving all current content and behavior, repairing proven existing defects, and materially improving large-world loading, cold render latency, zoom quality, and interaction consistency.

The work is not a rewrite. It is a staged extraction and optimization of the current working tree, including the uncommitted flyweight, mipmap, weather, icon, installer, and test changes present when this plan was written.

## 2. Agreed Decisions

| Decision | Requirement |
|---|---|
| Refactor depth | Moderate split. Keep application event/render orchestration in `BlocFantome`, but move domain data and major systems behind deep module interfaces. |
| Zoom quality | Improve both zoom-in and zoom-out quality. |
| Performance | Use balanced acceptance gates covering load time, cold frames, p95 frame time, fit/zoom stalls, and memory. |
| Dependencies | Pygame remains the required fallback. NumPy may be optional when measured. A GPU adapter is accepted only through a measured decision gate. |
| GPU target | Benchmark on the AMD Ryzen AI 7 350 and integrated Radeon 860M. Do not assume a discrete GPU. |
| Compatibility | Preserve source launch, the Windows one-file executable, user assets, app/tutorial config, and save formats v1-v5. |
| Existing defects | Fix only defects demonstrated by tests or profiling. Do not perform unrelated behavioral redesign. |
| Documentation | Add module documentation and update `CONTRIBUTING.md`. Do not edit `README.md`. |
| Git state | Keep all changes unstaged, uncommitted, and unpushed. Do not overwrite unrelated working-tree changes. |

## 3. Baseline Evidence

### 3.1 Current Size and Responsibility Map

| Area | Current location | Approximate size |
|---|---|---:|
| Global runtime/configuration | `Code/blocFantome.py:1-428` | 428 lines |
| Block enum and catalogs | `Code/blocFantome.py:432-1653` | 1,222 lines |
| Built-in structures and loaders | `Code/blocFantome.py:1656-2916` | 1,261 lines |
| Tutorial UI | `Code/blocFantome.py:2926-3769` | 844 lines |
| Asset manager | `Code/blocFantome.py:3776-7584` | 3,809 lines, 60 methods |
| Dead in-file `World` implementation | `Code/blocFantome.py:7591-8112` | 522 lines |
| Dead in-file renderer implementation | `Code/blocFantome.py:8119-8255` | 137 lines |
| Main application | `Code/blocFantome.py:8262-19352` | 11,091 lines, 242 methods |
| Main application initialization | `Code/blocFantome.py:8270-8775` | 506 lines |
| Keyboard dispatch | `Code/blocFantome.py:10079-10515` | 437 lines |
| Panel click/render pair | `Code/blocFantome.py:10517-10836`, `18464-19241` | 1,098 lines |
| Save/load/staging | `Code/blocFantome.py:12953-13890` | 938 lines |
| World rendering | `Code/blocFantome.py:17841-18311` | 471 lines |

Existing extracted modules are useful and must be evolved rather than replaced wholesale: `Code/engine/world.py`, `renderer.py`, `performance.py`, `scene_cache.py`, `model_renderer.py`, `audio.py`, `undo.py`, `lighting.py`, `topology.py`, `terrain.py`, `anvil.py`, and the existing `Code/ui/` modules.

### 3.2 Test Baseline

Command:

```powershell
python -m pytest -q
```

Result on 2026-08-20: 78 passed in 24.81 seconds. The only warning was inability to create `.pytest_cache` under the OneDrive workspace.

### 3.3 Performance Baseline

Command:

```powershell
python tests/benchmark_large_world.py ancient_city_121 trial_chamber_121
```

| Scene | Blocks | Cached load | Cold render at 50% | Forced pan rebuild | Stable full-frame p95 | Fit plus first frame | Overview p95 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Ancient City | 153,520 | 1,061.0 ms | 38.3 ms | 29.3 ms | 2.85 ms | 836.97 ms | 2.80 ms |
| Trial Chamber | 181,697 | 2,116.5 ms | 187.5 ms | 136.2 ms | 4.34 ms | 870.39 ms | 2.71 ms |

The stable cached path is already fast. The priority is eliminating load and cache-rebuild stalls rather than optimizing the already-cheap cached frame.

### 3.4 Profile Findings

The profiled Trial Chamber cache-hit load spent most time in these paths:

| Cost center | Profile evidence | Interpretation |
|---|---:|---|
| `_applyStagedBuild` | 2.612 s cumulative under profiler | Per-cell application and index construction dominate cached load. |
| `World._rebuildSurfaceIndex` | 1.453 s cumulative | Six-neighbor surface discovery is rebuilt after every bulk import. |
| `_findExteriorGlassPositions` | 0.927 s cumulative | Derived structure visibility data is recomputed even after a cache hit. |
| `World.setBlock` | 0.905 s cumulative over 181,697 calls | Bulk loading uses an editing interface with unnecessary queue/state work. |

The profiled Trial Chamber 50% cold frame spent most time in these paths:

| Cost center | Profile evidence | Interpretation |
|---|---:|---|
| `_visibleScreenRenderPlan` | 0.275 s cumulative | Candidate planning and screen rejection are the main cold-frame bottleneck. |
| `_visibleBlocksInDrawOrder` | 0.179 s cumulative | Structure positions are rescanned and sorted too broadly. |
| `_blockIsOnScreen` | 49,456 calls, 0.094 s cumulative | Per-block projection occurs before the candidate set is sufficiently narrow. |
| `_isFullyOccluded` | 7,540 calls, 0.051 s cumulative | Occlusion is useful but repeatedly performs dictionary and definition lookups. |
| Pygame blits | 4,289 calls, 0.009 s cumulative | Sprite scaling/blitting is not the first bottleneck in this profile. |

Conclusion: retain the current flyweight and mipmap work, but do not treat it as the main stutter solution. Fix indexing, invalidation, candidate planning, and first-frame compositing first.

## 4. Non-Negotiable Invariants

1. `python Code/blocFantome.py` continues to launch the application.
2. `import blocFantome` continues to expose `BlocFantome`, `BlockType`, `BlockDefinition`, `SoundDefinition`, `BLOCK_DEFINITIONS`, `BLOCK_SOUNDS`, `BLOCK_CATEGORIES`, `PREMADE_STRUCTURES`, dimension constants, and paths used by tests and tools.
3. `Code/build_exe.py` continues to produce the standard and diagnostic one-file Windows executables.
4. User-provided assets remain external and are resolved identically in source and frozen modes.
5. Save v1-v5 parsing, v3 single-cell door migration, v5 bounds/provenance, gzip/plain JSON input, atomic writes, scene roles, liquid state, stairs, slabs, and doors remain supported.
6. Block enum names and numeric values do not change.
7. Block catalogs, sound mappings, categories, tutorial content, structures, weather, horror content, dimensions, tools, and UI capabilities are not dropped.
8. Painter ordering, picking, camera rotation anchoring, cursor-centered zoom, scene terrain modes, and hidden-cube behavior remain visually and behaviorally stable unless a test proves an existing defect.
9. Pygame calls that create, convert, mutate, or display `Surface` objects stay on the main thread unless the Pygame documentation explicitly guarantees safety.
10. Background workers stage immutable Python data only. They never mutate the live `World`, Pygame surfaces, or application UI state.
11. Every optimization has a benchmark before and after it. Remove an optimization if it does not improve the targeted metric or if it weakens visual correctness.
12. `README.md` remains untouched.

## 5. Target Dependency Direction

Dependencies must point inward toward stable domain and engine modules. No extracted module may import `blocFantome` at runtime.

```text
blocFantome.py
    -> domain/*
    -> engine/*
    -> assets/*
    -> ui/*
    -> effects/*

ui/*, effects/*, assets/*
    -> domain/*
    -> narrow engine interfaces where required

engine/*
    -> domain/*

domain/*
    -> Python standard library only
```

The main `BlocFantome` class remains the composition root and frame orchestrator. It should sequence input, simulation, world rendering, effects, and UI, but should not implement those systems internally.

Avoid mixin-based file splitting. A mixin would move lines without reducing the caller interface or hidden shared state. Extract modules with explicit state and a small interface instead.

Avoid adding an event bus solely for decoupling. Direct composition and explicit return values are preferable for the current single-process application unless two real adapters need an event seam.

## 6. Target Module Layout

The exact names may change during execution only when an existing name would be clearer. Preserve the responsibility and dependency direction.

```text
Code/
  blocFantome.py                 # BlocFantome composition/orchestration, compatibility exports, main()
  runtime_paths.py               # Frozen/source path and application runtime configuration
  domain/
    __init__.py
    blocks.py                    # BlockType and block-state value objects
    block_catalog.py             # Definitions, sounds, categories, catalog queries
    structures.py                # Built-in structures and JSON structure registry
    dimensions.py                # Dimension identifiers and weather presentation data
  assets/
    __init__.py
    manager.py                   # Stable facade used by BlocFantome and UI
    textures.py                  # Texture loading and animation source frames
    sprites.py                   # Isometric/model sprite generation and multi-resolution cache
    sounds.py                    # Sound loading and AudioRouter-facing sound library
    ui_theme.py                  # UI textures, tiled backgrounds, buttons, and slots
  engine/
    world.py                     # Sparse editable world and indexes
    world_snapshot.py            # Immutable staged world data and bulk replacement
    build_io.py                  # Save/load, migration, serialization, scene-cache integration
    renderer.py                  # Projection/camera geometry only
    world_renderer.py            # Candidate planning, culling, ordering, compositing, render stats
    render_cache.py              # Byte-budgeted sprite/view caches and invalidation policy
    editor.py                    # Placement/removal/special-block and bulk editing commands
    input_commands.py            # Context-aware command resolution without Pygame rendering
    performance.py               # Measurement utilities that are actually used
  effects/
    __init__.py
    weather.py                   # Rain/snow/dimension weather state, update, render
    atmosphere.py                # Celestial cycle, stars, clouds, dimension fog
    particles.py                 # Block, placement, and spawner particles
    horror.py                    # One canonical horror implementation
  ui/
    tutorial.py                  # Tutorial state, input, and rendering
    inventory_panel.py           # One shared layout for rendering and hit testing
    overlays.py                  # Hotbar, indicators, settings, history, tooltips, minimap
    build_library.py             # Existing modal
    world_library.py             # Existing modal
```

This is a moderate split, not a one-class-per-file split. Combine responsibilities when splitting would create pass-through modules. The expected end state for `blocFantome.py` is approximately 3,000-5,000 lines of real orchestration, not an arbitrary sub-300-line bootstrap.

## 7. Execution Protocol

Use this protocol for every phase.

1. Inspect `git status --short` and the focused diff before editing.
2. Preserve all pre-existing uncommitted changes. Never restore a file to `HEAD` to simplify extraction.
3. Add or tighten a focused test before changing behavior.
4. Make one responsibility move or one measured optimization at a time.
5. Run the focused test immediately.
6. Run the full test suite before declaring the phase complete.
7. Run the relevant benchmark when a hot path changes.
8. Compare visual checks when projection, sprites, ordering, lighting, zoom, weather, or UI changes.
9. Keep compatibility wrappers only while call sites still need them. Record their deletion condition in code or this plan.
10. Do not begin the next phase while the current completion gate is red.

## 8. Phase 0: Characterization, Metrics, and Safety Net

Goal: make behavior loss and performance regressions observable before moving code.

### 8.1 Extend Test Organization

Create focused test files rather than continuing to grow `tests/test_app_integration.py` indefinitely:

| Test file | Coverage to add |
|---|---|
| `tests/test_public_contract.py` | Required `blocFantome` exports, enum values, catalog counts/order, structure names, path behavior. |
| `tests/test_input_commands.py` | Contextual shortcut contract and modal/event precedence. |
| `tests/test_build_io.py` | v1-v5 fixtures, gzip/plain input, atomic save, door migration, liquids, scene metadata, invalid-file transactionality. |
| `tests/test_world_indexes.py` | Chunk, height, surface, type, bounds, and scene indexes after single edits and bulk replacement. |
| `tests/test_world_renderer.py` | Candidate selection, order, culling, invalidation, static/dynamic behavior, and stats. |
| `tests/test_sprite_quality.py` | Sprite cache identity, byte budget, zoom buckets, alpha edges, and model variants. |

Do not copy all integration tests into new files immediately. Move a test only when its implementation seam is extracted, preserving its assertions.

### 8.2 Lock the Public Data Contract

Add assertions for these values before moving catalogs:

1. Every `BlockType` member name and numeric value.
2. Every `BLOCK_DEFINITIONS` key and relevant definition field.
3. Every `BLOCK_SOUNDS` mapping.
4. Category names, order, and block order.
5. Every built-in and JSON structure key, display name, block count, normalized bounds, and source metadata.
6. Tutorial step titles, order, demo identifiers, and icon identifiers.
7. Weather config names and styles for all dimensions.

Use compact generated tuples/digests in tests where literal duplication would be unmaintainable. A digest failure must print a useful structural diff helper, not only a hash mismatch.

### 8.3 Lock Visual Behavior

Evolve `tests/render_visual_checks.py` and `tests/render_world_checks.py` into deterministic headless checks for:

1. Zoom levels `0.05`, `0.10`, `0.18`, `0.25`, `0.50`, `1.0`, `1.5`, and `2.0`.
2. All four rotations.
3. Full cubes, transparent cubes, stairs, slabs, doors, liquids, plants, walls, fences, portals, and exterior-shell glass.
4. Picking at the centroid and shared edges of each visible face.
5. Painter-order overlap fixtures.
6. Overview scenes that preserve buried canonical structure surfaces.

Use exact pixel comparison where output is expected to be unchanged. Use an explicit per-channel error threshold only for approved zoom-quality changes. Save diagnostic images under the temporary Kilo directory or an ignored test-output directory, not under `References/`.

### 8.4 Expand the Benchmark Harness

Refactor `tests/benchmark_large_world.py` without changing application behavior. Add:

1. Warmup and at least five measured repetitions for cold operations.
2. Median, p95, and maximum timings.
3. Separate timings for file decode, staging, live-world replacement, index construction, visible-order planning, screen-plan construction, sprite resolution, compositing, and full frame.
4. Zoom-in and zoom-out wheel sequences, including the first exact frame after the temporary preview expires.
5. Rotation, terrain-mode change, one-block edit, 3x3 brush edit, selection fill, and render-distance boundary crossing.
6. Memory estimates for Python indexes, sprite surfaces, zoom surfaces, lit surfaces, and cached world surfaces.
7. Optional JSON output so before/after results can be compared automatically.
8. A `--scene` or positional filter that continues to support the existing command.

Add section timing to the existing `PerformanceMonitor` or replace it with a small context-manager interface. Do not leave instrumentation that is initialized but never read.

### 8.5 Capture the Shortcut Contract

Write failing tests for the agreed behavior before changing dispatch:

| Input | Intended behavior |
|---|---|
| `F` with a selected stair/slab | Toggle preview top/bottom position. |
| `F` otherwise | Toggle Fill mode. |
| `M` | Toggle Measurement mode. |
| `Shift+M` | Toggle Y mirror. |
| `Ctrl+M` | Toggle X mirror. |
| `Ctrl+B` | Start/confirm Selection mode. |
| `Ctrl+Shift+B` | Toggle Blueprint mode. |
| `Ctrl+H` with active confirmed selection | Hollow the selection. |
| `Ctrl+H` otherwise | Toggle History panel. |
| `Ctrl+R` | Enter/exit two-click Replace mode. |
| `Home` | Fit occupied world to viewport. |
| `Shift+Home` | Center on hovered cell, selection, or grid. |
| `Esc` | Close/cancel the highest-priority active mode before quitting. |

Define Esc precedence in this order: modal, search, history, settings, shortcuts, blueprint, fill, selection, measurement/replace/stamp modes, tutorial, then application quit.

### 8.6 Phase 0 Completion Gate

```powershell
python -m pytest -q
python tests/render_visual_checks.py
python tests/render_world_checks.py
python tests/benchmark_large_world.py ancient_city_121 trial_chamber_121
```

Record the baseline JSON and environment metadata. All existing tests must remain green; newly written defect tests may remain red only until Phase 2.

## 9. Phase 1: Canonical Domain Data and Dependency Cleanup

Goal: remove duplicate definitions and reverse dependencies before moving behavior.

### 9.1 Extract Canonical Domain Modules

Move without semantic edits:

1. `BlockType` and block-state value objects to `domain/blocks.py`.
2. `BlockDefinition`, `SoundDefinition`, definition/sound maps, categories, and catalog queries to `domain/block_catalog.py`.
3. dimensions and weather presentation constants to `domain/dimensions.py`.
4. built-in structures, JSON structure conversion, and structure tuple normalization to `domain/structures.py`.
5. source/frozen path resolution to `runtime_paths.py`.

Preserve enum identity by having every module import the one canonical `BlockType`. Never recreate an equivalent enum in another module.

Replace import-time mutation from `_loadJsonStructureLibrary()` with an explicit registry construction function called during application composition. Preserve the resulting `PREMADE_STRUCTURES` compatibility export from `blocFantome.py`.

### 9.2 Repair `constants.py`

`Code/constants.py` is stale and unused: it duplicates projection types, has old liquid delays, and claims to export a `BlockType` it does not define. Convert it into a compatibility re-export of canonical domain/runtime values or remove it only after proving there are no source, packaging, or external-script consumers. Do not retain two writable sources of truth.

### 9.3 Remove Runtime Injection From `engine.world`

Replace the `BlockType = None`, `BLOCK_DEFINITIONS = None`, and `init_world_module(...)` runtime-global pattern in `Code/engine/world.py`.

Introduce a compact immutable world catalog dependency containing only what `World` needs: air, water, lava, obsidian, cobblestone/stone reaction products, and definition lookup for light/opacity. The production catalog is the default adapter. Tests may inject a small fake catalog.

Retain `init_world_module` temporarily as a compatibility adapter only if a test or external tool still calls it. Remove the application call at `blocFantome.py:8285`. Delete the adapter when all callers use constructor injection and the public-contract decision confirms it is not required.

### 9.4 Make Projection Metrics Instance-Owned

Replace mutable module globals set by `set_tile_dimensions` with an immutable `ProjectionMetrics` value passed to `IsometricRenderer`. Keep `set_tile_dimensions` as a temporary compatibility wrapper if required by tests. Sprite rasterizers and picking must consume the same metrics object.

### 9.5 Phase 1 Completion Gate

1. Public-contract tests show no enum, catalog, category, structure, tutorial, or weather loss.
2. No runtime import from `engine`, `assets`, `ui`, `effects`, or `domain` points to `blocFantome`.
3. `grep` finds no second `BlockType`, `BlockDefinition`, `Facing`, or projection-constant implementation.
4. Full tests and deterministic visual checks pass.
5. Import time does not regress by more than 10%.

## 10. Phase 2: Repair Input and Undo Defects Behind Explicit Commands

Goal: fix proven unreachable behavior before extracting more application logic.

### 10.1 Introduce Context-Aware Command Resolution

Create `engine/input_commands.py` with a pure command resolver. It accepts a normalized key chord and a small immutable editor/UI context, and returns one semantic command such as `TOGGLE_FILL`, `FLIP_PREVIEW_HALF`, `START_SELECTION`, or `CANCEL_ACTIVE_MODE`.

Keep Pygame event reading in `BlocFantome._handleEvents`. The app converts Pygame state to the normalized context and executes the returned command. This makes precedence testable without constructing the full Pygame application.

Do not build a generic command framework for every mouse movement. Use it for conflicting keyboard actions and modal cancellation where ordering is currently error-prone.

### 10.2 Replace Nonexistent Undo Calls

The paths at the current `_replaceAllBlocks`, `_deleteMagicWandSelection`, and `_handleStampClick` call nonexistent `UndoManager.recordPlacement`. Replace them with `PlaceBlockCommand`, `RemoveBlockCommand`, and `BatchCommand` through one editor operation interface.

Run bulk commands inside `World.bulkUpdate()` so one logical action produces one revision/index update and one undo entry. Preserve per-cell previous block properties, liquid state, and door pair behavior.

### 10.3 Correct State Invalidation

Every successful edit must update these states through one path:

1. World blocks/properties/liquids and spatial indexes.
2. Stair and door topology where relevant.
3. Lighting dirty state.
4. Render-plan and world-surface invalidation.
5. Minimap invalidation.
6. Build height and usage statistics.
7. One undo/redo command boundary.

Avoid having each tool remember a different subset of invalidations.

### 10.4 Phase 2 Completion Gate

1. All contextual shortcut tests pass.
2. Replace, magic-wand delete, stamp, selection fill/hollow/delete, door operations, and undo/redo have focused tests.
3. One action creates one undo entry and one world revision increment where practical.
4. No call to `recordPlacement` remains.
5. Full tests and visual checks pass.

## 11. Phase 3: Asset Module Extraction and Multi-Resolution Sprite Ownership

Goal: reduce the 3,809-line `AssetManager` while establishing one measurable sprite interface for rendering.

### 11.1 Preserve a Stable Facade

Move `AssetManager` to `assets/manager.py` and keep a compatibility export from `blocFantome.py`. Its external interface should remain small:

```python
load_all()
update_animations(elapsed_ms)
get_block_sprite(block_type, state, view_rotation, zoom)
get_icon_sprite(block_type)
play_block_sound(...)
play_ui_sound(...)
draw_button(...)
draw_slot(...)
draw_background(...)
cache_stats()
```

Existing camelCase wrappers may remain during migration. New internal code should use one naming convention consistently with repository guidance.

### 11.2 Split Internal Ownership

Move texture discovery and animation source frames to `assets/textures.py`. Move block/model/icon rasterization and zoom variants to `assets/sprites.py`. Move sound discovery and routing to `assets/sounds.py`. Move background/button/slot rendering to `assets/ui_theme.py`.

Do not create public seams between these internals unless there are two real adapters. They are implementation details behind `AssetManager`.

### 11.3 Replace Count-Only Caches With Byte Budgets

Implement a byte-budgeted LRU using `Surface.get_width() * get_height() * get_bytesize()`. Track hits, misses, evictions, current bytes, and peak bytes.

Use separate budgets for source/model sprites, zoom variants, lit variants, icons, and cached world surfaces. Start with conservative defaults derived from measurement rather than one hardcoded count. A suggested initial total sprite budget is 256 MiB on the 32 GiB target machine, configurable downward; keep it only if stress tests show stable memory and improved hit rate.

### 11.4 Implement Hybrid Zoom Quality

Preserve the current flyweight intern pool and existing mipmaps as the starting implementation, then compare alternatives.

Zoom-out path:

1. Generate downsampled levels from the canonical unscaled sprite, never by repeatedly scaling a previous level.
2. Compare nearest-neighbor, `smoothscale`, and a hybrid alpha-aware method on pixel-art edges and transparent models.
3. Use LOD only where the projected block is too small to retain all faces. Keep canonical structure silhouettes present.
4. Quantize by projected pixel dimensions or bounded relative error, not an arbitrary percentage alone.

Zoom-in path:

1. Re-rasterize geometric models at target projection metrics for 1.5x and 2x buckets instead of scaling a 64-pixel result where profiling permits.
2. Scale 16x16 source textures with pixel-preserving integer sampling before face mapping.
3. Preserve hard alpha edges for pixel-art blocks; do not apply smoothing globally.
4. Cache the resulting high-resolution variants under the byte budget.

Document the unavoidable limit: 16x16 source textures cannot gain new texture detail. The goal is crisp geometry and stable pixels, not fabricated detail.

### 11.5 Phase 3 Completion Gate

1. Asset loading, animation, model, icon, audio, and UI tests pass.
2. All zoom/rotation visual fixtures pass approved thresholds.
3. Cache stress tests show bounded memory and useful hit rates.
4. Startup asset load does not regress by more than 15% unless the added cost removes a larger first-use stall.
5. `AssetManager` no longer contains persistence, world, input, or application state.

## 12. Phase 4: Bulk World Replacement and Load-Time Optimization

Goal: meet the cached large-world load budget without changing save semantics.

### 12.1 Extract Build I/O

Create `engine/build_io.py` with these deep interfaces:

```python
read_build(path, block_catalog, cache_policy) -> WorldSnapshot
write_build(path, snapshot, metadata) -> SaveResult
stage_java_blocks(java_blocks, block_catalog) -> WorldSnapshot
```

`WorldSnapshot` should contain bounds, dimension, blocks, properties, liquid state, scene metadata, structure roles, and derived scene indexes. It must be immutable or treated as immutable after construction.

Move v1-v5 validation/migration, gzip/plain handling, scene-cache integration, Java block mapping, and atomic save serialization from `BlocFantome` into this module. Keep app wrappers only for dialogs, user notifications, and swapping the live world.

### 12.2 Add a Purpose-Built Bulk World Interface

Add `World.replace(snapshot)` or an equivalent bulk constructor. It must build in bounded passes:

1. Flat block/property/liquid dictionaries.
2. Chunk-local storage.
3. Column level and height indexes.
4. Block-type position/count indexes.
5. Occupied bounds.
6. Surface positions and surface positions by chunk.
7. Scene structure positions by chunk and precomputed view-facing surface sets where justified.
8. One revision increment and one full-view invalidation.

Do not call the interactive `setBlock` path 181,697 times. Interactive edits and bulk replacement have different invariants and deserve different interfaces.

Build surface membership with direct dictionary/set membership against the already-built block map. Avoid repeated `isInBounds` and enum lookups inside six-neighbor loops.

### 12.3 Maintain Useful Indexes Incrementally

Add and test indexes that eliminate repeated whole-world scans:

| Index | Replaces |
|---|---|
| Block-type counts/positions | `hasBlockType` scans and periodic fire/spawner scans. |
| Occupied bounds | Six full scans in `_fitPositionsToViewport`. |
| Structure positions by chunk | Full `sceneStructurePositions` scans during every cold render plan. |
| Surface positions by chunk and view | Repeated structure-neighbor checks during candidate construction. |
| Height index | Weather top-surface reconstruction and overview terrain scans. |

Incremental edit costs must remain local. Bulk replacement may rebuild all indexes once.

### 12.4 Improve the Derived Scene Cache

Bump the derived cache magic/version when its record format changes. Old `.bfc` files are disposable and should fail closed, then regenerate.

Persist expensive immutable derived data, including structure roles and exterior-shell glass positions, when doing so reduces cache-hit load time. Validate source digest, metadata size, record count, enum range, and bounds before trusting the cache.

Do not cache live editor state, undo history, Pygame surfaces, or Python pickles.

### 12.5 Keep Threading Transactional

The worker may read, decompress, validate, migrate, and build immutable snapshot indexes. The main thread performs the final atomic assignment to the live world and updates app state. If a future fails, the existing world remains unchanged.

### 12.6 Phase 4 Completion Gate

On the Trial Chamber, using five runs and the median:

1. Cached load is at or below 1,000 ms.
2. The current world remains unchanged after malformed or failed loads.
3. v1-v5 round trips and migration tests pass.
4. Index equivalence tests compare bulk construction against a reference world built through interactive edits.
5. No whole-world scan remains in the per-frame update loop for portal, fire, spawner, snow, or horror surface selection.
6. Full tests and visual checks pass.

## 13. Phase 5: World Renderer Extraction and Cold-Frame Optimization

Goal: isolate rendering behind one interface and meet cold view-rebuild budgets.

### 13.1 Extract Before Optimizing

Move candidate planning, painter ordering, culling, occlusion, screen planning, world-surface caching, sprite selection, and render stats from `BlocFantome` into `engine/world_renderer.py` without changing algorithms first.

Use a small interface such as:

```python
stats = world_renderer.render(target, world, camera, scene_view, render_options)
world_renderer.invalidate(reason, affected_positions=())
```

`WorldRenderer` owns all render-plan and world-surface cache keys. `BlocFantome` must not manipulate `_visibleOrderCacheKey`, `_screenPlanCacheKey`, `_worldSurfaceCacheKey`, margins, chunk anchors, or culling anchors directly after extraction.

### 13.2 Define an Explicit Invalidation Matrix

| Change | Required invalidation |
|---|---|
| One block/property/liquid edit | Affected world/scene chunks, local occlusion, draw plan, composed surface region or cache layer. |
| Bulk world replacement | All world-renderer caches. |
| Camera pan inside cached margin | Reuse composed surface; no candidate rebuild. |
| Camera crosses culling/chunk threshold | Candidate/screen plan and composed surface, not sprite caches. |
| Zoom bucket change | Projection plan, zoom sprites, screen plan, composed surface. |
| Rotation | Painter order, view-facing surface index, sprite orientation, screen plan, composed surface. |
| Lighting change | Lit variants and affected composition; do not clear source sprites. |
| Animation frame | Animated entries only where ordering permits; never invalidate unrelated source/catalog data. |
| Terrain mode | Scene candidate plan and composition only. |
| X-ray mode | Alpha variants and composition only. |

Represent invalidation reasons with an enum or typed value, not scattered assignments to `None`.

### 13.3 Narrow Candidates Before Per-Block Projection

Use direct chunk-key lookup for the current horizontal range instead of iterating every occupied/surface chunk and filtering it. Query structure positions by chunk instead of scanning the full structure set.

Cache view-facing structure surface sets for each rotation and terrain mode. Recompute only after scene structure edits or replacement.

Precompute stable per-block render facts in the plan: depth key, position, block type, model/state key, and opacity class. Avoid repeated definition lookups in culling and drawing.

Keep exact painter-order tie breakers covered by tests. Any chunk-local ordering optimization must merge into the same global order; do not concatenate chunks in an order that introduces visual overlap defects.

### 13.4 Reduce Python Draw Overhead

Build ordered blit sequences and use `Surface.blits(...)` for contiguous runs where it is measurably faster than Python-level `blit` loops. The existing `RenderBatcher.flush` still loops in Python and is not sufficient evidence of batching.

Cache transparent/x-ray sprite variants instead of copying and setting alpha per cell. Reuse the large world-cache surface when dimensions match instead of allocating a new multi-megabyte surface on every cold frame.

Make the cache margin adaptive to viewport size, zoom, and recent pan velocity. Track its byte cost. The current fixed 640-pixel margin creates a roughly 2,220x2,080 alpha surface at the default viewport.

### 13.5 Use Dirty Information at a Safe Granularity

The current `DirtyRegionTracker` is updated but only cleared; it does not reduce render work. Do not patch arbitrary screen rectangles without accounting for painter overlap.

Preferred options, in order:

1. Invalidate cached ordered chunk/view plans while recomposing only affected depth runs.
2. Cache static depth runs or diagonal bands and merge dynamic entries in painter order.
3. Use a frame-budgeted rebuild while displaying the previous cached surface as a temporary preview.

Adopt the simplest option that meets the budget and passes overlap fixtures. Remove or redesign `DirtyRegionTracker` if it still has no consumer.

### 13.6 Make Zoom Rebuilds Frame-Budgeted if Needed

The current 140 ms scaled preview hides work temporarily, then permits a large exact rebuild. After algorithmic improvements, measure the first exact frame after preview expiry.

If it still exceeds 100 ms, build pure-Python candidate/plan data incrementally with a per-frame time budget while retaining the prior scaled surface. Keep event processing and cursor feedback responsive. Surface creation and final composition stay on the main thread.

Do not use a Python thread for CPU-bound planning without proving benefit; the GIL may only move the stall. Do not use multiprocessing unless snapshot transfer cost and frozen-build behavior are measured.

### 13.7 Separate Overview LOD From Normal Rendering

Retain the overview threshold concept, but make LOD explicit and testable:

1. Terrain may use one top representative per column at very small projected sizes.
2. Canonical structures use precomputed view-facing surface cells and never vanish at the threshold.
3. Transparent/model blocks use a readable representative when individual geometry is below one pixel.
4. LOD transitions use stable buckets to prevent flicker while wheel zooming.
5. Picking may use full world data even when rendering uses LOD.

### 13.8 Phase 5 Completion Gate

On the Trial Chamber:

1. Stable cached full-frame p95 remains below 16.7 ms.
2. Cold render after zoom, rotation, terrain-mode change, or culling-anchor rebuild is below 100 ms.
3. Fit plus first exact render is below 250 ms.
4. A one-block edit does not trigger a multi-hundred-millisecond full-world rescan.
5. Painter ordering, picking, overview visibility, and visual fixtures pass at all tested zooms and rotations.
6. Render caches remain bounded and report useful hit/miss/byte statistics.

## 14. Phase 6: Optional NumPy and GPU Decision Gates

Goal: adopt acceleration only when it improves this application on the target laptop without weakening the required Pygame path.

### 14.1 NumPy Gate

Profile candidate array-heavy work such as sprite shading, tinting, mip generation, and bulk pixel transforms. Build one isolated NumPy adapter only for a measured hotspot.

Accept NumPy only if all conditions pass:

1. The targeted operation improves by at least 30% on representative assets.
2. End-to-end startup or cold-frame performance improves materially.
3. Visual output stays within the approved threshold.
4. The Pygame-only implementation remains available and tested.
5. The optional dependency is documented outside `requirements.txt` unless it becomes required by an explicit later decision.

Delete the adapter if end-to-end impact is negligible.

### 14.2 GPU Prototype Gate

Create a narrow render-backend seam only for the world layer. Do not port UI, audio, persistence, or simulation during the prototype.

Benchmark a small representative adapter suitable for the Radeon 860M. Evaluate startup, texture upload, 4,000-block normal views, 45,000-block overview views, pan, zoom, rotation, transparency, and one-file packaging.

Accept a complete optional GPU path only if all conditions pass:

1. Stable p95 improves by at least 30% where the CPU path is constrained.
2. Cold view rebuild or first exact zoom frame improves by at least 20% after upload costs.
3. Visual/picking behavior remains equivalent.
4. Automatic fallback works when initialization fails or no compatible adapter exists.
5. The standard Pygame-only executable still builds and runs.
6. The accelerated executable or optional installation path has a tested PyInstaller configuration.
7. Added maintenance cost is justified in a short decision note inside `CONTRIBUTING.md` or module documentation.

If the CPU path already meets the practical strict budgets, the GPU prototype may be documented and rejected without implementing a second production renderer.

## 15. Phase 7: Editor, UI, Tutorial, and Effects Extraction

Goal: reduce `BlocFantome` to application orchestration after the performance-sensitive seams are stable.

### 15.1 Extract Editor Operations

Move block placement/removal, doors, stairs, slabs, structures, brush, fill, mirror, radial symmetry, selection, clipboard, stamp, replace, magic wand, and undo grouping into `engine/editor.py`.

Use a deep interface based on user intent, for example:

```python
editor.place(target, selection)
editor.remove(target)
editor.apply_tool(tool_action)
editor.undo()
editor.redo()
```

Return structured results containing changed positions, counts, sounds/notifications, and invalidation hints. Do not let the editor draw UI or directly mutate tooltip strings.

### 15.2 Unify Panel Layout and Hit Testing

Move inventory panel layout, rendering, hover, scrolling, and click resolution into `ui/inventory_panel.py`. Compute one layout model per relevant UI-state change and use the same rectangles for rendering and hit testing.

This replaces the duplicated arithmetic in the 778-line renderer and 320-line click handler. The module returns semantic actions such as `SelectBlock`, `ToggleCategory`, `OpenWorlds`, or `SetVolume`; the app executes them.

Cache text and scaled UI textures when content/state is unchanged. Avoid rendering identical labels and scaling identical button textures every frame.

### 15.3 Move Tutorial UI

Move `TutorialScreen` and its content to `ui/tutorial.py`. Keep demo execution in the app/editor through callbacks or returned actions. Replace the 92-line icon-name mapping with catalog lookup plus a small alias table.

### 15.4 Reconcile Effects

Create state-owning weather, atmosphere, particle, and horror modules. Each exposes a compact lifecycle such as `start`, `stop`, `update`, and `render`.

`Code/horror.py` currently duplicates behavior that remains in `BlocFantome`, and its `HorrorManager` is instantiated but never called. Choose the better-tested implementation per behavior, add tests, migrate state once, and leave one canonical `effects/horror.py`. Do not run both managers.

Avoid whole-world scans in effects. Consume world type/height indexes and visible positions from the renderer/world interfaces.

### 15.5 Move UI Overlays in Cohesive Groups

Move hotbar/search/tooltips together, settings/history together, and world indicators/minimap together. Do not create dozens of one-function modules.

The app keeps the top-level `_render()` order because ordering effects and overlays is application orchestration. Each call delegates to a module that owns its internal drawing and state.

### 15.6 Phase 7 Completion Gate

1. `BlocFantome` primarily composes modules, routes returned actions, sequences update/render, owns dialogs, and manages application lifetime.
2. `blocFantome.py` is approximately 3,000-5,000 lines unless a documented deep-module reason justifies more.
3. No extracted module reaches into arbitrary `BlocFantome` attributes through a back-reference.
4. No feature/content catalog or tool is lost.
5. All tests, visual checks, and performance gates remain green.

## 16. Phase 8: Dead Code, Packaging, and Permanent Documentation

Goal: remove superseded implementations only after replacements are proven.

### 16.1 Remove Proven Dead Duplicates

Delete these only after import/call searches and tests prove replacement coverage:

1. In-file legacy `World` and `IsometricRenderer` classes.
2. `Renderer3D` duplicates not used by the canonical model renderer.
3. `_legacySetAppIconEarly`, `_legacySetAppIcon`, `_legacyDetectBlockFace`, `_legacyUpdateHoveredCell`, `_legacyLoadBuilding`, and `_legacyLoadBuildingFromPath`.
4. Duplicate in-app horror logic after the canonical manager is active.
5. Stale cache/order fields such as `litBlockCacheOrder` if the real LRU no longer uses them.
6. Performance utilities with no caller, including atlas/batcher abstractions that do not improve software Pygame rendering.

Before deletion, map every removed behavior to its replacement test. “Legacy” in a name is not by itself proof that code is safe to delete.

### 16.2 Packaging Verification

Update static imports so PyInstaller discovers new packages. Add hidden imports only for genuinely dynamic optional adapters.

Run:

```powershell
python Code/build_exe.py --diagnostic
python Code/build_exe.py
```

Verify both executables launch, locate user assets, load a bundled world, load/save a user build, open Tk dialogs, play audio, and exit cleanly. Verify the optional acceleration path fails back to Pygame when disabled or unavailable.

Do not commit generated executables as part of this task unless the repository owner separately requests it.

### 16.3 Update Permanent Documentation

Update `CONTRIBUTING.md` with:

1. The actual module tree and dependency direction.
2. Where to add blocks, states, sounds, structures, tools, UI, and effects.
3. Source, test, benchmark, visual-check, and executable-build commands.
4. Cache/invalidation rules and performance budgets.
5. Save compatibility rules.
6. Optional acceleration decision and fallback behavior.

Add concise module docstrings that state responsibility, interface, invariants, thread restrictions, and performance characteristics. Document why a non-obvious cache key or painter-order merge is correct. Avoid comments that merely restate code.

Do not edit `README.md`.

## 17. Final Acceptance Matrix

### 17.1 Correctness

- [ ] All automated tests pass.
- [ ] All deterministic visual checks pass at eight zoom levels and four rotations.
- [ ] Block placement, removal, picking, doors, stairs, slabs, liquids, lighting, dimensions, weather, tutorial, structures, tools, undo/redo, and horror content remain present.
- [ ] Contextual shortcut contract passes.
- [ ] Failed loads leave the current world untouched.
- [ ] Save v1-v5 compatibility passes.

### 17.2 Performance on Trial Chamber

- [ ] Cached load median is at or below 1,000 ms.
- [ ] Stable cached full-frame p95 is below 16.7 ms.
- [ ] Cold view rebuild is below 100 ms.
- [ ] Fit plus first exact frame is below 250 ms.
- [ ] Zoom preview does not end in a visible long stall.
- [ ] One-block edits and common tools remain interactive.
- [ ] Memory stabilizes during a ten-minute pan/zoom/rotate/edit stress run.
- [ ] Total cache memory is bounded and reported.

### 17.3 Architecture

- [ ] One canonical block enum/catalog exists.
- [ ] `engine.world` has no runtime dependency injection through module globals.
- [ ] No extracted module imports `blocFantome` at runtime.
- [ ] `BlocFantome` orchestrates instead of implementing every subsystem.
- [ ] Panel rendering and hit testing share one layout.
- [ ] World rendering owns its cache and invalidation policy.
- [ ] Build I/O owns format compatibility and staging.
- [ ] One horror implementation exists.
- [ ] No known dead compatibility implementation remains without a documented reason.

### 17.4 Distribution and Documentation

- [ ] Source launch works.
- [ ] Standard one-file executable builds and launches.
- [ ] Diagnostic one-file executable builds and launches.
- [ ] Pygame-only fallback is fully functional.
- [ ] `CONTRIBUTING.md` and module docstrings match the implemented architecture.
- [ ] `README.md` is unchanged.
- [ ] Changes remain unstaged, uncommitted, and unpushed.

## 18. Required Validation Commands

Run focused tests throughout, then run this final sequence:

```powershell
python -m pytest -q
python tests/render_visual_checks.py
python tests/render_world_checks.py
python tests/benchmark_large_world.py ancient_city_121 trial_chamber_121
python Code/build_exe.py --diagnostic
python Code/build_exe.py
git status --short
git diff --stat
```

If a full executable build is too expensive during intermediate phases, run an import-collection smoke test after every module move and reserve both builds for Phase 8. Packaging verification is still mandatory before final completion.

## 19. Primary Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Large file moves hide behavioral changes | Separate extraction-only commits/diffs from optimizations conceptually, even though work remains uncommitted. Run tests after each move. |
| Enum identity or values change | One canonical enum plus explicit value-contract tests. |
| Save migration regresses | Fixture coverage for every supported version and transactional load tests. |
| Chunk caching breaks painter order | Global-order equivalence tests and overlap visual fixtures before accepting cache composition. |
| Cache invalidation shows stale blocks | Explicit invalidation matrix and edit/undo/rotation/zoom integration tests. |
| Threaded load races with Pygame/live world | Worker returns immutable snapshots; main thread performs atomic replacement. |
| More mipmaps improve speed but blur art | Visual threshold tests and hybrid scale selection by zoom direction. |
| GPU path expands scope without benefit | Mandatory measured gate; reject and remove it if end-to-end gains are insufficient. |
| Optional dependencies break frozen builds | Pygame-only required path, explicit optional packaging smoke test, automatic fallback. |
| Current dirty work is lost | Treat working tree as baseline and never restore modified files to `HEAD`. |
| Stable-frame optimization distracts from stalls | Gate work on load/cold/fit/zoom metrics, not average FPS alone. |

## 20. Execution Order Summary

1. Add characterization, visual, input, and benchmark safety nets.
2. Extract canonical domain catalogs and runtime paths; remove reverse imports/globals.
3. Repair contextual shortcuts and broken undo paths behind semantic commands.
4. Extract and deepen asset ownership; implement measured multi-resolution sprite caching.
5. Extract build I/O and implement indexed bulk world replacement.
6. Extract world rendering, formalize invalidation, and optimize cold candidate/composition paths.
7. Evaluate optional NumPy and GPU adapters through measured gates.
8. Extract editor, panel, tutorial, effects, and cohesive overlay modules.
9. Remove proven dead duplicates, validate both executable builds, and update `CONTRIBUTING.md`.
10. Run the final acceptance matrix and retain benchmark evidence with the working diff.
