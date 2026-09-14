# World Map biome refinement - 2.7.4

## Changes

- Seventeen map previews: six Overworld, six Nether, two End and three Ocean regions. Each has two named question marks, independent of saved mission completion. Preview markers do not launch levels; existing objective implementations are preserved.
- New source captures favor grassy plains, inland desert, snowy taiga and a flowered woodland shoreline. The swamp includes a naturally generated ruined portal on its adjoining bank. Default framing emphasizes the named terrain; overview retains the complete regional capture.
- Mushroom Fields expands from 384x384 to 512x512, revealing the larger island group to the west. Retained geometry includes 34,809 mycelium blocks, 2,889 red mushroom blocks and 3,060 brown mushroom blocks.
- Crimson Forest, Warped Forest, Soul Sand Valley and Basalt Deltas have separate previews. Nether blocks use a 32-pixel vertical projection at unit scale, consistently in the atlas, camera and markers. The first substantial cavern and structure-footprint cutaways expose buildings instead of higher cave floors. Source coordinates are not flattened or moved.
- The original fortress spans 218x172 blocks, with all 147 generated pieces inside the capture. Long bridges, crossings, corridors, stairs and rooms retain their source layout. The cutaway preserves nether-brick structure materials, the soul-sand garden beds and the lava well. Supports use the documented bottom section at Y16.
- The active Nether portal uses six portal cells and fourteen obsidian frame cells on a source clearing. It is explicitly authored decoration, stored separately from source cells, with a subtle animated violet glow. The reference world was not edited to place this portal.
- The Ocean keeps its water cutaway, source kelp and seagrass, and adds a naturally generated warm-ocean coral reef with sea pickles. All of these blocks exist in Java 1.16.1.
- Conservative raster coverage closes fractional-zoom gaps in opaque blocks, including the End pillars. Both End captures retain exactly the same block records and palette as the preceding checkout version.
- Splash background brightness is reduced by approximately 14.5 percent. The wordmark remains unchanged and is drawn after the background treatment.

## Source and fidelity

The source is the local official Minecraft Java 1.16.1 server/client, seed 1, DataVersion 2567. Additional terrain was generated in `.qa/worldmap-vanilla/reference-world`; generation was stopped before the final export and verification.

The verifier independently compared **3,567,537 retained cells across 17 captures**, with **zero mismatches**. The **20 authored portal cells** are counted separately and are not claimed as naturally generated. Evidence: `.qa/worldmap-274-source-verification.json`.

Biome selection uses source biome records and visual inspection. The `surface_biomes` metadata records the Y64 column sample, not a guarantee that every visible block belongs to that biome. Natural biome borders, rivers and adjoining terrain remain. The presentation is a stylized 2.5D cutaway, with simplified lighting, fluid surfaces and texture animation; it is not Minecraft's full renderer.

## Verification

- Focused map, rendering and app integration tests: **147 passed in 41.77 seconds**. The subsequent full suite includes those tests and the final region/framing changes.
- Final full suite: **289 passed in 56.66 seconds**. Evidence: `.qa/worldmap-274-full-final.log`.
- Compile checks and `git diff --check` passed.
- Visual QA: all 17 regions at 960x640, 1200x800 and 1920x1080, including overview, hover, marker click suppression, splash and builder restoration. Evidence: `.qa/worldmap-274-verified-visual/` and `.qa/worldmap-274-verified-visual.log`.
- Worst cached-pan p95 across 51 region/resolution combinations: **8.70 ms**. This excludes initial preparation and cache-boundary rebuilds. The focused cache test also verifies reuse at close zoom.
- Regression checks cover snowy terrain, both mushroom types, biome selection, coral/sea pickles, non-playable landmarks, fortress piece containment and garden/well retention, separate portal provenance, and pillar opacity at six fractional zooms.

## Release

The root EXE and installer were built as **2.7.4**. The archive check verified every region/atlas byte against the current source files, the embedded splash, and the Tk runtime. Nine packaging contract tests passed after the final packaging adjustment. Build logs: `.qa/worldmap-274-build.log` and `.qa/worldmap-274-installer-build.log`; archive evidence: `.qa/worldmap-274-archive.json`.

The installed EXE at `C:\Users\hunkb\AppData\Local\Programs\Bloc Fantôme\BlocFantome.exe` reports 2.7.4 and matches the root SHA-256: `C229DDFD9B20EE04E271349F38198C19C99E00A16E1347855A07EC8F41C69716`. Start Menu target, working directory, icon and required installed assets passed verification. Both saved hotbars were preserved. Evidence: `.qa/worldmap-274-install-verification.json`.

Both the root EXE and installed Start Menu launch passed their 20-second smoke checks. Their actual Pygame windows responded, all four windows per launch responded, and zero exact-path test processes remained afterward. Evidence: `.qa/worldmap-274-release-smoke.json`.

## Files and remaining scope

Application changes are in `Code/engine/world_map_regions.py`, `Code/ui/source_map.py`, `Code/ui/world_map.py`, `Code/splash.py`, the export/bake/verification tools, `Code/world_map_regions/`, release version definitions, and the focused/visual tests. The reference-world expansion and QA evidence live under `.qa/`.

The separate Bridge Bastion gallery is outside this change and remains unresolved. README was not edited. No changes were staged, committed or pushed by this task; unrelated redstone behavior and user saves were preserved.
