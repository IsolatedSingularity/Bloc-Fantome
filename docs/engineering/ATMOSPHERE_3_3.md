# 3.3 atmospheric review candidate

Status: local owner review, not accepted or released. The installed/root 3.1
executables and Start Menu route are deliberately preserved. Version resources
remain at the accepted baseline until the release gate.

The owner accepted the 3.2 source with its documented performance limitations in
this chat. Its local rollback commit is
`7235d87f336601b73cedcd170019e1505fc427f9`, based on
`85b0f465500d48ac71dc49d11591b2669a56119a`. Both local commits were explicitly
authorized. Unrelated recovery/documentation work remains outside this commit.
The candidate commit identity and final preservation hashes are recorded in
`.qa/atmosphere-3.3/handoff.json` after committing.

## Changes and boundaries

`Code/engine/atmosphere.py` owns bounded rain particles, world-space contacts and
cached fog. Fine and middle curtains sit behind architecture; a sparse foreground
layer adds depth. The middle drops over geometry terminate on exposed top faces.
Roofs, raised blocks, slabs and water levels use actual height-index contacts,
not a default ground plane. The incoming head and splash share that location.
The contact projection rotates its local face coordinates with the camera.
Nearer geometry rejects hidden rear contacts through the same painter stencil.
Streaks and crowns have dark edges and restrained blue highlights for contrast.

Three density banks evolve independently, with different speeds, thicknesses and
openings. A quarter-size alpha stencil follows the existing global painter order,
including glass and cutouts. Its distance is rotated horizontal x+y, so a tall
foreground tower stays near. Fog density updates at 12 Hz, or 3 Hz with Reduced
Motion, independently of world traversal. Native bulk world blits are retained.
No source textures, sky atlases, world records or UI art are recolored.

The World lighting control enables the Overworld fog. Skybox-off works too.
Underwater scenes retain their established presentation; Nether, End, snow and
Horror Rain retain their own weather. Reduced Motion slows the decorative motion
and suppresses ordinary lightning. Contact crowns and water ripples supply the
wet response without adding a glossy material/shader system. Rain intensity and
wind ease toward irregular long-period targets.

Caps are 1,250 curtain particles, 512 contacts, five depth masks, 384 rain glyphs,
and 384 depth glyphs additionally capped at 4 MiB including retained source
sprites. Cached world sources are weakly referenced. Fog masks are reused across
frames and camera-offset resampling happens only when needed.

## Recorded audio

The supplied mapped Java `WorldRenderer.java` uses a local motion-blocking
heightmap for impact placement and separate sheltered `WEATHER_RAIN_ABOVE`
playback. The supplied `sounds.json` contains eight normal and four above-roof
variants. This informed local exposure and bounded surface sampling. The three
visual depths, material profiles, rolling fog and long intensity variation are
Bloc Fantôme enhancements, not claims about vanilla Java behavior.

The original stereo recording and Java rain recordings remain unchanged.
`Code/tools/prepare_atmosphere_audio.py` reproduces a 72-second natural stereo
bed with a sparse recorded-rain weave, plus three variants of six designed
material responses. These responses are filtered recordings, not new recordings
of stone, wood or glass. Processing uses mild spectral shaping and fades, with
no generated noise, pitch shift, compression or reverb. Masters are 48 kHz,
24-bit FLAC; runtime Vorbis uses quality 7 at the existing 44.1 kHz mixer rate.
Resampling is format compatibility, not a claim of added detail.

The runtime manifest records source/output hashes, gain, peaks, RMS, decoded
memory and boundary steps. Nineteen files total about 18.36 MiB decoded stereo;
the largest measured decoded peak is 0.6234, with zero clipped samples. The
first gain experiment failed headroom and was retained in the QA log; the final
recipe lowers linear gain rather than adding a limiter or relaxing the check.

The bed uses the existing weather pool 2–3. At most two scheduled material
responses use effects 8–23, with the existing virtual listener and panning.
Ambience/effects mutes remain authoritative. Music/UI levels and channel pools
are unchanged. The original first 30 seconds used by Horror Rain are verified
PCM-identical while avoiding decoding a second twelve-minute buffer.

The lossless listening aid at
`.qa/atmosphere-3.3/auditions/rain-comparison-and-materials.flac` is an **offline
mix**, with an exact timeline and gains beside it. It is not runtime loopback.
No Windows audio capture device was exposed by FFmpeg's device enumeration.
Live system-device startup/rain was exercised separately; headphone/speaker
quality, repetition, spatial impression and music masking require owner review.

## Evidence and acceptance

The `.qa/atmosphere-3.3` folder contains the complete source-test log/XML,
deterministic UI/world captures, before-candidate renders, final renders,
motion clips, audio recipes/masters, input benchmarks and sustained-loop receipt.
Negative intermediate performance/asset attempts remain distinguishable from the
final candidate. The final quantitative summary is in `handoff.json`.

