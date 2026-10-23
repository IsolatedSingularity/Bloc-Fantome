# Pass A-R implementation and evidence checkpoint

Historical evidence. Local-only artifacts are recorded as paths; see the [recovery index](../../QA_ARCHIVE.md). Acceptance statements below describe that review date, not the current release.

**Review build, not accepted main. Overall acceptance remains HOLD for camera/loading latency and owner artistic review.** The approved placement repair and UI revision are implemented. Pass B, audio/cinematics and creature replacement were not started.

Base: `c9573dcba74a954fd1e3b79433a59b54bc2dbe62`. Continue on `historical owner-review branch (20 October 2026)`; the commit containing this report is the single implementation checkpoint. Accepted main stays `175686c21649a8d37826f8a22850c85482a69fd9`.

## Status by evidence layer

| Layer | Result |
|---|---|
| SOURCE | Implemented; original world cells, source textures, assets and legacy behavior retained. |
| TEST | Final full suite: 485 passed. Focused Python fallback: 19 passed. Exact renderer comparison: 16/16 scene/rotation images identical. |
| NATIVE USER INPUT | Actual mouse placement succeeds in ordinary Monument and tutorial liquids; wheel zoom, Library navigation, World rain toggle and independent Hotkeys scrolling exercised. Keyboard injection did not reach SDL, so physical shortcut acceptance remains unverified. |
| VISUAL | Windows SDL captures at 960×640, 1200×800 and 1920×1080; 100/125/150% in-app text at narrow size. Actual OS DPI was 120 dpi (125%). Native fullscreen/windowed round trip captured. Owner aesthetic acceptance pending. |
| PERFORMANCE | Picking substantially improved; full repaint, initial staging and save/reopen still stall. **HOLD**, with tails reported below. |
| INSTALLED | Intentionally unchanged under this handoff. Exact isolated review EXE launched, Build navigated, and process exited 0. All QA windows closed. |

## Reproduced defect and bounded repair

At 989,663 cells, the ordinary `ocean_monument_1161` scene rejected an actual OS click because the adjacent cell was source WATER, hidden by the cutaway. The visible source was `(83,87,57)`, right face; target `(84,87,57)` existed but the AIR-only target rule returned nothing. [Baseline trace](baseline-click.json) and [image](baseline-click.png) preserve the failure. Its diagnostic copied/scanned the entire world; its 474/496 ms handler/frame numbers are instrument overhead and **not valid latency estimates**.

Cutaway placement now permits replacing captured WATER/BUBBLE_COLUMN only in a water-cutaway scene. Existing undo commands preserve the original block properties and liquid state. Ordinary water and unrelated solid-block rules remain unchanged.

The same actual click now changes that exact WATER cell to GOLD_BLOCK: handler 0.95 ms; event-processing start to completed render 81.64 ms. The liquids lesson actual click changes `(77,78,49)` WATER to OAK_PLANKS: handler 1.00 ms; completed render 104.98 ms. These are two individual observations, **not p95 or hardware-input-to-display latency**. Cursor delivery and compositor scanout are outside the timer.

[Native input evidence](native-input/clicks.json) includes cells and frames; [OS event log](native-input/input-events.jsonl) confirms delivered mouse and wheel events. The ordinary edit survives OS wheel zoom plus scripted pan, undo restores WATER, redo restores GOLD_BLOCK, and save/reopen retains GOLD_BLOCK. The tutorial edit survives scripted camera movement, undo/redo and [separate native reopen](native-input/tutorial-reopened.json). Undo/redo, pan, save and reopen were staged through application commands, not falsely attributed to OS keys. Ctrl+Z injection returned without SDL keyboard events; that tooling limitation remains a hold for physical keyboard verification.

Picking previously hit the paged sequence's indexed reverse fallback, generating millions of page-length calls. Direct reverse iteration plus a conservative projected candidate filter retains the exact reverse painter order and original alpha/model face test. Projection storage holds one draw order and two coordinate arrays, invalidated with the visible-order key/rotation. A per-repaint material raster cache reduces repeated captured-palette transforms without reordering cells or retaining stale frame content. Exact [pixel comparison](pixels/equivalence.json) covers four heavy scenes and all four rotations against the baseline renderer. This isolates the raster-cache optimization; it does not assert that the deliberately revised zoom sampling is pixel-identical.

