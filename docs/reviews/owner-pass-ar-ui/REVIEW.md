# Owner UI restoration and icon checkpoint, 2026-10-21

Review build: `.qa/owner-pass-ar-ui/package-v2/BlocFantome.exe`.
SHA-256: `6229eea74c0c3db04ae8e60168c832bd6c2599f4433f62d775a1175b41d6830e`.
This is an isolated local build with an Assets junction into this checkout. Keep it in this directory. Installed EXE, Start Menu, accepted main, saves and previous review builds remain unchanged, as requested for this review cycle.

The implementation is unstaged and uncommitted on the existing shared review branch at `c34520df`; no new branch or push. [Checkpoint](checkpoint.json) records source hashes, packaged art, accepted main and rollback EXE hashes. All [59 preservation checks](preservation.json) match the pre-A-R baseline. This checkpoint supersedes the earlier shrink-refusal and removed-block-description decisions in the A-R review following the owner's explicit corrections.

## Result

- Restored the original green grow, red shrink and blue terrain hover renderers, with cached transparent surfaces and dimension-only resize queries. Noise preview and click retain the same seed and protected terrain plan.
- Shrink applies immediately without confirmation or an empty-border refusal. Resize is now an Undo command, preserving cropped blocks, properties, fluids, structure/glass sets, metadata, app coordinates and preceding edit history. Undo/redo cycles are regression-tested.
- Restored held-block artwork, name and relevant facing/half information, anchored beside the hotbar at bottom left. No Unsaved/Fill/More footer was reintroduced. Quiet HUD and clean mode still suppress it.
- Removed the floating grid from the current editor and its controls/help; the original implementation remains available in the archived legacy interface. All previous icon source sheets and review EXEs are retained.
- Fixed the Saved tile/X overlap, standardized square close controls and navigation gaps, measured tooltip/toast height, and right-aligned compact canvas tooltips.
- Added generated white Tools symbols and bespoke Worlds/Biomes/Saved Library artwork. The crowned Structures arch and approved World action/toggle art are byte-identical. Rain/snow/flame and other active motion, plus reduced-motion behavior, remain covered. [Asset provenance](../../../Code/ui/art/provenance.json) preserves source generation names and hashes.
- Removed decorative Tools corner triangles and corrected rounded-control alpha coverage. Rounded edges now preserve one RGB color rather than filtering against transparent black and blending it again. Text stays at its final raster size.

## Verification

Final complete suite: [496 passed](final-full.log). Focused final checks: [36 passed](final2.log). [Build log](build-v2.log) records packaging success; all six PNGs extracted from the EXE match source bytes exactly.

Hidden Windows SDL captures cover 960x640, 1200x800 and 1920x1080, and 100/125/150% text. Inspect [editor](editor-1200.png), [Library hover](library-saved-hover-1200.png), [narrow Library](library-home-960-text150.png), [Tools](tools-1200.png), [large-text Tools](tools-960-text150.png), [World](world-1200.png), [Menu](menu-1200.png), [grow](preview-grow.png), [shrink](preview-shrink.png), [noise](preview-noise.png), and [measured error toast](save-failure-text150.png). These are scripted native-renderer checks, not OS input.

Real Computer Use mouse input on the packaged restoration build verified grow, immediate shrink, Menu Undo, terrain application and Library navigation. That build exited normally with code 0. The final package-v2 was separately launched by exact path; native navigation displayed the three new Library symbols and preserved arch, removed grid and anchored block card. Its close-button attempt was inconclusive during overlapping owner desktop activity. The QA process was then stopped by exact executable path, and zero matching processes remained. No user save was created or modified by these QA instances.

[Preview timings](preview-performance.json) use 61 calls per control on real Windows SDL. Ocean Monument contains 989,663 cells. First grow/shrink/noise preview: 10.23/10.03/23.76 ms; cached p95: 0.58/0.59/0.55 ms. These measure preview compositing only, not full-frame camera latency. Other background tests were running, so the figures are observations rather than an isolated performance gate.

## Remaining holds

- Owner artistic acceptance of the new Tools and three Library symbols.
- Prior A-R large-world camera/zoom and loading/save performance holds remain. This pass does not claim to resolve them.
- Native keyboard shortcuts were inconclusive while the owner was actively using the desktop. Engine/event regression tests pass; they do not substitute for a physical keyboard check. Final package-v2 graceful exit, fullscreen round trip, physical trackpad, and OS DPI matrix were not reverified in this follow-up. Fullscreen is explicitly bypassed in the hidden render harness.
- Installation/Start Menu promotion remains deferred by the owner. Pass B and original creature replacement were not started.

Local reproduction: `.venv/Scripts/python.exe -m pytest -q --basetemp .qa/owner-pass-ar-ui/pytest-recheck`; `.qa/owner-pass-ar-ui/render.py` and `performance.py` provide the hidden native harnesses. `checkpoint.py` verifies preservation and packaged assets. Existing prepared lessons were rebaked for the changed application fingerprint; the preceding bundle remains in `.qa/owner-pass-ar-ui/prepared-before`.
