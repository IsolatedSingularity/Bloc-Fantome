Bloc Fantôme 3.0 development candidate, Pass C, 22 October 2026.

Historical evidence. Local-only artifacts are recorded as paths; see the [recovery index](../../QA_ARCHIVE.md). Acceptance statements below describe that review date, not the current release.

Launch the isolated review EXE (local artifact: `../../../.qa/pass-c/package/BlocFantome.exe`). Keep it in that directory: its Assets junction uses this checkout. This is a local review build, not a portable distribution. The ignored `.qa` executable and local QA logs are not uploaded to GitHub; the source, measurements, representative screenshots and recordings are included here. [Package hash and contents](package.json), [source provenance](source-manifest.json).

Local `main` was safely fast-forwarded to accepted `2ea56e34`; its runtime baseline is `0a90d833`. Pass C source and review evidence are on `development`; 3.0 has not been promoted to `main`. Root/installed executables, shortcuts, owner data, README and original media were preserved. Cathedral Soft Blue is now reserved for 4.0; creature work remains deferred.

The original tutorial book is restored with a persisted white unread dot. Settings has no version footer. Goodbye has larger centered typography, preserved artwork/blocks/farewells, and immediate skipping without the hint. The cached atlas composition has contours, framing and a slightly turned compass, with reciprocal Back/Escape transitions. Library morphing now takes 240 ms and retains interruption/reversal.

Segoe remains the default. Native comparisons show [Settings](font-settings-960-150.png), [Library](font-library-1200-100.png), [Menu](font-menu-960-150.png) and [HUD](font-hud-960-150.png), Segoe left and Plex Light headings/Regular labels right. Plex is thinner and more distinctive; small labels remain legible at 960×640/150% without observed clipping. Regular/Text alternatives are in the [48-image matrix](matrix.json), with originals in `.qa/pass-c/visual`. The opt-in `BLOC_FONT_EXPERIMENT=plex-light` is reversible and preserves the wordmark. [Official IBM source](https://github.com/IBM/plex), OFL and exact font hashes are bundled.

Array rasterization preserves all 464 accepted sprite hashes. Reusable painter commands and flat projection columns reduce temporary-object allocation; garbage collection stays enabled. Zoom/rotation repaint yields between frames while retaining the complete fallback image.

[Startup measurements](startup-summary.json): packaged launch to first editor presentation was **7.91–8.10 s**, source 4.82–5.13 s. The common internal editor-ready marker improved from accepted 5.23–5.43 s to 3.77–4.19 s. These fresh-process runs used existing filesystem caches; true cold-disk startup was not measured. Historical 14.84 s is not a directly comparable control. Packaged medians separate pre-run initialization/imports/construction (3.53 s), texture discovery (189 ms), decoding (192 ms), sprites (292 ms), mipmaps (7 ms), sound loading (2.16 s), tutorial music (751 ms) and first-floor creation (0.8 ms). First-presentation gaps still reach 532 ms.

[Matched camera measurements](performance/summary.json) use four alternating measured repetitions after warm-up, the accepted painter method on shared assets, real edits/picking, and exact final RGBA equality at 1200×800. Worst zoom repaint frame:

| World | Accepted | Candidate |
| --- | ---: | ---: |
| Ancient City | 258 ms | 27 ms |
| Trial Chamber | 411 ms | 11 ms |
| Village | 576 ms | 12 ms |
| Ocean Monument | 147 ms | 11 ms |

Candidate zoom-frame medians are 8.8–9.2 ms. Work is spread across frames: median total zoom repaint changes from 112/231/235/146 ms to 120/253/220/160 ms respectively. Pan repaints still peak at 190 ms, edit repaints at 68 ms, rotation at 37 ms. These are painter timings, not whole-application frame times or input-to-photon measurements. Large-world fluidity remains incomplete.

[586 tests passed](full-suite.txt). Final native SDL [source](source.json)/[packaged](frozen.json) probes cover maps, cancellation, Library, resize, manual tutorial, save success/failure and Exit/Stay; [source](source-edges.json)/[packaged](frozen-edges.json) edge probes cover skips and safe worker shutdown. Scalar/array tests include alpha, clipping and wrapped UVs. Native mouse checks passed; injected keyboard navigation was inconclusive, while SDL keyboard-event tests passed. Physical keyboard/trackpad and human audio listening remain owner checks.

The atlas recording (local artifact: `atlas.mp4`) retains sampled presentation times across three Back/Escape cycles, five rapid cancellations and Reduced Motion, with world-state equality. Goodbye recording (local artifact: `goodbye.mp4`) and [final native capture](native-goodbye.jpg) show the preserved composition. Clips are silent, sampled at up to 30/15 FPS respectively, and do not establish universal frame-rate smoothness. Typography was rendered at 960/1200 widths and 100/150% text; Goodbye also at 1920. OS DPI was 125%; other OS DPI settings were not tested.

VSync remains honestly unavailable. Profiling identifies CPU raster/allocation work; it does not establish an alternative backend's benefit. No backend switch was justified without native input/DPI/stability evidence. Pygame's [display contract](https://www.pygame.org/docs/ref/display.html#pygame.display.set_mode) also does not guarantee requested VSync.

Reproduction uses `.venv/Scripts/python.exe`, `tests/profile_pass_c.py`, `tests/render_visual_checks.py --pass-c`, and the isolated startup driver `.qa/pass-c/measure_startup.py`. Final build/probe logs remain in `.qa/pass-c`; earlier failed and overlapping runs are retained, not counted as passing evidence. QA windows were closed.

This is the historical Pass C report. The [final 3.0 finishing review](../final-3/REVIEW.md) supersedes its font default, startup and window presentation.
