# Bloc Fantôme 2.9.9 implementation and evidence checkpoint

Owner-authorized continuation of Pass A-R, 21 October 2026. This checkpoint consolidates the generated artwork, restored previews/undoable resize, and final Library/Save/World Map revisions. It does not promote accepted main or begin Pass B, original-creature replacement, or borderless presentation.

## Delivered behavior

- Library toggles from the toolbar. Its Dimensions tile replaces the ambiguous Worlds label; child views have one back arrow and expand into a stable two-column gallery. Dimension selectors occupy the left rail. Selection never opens or places content until Open/Place. Transition content and hit regions stay inside the animated panel.
- World/biome previews trim capture margins and fill their tile, with centered cropping. Structure/build previews trim transparent margins while retaining the complete silhouette. All preview images remain clipped inside their cells.
- The owner-approved Structures arch, Saved icon and existing World/Tools art are preserved. New simpler monochrome art supplies Dimensions, Biomes and the three large dimension selectors; the owner specifically preferred cells 2 and 4. Original generation sheets remain unchanged. Seven sheets are verified inside the EXE.
- World dimension and Horror Rain actions leave their panel open. Active dimensions receive green/red/purple fills. Liquid controls retain their approved silhouette and add falling drops and spreading ripples. Reduced motion remains respected.
- The held-block preview is larger and anchored at bottom left. Grow/shrink/noise retain colored spatial hover previews; shrink is immediate and undoable. Modern editor grid, oversized status spacing and uneven button-corner shading are removed. Menu keeps its existing groups with clearer primary icon controls.
- First manual Save, including Ctrl+S, asks for a name/location. Cancel preserves the unnamed build and writes no file. Subsequent saves update the chosen file. Quick saves/autosaves retain their separate behavior.
- World Map starts with the viewport inside the projected landscape footprint, removing the exposed repeating/flat backdrop from the initial Overworld framing. Existing map geometry, textures and navigation remain.

## Verification and limits

The first full suite passed 502 tests. A subsequent transition-clipping regression was found during visual review and fixed; the final suite passed **503 tests in 477.74 seconds**, retained in [tests.txt](tests.txt). [transition-tests.txt](transition-tests.txt) covers the targeted interactions and animated bounds. Eight additional transition captures at 0/45/90/180 ms verified clipping at normal and enlarged text.

Hidden Windows SDL rendered a 79-state matrix across 960×640, 1200×800, 1920×1080 and 100/125/150% text, plus sixteen world overview/detail images across eight scenes. Selected current screenshots are in this folder; the complete matrix remains under `.qa/release-299/visual/`. This is scripted rendering, not native user input. Fullscreen was bypassed in that matrix; Windows DPI was 120 (125%). Other OS DPI settings and physical trackpad gestures were not verified.

Native packaged mouse input before the final clipping correction verified Library open/second-click close, first-save dialog appearance, and cancellation. The isolated saves folder remained empty. A keyboard attempt was interrupted by simultaneous owner input; it is not counted as a native keyboard pass. The installed Start Menu shortcut launched the intended 2.9.9 process and its loaded tutorial scene was inspected. Its transient startup window was replaced by the loaded SDL window, requiring one fresh window lookup. After installing the final clipping correction, binary hashes agreed and the Start Menu launch was repeated, but the owner stopped Computer Use with physical Escape before the final visual capture. Desktop interaction stopped immediately. Final visual reinspection is therefore a hold, not a claimed pass. Exact-path QA processes were closed afterward. Automated tests cover the Ctrl+S behavior separately.

The ten-minute hidden editor soak completed 60 cycles visiting Build/Tools/World and all Library categories, performing edit/undo/redo and checking save/read equality. Working set stabilized near 437 MiB after warmup. Its completion and memory samples are in [soak.json](soak.json). It began before the final transition-clipping correction; the correction has separate focused and full-suite coverage. The soak is a bounded stability check, not proof that every game state is error-free.

The large-world benchmark ran after the full suite and first packaging jobs completed, before the soak. It uses real Windows SDL in a hidden 1200×800 window, scripted inputs, 30 stable frames and 60 pan/zoom samples per scene. See [raw samples](performance-frames.json) and [summary](performance-summary.json). Existing cached-load conditions are not identical to prior runs, so these are current measurements rather than controlled speedup claims.

| Scene | Load ms | Stable frame p95 ms | Pan p95 ms | Zoom maximum ms |
| --- | ---: | ---: | ---: | ---: |
| Ancient City | 1694 | 5.3 | 130.7 | 128.8 |
| Trial Chamber | 2074 | 1.5 | 251.6 | 291.4 |
| Plains village | 6780 | 1.7 | 265.4 | 263.4 |
| Ocean Monument | 6295 | 4.8 | 195.9 | 420.0 |

**Performance HOLD remains:** cold camera/global composition, loading and large-save stalls are not resolved to the original acceptance targets. The placement repair and earlier native Ocean persistence evidence remain documented in `docs/reviews/owner-pass-ar/`. This checkpoint does not claim a new native Ocean playthrough or an exhaustive completed tutorial run. Final artistic acceptance and unavailable native keyboard/trackpad/DPI targets remain owner-review holds.

## Delivery and recovery

The complete installer is `Code/build/installer/BlocFantome_Setup_2.9.9.exe`; the isolated EXE is `.qa/release-299/package/BlocFantome.exe`. The installed app is `C:\Users\<user>\AppData\Local\Programs\Bloc Fantôme\BlocFantome.exe`. Root, review and installed EXE hashes must agree in [checkpoint.json](checkpoint.json). Start Menu target/icon/working directory are recorded in [shortcuts.json](shortcuts.json).

Root and installed prior executables were copied into `.qa/release-299/rollback/` before upgrading. Earlier review packages and installers remain. The preservation manifest checks saves, settings, source media and accepted main; only the explicitly upgraded root/installed EXEs may differ. No README edit or Git history rewrite was performed.

[Laptop reset checklist](../../LAPTOP_RESET_CHECKLIST.md) explains what must be copied. The detailed private filename inventory is local at `.qa/release-299/recovery-inventory.json`, with grouped sizes in `ignored-summary.json`; it records the pre-cleanup inspection. No recovery archive was created. Cleanup removed 568,336,736 bytes (542 MiB) across 44 untracked disposable test/build-cache directories after tests/builds completed, with path, tracked-file and junction checks. Its exact byte report is retained locally. Rollback installers, media, saves, references and evidence were retained.

Branch audit: one worktree, no open PRs, and the owner is the sole listed GitHub collaborator. Engineering-consolidation has zero unique commits relative to the active base. The research branch has nine unique commits and must remain. Neutral branch mapping and publication results are recorded alongside the checkpoint; accepted main stays at `175686c21649a8d37826f8a22850c85482a69fd9`.

References used for the incremental Menu/navigation pass: [Microsoft navigation design](https://learn.microsoft.com/en-us/windows/apps/design/basics/navigation-basics), [Xbox clear and consistent UI navigation](https://learn.microsoft.com/en-us/gaming/accessibility/xbox-accessibility-guidelines/112). These informed grouping and consistent back/selection behavior; no framework or wholesale menu replacement was introduced.