## Performance and remaining tails

[Every sample](before/frames.json), [after samples](after/frames.json), [summary](performance-summary.json) and camera/edit profiles are retained. Each scene has 60 hover, 60 pan, 60 alternating zoom and 30 stable samples. p95 below uses nearest rank. Three edits are diagnostic only; the first is profiled and excluded from the two-edit ranges.

| Scene | Hover p95 before → after (ms) | Pan p95 / max after (ms) | Zoom p95 / max after (ms) | Unprofiled edit + render after (ms) |
|---|---:|---:|---:|---:|
| Ancient City | 473.8 → 0.22 | 148.1 / 233.6 | 26.3 / 142.9 | 132.7–135.2 |
| Trial Chamber | 768.3 → 0.21 | 327.7 / 385.7 | 2.9 / 271.2 | 277.0–283.0 |
| Plains village | 1709.3 → 10.61 | 309.6 / 387.1 | 2.9 / 299.3 | 90.6–91.1 |
| Ocean Monument | 825.6 → 0.77 | 215.4 / 284.9 | 244.6 / 462.0 | 94.8–100.8 |

Ocean cold hover reached 57.85 ms. Its first complete paint was 630.3 ms before / 477.1 ms after; rotation was 554.4 / 231.3 ms. Before pan max was 560.1 ms and zoom max 808.8 ms. Initial fit/paint is sampled once; fit is not independently characterized by a robust tail distribution. Alternating zoom often reuses warm surfaces, so low zoom p95 in other scenes does not describe arbitrary cold zoom.

**Comparison limitations:** before used a visible Windows SDL window; after used hidden Windows SDL. Later Ocean baseline samples overlapped the initial test run. File/derived caches also differ. These are diagnostic measurements, not controlled percentage speedups or proof of perceived smoothness. The baseline profiles independently identify the reverse-iteration problem; optimized profiles still show global world traversal/composition dominating cold repaints. No blocks were dropped, no stale completed image substituted, and no acceptance threshold relaxed.

[Prepared tutorial report](tutorial/report.json) separates staging, activation and complete paint. This run overlapped other validation and is not comparable as a speedup benchmark. Liquids staging was 6178 ms, activation 86 ms, complete paint the sum of its retained frame samples, and edit/render 1439 ms. Native reopening of the million-cell QA save took 18.3 seconds in the separate persistence check. These are additional **loading/edit/save-path holds**, not successes hidden behind handler timing. The existing progress/staging path remains. Prepared caches were rebaked and all 12 bundles are present in the EXE; old bundles remain locally in `.qa/owner-pass-ar/prepared-rollback`.

## UI revision and fidelity

Shared navy/translucent tokens, native Segoe typography, bounded antialiased corner buffers (12 MiB) and original scalable icon buffers (8 MiB) replace the prior green-grey treatment. No Microsoft font is bundled. Text is rendered at final size. Native source textures are unchanged: nearest sampling at normal/near zoom preserves source texels; far views below 50% use area filtering. [Near/normal/far comparison](zoom-comparison.png) documents the choice; it does not invent a texture pack.

- Build uses a genuine vertical icon/text category rail, all 464 identities, search/favorites/properties/hotbar routes, and a narrow two-step category gallery. Recent and the noisy footer are absent.
- World uses icon-only toggle tiles, tooltip state, semantic active animation and reduced-motion support. Dimension, generation, sky and destructive actions remain separate. The actual rain click and visible rain are captured.
- Library opens a detached illustrated four-choice palette. A 180 ms reciprocal rectangle transition expands into preview galleries; selecting a preview does not place or replace a world. Explicit Open/Place, import and cancellation remain. Actual mouse sequence (local artifact: `native-ui/native-input.mp4`) and [selection](native-ui/library-selection.png) show the result.
- Menu is grouped; Tools retains separate command/Hotkeys scrolling, right-inset glyphs, keycaps and italic descriptions. Native review caught and removed duplicated Undo/Home entries; final hidden-native captures reflect that correction.
- Colored terrain thumbnails return to grow/shrink/noise. Occupied-edge shrink now refuses with a small cue; safe shrink proceeds directly. The old clipping test was updated to verify refusal, preservation, then safe shrink and growth. Bottom-left identity/Unsaved/Fill prose is removed; internal save state and tool routes remain.

