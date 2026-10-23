# Proposed 3.2 architecture and performance plan

## Release delivery contract

3.2 remains future work covering both measured performance and moderate
monolithic-app refactoring. After 3.1 acceptance, preserve its source, root EXE,
complete installation, settings and private inputs as the next rollback baseline.
An accepted 3.2 release must update main, its version tag, version resources,
changelog and relevant documentation, then rebuild the root `BlocFantome.exe`,
upgrade the installed executable and verify the actual Start Menu application,
running identity, basic gameplay and matching release source. A package only
under `.qa` is a review build, not a completed release. Do not start 3.2 during
the final 3.1 review.

Status: plan only, 23 October 2026. Both objectives are owner-approved future work;
no 3.2 extraction or renderer optimization is implemented in 3.1. Accepted behavior
comes from 3.0 commit `46324ef4`, current regression contracts and actual renders.
`References/REFACTOR_IMPLEMENTATION_PLAN.md` is historical research, not a spec.

## Current ownership and coupling

An AST inventory of the accepted composition root finds 22,684 lines, 1,121,036
working-file bytes, 339 application methods and 437 distinct directly assigned
`self` fields. These are descriptive counts, not reduction targets.

| Area | Current owner and dependency | Proposed boundary |
| --- | --- | --- |
| Stable identities | `domain/blocks.py`, `domain/block_catalog.py`, `domain/dimensions.py`, `domain/structures.py`; compatibility exports in `blocFantome.py` and `constants.py` | Retain canonical enum/class identities and constructor-injected `WorldCatalog`; move catalog data only after import contracts pass |
| World state | `engine/world.py`, `world_snapshot.py`, `undo.py`, lighting/redstone/fluid modules | Retain; a document session owns world, revision, generation, path and dirty state together |
| Persistence | `build_io.py`, `save_job.py`, `settings_io.py`; application owns dialogs, save executor and completion | Small save coordinator taking immutable snapshot and explicit document token; no UI imports in serializer |
| Loading | `WorldLoadingAppMixin`, `_stageBiomeScene`, `_readBuildFile`, `_applyStagedBuild`; one world executor | Load coordinator owns cancellation/generation, staged results and pending work; main-thread adapter owns application and SDL mutations |
| Rendering | `engine/renderer.py` owns projection; application `_renderWorld` owns visible traversal, composition, surfaces and invalidation | World-view composer with explicit world revision, camera and view options; retain renderer and global painter order |
| Assets | 4,279-line `AssetManager`, 82 methods, 113 assigned fields; sprite recipes and sound loading share lifetime | Extract texture/sprite service first, then audio assets separately; explicit byte budgets and invalidation rules |
| Audio | `engine/audio.py`, `audio_decode.py`, channel router, `ui/feedback.py`, `opening_audio.py`; app orchestrates dimension/session policies | Keep existing controllers; one session owner for channels, queued preparation and shutdown |
| UI/input | `ui/workshop*`, library/preview/browser/settings/chrome/lifecycle modules; app keyboard/mouse dispatch retains legacy paths | Explicit action adapter and modal/input owner; preserve hitboxes, priorities, focus and release consumption |
| Tutorial/opening/map/lab | Existing `ui/tutorial.py`, opening modules, map preparation/transition, engine map/lab | Session adapters for capture/restore of editor state; no cross-session mutation of the live document |
| Paths/build | `runtime_paths.py`, build scripts and native receipt | Retain single source/frozen path authority; explicit private-input manifest |

`_handleKeyDown` is 513 lines, `_renderWorld` 452, `_onTutorialStepChange` 345,
`_renderPanel` 543 and initialization 665. World, document state, camera, lighting
and transient UI fields cross these boundaries. `tooltipText`/`tooltipTimer` have
81/77 assignment sites. Avoid moving these methods into mixins that continue to
read the entire application object; that changes location without ownership.

`_LegacyTutorialScreen` is still inherited by `TutorialScreen`, and is not dead.
Definition-only `_legacy_createEndPortalBlock`, `_legacy_createFireBlock`,
`_legacy_createMatrixBlock`, `_legacyUpdateHoveredCell`, `_legacyLoadBuilding` and
`_legacyLoadBuildingFromPath` are removal candidates. Before removing each, check
dynamic dispatch, public imports, diagnostic hooks and source/frozen behavior.
The earlier duplicate enum, World and renderer definitions were already removed;
do not redo that completed work.

## Stages and rollback points

1. **Freeze contracts and measurement.** Record the accepted 3.1 source/package
   hashes, native/fallback identity, deterministic images, source/cache semantics,
   save v1-v5 corpus and input/action traces. No production behavior changes.
2. **Document/save ownership.** Introduce one document token and a narrow save
   coordinator, retaining application compatibility methods. Test edits during
   save, Save As, cancelled dialogs, autosave/manual interleaving, failure/retry,
   backup rotation, dirty exit and shutdown. Roll back this adapter independently.
