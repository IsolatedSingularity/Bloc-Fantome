# Bloc Fantôme 2.9.9: Pass B acceptance candidate

22 October 2026. Runtime: `0a90d833a5f49a83249ab1f5759bd7c5fe7859d4`, on `development`.
Supersedes the polish candidate for review; acceptance remains pending.

Local EXE: `.qa/pass-b-acceptance/package/BlocFantome.exe` (279,999,043 bytes).
SHA-256: `856d38b26d1fa4f8069319b9ff8cf306d0ffd363386705c31f8fa216329c36af`.
Its Assets junction uses this checkout. Keep the EXE in that folder; this is an
isolated local candidate, not an installation or a portable standalone package.
[Archive checks](package.json) verify the exact Night artwork and renderer module.

## Resolved

The three boot blocks jump left, middle, right during actual loading. Goodbye
reuses them right, middle, left, with lower, softer, slightly slower movement,
settling before the 350 ms fade. The aspect-correct Night composition lasts
three seconds and protects the moon and both figures. Eight farewell phrases,
static Reduced Motion and immediate any-key/mouse/window-close skips are retained.
The supplied file is actually `night.png`, a 2560×1419 PNG, preserved unchanged.

An early Escape during the 220 ms startup reveal reproduced old painting and
black margins inside exit confirmation: [before](exit-transition-before.png),
[after](exit-transition-after.png), [method and limitation](transition-reproduction.json).
This establishes one real transition defect, not every detail of the owner's
unrecorded sequence. Confirmation now captures the editor, confirmed Exit skips
another editor frame, and SDL remains alive until active workers finish.

The [tutorial control](tutorial-states-native.png) has shared dark-navy fill,
optically centered glyph, responsive dimensions, eight-pixel spacing, continuous
border, hover and keyboard-focus states. Old auto-launch preferences cannot open
the tutorial. Its manual dock remains available; fresh skyboxes stay enabled,
saved disabled choices remain authoritative, and the introduction stays manual.

Shared outlines now have consistent corner coverage. Tutorial footer and dialog
controls fit enlarged text. Drawer fades use elapsed time and reverse smoothly;
closing/replaced controls immediately lose stale hit regions. Library previews
clip to their visible panel. Reusable layers avoid repeated viewport allocation.

## Rendering investigation

History confirms native fullscreen surfaces in `98fc6485` and intentional nearest
sampling near normal zoom in `c34520df`. Neither fullscreen nor Windows DPI is
stretching a low-resolution viewport here. The avoidable defect was magnifying
already-projected 64×70 cube sprites, including their jagged geometry.

Opaque editor cubes above 1× now project original face textures at final output
dimensions, preserving nearest source texels, lighting, picking and cache limits.
Coverage antialiasing affects silhouette alpha only; definition lines remain one
output pixel. Overview/normal views, transparent and modelled blocks, and captured
Java atlases retain their previous paths.

[Native sampling comparison](sampling-comparison.png) includes blanket smoothing
for comparison only. Source textures are still 16×16; the renderer cannot invent
detail. Options remain preserving these textures, separately extending native
projection to models, or explicitly choosing a higher-resolution pack. None of
the latter options was silently applied. See the primary [Pygame transform
contract](https://www.pygame.org/docs/ref/transform.html).

Native source A/B screenshots use identical scenes and sampling settings:

| Display | Previous path | Candidate |
| --- | --- | --- |
| Window 1200×800, 2× | [before](window-zoom2-before.png) | [after](window-zoom2-after.png) |
| Fullscreen 1920×1200, 2× | [before](fullscreen-zoom2-before.png) | [after](fullscreen-zoom2-after.png) |
| Window 1200×800, 1× | [before](window-zoom1-before.png) | [after](window-zoom1-after.png) |
| Fullscreen 1920×1200, 1× | [before](fullscreen-zoom1-before.png) | [after](fullscreen-zoom1-after.png) |

## Verification and limits

[576 tests passed](full-suite.txt). Native [source](source.json) and
[frozen](frozen.json) checks passed startup/defaults, maps, Library, rapid reversal,
resize, manual tutorial, Reduced Motion, failed/successful saves and Exit/Stay.
[Source](source-edges.json)/[frozen](frozen-edges.json) edge checks passed: ordinary
skips 54–84 ms, worker completion before SDL teardown, and static Reduced Motion.
The first packaged attempt lacked its Assets junction; the repaired run passed.
An initial timing-verifier PNG write was moved after shutdown without relaxing limits.

The native UI matrix covers 960×640, 1200×800 and 1920×1080, text 100/125/150%,
bright/dark backgrounds. Contact sheets across all size/scale combinations and
representative full-size images were visually inspected. [Matrix](visual-matrix.json);
full originals remain in `.qa/pass-b-acceptance/visual-candidate`. OS DPI was
measured separately at 120 (125%); other OS DPI settings were not tested.

[Boot](boot.mp4), [interaction/resize](interactions.mp4), and [Goodbye](goodbye.mp4)
clips retain presentation timestamps. Captured frames are sampled at 15 FPS;
30 FPS export repeats frames. Audio is an explicitly offline cue reference,
not speaker loopback. Boot requests followed first flips by 0.89/1.28 ms
(source/frozen). Physical input and headphone/speaker listening remain owner checks.

Current frozen editor-ready time was 14.84 s; the unchanged
[previous EXE control](previous-build-control.json) took 15.94 s in this environment.
Recipe-enabled/disabled profiles both took 20.46/20.47 s with profiler overhead.
Historical five-second startup was not reproduced. Startup gaps remain 628 ms
candidate versus 690 ms control; no universal smoothness claim is made. Previous
large-world performance holds remain for Pass C and were not rebenchmarked.

Main remains `175686c21649a8d37826f8a22850c85482a69fd9`; root EXE remains
`68f6cb069801b2bc51a0cd2c427287dda86fbd352d7bec87a31c0a8d46ee5528`.
QA used isolated settings/saves. Installation, shortcuts, README, original media
and previous candidates were not changed. No Cathedral or creature work began.
