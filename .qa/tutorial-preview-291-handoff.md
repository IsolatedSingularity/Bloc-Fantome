# Bloc Fantôme 2.9.1 tutorial and preview handoff

## Scope and implementation

The owner approved the direction after the read-only AGENTS/README/2.9.0 handoff and Git audit. Existing unrelated checkout changes were preserved. README was not edited; nothing was staged, committed or pushed.

- `Code/engine/tutorial_lessons.py`, `tutorial_scenes.py`, `tutorial_runtime.py` and `Code/ui/tutorial.py`: sixteen demonstration pages with no required tasks. Original editable scenes include a workshop, market, watchtower, terraced garden, bridge, gatehouse, colonnade, village, domed observatory, millrace, archive and hillside home. The panel uses the shared Minecraft artwork, native Zekton text, Back/Next/Leave, dragging and minimize/restore. Horror is a separate optional chapel detour on the final page.
- Terrain and biome pages use the actual bundled Flower Forest and Warped Forest captures. The dimensions page uses an entire source End City including its ship, retaining all 99,237 blocks from the source box instead of using a simplified tower. `Code/biome_captures/tutorial_end_city.json.gz`, its four atlases, capture material definitions and `Code/domain/blocks.py` preserve source End Rod, Dragon Wall Head and Brewing Stand cells. The regular biome catalog is unchanged. Source chunk/region hashes and capture evidence: `.qa/tutorial-city-source-291.json`.
- Tutorial load cancellation rejects stale results, cached snapshots are copied before editing, and the World Map excursion returns to the same page. Leaving the tutorial restores the original editor session.
- `Code/ui/preview_browser.py` restores separate right-panel Worlds/Biomes/Structures shelves, one expanded shelf at a time, with two previews per row, filters, pagination and a larger hover preview. Worlds/Biomes require explicit Open scene; Structures enter cursor placement. All fifteen bundled Worlds have actual rendered previews in `Code/world_previews/`. Saved Builds in the Library render previews asynchronously.
- `Code/ui/library.py`, `chrome.py`, `help.py`, `redstone_lab.py` and `Code/blocFantome.py` align headings, textured surfaces and measured native text with Blocks. The fixed tutorial/settings controls have reserved space, so scrolling controls cannot overlap them. Library descriptions and warnings fit at 960x640. `AGENTS.md` records UI consistency and real previews as release requirements.
- Loading workers prepare capture visibility; incremental canvas drawing and cached snapshots reduce repeated work. Mip selection avoids enlarging low-resolution sprites; a small opaque-cube edge seal closes low-zoom raster cracks without changing transparent/model silhouettes. UI text remains rendered at its final display size.
- `Code/build_exe.py` packages the new previews and runtime modules; application, build and installer metadata are 2.9.1.

## Verification

- Full suite: **321 passed in 105.27 seconds**, `.qa/tour-291-full.log`.
- After the final observatory, footer and text-layout refinements: **152 relevant tests passed in 63.90 seconds**, `.qa/tour-291-release-check.log`.
- `python -m compileall -q Code tests` and `git diff --check` passed. Whitespace log: `.qa/tour-291-diff-check.log`.
- New regression coverage in `tests/test_tour_preview.py`: stale loads, original-world restoration, World Map return, complete source city cells/four atlases, displayed preview hitboxes, explicit scene opening, structure placement, catalog separation, fifteen world images and the three tutorial navigation buttons. Related integration/public-contract tests updated for the demonstration tour.
- `tests/render_visual_checks.py --tour` generated **129 images**: every main page at 960x640, 1200x800 and 1920x1080, four camera directions at 1200, optional/minimized tutorial and all shelves/Library/Settings/Help. Evidence: `.qa/tour-291-release-visual/`. Representative builds, source city, galleries, small-window layouts and final sky dome were visually inspected.
- Final local rendering sample: settled p95 **1.84–8.94 ms** across 48 page/resolution cases. At 1200, first Flower Forest/Warped Forest/End City readiness was approximately **0.72/1.00/1.89 seconds**; longest loading frames were **241/502/468 ms**. Cached revisits were faster. These are local measurements, not a promise of instant loading or universal 60 FPS. Raw data: `.qa/tour-291-release-visual/performance.json`.
- PyInstaller and Inno Setup completed successfully. Archive verification checks **547 biome files byte-for-byte**, all fifteen World previews, new tutorial modules, native DLL, splash/title, World Map data and Tk runtime. External licensed Zekton font exists and is included by the installer. Logs: `.qa/tour-291-build.log`, `.qa/tour-291-installer.log`, `.qa/tour-291-archive.log`.
- Root EXE desktop QA confirmed 2.9.1 startup, tutorial Next/Leave, minimize/restore, real World Map navigation back to the same page, original editor restoration, Structures and Biomes shelves, larger hover image, selection without replacement and explicit Open scene loading Flower Forest. The root application remained responsive throughout. Desktop screenshots were inspected through Computer Use; source visual evidence is in the directory above.

## Deferred work and practical limits

- **Redstone Lab functionality is deliberately deferred at the owner's request.** It is excluded from the tutorial and retains one styled workbench panel. Its existing circuit behavior has not been represented as repaired. This is the next separate functional task when the owner chooses to resume it.
- Large first-time scene preparation still has a brief main-thread pause, measured above. Further work can split the remaining apply/warmup step while preserving exact source cells.
- Subjective audio listening and physical keyboard Q/E behavior were not verified in this pass; automated input routing and regression coverage passed. Previous handoff describes the desktop helper keyboard limitation.

## Release artifacts

- Root `BlocFantome.exe` SHA256: `6CF0D2B0A07B6D249B5A111818517E837D94D29830EDE31FBDEDE76ACCAFA541`.
- `Code/build/installer/BlocFantome_Setup_2.9.1.exe` SHA256: `EAB86440B9DB933B75A152016831EAFE90888388705E07B7375F7EA2122BAB61`.
- Installation completed successfully (exit 0). Installed EXE matches the root SHA256 and reports 2.9.1. App and uninstall shortcuts were staged, copied and verified for target, icon, working directory and target existence. The actual app shortcut launched a responsive Bloc Fantôme 2.9.1 window; Next advanced to the market page. The installed Zekton font and icon exist. All nine pre-existing config/save files remained byte-identical after installation and smoke. All exact-path root/installed QA processes were stopped; zero remained. Evidence: `.qa/tour-291-install.log`, `.qa/consistency-start-menu-291.json`, `.qa/tour-291-installed-smoke.json`, `.qa/tour-291-userdata-before.json`, `.qa/tour-291-root-smoke.json`.