3. **Load/session ownership.** Extract generation/cancellation ownership using the
   existing immutable staging layer. Reproduce stale completions after edits,
   resize, dimension change and tutorial/map/lab entry/exit. Verify worker drain
   before SDL teardown and restore exact camera/world/undo/sky state. Keep one
   scheduler per workload, not an executor per scene.
4. **Texture/sprite ownership.** Move a coherent asset family behind a narrow
   interface; retain names used by the app and tests. Compare exact sprite RGBA,
   animated frames, lighting, transparency, cube projection and bounded caches.
   Keep original textures and native-size fonts unchanged. Roll back by family.
5. **World composition and measured performance.** Extract composition only after
   camera/edit/load profiles locate costs. Preserve global painter order and
   atomic visible updates. Integrate one optimization at a time with randomized
   execution order and alternating baseline/candidate measurements.
6. **Input/UI adapters and dead paths.** Remove verified unreachable implementations
   after new owners are stable. Keep public `blocFantome` exports, data identities,
   CLI diagnostics, save format and source/frozen paths compatible. Run rendered
   comparisons and real Windows interaction checks before accepting each removal.

Each stage is a separately reviewable change on development with a recoverable
source snapshot and isolated executable. Failed equivalence or owner-visible
regressions revert that stage; do not rewrite history or relax the acceptance
criteria. Full tests and the two visual scripts gate rendering/geometry changes.

## Performance protocol

Existing accepted measurements identify complete camera repaints, exact zoom,
large-world editing, loading and snapshot capture as targets. The final 3.0
matched profile measured Ocean Monument pan near 378 ms and edits near 122 ms,
with Trial Chamber pan reaching 759 ms. These are historical machine-specific
observations. Current 3.1 evidence distinguishes clean measurements from runs
contending with QA/archive work; do not call contention a regression.

The isolated 3.1 matched-method trace at 1200x800 confirms equal final RGBA on
four worlds. Current complete repaint medians include Trial Chamber pan 191 ms
and zoom 288 ms; Ocean Monument pan 136 ms and edit repaint 44 ms. A settled Fit
view and shared current dependencies make these different from historical 3.0
traces, not evidence of acceleration. Visible-plan traversal/rounding remains a
measured profile cost. See the [3.1 report](CONSOLIDATION_3_1.md) for methodology,
resource trace and limitations; preserve full OS-input-to-visible timing as a
separate 3.2 acceptance measurement.

Use Ancient City, Trial Chamber, Ocean Monument and a small ordinary scene at
1200x800, plus 960x640 and 1920x1080 checks. Record Python/Pygame, CPU/GPU, native
backend, display driver/DPI, cache state, scene hashes, block counts and memory.
Warm each path, alternate order, collect at least five repetitions. Measure:

- Load: disk/hash/decode/staging, main-thread apply, first complete visible frame.
- Camera: event receipt to final correct frame for pan, zoom, rotation and Fit;
  include all incremental frames, not only a cached overview or first batch.
- Edit: real input hit test, changed cell, undo bookkeeping, invalidation, final
  RGBA and persisted result. Handler-only latency is insufficient.
- Caches: retained surface/sprite/previews, source versus derived world data,
  invalidation reason, disk eviction, decoded audio bytes and working set.
- Sustained behavior: repeated scene/session changes, full music transitions and
  ten-minute-or-longer RSS/thread/handle traces after warmup; report spikes and
  retained allocations separately from leaks.

Retain the existing targets: cached load <=1,000 ms, stable full-frame p95 <16.7 ms,
cold rebuild <100 ms, Fit plus exact frame <250 ms. Report failing targets as HOLD;
do not substitute lower-fidelity frames, smaller worlds or weaker tolerances.
Potential experiments include revision-scoped visible plans, reducing repeated
Python traversal/allocation, separating camera versus sprite invalidation and
bounded cache admission. Chunk composition requires a painter-order equivalence
proof. No GPU rewrite or speculative renderer replacement is implied.

## Reference collections

Keep `Game Reference`, `WorldBuilder Reference` and `Redstone Reference` physically
unchanged in 3.1. `export_biome_catalog.py`, `capture_biome_world.py` and
`capture_scene_regions.py` depend on the Java corpus; map template/sprite builders
depend on WorldBuilder. The biome catalog stores Java source provenance strings.
`test_biomes.py` and `test_redstone_lab.py` have optional local-reference checks;
`check_local_assets.py` inventories all three. Runtime reads exported Assets/Code
data, not a consolidated reference folder.

A future migration first inventories path consumers and hashes every source,
then introduces configurable roots with current defaults, tests both layouts,
copies and verifies a separate destination, and proves regeneration equivalence.
Only then switch defaults. Keep old paths and a rollback mapping through an
accepted release; never treat a same-disk copy as an independent backup.
