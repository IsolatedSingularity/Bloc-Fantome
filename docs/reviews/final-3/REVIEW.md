# Bloc Fantôme 3.0 finishing candidate

Historical evidence. Local-only artifacts are recorded as paths; see the [recovery index](../../QA_ARCHIVE.md). Acceptance statements below describe that review date, not the current release.

Stage A implementation and local review build, awaiting owner artistic acceptance.
Stage B has not started. Launch the review EXE (local artifact: `../../../.qa/final-3/package/BlocFantome.exe`)
in its existing folder; its Assets junction uses this checkout. It is not a portable
distribution. Main, root/installed EXEs, Start Menu, saves, README and owner `night.png`
remain unchanged. [Executable preservation](preserved-executables.json), [package](package.json).

IBM Plex Sans is now the default. The complete swamp painting and editor share one
floating window, with a direct fade. Cubes are 18% larger at unchanged centers;
ballistic descent transfers into finite compression/recoil, and Goodbye reverses the
order with softer motion. Reduced Motion stays static. A 28px navy title uses
SDL native drag/resize hit testing, real minimize/fullscreen/close controls and exact
floating geometry restore. F10 focuses title controls; arrows/Tab, Enter/Space and
Escape operate them. `BLOC_NATIVE_FRAME=1` retains the native frame.

World retains its accepted organization with translucent material, original white
masks and eight independent animations. The End silhouette is simplified. Settings
is a measured inspector with three audio sliders/mutes, compact preference switches,
separate Play Introduction and honest VSync text. Autoplay remains off.

Review the World recording (local artifact: `world.mp4`), [complete drawer](world.png),
[Settings at 960×640/150%](settings-960-150.png),
[Settings at 1200×800/100%](settings-1200-100.png),
startup (local artifact: `startup.mp4`) and Goodbye (local artifact: `goodbye.mp4`).
Recordings use actual native SDL presentations sampled up to 20 FPS with their
recorded timestamps; they are silent, and do not establish universal smoothness.
Static frames and contact sheets were inspected. Owner judgment of motion remains
an acceptance gate, not an automatic consequence of successful rendering.

## Audio and startup

SDL_mixer holds its playback lock while decoding compressed chunks, including the
roughly one-second rain MP3 load. Moving that work to a thread alone did not help.
OGG/MP3 now decode through SoundFile/libsndfile outside that lock; SDL still performs
PCM conversion and routing. Owner WAVs retain the original decoder and hashes.
The existing menu bed begins its fade during loading after 3.2 seconds. The
1024-sample mixer buffer and accepted channel ownership remain unchanged.

Windows output comparison (local artifact: `startup-listening.wav`): baseline source starts at 0.5s;
packaged candidate at 9s. Selection audition (local artifact: `selection-audition.wav`): original click
at 0.6s, new selection at 1.95s, new switch at 2.99s.
[Recipes/hashes](sound-variants.json) preserve their sources; [all accepted recordings](preserved-audio.json)
were rehashed unchanged. [Material audit](material-audit.json) found no missing
place/break routes among 464 block definitions and 106 loaded sound categories;
existing variability was retained without speculative remapping.

The baseline loopback has an approximately 1.02s near-silent interval during audible
boot material. Three source and three frozen fresh-process captures, plus a final-build check, have
no detected unexpected silence and no capture status errors. [Analysis](audio-continuity.json)
uses aligned mono 6kHz waveforms and 20ms RMS windows: output below 0.00015 where
the original exceeds 0.004. This is a dropout detector, not proof of musical quality
or the absence of every hardware underrun. Human listening remains required.

| Launch to first editor presentation | Pass C median | Candidate median |
| --- | ---: | ---: |
| Source | 5.32 s | 5.53 s |
| Packaged | 8.48 s | 8.96 s |

[Twelve fresh-process measurements](startup-timing.json), three per condition, used
existing filesystem caches and muted dummy audio. Candidate startup is slower by
0.21s source / 0.48s packaged; continuity is the improvement. True cold-disk behavior
was not measured. Audio recordings are separate real WASAPI loopback measurements.

## Verification and remaining gates

[603 complete tests](full-suite.txt), [source](source-integration.json)/[frozen](frozen-integration.json)
integration and [frozen shutdown edges](frozen-edges.json) cover save success/failure,
cancel, map, cinematic restoration, silent cancellation and safe SDL worker teardown.
[Source](source-native.json)/[frozen](frozen-native.json) native probes exercise all
eight toggles both ways, nine Settings size/text combinations, 1920×1200 desktop
fullscreen and exact restore. [OpenGL title checks](title-gpu.json) catch stale SDL
surface dimensions; the title now uses actual drawable dimensions and Skip stays
below it. Actual Windows DPI was 125%; application text scaling was 100/125/150%.

One intermediate frozen probe crashed after map restoration. Investigation found
temporary SDL Window wrappers in fullscreen restore and the probe: Pygame 2.6.1
stores a borrowed Python pointer in window user data. The application/probe now
retain those wrappers, including fast shutdown. A lifetime regression and repeated
native runs verify the repair. [Failure and recovery](native-recovery.json).

Source mouse checks verified native title drag, corner resize, fullscreen/restore,
minimize/return, World interaction and Exit/Stay/Goodbye. Packaged physical input
could not be completed: the Windows helper repeatedly returned `foreground window
did not report a process id`, including after refreshing the handle and relaunching.
Those QA processes were closed. Injected keyboard checks were inconclusive; SDL
keyboard regressions pass. Physical keyboard/trackpad, Snap, other OS DPI settings
and multiple monitors remain unverified. [Physical record](physical-checks.json).

The bounded culling/patch-bound optimization was rejected: exact pixels matched,
but timing did not improve. [Negative measurements](performance/summary.json) are
retained. [Final painter/culling AST equality](performance/retained-renderer.json)
confirms restoration to Pass C. Its roughly 190ms pan / 68ms edit peaks remain a
limitation; no renderer migration or performance acceptance is claimed.

Reproduce with Python 3.12, `requirements-dev.txt`, `Code/tools/bake_tutorial.py`,
`pytest -q --basetemp=.qa/pytest-review`, `tests/render_visual_checks.py OUTPUT --final-finishing`,
and `Code/build_exe.py --output-dir .qa/final-3/package`. Detailed raw captures,
failed attempts and timing drivers remain under `.qa/final-3`; concise evidence is
published here. [Source provenance](source-manifest.json).

References: [SDL hit testing](https://wiki.libsdl.org/SDL2/SDL_SetWindowHitTest),
[Pygame SDL window API](https://www.pygame.org/docs/ref/sdl2_video.html),
[Windows custom frames](https://learn.microsoft.com/en-us/windows/win32/dwm/customframe),
[SDL_mixer decoding implementation](https://github.com/libsdl-org/SDL_mixer/blob/SDL2/src/mixer.c),
[SoundFile documentation](https://python-soundfile.readthedocs.io/en/latest/).
The wrapper ownership check follows [Pygame's constructor](https://github.com/pygame/pygame/blob/2.6.1/src_c/cython/pygame/_sdl2/video.pyx#L212-L220)
and [event conversion](https://github.com/pygame/pygame/blob/2.6.1/src_c/event.c#L1233-L1238).

Owner acceptance must precede promotion to main, the rollback-protected root build,
verified installation and actual Start Menu launch. Those release steps are pending.
