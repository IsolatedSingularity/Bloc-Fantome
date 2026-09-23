# Current baseline and inspection boundary

Repository: `IsolatedSingularity/Bloc-Fantome`, `main` at `0391259c5ebc0519feb324477fdc1f62bc66ccb7`. The observed commit is the 2.9.2 runtime-responsiveness release. This is the baseline for these notes, not a claim that every README statement was executed or validated.

## Observed ownership

| Area | Existing entry point | What the research established |
|---|---|---|
| Canonical circuit state and movement | `Code/engine/redstone.py` | Sparse circuit simulation, 50 ms logic step, 100 ms piston motions, interpolated moving payloads |
| Component geometry | `Code/engine/piston_models.py`, `model_renderer.py` | Existing Java-style model elements/UVs and explicit axis mapping |
| Electrical-only render reuse | `Code/engine/lab_render_cache.py` | Reuses draw lists while retaining painter order; geometry/camera changes require normal rendering |
| Tutorial session | `Code/engine/tutorial_runtime.py` | Snapshot/restore, staged lesson scenes, placement observation and existing progress events |
| Skybox | `Code/engine/skybox.py` | Software/native cubemap projection, cached views, independent drift and crossfade |
| Audio | `Code/engine/audio.py` | Predecoded sound backend, bounded preload behavior and ordered sequences |
| Integration / QA | `tests/render_visual_checks.py`, `tests/test_app_integration.py` | Relevant existing entry points located, not run |

Sources: [redstone](../SOURCES.md#b-redstone), [models](../SOURCES.md#b-models), [cache](../SOURCES.md#b-cache), [tutorial](../SOURCES.md#b-tutorial), [sky](../SOURCES.md#b-sky), [audio](../SOURCES.md#b-audio), [visual QA](../SOURCES.md#b-visual-tests).

## Important distinctions

This is a Python/Pygame 2.5D application with native CPU acceleration paths, not an empty browser renderer waiting for WebGL. Preserve its architecture. The current engine already includes substantial behavior and asset handling; this kit is not an instruction to rebuild them.

The tutorial runtime already stages scenes, clears temporary edit tools, tracks placement categories and restores practice state. It is a stronger starting point for a later cinematic/interactive gate than a second tutorial implementation. Existing skybox code is equally concrete: it expects a six-face atlas and has asynchronous preparation of projected RGB bytes. [Tutorial](../SOURCES.md#b-tutorial), [skybox](../SOURCES.md#b-sky).

Documentation includes historical release/QA material. The 2.9.2 handoff describes a 16-page tutorial; older 2.8.1 material described 27 pages. Neither count should be used as an architectural constant. Read current code before editing. Existing optional horror content is outside this research scope and remains untouched. [Handoff](../SOURCES.md#b-handoff).

## Known gaps, not inferred bugs

`Code/blocFantome.py` exists and is 1,092,830 bytes at this snapshot. Multiple connector reads returned metadata without its body, or an explicit size/unsupported-content error. The source was not empty. This blocked a complete trace from motion events into final application compositing. The downloader includes that exact pinned path so a local agent can finish the trace. [Path](../SOURCES.md#b-app).

Lighting implementation and native rasterization internals were not exhaustively inspected. Existing README feature descriptions are documentation claims, not measurements. No local build, gameplay session, screenshot comparison or performance run was performed. Recommendations below therefore specify diagnostics and acceptance criteria rather than declaring a discovered defect.
