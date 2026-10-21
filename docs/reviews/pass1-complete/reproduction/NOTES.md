# Reproduction notes

These are the exact QA/authoring scripts from `.qa/pass1-complete/`, archived as evidence. Their `parents[2]` root calculation assumes that original location: copy a script there before running it. Do not execute the archived path directly. Native scripts isolate saves and preferences; `final_native.py` uses scripted application actions, not OS-input automation.

- `final_native.py`: native enlarged tutorial/map/history/confirmation, compressed save/reopen, three fullscreen camera round trips.
- `native_review.py`: isolated interactive application harness. `command.json` changes are scripted and must be distinguished from mouse or keyboard input.
- `ui_latency.py`: 600 native drawer transitions; handler/render/flip timing, no device latency claim. Run without other QA/build jobs.
- `opening_capture.py`: Windows/WGL opening video and separate timed render interval; dummy audio. It requires FFmpeg.
- `run_performance.py`: inherited full-world benchmark, isolated cache, three large scenes, five repetitions at 1080p. Run without concurrent tests, rendering or encoding.
- `render_audio.py`: B4 recorded-source composites using installed SuperCollider 3.14.1, FFmpeg and NumPy. Keep the prior `docs/reviews/pass1-revision2/audio_study.scd` template at `.qa/pass1-revision2/audio_study.scd`. The four Sonniss source files and two original CC0 decoded source files remain local, at their recorded paths. Source URLs, hashes and license links accompany the auditions. No raw pack is included here.
- `prepare_piano.py`: creator chapter boundaries from the unchanged owner master and its `.info.json`; no master download or replacement. The existing master and selected chapters remain private local media.
- `assemble_review.py`: creates explicitly offline scene mixes and UI/piano auditions; copies selected native evidence. It does not capture live audio.
- `verification_report.py`: hashes the 56 preserved targets, changed source, prepared manifest, derived audio and isolated EXE. Requires the original local preservation manifest.

The six short UI cues remain in `Assets/Sound Hub/ui/workshop/`; their source families and credits are in `audio/UI_CREDITS.txt`, and exact runtime hashes are in `verification/derived-audio.json`. The original game recordings, original opening cues and owner piano master are not replaced. The build validates presence of every new runtime cue. No Microsoft Segoe font binary is copied or distributed.
