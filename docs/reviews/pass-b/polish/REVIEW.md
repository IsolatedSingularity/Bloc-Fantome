# 2.9.9 final Pass B polish

Runtime commit: `776692d2e485c9a0856c94384648506baf41d2cb`. Starting point: `52194d4c224f81048aae44aa68c9f103df71de0b`.
Development-only review candidate. [Exact changed files](changed-files.txt).

## Delivered behavior

Menu is a compact File/Edit/View/More command palette with Save/Open/Settings,
all prior commands and four expandable quick slots. Keyboard focus, shortcuts,
scrolling and save/error status remain available. Satin navy surfaces are slightly
more translucent, with restrained edges and native-size text.

Only **Library Dimensions** receives the generated white Overworld village and
End-island variations. The World dimension icons and Nether art are preserved.
Lighting and Clouds use the established generated white style, with cached face
illumination/ground shadow and independent cloud drift. Other tile animations
retain their roles; On/Off state and Reduced Motion remain authoritative.
[Native sizes](icons-native.png), [Library](library-1200-100.png),
[World](world-1200-100.png), [six-second motion study](tile-motion.mp4).

The original close recording is untouched. Its [400 ms derivative](close-short.wav)
has a 3 ms attack ramp and 150 ms cosine fade; [recipe and hashes](close-short.json).
Library opening and closing each use one cue. Button gain increases 0.80 → 0.90.
Boot retains the swamp painting/title with three small assembling forms during
actual loading. Goodbye is a distinct navy composition lasting 1.8 seconds with
300 ms music fade and immediate skip. Stay has initial exit-dialog focus; Escape
returns to the game. Save failure continues to retain the world.

Fresh Overworld terrain is grass and skyboxes default on when available; saved
choices remain respected. [Native fresh startup with Menu](fresh-editor.png).
The normal editor already had no version label; Settings retains it.
Map timing/music/unfolding/cancellation remain intact with small static cartographic
additions. VSync is accurately unavailable for the current native software
RESIZABLE display, not an ineffective preference. OPENGL/SCALED migration and
physical refresh verification remain Pass C work; see [Pygame's contract](https://www.pygame.org/docs/ref/display.html#pygame.display.set_mode).

## Verification

Focused checks: 51 passed in 18.99 s, then 12 final layout/icon contracts passed in 4.82 s. Full regression: **550 passed in 280.74 s**. [Test transcript](tests.txt).
The final suite is the only completed full run for this pass; earlier in-flight
runs were stopped for owner icon corrections and a status-layout correction.
Their partial logs remain in `.qa/pass-b-polish/` and are not counted as passes.
The tutorial accelerator was rebaked for the changed application fingerprint.
No unrelated cinematic assets or encounter evidence were regenerated.

[Visual matrix](visual-matrix.json): 960×640, 1200×800 and 1920×1080 at 100/150%
app text scale, bright quartz and dark obsidian stress scenes. These are QA scenes,
not changed defaults. Representative native captures were inspected for clipping,
legibility and icon consistency. OS DPI and physical input remain owner checks.

[Source probe](source-report.json) and [frozen probe](frozen-report.json) use native
Windows SDL and real events/channels, isolated settings/saves and muted audio.
They check fresh defaults, palette groups, cold/warm maps and Library, single
Library cues, failed/successful saves, Escape/Stay and explicit Exit. The separate
[native fast-exit check](fast-exit.json) took 42.5 ms including SDL teardown.
[Lifecycle/UI clip](lifecycle-ui.mp4) uses actual presentation timestamps with an
explicitly offline cue reference, not speaker loopback. Its [audio measurements](audio-reference.json)
show zero clipped samples; acoustic and artistic approval remain open.

| Measurement | Source | Frozen |
| --- | ---: | ---: |
| First splash / boot request | 35.0 / 37.0 ms | 32.6 / 34.8 ms |
| Editor ready | 5.069 s | 5.219 s |
| Map cold / warm | 1.264 / 0.569 s | 1.292 / 0.564 s |
| Library cold / warm max | 19.8 / 2.9 ms | 19.2 / 1.8 ms |
| Largest startup frame gap | 74.2 ms | 176.5 ms |

Previous finalization: editor 5.091/5.445 s; map cold 1.354/1.300 s and warm
0.569/0.552 s (source/frozen). No broad benchmark rerun was needed. The frozen
startup hitch remains a hold despite improvement from the earlier 205 ms gap.
Shutdown duration intentionally increases from 620 ms to 1.8 s with a fast skip.

These are local observations, not universal 60 FPS claims. Prior broad-render
holds remain: Ocean zoom max 702 ms versus 646 ms baseline; Trial repaint median
258 ms; encounter p95 29.05 ms; input queued briefly during large snapshot capture.
Those workloads were not rebenchmarked. No creature work was reopened.

## Review handoff and acceptance

Local review EXE: `.qa/pass-b-polish/package/BlocFantome.exe`.
SHA-256: `75be54287be6efb6e4171937bb372818bbd232538a9f31de3138caf923245c0b`. Its Assets junction points to this checkout; it is not a
portable lone executable or an installation. Root and installed EXEs remain
`68f6cb069801b2bc51a0cd2c427287dda86fbd352d7bec87a31c0a8d46ee5528`.
Main remains `175686c21649a8d37826f8a22850c85482a69fd9`. Saves, originals, backups,
previous candidates, README and shortcuts are unchanged. QA processes are closed.

- Accept Library-only dimension variations, preserved World icons, glass and
  compact Menu at normal/enlarged text; check quick slots and physical navigation.
- Check real OS DPI/resizing, enabled/disabled tile motion and Reduced Motion.
- Listen on headphones and speakers: short close, single Library cues, ordinary
  buttons against ambience, boot, 1.8-second Goodbye, mute and fast skip.
- Approve or reject this candidate before main/installation. After approval,
  2.9.9 may be finalized before Pass C. Pass C and Pass D remain separate decisions.
