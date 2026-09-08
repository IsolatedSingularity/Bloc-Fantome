# World Map expansion — 2.7.3

## Changes

- Overworld: five official Java 1.16.1 seed-1 captures covering plains and river, a taiga village, flower forest, mushroom fields, and a desert coast with a naturally generated temple.
- Deep Ocean: generated monument and shipwreck regions with the original seabed, ocean ruins, kelp and seagrass. The monument is at `[-909,39,-877]` through `[-852,61,-820]`; the wreck is at `[-292,50,187]` through `[-269,58,195]`. Neither structure was relocated or assembled by hand.
- Outer End: expanded the survey from 240x240 to 768x768 blocks. The complete city island and surrounding complete islands are retained. Whole distant islands that intersect the survey boundary are omitted; no end-stone column touches the displayed capture boundary.
- Nether: reduced the vertical projection to 60% of its previous height, consistently across block models, map coordinates, camera framing and markers. Original block coordinates remain unchanged; genuine cliffs and structure supports remain.
- Splash: a 3840x2160 render of the captured warped forest, aspect-filled behind the existing horror wordmark. Regenerate with `Code/tools/render_world_map_splash.py`.
- Builder hotbar: preference saves now read the preserved builder session while the Lab or tutorial is active. Both hotbar rows are restored after temporary sessions. The root EXE's incorrectly saved Lab palette was backed up and repaired; the installed configuration is repaired during release verification.
- Rendering: biome colormap tints, source bed ModelParts, underwater haze and rays, wider ocean/temple framing, and larger/overscanned geometry caches for smooth map panning.

## Verification

- All 4,498,951 retained cells across 14 captures independently matched their original Minecraft chunk states: zero mismatches. Evidence: `.qa/worldmap-expansion-source-verification.json`.
- Full regression suite: 284 passed in 93.86 seconds. After the final caching change, 21 focused scene/UI tests passed, including a new close-zoom cache-reuse test. Earlier map/app integration pass: 30 passed, 112 deselected.
- Visual QA: every region at 960x640, 1200x800 and 1920x1080, with overview and available hover states; splash at all three sizes; builder hotbar after leaving the map. Evidence: `.qa/worldmap-expansion-final/`.
- Final measured default-view cached pan p95: worst 12.16 ms, down from over 300 ms in the first expansion pass. These measurements exclude initial map preparation; close-zoom cache-boundary rebuilds can still take longer.
- Compile checks and `git diff --check` passed. Every used block state that has visible geometry has a nonempty atlas sprite. Bubble columns have no solid block surface.

## Presentation limits

The original 2.5D rendering limits still apply: this is not Minecraft's full lighting or shader pipeline. Models and textures are source-derived, with static texture frames, unblended biome-column tints and simplified fluid surfaces. Overworld scenes expose a 12-block-deep source geology section. Ocean scenes omit water blocks to expose the source seabed and label this as a water cutaway. These display choices do not invent terrain or move structures. Playable level contents were not changed.

## Files and release evidence

Primary files: `Code/engine/world_map_regions.py`, `Code/ui/source_map.py`, `Code/ui/world_map.py`, `Code/engine/world_map.py`, `Code/blocFantome.py`, `Code/splash.py`, `Code/tools/`, `Code/world_map_regions/`, the warped-forest PNG in `Assets/Icons/`, focused tests, and the build/installer definitions.

Release logs and smoke evidence use the `.qa/worldmap-273-*` prefix. The root and installed EXEs report 2.7.3 and match by SHA-256. Archive checks confirmed all 14 captures and required Tk runtime files. The installed forest splash matches the source artifact. Start Menu target, working directory and icon are correct.

The root EXE passed its 12-second responsiveness smoke. The installed app needed a longer cold-start check; its actual Pygame window and all helper windows responded at 20 seconds. Both checks left zero exact-path processes. Evidence: `.qa/worldmap-273-release-smoke.json` and `.qa/worldmap-273-installed-ready.json`. The installed Lab palette was backed up and repaired without changing other saved preferences.

The root README is unchanged. Changes remain unstaged and uncommitted.
