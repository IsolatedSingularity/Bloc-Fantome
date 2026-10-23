# Owner Pass A: production editor review

Historical evidence. Local-only artifacts are recorded as paths; see the [recovery index](../../QA_ARCHIVE.md). Acceptance statements below describe that review date, not the current release.

Development branch: `codex/pass1-owner-review-2026-10-20`. Base: `120e619b`; canonical main remains `175686c2`. This is a bounded implementation with **performance and native-keyboard holds**, not an overall acceptance PASS. No Pass B, main promotion, installer, or installed-game replacement.

## Implemented

- Exact prepared painter orders now use immutable, shared pages. Edits replace affected cells and exposed neighbors instead of traversing twelve complete orders. Local opaque-terrain edits clear and replay overlapping painter layers inside conservative dirty bounds; glass remains composited in exact order. Camera changes finish a complete repaint instead of presenting a partially drawn plane. Initial tutorial loading retains explicitly separate staging/rendering work.
- Original texture sprites use area-filtered minification and nearest-neighbor enlargement, keyed by exact raster size in the existing bounded cache. Snow follows sampled exposed columns, including roofs and canopies, without accumulation or all-world height scans.
- Build/Library/World/Map sit on the left; Tools/Save/Menu on the right. Both navigation groups fade after four seconds, recover on movement/F1, and retain focus/gesture/modal safeguards. Hidden legacy hitboxes no longer capture canvas clicks. Always Visible, pinning, reduced motion and keyboard focus remain.
- Tools has independent command/reference scroll regions. Build uses paged icon/text category tabs, retains the full catalog/favorites/assignment/properties, and removes visible Recent and the redundant selected-material footer. Library uses real thumbnail tiles with separate preview and Open/Place. World uses rounded colored toggles, distinct action rows and small canvas controls; destructive shrinking requires confirmation. Minimap/coordinates default off and remain optional.
- Shared precise-wheel easing covers the workshop, Library, legacy libraries/biomes, inventory, history and Lab. The tour has 15 lessons, excludes the Redstone lesson, retains standalone Lab, and frames both welcome buildings without removing geometry.

## Performance: improvement and remaining hold

Windows SDL, native accelerator, 1200×800, scripted actions. [Before](before/frames.json) and [after](after/frames.json) retain every frame sample. The first edit in each scene was profiled and is excluded from the completion medians below. Other edits have only two samples; these are diagnostics, not robust tail estimates.

| Scene | Edit handler + complete repaint, median ms before → after | Worst sampled interaction render frame, ms before → after |
|---|---:|---:|
| Ancient City | 677.1 → 148.4 | 67.7 → 224.8 |
| Trial Chamber | 949.8 → 270.1 | 65.7 → 336.3 |
| Plains village | 1,281.4 → 68.1 | 386.1 → 406.1 |
| Ocean monument | 1,300.2 → 78.7 | 120.7 → 309.9 |

Unprofiled placement handlers fell from 177–345 ms to 0.6–1.2 ms. The Ancient City baseline profile spent 560 ms in prepared-order maintenance. Local replay helps eligible edits, but screen-plan traversal and full rebuilds remain expensive. **Atomic camera repaint increases the worst individual frame in these samples.** It removes the visible sweep, not the remaining stall. No performance gate is waived, and stable-frame averages are not acceptance evidence.

The separate [native tutorial report](tutorial/report.json) records prepared-file staging, activation, first complete image, and subsequent edits for welcome, snowy taiga, village and monument. Large lessons still incur substantial visible latency. Source loading samples used a cache warmed by the baseline, so their lower after-times do not establish a loading improvement. Chunk-local camera rendering remains a future bounded engineering task.

Final tutorial diagnostic, milliseconds (single visit; scripted native input):

| Lesson | Prepared staging | Activation | First complete image | Edit + render |
|---|---:|---:|---:|---:|
| welcome | 175.5 | 7.0 | 41.1 | 22.7 |
| snow | 317.3 | 2.9 | 230.4 | 96.6 |
| structures | 2205.9 | 28.4 | 671.4 | 377.1 |
| liquids | 3290.3 | 40.0 | 1161.7 | 719.7 |