The four-second fade, any-motion recovery, F1/focus paths, hidden hitbox suppression, tutorials, Map and Lab remain covered by existing and focused tests. See [native matrix](native-hidden/matrix.json), [Build](native-hidden/build-rail-1200.png), [narrow categories](native-hidden/categories-960-text150.png), [World](native-hidden/world-960-text150.png), [Tools](native-hidden/tools-960-text150.png), [Menu](native-hidden/menu-960-text150.png), [Library home](native-hidden/library-home-960-text150.png), [quiet state](native-hidden/quiet.png), and [save error](native-hidden/save-failure-text150.png). World/terrain bright/dark captures are in `worlds/`. The duplicate dummy matrix remains local at `.qa/owner-pass-ar/visual-final`, indexed by [manifest](dummy-matrix-manifest.json).

The matrix uses real Windows SDL but hidden windows and scripted application state. It is not OS input evidence. Its fullscreen-named no-op frames are explicitly marked as bypassed; actual fullscreen/return frames are in [native-ui](native-ui/fullscreen.json). Periodic camera snapshots agree, but do not establish continuous center-drift accuracy. OS DPI 100/150/200%, physical trackpad gestures and physical keyboard shortcuts were unavailable in this run. No system display settings were changed while the owner used the computer.

References consulted: [Fluent layout](https://fluent2.microsoft.design/layout), [tokens](https://fluent2.microsoft.design/design-tokens), [typography](https://fluent2.microsoft.design/typography), and Pygame [transforms](https://www.pygame.org/docs/ref/transform.html), [gfxdraw](https://www.pygame.org/docs/ref/gfxdraw.html), [freetype](https://www.pygame.org/docs/ref/freetype.html). Apple HIG's page did not expose substantive content through the available fetch. Actual Ratchet & Clank (2002) interaction footage was not verified; the transition follows the owner's functional brief, not a claim of footage-based replication.

## Delivery, reproducibility and rollback

Review EXE: `.qa/owner-pass-ar/package/BlocFantome.exe`, version label 2.9.8. [Package manifest](package.json) records SHA-256, embedded modules, accelerator and prepared fingerprint; [packaged Build screenshot](packaged-build.png) and runtime log document exact-path native launch. Assets are a local junction to this checkout, so this is an isolated local review package, not a portable public distribution. Opening/tutorial launch preferences and saves are package-local.

Run the suite with `.venv/Scripts/python.exe -m pytest -q --basetemp .qa/pytest-ar-final`. Diagnostic entrypoints are `tests/owner_pass_ar_performance.py`, `tests/owner_pass_ar_pixels.py` and `tests/owner_pass_ar_native.py`; native harness starts hidden and accepts JSON staging commands in its isolated QA directory. Actual input must still come from a human or Computer Use. The first native harness's set-serialization logging failure is preserved in `native-harness-first.log`; the reusable harness serializes diagnostic metadata safely. Final suite/fallback/build logs and earlier negative runs are preserved separately.

[Preservation hashes](preservation-after.json): all 59 checked paths unchanged, including root/installed/prior-review executables, saves and media references. README and accepted main were untouched. Reverting this single checkpoint restores source; use the previous Pass A review EXE or unchanged installed app for binary rollback. Retain the old prepared bundle folder when restoring older source.

Branch audit found one worktree. The engineering-consolidation branch has no unique commits relative to this base; the research branch retains nine unique documentation commits. Collaborator dependence on existing remote names cannot be established from this checkout, and active owner handoffs reference the legacy name. Consequently no speculative rename/deletion was performed and no new branch was created. Neutral naming/consolidation remains a coordination hold under CONTRIBUTING.md; ignored local AGENTS.md remains intact.

**Remaining holds:** cold camera and loading/save stalls; physical keyboard/trackpad and other OS DPI targets; final owner visual/interaction acceptance; coordinated branch retirement/rename. No main promotion or installation acceptance is implied by passing tests.
