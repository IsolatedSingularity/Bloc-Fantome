# Pass 1 owner checkpoint, 2026-10-20

Historical evidence. Local-only artifacts are recorded as paths; see the [recovery index](../QA_ARCHIVE.md). Acceptance statements below describe that review date, not the current release.

This is an unaccepted development slice, not a finished Pass 1 or release. Baseline remains `ef6dae62a86a148bdf77d508e4e2422fe2ba5e02`. Changes are unstaged and uncommitted. The pinned browser specification and its five linked research documents were read; private working copies are in `.qa/pass1/research/`. No branch replacement, installation, README edit or creature change occurred.

## Owner decision

Review the upper-left stone workshop against the lower-left glass variant. Both are within direction A. The stone layout is preferred visually: the glass layout covers the build at 960x640. The stone card was reduced and its redundant heading removed. The entire established right palette remains during this review. Menu > Original HUD retains all existing canvas/advanced controls; Ctrl+Tab returns to the prototype. This temporary route is not the final migration.

- Stone, 1200x800 (local artifact: `../../.qa/pass1/refined/stone-1200.png`), glass, 1200x800 (local artifact: `../../.qa/pass1/refined/glass-1200.png`), stone with enlarged text at 960 (local artifact: `../../.qa/pass1/refined/stone-960-text125.png`).
- Fade, held gesture and fill-state video (local artifact: `../../.qa/pass1/refined/workshop-fade-gesture.mp4`). Scripted application events on Windows SDL; world revision and camera remain unchanged. Actual window DPI is 120 (125%). Images also cover 960x640 and 1920x1080.
- OS pointer verification: placed stair (local artifact: `../../.qa/pass1/native-placed.jpg`), side preview without activation (local artifact: `../../.qa/pass1/native-library-preview.jpg`), redo and isolated save (local artifact: `../../.qa/pass1/native-redo-saved.jpg`). Sky drove actual pointer input. Keyboard behavior has automated coverage but was not fully verified through OS input.
- Rise/ambience A in scene (local artifact: `../../.qa/pass1/audio/opening-A-offline-audition.mp4`), B in scene (local artifact: `../../.qa/pass1/audio/opening-B-offline-audition.mp4`), six UI cues (local artifact: `../../.qa/pass1/audio/ui-six-cues.mp3`). These are offline mixes over native video, not loopback recordings. A emphasizes direct masonry; B uses slower, more diffuse source treatments. Listening acceptance is outstanding.
- Piano chapter boundary at 258 s (local artifact: `../../.qa/pass1/audio/piano-boundary-258.mp3`), 470 s (local artifact: `../../.qa/pass1/audio/piano-boundary-470.mp3`), provisional cue sheet (local artifact: `../../.qa/pass1/audio/piano-cue-review.json`). The retained 1,952-second source has eight creator chapter markers; the runtime OGG contains chapter one only. Review clips expose boundaries. No claim of phrase-safe edits and no runtime playlist replacement yet.

## Source and tests

Opening cues now own channels 32 through 36. A real SDL mixer test reproduced paused editor channel 26 blocking the ambience, and verified the fix preserves suspended editor loops. Missing cue files are now reported. All nine current cues decode. This establishes a channel defect, not the cause of every owner-reported installed regression.

Corrected Java 1.16.1 constant light levels for Ender Chest, fire, soul fire and End Portal, plus red sand, bamboo and three coral sound groups. World propagation, rendered neighboring sprite shading, removal and undo/redo are tested. Soul-fire colored tint is a builder approximation, not vanilla colored lighting. All 465 catalog identities and coverage (local artifact: `../../.qa/pass1/catalog-coverage.csv`), exact differences and source hashes (local artifact: `../../.qa/pass1/catalog-differences.json`). Modern/stateful fidelity categories remain explicitly unverified.

The full suite passed 438 tests; after the last focus/preview routing refinements, the final relevant regression suite passed 82 tests. Initial four failures are retained in `full-tests.xml`: the deliberate selection contract, catalog fingerprint and two stale prepared-lesson checks. Original prepared lessons were preserved in `.qa/pass1/prepared-lessons-ef6dae62/` before regeneration. See `final-tests.xml`, `final-regression.xml` and the corresponding logs under `.qa/pass1/`.

## Native visual and opening diagnosis

1080p source opening (local artifact: `../../.qa/pass1/opening1080/source-opening-silent.mp4`) is silent. Matched GPU/software stills at 4.05, 18.05 and 26.05 seconds are in `.qa/pass1/opening-comparison/`. Both show sparse motes; software materials are flatter. Source opening geometry/effects match the engineering baseline and 2.9.8 source. No particle deletion was established. The historical installed/older-version comparison and hardware loopback audition are still unverified. The first wrongly sized capture in `.qa/pass1/opening/` is invalid 1080p evidence and is superseded by `opening1080/`.

## Audio provenance and limitations

SuperCollider authored the recorded-source studies offline. Direct/reflection stems, source hashes, cue timing, analysis and attribution are in `.qa/pass1/audio/`; originals are untouched. These studies use existing local preview recordings. They are not newly acquired full-resolution Sonniss recordings, and no subjective listening PASS is claimed.

The official Sonniss track list and license were inspected and retained. Selective ZIP range requests returned HTTP 403; the official Drive mirror presented a download warning. No bulk pack was fetched and no Sonniss audio is claimed. Human audition, stronger source selection, phrase/tail decisions, mono/low-volume listening and native layered playback remain necessary before final integration.

## Measured performance

Five alternating baseline/current runs used identical real scene data and produced identical preview pixels. Preview bounds now run in worker preparation; retention is byte bounded and content-aware, and abandoning a partial preview cannot starve subsequent selection. A first implementation added costly path resolution per slice; that was measured and removed.

| Preview workload | First display slice, before/after | Full display work, before/after |
| --- | --- | --- |
| Ancient City, 153,520 cells | 27.37 / 2.16 ms | 74.87 / 50.70 ms |
| Trial Chamber, 181,697 cells | 23.80 / 2.31 ms | 70.57 / 51.33 ms |

Worker preparation increased from 93.35 to 106.84 ms and 100.97 to 111.90 ms respectively. These are median processing measurements, not input-to-photon or cached-world-load results. Raw samples are `preview-performance-*.json`.

Three separate settled-cathedral 1080p WGL runs on Radeon 860M measured update/render/glFinish p95 11.98, 11.95 and 11.76 ms, with no samples above 50 ms. This is not whole-opening pacing acceptance. The inherited Ancient City/Trial Chamber 1-second cached-load holds and plains 9-versus-8-frame camera hold remain.

## Continuation boundary

Owner visual/listening direction is required before broad panel migration. Remaining work includes complete action/accessibility migration, pinned Library/error-state review, semantic audio integration, human-approved piano cuts, atmosphere redesign after diagnosis, native installed comparison, layered listening and broader latency/pacing evidence. Do not call this checkpoint completion of the overall assignment or silently accept these pending gates.

`preservation-after.json` verifies all 56 tracked preservation targets unchanged. Root and installed 2.9.8 executables retain SHA256 `b90eeba07012c3e1818aafcd4e275673fa66e3e59d0d3cd5221a12337da040c7`. No installed release was attempted.
