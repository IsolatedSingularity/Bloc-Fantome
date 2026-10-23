# Pass B finalization: verified behavior and evidence

Historical evidence. Local-only artifacts are recorded as paths; see the [recovery index](../../../QA_ARCHIVE.md). Acceptance statements below describe that review date, not the current release.

## Scope and identity

Version 2.9.9, `development`, starting at
`e25a451edcbdd243fb63c52d3f406665f8abf2e8`. Application changes are in `39cef8ca`;
`ddea1e7c` adds the fail-closed native probe and is the compiled source revision.
The following evidence commit changes no runtime code. No deployment, main-branch
change, Pass C work, Cathedral restyle or original-creature replacement occurred.

## What changed

Boot is requested once immediately after the first swamp flip. Asset/audio loading
pumps and presents the splash; the editor handoff fades for 220 ms without a fixed
minimum loading delay. A failed audio device falls back to silent SDL playback.
Settings exposes **Play Introduction**; autoplay requires explicit opt-in and is
separate from guided tutorial preferences. The full cinematic and Skip remain.

The welcome uses the existing 18,598-cell sanctuary, close framing, sky and lighting.
The minimized tutorial is 8 px right of the lower-left preview, moving upward to
clear the hotbar. Skyboxes default on when available and explicit saved off survives.
World controls add a reversible 200 ms switch and On/Off text; Reduced Motion snaps.
Horror Rain now moves/renders actual particles, clears precipitation/loops on mode
and dimension changes, and caches haze/glows/columns. Its sound preparation uses a
bounded 30-second excerpt of the unchanged recording.

Map opening unfolds contour paper then reveals the actual map. Data, atlas and
music preparation run independently with cooperative blit batches, a two-entry
cache and safe cancellation/shutdown. Library Structures avoids save scans;
Saved Builds scans asynchronously; previews retain bounded source-image caches.

Save shows Saving… before capture. Independent immutable property values avoid
live references and duplicate objects. Capture pumps/presents progress, queuing
editing input until capture completes. A single worker streams v5 JSON through
gzip and atomic replacement, including autosave backups. Completion belongs to
the captured document/revision, so later edits remain dirty. Errors, canceled
Save As, overlapping requests and save-on-exit retain the world. v1–v5 loading,
undo/redo and backup behavior remain covered.

Free Escape and window close share the exit dialog; active tools/modals own Escape
first. Second Escape confirms, with Stay/Exit and dirty-only Save and Exit.
Shutdown crossfades the original swamp painting and preserves the selected WAV's
attack, then fades audio from 500 to 620 ms. Menu retains Save/Open/Settings and
adds clear command groups plus four occupied/empty Save/Load slot rows.

## Measurements on this Windows system

Python 3.12.10, Pygame 2.6.1, SDL 2.28.4, AMD Radeon 860M. Native windows are hidden;
scripted events are not physical input. Startup times below begin at `run()`,
excluding Python import and frozen bootstrap/unpacking. These are individual runs,
not statistical latency guarantees. Full records are in [evidence.json](evidence.json).

| Measurement | Source | Frozen |
| --- | ---: | ---: |
| First splash / boot request | 40.2 / 43.6 ms | 32.5 / 34.9 ms |
| Assets ready / editor ready | 3.875 / 5.091 s | 4.249 / 5.445 s |
| Startup presented frames / worst gap | 275 / 81.8 ms | 296 / 205.3 ms |
| Cold / warm complete map reveal | 1.354 / 0.569 s | 1.300 / 0.552 s |
| Map presented frames / worst gap, both visits | 110 / 43.7 ms | 106 / 41.5 ms |
| Library cold / warm maximum refresh + render | 20.2 / 3.6 ms | 18.4 / 1.3 ms |
| Actual Horror Rain frame gap maximum | 17.9 ms | 20.7 ms |
| Manual-intro probe shutdown total | 669 ms | 678 ms |

The previous 316–339 ms synchronous map activation has moved to worker preparation;
a diagnostic main-thread commit measured 3 ms. Total reveal now includes deliberate
220/320 ms transitions and preparation, so this is a responsiveness improvement,
not a claim that cold total opening is shorter. The frozen 205 ms startup gap occurs
immediately after the first splash; later measured startup gaps stay below 66 ms.
It remains an observed hitch. Library samples cover four tabs, three dimensions,
and cold/warm visits; save scanning itself runs in the background.

Save measurements use this OneDrive-backed checkout, not a claimed completed cloud
sync. The display pump isolates save cost from complex-world repaint cost.

| Build | Submission | Worker write | Frames during write / worst gap |
| --- | ---: | ---: | ---: |
| 576 cells | 2.8 ms | 6.4 ms | 3 / 8.2 ms |
| 102,400 cells | 1.3 ms | 573 ms | 105 / 6.5 ms |
| Actual Ocean, 989,663 cells/properties | 818 ms | 5.928 s | 1,071 / 40.3 ms |

