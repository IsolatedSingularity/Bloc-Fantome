# Bloc Fantôme · visual/audio reference kit

Research snapshot: 20 September 2026. **Reference material, not a game update.**

Start here, then read only the relevant branch below. This kit contains source-grounded notes, a complete **47-file Create scene catalogue**, source/asset manifests, and a tested selective downloader. It does not contain a replacement renderer, a Java-to-Python port, an implemented tutorial, commercial music recordings, or a downloaded asset dump.

## What matters first

1. Bloc Fantôme already interpolates piston payloads over 100 ms. Ponder's basic section movement is also linear. Investigate timing, compositing, cache invalidation and shared motion state before adding an easing system. [Sources](SOURCES.md#b-redstone), [Ponder interpolation](SOURCES.md#p-animate).
2. Ponder's reusable unit is **a selected collection of geometry with an independent presentation transform**. Its virtual world and instruction queue organize demonstrations; they do not replace a gameplay simulator. [Source](SOURCES.md#p-section).
3. Pixel-aligned shadows anchor shadow samples to object/world surface coordinates. Downscaling a finished screen image is not equivalent. [Source](SOURCES.md#x-fragment).
4. Existing skyboxes expect a specific **3×2 cubemap atlas**. A panorama or HDRI is a source asset, not a direct drop-in. [Source](SOURCES.md#b-sky).

## Reading routes

**Improve piston visuals:** [baseline](bloc_fantome/current_architecture.md) → [piston deep dive](ponder/piston_redstone_deep_dive.md) → [mapping](bloc_fantome/ponder_mapping.md) → [bounded opportunities](bloc_fantome/opportunities.md).

**Understand Ponder:** [architecture](ponder/architecture.md) → [animation primitives](ponder/animation_primitives.md) → [rendering](ponder/rendering.md) → [scene catalogue](ponder/scene_catalog.md) → [source map](ponder/source_map.md).

**Atmosphere/assets:** [pixel-locked shadows](rendering/pixel_locked_shadows.md), [lightweight lighting](rendering/lightweight_lighting.md), [fog](rendering/fog_atmosphere.md), [skyboxes](skyboxes/catalog.md), [music](audio/music_references.md), [UI audio](audio/ui_sound_references.md).

## Retrieve actual upstream code

Python 3.10+; standard library only. PowerShell wrappers use the same Python implementation. Commands default to a dry-run plan. Downloads require `--execute`. No command modifies a game repository.

```powershell
python scripts/fetch_references.py --group ponder --group create --group create-scenes
python scripts/fetch_references.py --group ponder --group create --group create-scenes --execute
python scripts/index_scene_methods.py downloads/create-scenes/Create
python scripts/fetch_references.py --group shaders --execute
python scripts/fetch_references.py --group bloc-baseline --execute
```

The normal download budget is 16 MiB, checked during transfers. Files are fetched individually from pinned commits, not as whole-repository archives. Existing files are never overwritten. Choose an empty destination to refetch. `downloads/` stays separate from game source and is not part of this ZIP.

For all remaining Ponder-package Java classes, use the optional pinned-tree expansion in [the helper guide](scripts/README.md). For optional asset downloads, see [asset commands](scripts/README.md). Direct published ZIP links exist for selected CC0 packs. Other entries deliberately retain their official acquisition page rather than inventing an unstable asset URL.

## Evidence and boundaries

**Observed** means read in source or published metadata. **Inference** means an explanation supported by that evidence but not measured here. **Proposal** is a future experiment, not an implemented feature.

The main application file exceeded connector content limits. Its render-loop body was not audited. No game was built or run, and no before/after visual improvement is claimed. Audio selections are metadata-grounded audition candidates, not files listened to during this run. No skybox or sound archives were downloaded in this environment: external DNS was unavailable. The downloader was exercised with local HTTP fixtures instead. See [QA](QA.md).

Keep the current game intact. Match a reference behavior in a bounded future experiment, then make it Bloc Fantôme's own. Do not add horror cues, redesign the opening disc/tutorial, or import all of Create merely because these references exist.
