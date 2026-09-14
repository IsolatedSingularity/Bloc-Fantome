# Bloc Fantôme 2.8.1 QA

## Changes

- `Code/ui/biomes.py` and `Code/engine/biome_catalog.py`: larger two-column browser, familiar biome families first, dimension filtering and explicit Open Scene confirmation.
- `Code/biome_captures/`, `Code/engine/biome_capture.py`, capture/export/baking tools: 79 Java 1.16.1 biome specimens, baked previews and four camera views. Source palette identifiers survive editing and save/load through `Code/domain/blocks.py` and `Code/engine/build_io.py`. Extra captured materials have stable IDs in `Code/engine/capture_materials.py`.
- `Code/ui/tutorial.py`, `Code/engine/tutorial_lessons.py`, `Code/engine/tutorial_runtime.py`: one styled, draggable/minimizable 27-page Back/Next tour, optional interaction, immediate example switching and restoration of the original build on exit. Includes the horror page and current app features.
- `Code/engine/sky_layers.py`, `Code/engine/skybox.py`, `Code/blocFantome.py`: perspective-projected voxel scenery, slow continuous movement and migrated enabled defaults. Overworld defaults to Night; later user settings persist.
- `Code/splash.py`, `Code/tools/bake_builder_splash.py`, `Assets/Icons/Splash_Midnight_Workshop.png`: cottage island, orchard, pond and a small eerie seam, with the existing Bloc Fantôme wordmark. Title fits at 960, 1200 and 1920 pixel widths.
- `Code/build_exe.py` and `Code/installer.iss`: release 2.8.1, captured biome data and new splash packaging.
- `Code/build_native.py`: reuse an output DLL only when it matches the freshly compiled DLL byte-for-byte, avoiding unnecessary Windows locked-file replacement. Native compilation precedes engine imports in the release builder.

## Generation provenance

All 2,829,617 exported cells were compared with their original Java 1.16.1 Anvil block states. No authored decoration was added to biome specimens. The source audit is `.qa/biome-source-verification-281.json`.

74 specimens come from natural seed-1 generation. Mountain Edge, Deep Warm Ocean, Modified Jungle Edge and Modified Badlands Plateau use the unmodified vanilla generator with a fixed biome because the natural survey did not find them. The Void uses the vanilla Void preset. These exceptions are labelled in the browser. Captures are bounded display sections, not entire chunks: geology is cropped, Nether ceilings removed, and ocean cutaways expose underwater features. Closely related vanilla biomes can still share vegetation and terrain characteristics.

Source palette rendering preserves the captured appearance; it does not add every vanilla block simulation mechanic to this builder.

## Verification

- Full suite: **305 passed** (`.qa/pytest-281-release.log`).
- Subsequent drawer routing changes: **127 integration tests passed** (`.qa/pytest-281-drawer.log`).
- Final tutorial navigation/highlight adjustments: **5 targeted tests passed** (`.qa/pytest-281-last-ui.log`).
- Compile checks and whitespace checks passed. Splash sizing was asserted at three resolutions.
- Final packaging/public-contract checks: **10 passed** (`.qa/pytest-281-package.log`).
- Visual outputs cover all 79 previews, all 27 tour pages at three resolutions, dimension browsers, skies and splash (`.qa/visual-281-final/`).
- Live packaged QA exercised Next, Back, Leave, the actual Biomes header, two-column selection and opening a captured Plains scene.

At 1920×1080, measured render-work p95 was 7.56 / 8.60 / 10.52 ms settled and 13.38 / 17.14 / 16.55 ms during rotation for Overworld / Nether / End. Cold rotation frames reached approximately 28 ms. These are local measurements excluding frame pacing, not a guarantee of locked 60 FPS on every system. Evidence: `.qa/visual-281-final/performance.json`.

README and unrelated existing work were preserved. Changes remain unstaged and uncommitted.

## Release handoff

Built `BlocFantome.exe` and `Code/build/installer/BlocFantome_Setup_2.8.1.exe`, then installed 2.8.1 into the existing local installation. All 539 biome files, the new splash and title matched their archive entries byte-for-byte. Required runtime modules, Tk support and the native DLL were verified (`.qa/archive-281.log`).

Installed and root executable SHA-256: `AFF85A9C21CE60075E1F30175BB7C0F2D78CF7590E4C64DF71F281B1DC3E7112`.

The existing Start Menu shortcut targets the installed executable with the correct working directory and Respawn Anchor icon. Both hotbars were preserved. Evidence: `.qa/guided-281-install-verification.json`.

Final root and installed smoke checks ran longer than 12 seconds and remained responsive; installed tutorial Next switched immediately. All exact-path test processes were stopped, with zero remaining. Evidence: `.qa/root-281-final-smoke.json` and `.qa/installed-281-final-smoke.json`.

Next: owner play-through and visual preference feedback; no pending implementation or release step for this request.