Ocean capture takes 813 ms and presents 44 progress frames. Early finalization
measured 1,814 ms capture, 10.82 s write and a 196 ms write-frame gap. This negative
large-scene result prompted immutable-state interning and streaming. Input remains
queued during capture; writing allows editing. Round-trip block counts passed.

A separate instrumented 102,400-cell save plus backup took 1.502 s: two writes,
640 ms zlib compression, 341 ms JSON encoding, 175 ms record generation, and
2 ms atomic replacements. Buffered-writer self time was 39 ms; this is not physical
disk or cloud-sync latency. Profiling adds overhead and cumulative timings overlap.
Direct saves have no dialog delay. Scripted Save As cancellation performs no write;
physical native-dialog dwell/OneDrive UI latency is unmeasured. Backup failure,
partial serialization failure and destination failure preserve the original save.

## Visual and listening review

107 final deterministic captures cover 960×640, 1200×800, 1920×1080 and enlarged
text. Inspected captures confirm native-size text, complete exit/quick-slot labels,
scrolling, tutorial/hotbar separation, visible weather and dominant architecture.
[Welcome before](welcome-before.png) reconstructs the starting revision's scene,
wording and camera with the current renderer and its original sky/lighting flags;
[after](welcome-after.png) is the final scene. Menu/dock before images are preserved
Pass B captures. This comparison does not imply an exact baseline executable run.

Map clip (local artifact: `map-presented.mp4`) and startup/UI/shutdown audition (local artifact: `startup-ui-shutdown.mp4`)
use native source frames captured at up to 15 FPS after actual display flips, with
real elapsed durations. The app presented more frames than the recording samples.
The latter adds an offline reference mix at recorded cue onsets/channel interruptions,
with 50% effects and 0.72 headroom. It is not live speaker loopback. The separate
before (local artifact: `balance-before.wav`)/after (local artifact: `balance-after.wav`) 15-second references compare
all seven original cues over matched rain ambience. No extra UI recordings or
synthesized cues are assigned. Original selected hashes match source/frozen.

| Listen for | Before → after | Verification / acceptance |
| --- | --- | --- |
| Boot with visible artwork | After asset load → first splash | Native timing; owner listening open |
| Button and close clarity | Gains .48/.42 → .80/.72 | Real channel routing; reference mix |
| Map/save/error | .52/.50/.48 → .82/.78/.80 | Real map, confirmed write and failed path |
| Ambience balance | Bus 1.0 → 0.60 | Matched reference; effects/ambient mute tests |
| Shutdown attack | 320 ms tail → 500 ms + 120 ms fade | Native cleanup; owner device check open |
| Cancel/hover/typing/autosave | Silent → silent | Regression and native cancel checks |

Both balance references and the timed audition have zero clipped samples; peaks
are 0.137 before, 0.211 after and 0.223 timed. This does not establish live acoustic
acceptance. High-priority semantic cues may replace lower-priority semantic tails;
UI never steals the music bus. Low-volume/mute and ownership tests remain separate
from headphone/speaker approval.

## Verification, failures and remaining holds

**538 tests passed in 266.84 s**; compile/diff checks passed. Tutorial accelerators
were rebaked with the new architectural dependency. Source and frozen native audio
probes decode seven selected and fourteen derived sounds. Both manual-intro probes
advance phases for Skip/state checks, not a new real-time cinematic benchmark. They
report zero GL errors; their encounter and restored-editor PNG hashes match exactly.
The complete frozen startup/map/library/weather/save/exit probe exits successfully.

Earlier runs are retained in `.qa/pass-b-finalization/`: the first full run had
523 passes/9 failures (stale contracts, an autosave failure-status defect, stale
lesson bundles); fixes preceded the green runs. Profiling experiments that failed
are not performance evidence. The first frozen attempt lacked the Assets junction
and never reached the editor; its report is preserved separately and not counted
as validation. The final probe now rejects incomplete runs explicitly.

Review executable: `.qa/pass-b-finalization/package/BlocFantome.exe`, with a local
Assets junction to this checkout. It is not a portable lone EXE or installed release.
SHA-256: `2846ddb42e89ed8328f4489009ec0b093011605fcfcaa83f7920ffa73620771a`.
Root/installed rollback hashes remain
`68f6cb069801b2bc51a0cd2c427287dda86fbd352d7bec87a31c0a8d46ee5528`.
Existing backups and QA evidence remain intact; review processes are closed.

Open holds: physical keyboard/mouse/trackpad and OS DPI checks; speaker/headphone
balance, shutdown attack and artistic acceptance; the observed frozen startup hitch;
brief queued input during million-cell capture. Earlier broad-render holds remain:
Ocean zoom max 702 ms versus 646 ms baseline, Trial repaint median 258 ms, full
encounter p95 29.05 ms. This pass does not claim universal 60 FPS. Follow the approved
roadmap into Pass C only after this handoff, with original creature work in Pass D.