## Verification and review artifacts

Final suite (local artifact: `full-suite.xml`): 475 passed. Python fallback (local artifact: `fallback.xml`): 27 passed. New regressions compare edited orders against fresh sorts across all modes/views, retain old snapshots, compare partial/full RGBA pixels in four rotations with glass, verify precise-scroll bounds/ownership, and exercise preview-only selection. Historical failures and logs are retained. Earlier failures were a missed staging conversion and obsolete progressive-render/16-lesson assertions; the replacement checks require complete interaction surfaces and preserve independent Lab/restoration coverage.

[Native matrix](native/matrix.json): 960×640, 1200×800, 1920×1080, 100/125/150% in-app text, map/Lab, and fullscreen/windowed camera equality. OS DPI stayed at 125%. [Tutorial/persistence checks](tutorial/report.json) verify stair facing/half through undo, redo and compressed save/reopen, then exact original-world restoration after tour scenes.

Actual OS mouse input: short footage (local artifact: `native/mouse-interactions.mp4`), [events](native/input-events.jsonl), [Library selection](native/os-library-preview.png), [active snow](native/os-world-active.png). Captures otherwise use scripted application actions. F1/Escape injection produced no SDL keyboard events; physical keyboard/precision-trackpad acceptance and other OS DPI scales remain unverified. The mouse footage predates the final cosmetic tile-icon polish. A QA logger error is retained separately; the corrected recording completed.

Visual entry points: [Build](native/catalog-1200.png), [Tools at 150%](native/tools-960-text150.png), [World](native/world-1200.png), [Library](native/library-structures.png), [quiet controls](native/quiet.png), [welcome](tutorial/welcome.png), [snow](tutorial/snow.png).

## Isolated playable handoff

Run `.qa/owner-pass-a/package/BlocFantome.exe` from this checkout. The folder contains its own review preferences/saves and an Assets junction to the existing licensed assets; it is **not a portable installer**. Opening/tutorial auto-start are disabled only in this isolated folder; both remain available from Menu. [Package identity](package.json), [source hashes](source-manifest.json), prepared-bundle bake (local artifact: `bake.log`), build log (local artifact: `build.log`), [final packaged World capture](native/packaged-world.png).

[Preservation](preservation.json) compares all 56 prior review targets: original media, root rollback executable, saves and settings. All match. The [installed executable](installed-check.json) also matches the preserved root rollback hash; its settings timestamps predate this QA session. The UI launcher initially resolved an explicit QA path to the installed app; process-path/time inspection caught this, all QA-created processes were closed, and the isolated executable was then launched directly and verified. That mistaken launch appended the installed diagnostic log. No Start Menu change was made. Final QA process count is recorded in `process-cleanup.txt`.

Local SHA256 manifests describe Windows QA bytes. Git may normalize text line endings; executable/media hashes are unaffected.

## Reproduce

Use the existing Windows Python 3.12/Pygame 2.6.1 environment and private assets. `tests/owner_pass_a_performance.py before|after` writes native scripted frame diagnostics. `tests/owner_pass_a_tutorials.py` verifies prepared tours and persistence. `tests/render_visual_checks.py OUTPUT --workshop` produces the matrix (`SDL_VIDEODRIVER=windows` for native windows). Bake with `Code/tools/bake_tutorial.py`, run pytest, and build with `Code/build_exe.py --output-dir .qa/owner-pass-a/package`. The archived interaction harness assumes its original `.qa/owner-pass-a/` location.

Sampling/input references: [Pygame transforms](https://www.pygame.org/docs/ref/transform.html) and [Pygame wheel events](https://www.pygame.org/docs/ref/event.html). Existing native Pass 1 captures were the visual reference; the Minecraft catalog and Segoe/charcoal design remain the basis.
