# World Map 2.7.2 verification

The Nether and End selectors now display seven larger, pannable and zoomable captures from an official Minecraft Java 1.16.1 world (seed 1). Level contents are unchanged. The existing dimension navigation and route markers remain, with region navigation, overview framing and subtle dimension effects added.

## Source fidelity

- Five Nether captures cover all five vanilla Nether biomes, a naturally assembled 112-piece hoglin stable bastion and a complete 147-piece fortress.
- Two End captures contain the central island with ten crystals, pillars and the inactive exit fountain, and an outer island with a naturally assembled 57-piece End City including its ship.
- `Code/tools/verify_world_map_regions.py` independently compared all 2,299,496 retained block cells with the original region-file palettes and packed block states: zero mismatches. Evidence: `.qa/worldmap-current/source-verification.json`.
- The source server JAR is `Game Reference/01_upstream/minecraft-1.16.1-server.jar`; the separate generated world is `.qa/worldmap-vanilla/reference-world`.
- Captures and source-model atlases are in `Code/world_map_regions/`. Export and baking tools are in `Code/tools/`.

These are bounded captures of actual terrain, not a seamless reconstruction of an entire dimension. The Nether uses a labeled roof cutaway and bottom cut to expose its interior; invisible solid interiors are omitted. The isometric presentation uses Minecraft block models and textures but is not pixel-identical to Minecraft: lighting, texture animation frames, weighted model selection and fluid surfaces are simplified. Block positions and states, terrain shape and structure assembly are source-backed.

The separate existing Bridge Bastion gallery scene was investigated but not repaired in this change. The new selector uses the requested non-bridge bastion.

## Verification

- Full suite: 280 passed in 73.08 seconds (`.qa/worldmap-full.log`).
- Final focused map tests after marker corrections: 18 passed. App integration checks: 26 passed, 112 deselected.
- Compile checks and `git diff --check` passed.
- Visual captures cover all seven regions at 960x640, 1200x800 and 1920x1080, including overview and hover states; Overworld and Ocean were also captured. Evidence: `.qa/worldmap-final/`.
- Worst measured map panning p95 was 10.29 ms across these captures (`.qa/worldmap-final/performance.json`). This is a map-rendering measurement, not a guarantee of whole-app performance on other hardware.

## Release

- Root EXE and Inno Setup installer built as 2.7.2.
- Archive inspection confirmed all 16 region/atlas files, the Tk modules, `_tkinter.pyd` and `pyi_tk_runtime`; the build's Tk discovery warnings did not indicate missing packaged runtime files.
- Installer completed successfully and the installed EXE matches the root EXE by SHA-256.
- Start Menu target, working directory and icon resolve to the real user's installed app directory.
- Root and Start Menu launches each remained responsive through a 12-second smoke check (all four enumerated windows answered a timed Windows message). Both checks left zero exact-path processes. Results are recorded in `.qa/worldmap-release-smoke.json`.

Primary implementation files: `Code/engine/world_map_regions.py`, `Code/ui/source_map.py`, `Code/engine/world_map.py`, `Code/ui/world_map.py`, `Code/blocFantome.py`, and the build/installer definitions. Root README remains unchanged. Changes are left uncommitted.
