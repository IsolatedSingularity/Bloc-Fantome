# Bloc Fantôme 2.9.2

Installed and verified through the Start Menu shortcut. The installed EXE and root EXE have identical SHA256:
`8D561715E66B58E11C34FE6858EC5A02D1B7DC9EF326716E251B40E10D494FED`.

## Delivered

- Reworked the 16-page tutorial with distinct source scenes, original cryptic Minecraft prose, dimensions, independently turning skyboxes, rain, snow, the live World Map, and the full 4-bit counter lab. Leaving the tutorial restores the original build; map and lab excursions preserve the tutorial and original preferences.
- Expanded all 37 featured biome captures. The central End is 256 × 256 with all ten pillars clear of the capture edges; other featured biomes are at least 96 × 96, with outer End captures at 128 × 128.
- Replaced 13 Java 1.16.1 Worlds with natural source locations, including villages with nearby pyramids/outposts, four bastions, the ocean monument, the End City, and the fortress. Landmarks retain their original positions. Surface and cavern cutaways retain actual source cells rather than generating replacement terrain.
- The final fortress capture is 98.55% Nether Wastes. Its cavern cutaway contains all 65,678 source fortress structure cells, including supports. The World has 659,181 cells; its closer tutorial view has 488,992.
- The deep-ocean World retains all 989,663 captured cells, including water. Water is visually cut away to reveal the real monument and seabed; hidden water does not intercept monument clicks.
- Removed the upper coordinate duplicate and extra tutorial controls. One persistent question mark sits immediately left of Settings, with Redstone Lab above Settings. Top controls and hotbar align to the building viewport.
- Replaced the splash with the supplied swamp painting, preserving its complete aspect ratio and using a small regular title at bottom center.
- Packed source records without adding runtime dependencies; staged palette resolution and render indexes on the loading worker; reduced overview, minimap, and underwater rendering work.

## Verification

- Full suite: **333 passed in 162.71 seconds** (`revision-292-packed-full.txt`). Compile checks and `git diff --check` passed.
- All 95 packed captures reproduce the original metadata and **19,349,635 cell records exactly** (`revision-292-packed-verification.json`).
- **17,898,383 retained scene/biome cells** compared directly with their official Java source chunk states (`revision-292-source-verification.json`). The fortress has an additional independent completeness check against every source fortress material cell (`revision-292-fortress-completeness.json`).
- All 15 Worlds loaded through the library path and rendered in four views at 1920 × 1080. Ninety complete update/render samples per view; maximum settled-frame p95 was **9.41 ms**. Raw measurements: `revision-292-worlds/performance.json`.
- Final loading times ranged from 1.79 to 12.52 seconds. Ocean: 6.48 s; fortress: 8.94 s; the largest village scene: 12.52 s. Loading still has occasional visible pauses, so these are not claims of uninterrupted 60 FPS during scene replacement.
- Full tutorial and shared UI captures at 960 × 640, 1200 × 800, and 1920 × 1080 are in `revision-292-final-visual`. Updated fortress/ocean pages, panels, and splash are in `revision-292-release-visual`; central End and deep-ocean biome views are in `revision-292-biomes`.
- Archive inspection verified **938 source and visual assets byte-for-byte**, native acceleration, and the Tk dialog runtime (`revision-292-archive.json`).
- Root and installed EXEs launched as **Bloc Fantôme 2.9.2**. The installed launch used its Start Menu shortcut. Desktop checks confirmed tutorial leave/reopen/minimize and the native Open dialog followed by cancellation.
- Both app and uninstall Start Menu shortcut targets, icons, working directories, and target existence verified (`consistency-start-menu-292.json`). All **9 existing installed save/configuration files retained their hashes**. No QA app processes remain (`revision-292-root-smoke.json`, `revision-292-installed-smoke.json`, `revision-292-userdata-verification.json`).

## Files and artifacts

Main changes: `Code/blocFantome.py`, `Code/engine/tutorial_lessons.py`, `Code/engine/tutorial_runtime.py`, `Code/engine/skybox.py`, `Code/engine/world.py`, `Code/engine/world_snapshot.py`, `Code/engine/capture_records.py`, `Code/engine/biome_capture.py`, the source export/packing tools, world catalogs and captures, `Code/ui/tutorial.py`, `Code/splash.py`, release scripts, regression tests, `CHANGELOG.md`, and the approved splash/tutorial guidance in `AGENTS.md`.

- Root EXE: `BlocFantome.exe`.
- Installer: `Code/build/installer/BlocFantome_Setup_2.9.2.exe`.
- Installed EXE: `C:\Users\hunkb\AppData\Local\Programs\Bloc Fantôme\BlocFantome.exe`.
- Start Menu: `C:\Users\hunkb\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Bloc Fantôme\Bloc Fantôme.lnk`.

`README.md` was not edited. Changes remain unstaged, uncommitted, and unpushed. Existing unrelated checkout changes and user data were preserved.

## Remaining limits

The existing **Ancient City and Trial Chamber Java 1.21 entries remain source-template assemblies with representative terrain**. They are not among the 13 natural Java 1.16.1 World replacements. Converting those two entries to natural Java 1.21 captures is the next fidelity task.

The public free-build download considered during research was blocked by its download route; no external build was imported from it. The tutorial instead uses the local Java references and a small number of authored practice scenes. The prose is original.
