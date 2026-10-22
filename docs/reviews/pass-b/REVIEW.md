# 2.9.9 Pass B review

Development only. The 2.9.9 interface, startup policy, installed/root executable,
Start Menu route and main branch are preserved. Cathedral UI implementation and
Pass C remain paused. This is an isolated review handoff, not an installed release.

Checkpoint 1: `ad6c2e1f`, design foundation and all seven selected UI cues.
Checkpoint 2: `2881e2bf`, world/cinematic work and bounded repaint improvement;
`1dc9f15b` and `e2147179` correct the packaged probe dependency and frame capture.
Exact source revision, artifact hashes and verification results are in
[evidence.json](evidence.json). The subsequent evidence commit changes no runtime code.

## Design and preservation

[DESIGN.md](../../../DESIGN.md), [AUDIO_DESIGN.md](../../../AUDIO_DESIGN.md),
[reference index](../../design/REFERENCES.md),
[review checklist](../../design/REVIEW_CHECKLIST.md) and
[asset register](../../design/ASSETS.md) separate preserved 2.9.9 rules from 3.0.
The missing Downloads image already existed in the repository; its unchanged
Variant D PNG is now tracked with its hash, palette and interpretation.

All selected WAVs remain unchanged in `Sounds/`, with byte-identical runtime
copies under `Assets/Sound Hub/ui/selected/`:

| File | Assignment |
| --- | --- |
| bootUp.wav | Launch once after audio is ready |
| shutDown.wav | Normal exit, bounded 320 ms playback tail |
| worldMap.wav | Map cover/reveal transition |
| save.wav | Confirmed successful manual write |
| error.wav | Actual failed/rejected operation |
| pressButton.wav | Ordinary UI activation |
| close.wav | Mouse/keyboard panel dismissal |

Piano_Ui (6)/(7) and SkywardHero_UI (13)/(14) remain unassigned in `Extra/`.
The selected-media ZIP round trip verifies all eleven originals. A second ZIP
verifies 40 presentation source/output/attribution files. Both backups are local
under `.qa/pass-b/`, not off-device protection. Private licensed media stay ignored;
tracked inventories retain hashes, known source/license terms and restore recipes.

## Implemented behavior

Semantic UI transactions suppress duplicate clicks, respect effects mute/gain,
reserve channels and preserve music. Map transition supports Escape and reduced
motion. Water/lava editing now uses bucket fill/pour recordings; comparator mode
changes click once; door interactions respect effects gain. The 464-entry material
audit resolves every non-air placement/break pool without missing recordings.

The temporary encounter uses eleven distinct recorded human voices, localized
contacts, inverse-distance attenuation and two quieter delayed reflection paths.
The shared impact timeline, shoulder anticipation and held weight transfer refine
the existing rig. Dark shared-vertex sea facets have restrained multi-directional
motion. Piano, older score and original source recordings remain intact. Skip is
visible and works by click or Escape in every introduction phase, restoring editor
world, camera, history and save path and releasing presentation audio/graphics.

## Verification and limits

Baseline: 503 tests passed. Final full regression: **525 passed in 391.35 s**.
The preceding full run exposed only the intentionally changed fluid sound contract;
the corrected test explicitly checks those two changes while retaining the old
digest for everything else. All 16 affected checks passed before the green rerun.
Compile and diff checks pass. Prepared tutorial data was rebaked, not bypassed.

Deterministic QA produced 83 editor and 63 opening captures, including 960x640,
1200x800, 1920x1080 and enlarged text. Representative images were inspected:
[editor](evidence/editor-library.png), [map cover](evidence/map-cover.png),
[Skip](evidence/encounter-skip.png), [sea](evidence/cathedral-sea.png).
Hidden Windows SDL/WGL checks use the AMD Radeon 860M. Two complete 44-second
motion captures at 960x640 and 1920x1080 include the final offline audition mix.
They are render captures plus offline audio, not speaker-loopback recordings.

The scalar/batch comparison is pixel-exact across two large worlds, four rotations
and two zooms. Matched repaint medians improve from 148.0 to 131.9 ms (Ocean) and
306.9 to 257.8 ms (Trial Chamber). This does **not** resolve end-to-end stalls:
the broader after-run is worse than the earlier run, with Ocean zoom max 702.2 ms
versus 645.7 ms. Preserve that negative result; do not claim a general speedup.
Sea refinement adds about 2.5 ms to matched FHD sanctuary p95 (14.08 to 16.57 ms).
Full encounter sampled p95 remains 29.05 ms, so 60 FPS is still an open hold.

Source and compiled native handoffs verify save/cancel/error, close, map and Skip;
the [compiled frame](evidence/frozen-encounter.png) exactly matches the source PNG,
with zero GL errors and [editor restoration](evidence/frozen-restored-editor.png).
Map activation still blocks 316–339 ms. Automated channel playback and a silent
native mixer probe are distinct from human listening approval. The offline mix
has peak 0.1583 and zero clipped samples; live acoustic quality remains unapproved.
The short shutdown tail, vocal treatment and reflection balance need owner listening.
Physical keyboard/mouse, trackpad and OS DPI behavior remain unverified.

## Local review artifacts

- EXE: `.qa/pass-b/package/BlocFantome.exe` (2.9.9). Its Assets junction uses this
  checkout's licensed media; it is a local review package, not a portable lone EXE.
- Installer: `.qa/pass-b/installer/BlocFantome_Review_2.9.9_PassB.exe`.
  Compilation validates required media and includes the selected/derived files.
  Installation remains held for owner review; it was not run against the installed app.
- Motion/audio: `.qa/pass-b/motion-1920/encounter-final.mp4`,
  `.qa/pass-b/motion-960/encounter-final.mp4`, `.qa/pass-b/encounter-audition.wav`.
- Backups: `.qa/pass-b/selected-audio-originals.zip` and
  `.qa/pass-b/presentation-recordings.zip`.

Listen for distinct boot/exit and close cues, single ordinary clicks, silent save
cancel, genuine save/error feedback, smooth map audio, mute at low/default levels,
quiet intervals, localized impacts, human vocal variety, and immediate Skip cleanup.
Repeat on headphones and speakers. Source/native/packaging evidence and exact
commands are indexed in evidence.json; full logs remain in `.qa/pass-b/`.
