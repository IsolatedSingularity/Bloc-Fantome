# Bloc Fantôme 2.9.0 UI consistency handoff

Implementation and installation are complete. The owner approved the upgrade on September 12, 2026; the installed 2.9.0 executable matches the verified build byte-for-byte.

## Changes in this task

- Shared textured panel backgrounds, grey Minecraft button artwork with preserved borders, native-size Zekton labels, and consistent selection states in `Code/ui/chrome.py` and `Code/blocFantome.py`.
- One Library with Worlds, Biomes, Structures and Saved Builds tabs in `Code/ui/library.py`; shortcut help in `Code/ui/help.py`. Settings holds full volume controls.
- Tutorial, Biomes and Redstone Lab use shared panel/button rendering (`Code/ui/tutorial.py`, `biomes.py`, `redstone_lab.py`). Tutorial remains draggable and minimizable, with secondary actions under Options.
- Curated 37 biome specimens, at most two per family; all underlying captures retained. Background staging, four-view preparation, occupied-bounds rotation centering, cropped sprite caching and settled fluid handling improve loading and camera behavior (`Code/blocFantome.py`, `Code/engine/biome_capture.py`). Invisible expensive animations are skipped until needed.
- UI sounds follow Effects volume. Active audio group mute/unmute preserves channel pan (`Code/engine/audio.py`). Tutorial blank clicks are silent; lesson/runtime copy follows the consolidated navigation.
- Release version updated in `Code/blocFantome.py`, `Code/build_exe.py`, `Code/installer.iss`. Focused regressions added in `tests/test_ui_consistency.py`, `tests/test_app_integration.py`, `tests/test_audio.py`; visual coverage extended in `tests/render_visual_checks.py`.

README was not edited. Existing unrelated dirty work was preserved. Changes remain unstaged and uncommitted.

## Verification

- Full suite: **315 passed in 88.35 seconds**, `.qa/consistency-release-tests.log`.
- `compileall -q Code tests` and `git diff --check` passed; Git emitted line-ending notices only.
- All 37 curated biomes across four camera views: **148 views passed**. Data: `.qa/consistency-visual-final/biome_camera_performance.json`.
- UI captures at 960x640, 1200x800 and 1920x1080, including all 27 tutorial pages. Latest outputs: `.qa/consistency-release-visual/`.
- Local representative settled frame p95 approximately 6–16 ms; most measured prepared rotations 7–14 ms, heavier samples around 21 ms. Measurements are local samples, not a universal frame-rate guarantee. Data: `.qa/ready-biomes.json`.
- PyInstaller EXE build succeeded (`.qa/consistency-build.log`); Inno Setup compile succeeded (`.qa/consistency-installer.log`).
- Archive verification passed (`.qa/consistency-archive.log`): 539 biome files byte-for-byte, World Map data, splash/title assets, UI modules, native DLL and Tk runtime. Zekton is an external Assets font included by the installer, not an embedded EXE entry.
- Desktop packaged 2.9.0 QA: tutorial Next/Leave, restored previous build, Library/Biomes selection and explicit Open scene, Plains scene loading, on-screen E rotation, Settings and Redstone Lab rendering verified. App remained responsive for several minutes. Exact-path QA processes were stopped; zero remained.

## Remaining checks

- Real keyboard injection through the desktop helper did not visibly rotate the packaged scene; the on-screen control did. Actual Pygame KEYDOWN rotation regression passes. Physical Q/E keyboard verification remains advisable.
- Audio behavior has automated coverage; subjective listening was not verified.
- Installation and Start Menu verification completed September 12, 2026. Installer exit code 0. App and uninstall shortcuts were staged, copied and read back with correct target, icon and working directory; both targets exist. Launching the actual Start Menu app shortcut produced a responsive `Bloc Fantôme 2.9.0` window after 15 seconds. QA processes were stopped and zero remained. Evidence: `.qa/consistency-start-menu-290.json`, `.qa/consistency-installed-smoke-290.json`, `.qa/consistency-install-290.log`.
- `AGENTS.md` now records standing permission for app-specific release installation and Start Menu repair, and makes verified Start Menu launch a required handoff step.

## Artifacts

- `BlocFantome.exe` SHA256: `5BA0F8DA840B7F2DD381CCD466C0DF773CFDCF88E1495FC31085B5372C12DED6`
- `Code/build/installer/BlocFantome_Setup_2.9.0.exe` SHA256: `87BCC10EB3972DBCF09633EAB520510D6C84EEB6A6A88F35F44F14E720F12B9A`