Final validation: **702 working-tree tests passed**, including the pre-existing
3.2 regression/recovery tests. Both deterministic visual scripts completed.
The paired renderer checks matched every compared world frame across Trial
Chamber, Ancient City, Ocean Monument and the small baseline fixture. Active
rain placement/removal, exact undo and save/reopen passed in the courtyard on
both Rust and Python backends. Captures cover 960x640, 1200x800, 1920x1080,
day/night, four rotations, Reduced Motion and skybox-off. Motion clips include
clear, rain, fog, combined camera movement, and controlled light/heavy poses.
The latter use scripted 60 Hz weather time and are not physical-input recordings.

On Windows 11, Ryzen AI 7 350 / Radeon 860M, Python 3.12.10 and Pygame 2.6.1,
the five-repetition Trial Chamber comparison measured these medians (ms):

| Operation | Accepted 3.2 | Candidate |
| --- | ---: | ---: |
| Application-cold load | 6461.7 | 6265.6 |
| Cached load | 2912.7 | 3019.0 |
| Cold view rebuild | 129.5 | 129.4 |
| Fit | 6.2 | 6.4 |
| Placement | 132.5 | 132.0 |

Cached loading remains above target, and this sample is 3.6% slower than its
paired baseline. Clear stable render samples were 1.33/2.70 ms median and
1.64/5.47 ms p95 (baseline/candidate); these sequential stable blocks are not
evidence of unchanged frame cost. Both remain below the stable-frame target.
At 1080p, weather-update-plus-render p95 was 13.57 ms for rain and 11.00 ms
combined. These exclude the rest of the application's update work.

The actual loop ran 663 seconds, with 60 seconds warmup and ten observed minutes,
scene cycling and World Map roundtrips. Its p95 values were courtyard 13.54 ms,
Trial 12.68, Ancient City 15.26, village 14.22 and Ocean Monument **19.10 ms**.
Ocean remains a stable-frame HOLD. Recorded maxima include long synchronous
scene/map actions and reach 15.9 seconds; they are not hidden as steady-state
outliers. Early native review activity overlapped part of this soak; the separate
final rendering/input measurements ran sequentially without that activity.
Atmosphere-owned surfaces stayed below 9.64 MiB in the soak, excluding retained
source sprite references capped separately at 4 MiB. Whole-process RSS rose
across scene cycles (ending about 2.17 GiB, peak working set about 3.16 GiB);
this run does not establish a whole-process memory plateau or leak freedom.

The corrected package used real system-device playback, with rain/music busy
channels observed, opening cleanup and rain resumption checked, and SDL closed
on exit. Native mouse placement and isolated Save and Exit were exercised.
Native keyboard automation was inconclusive; scripted event checks passed.
The owner stopped Computer Use with Escape during the follow-up inspection, so
native UI checks stopped. The OpenGL opening's Pygame surface capture is black;
it does not establish the opening's visual acceptance.

The accepted baseline's cached-load, cold-rebuild and some interaction targets
were already failing. They remain HOLD targets: cached load <=1,000 ms, stable
full-frame p95 <16.7 ms, cold rebuild <100 ms, Fit plus first exact frame <250 ms.
The input benchmark alternates accepted 3.2 and candidate world-render methods
with identical shared dependencies and verifies exact world pixels. Its memory
is shared-process memory, not an independent baseline/candidate RSS comparison.
Atmosphere rendering measurements and actual-loop measurements are reported
separately. Scripted SDL input is not physical keyboard latency or scanout.

## Run the isolated review

Double-click `.qa/atmosphere-3.3/candidate/Review.cmd` from this checkout.
It uses the existing Python 3.12 environment, copied application source and
native DLL, and shared original media/world inputs. It is a local source package,
not a standalone redistributable EXE. Its preferences, saves and derived caches
live under `candidate/user-data`; the freshly baked tutorial accelerator is
under this task's QA root. The installed application remains untouched.
The review launcher starts the existing raised rain courtyard in daylight with
rain and lighting enabled. Running `launch.py` without `--courtyard` uses normal
startup instead.

Use World to toggle Rain and lighting, try the supplied rain courtyard or a
saved raised build, rotate/zoom/pan, and compare clear/rain/fog combinations.
Check the 64-second audio comparison using `auditions/timeline.json`, then listen
in the actual app with music, UI sounds, mutes and sheltered/open camera positions.
Review the village, Trial Chamber, Ancient City and Ocean Monument captures.

The single scratch root is `.qa/atmosphere-3.3`. Aggregate accounting retains
the 5 GiB limit. The owner explicitly authorized temporarily carrying forward
5,883,346 bytes for the same fourteen unreadable historical folders; any new
scan error still fails the gate. `budget-current.json` records accessible bytes,
that allowance, drive free space and the remaining limit. Shared original media
are unique inputs, not duplicated disposable files. No historical QA was deleted.

Stop here for owner visual, listening and functional acceptance. No push, final
tag/release, root EXE overwrite, installation or Start Menu edit is authorized
until the owner accepts this actual candidate.
