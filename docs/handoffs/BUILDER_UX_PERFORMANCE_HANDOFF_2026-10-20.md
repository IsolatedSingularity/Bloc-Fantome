# Codex handoff: one builder, contextual UI, measured responsiveness

Date: 2026-10-20  
Status: proposed implementation handoff following owner scope decisions; not a release approval.  
Research: [builder UX, performance and architecture](../research/BUILDER_UX_PERFORMANCE_2026-10-20.md).  
Browser-reviewed published baseline: `175686c21649a8d37826f8a22850c85482a69fd9` (2.9.8).

## Mission and hard boundaries

Make Bloc Fantôme a more coherent, responsive creative builder with a quiet, contextual, discoverable interface. Preserve its identity, all current functionality and the owner's source assets. Keep one game and one editor/data model. The proposed UI has persistent labelled entry points, contextual working controls, deliberate drawers, pinning and an Always visible preference.

Do not work on the creature, reinterpret the supplied creature reference, change the encounter/opening, expand Redstone Map gameplay, migrate engines, add telemetry or split the product into modes with separate worlds/saves. Do not broadly refactor or extract `blocFantome.py`, move `AssetManager`, replace the renderer, or target a smaller line count. Limited application integration edits and cohesive new UI code are allowed by this design; subsystem extraction is not.

Do not interpret earlier refactor plans as authority to resume their deferred phases. README edits, installers, installed-app replacement and merging unaccepted UI into `main` are not authorized merely by this document. Follow the owner's current publication/release instructions and local `AGENTS.md`.

## Reconcile with the engineering pass first

The owner reports concurrent work on archive verification, shadowed-definition removal, asynchronous loading, undo/redo exceptions, stale biome completion, atomic settings writes and temporary-session preference isolation. The browser has not independently verified that unpublished local work. Preserve it, inspect its final diff and handoff, and test the resulting baseline rather than restarting the same audit.

Record the actual branch/HEAD, working-tree changes, runtime version, active Windows clone and applicable local instructions. Preserve user changes and the separated creature draft. Read the latest `docs/handoffs` records. Do not run archived source-mutating `.qa` scripts. Never force checkout, stash, clean or reset an active working tree to apply these documents. If their paths collide with local work, reconcile rather than overwrite.

This research is intended to be delivered as one docs-only commit on a separate research branch. Incorporate that commit after reconciling the engineering branch; do not merge its older baseline over newer engineering work. The docs branch is temporary, not a new long-lived development line. Reuse the current coherent review branch where appropriate instead of creating a branch per subtask.

## Pass A: baseline and a complete working UI slice

### Establish the player-visible baseline

Capture the current native editor, tool states, Library, settings and tutorial at 960×640, 1200×800 and 1920×1080. Distinguish historical repository screenshots from these current captures. Record Windows display scaling and actual text rendering. Preserve saves/configuration with the existing safe QA workflow; do not restore an old configuration over later owner changes.

Inventory every current clickable action, shortcut and special-tool state. Map each to its destination in the new presentation, retaining access to all existing features. Record existing search, favorites/recent-item behavior and hotbar functions before proposing additions. Do not duplicate a feature because it was missed during reconnaissance.

Use the existing large-world benchmark and targeted tests. Correct measurement semantics before comparing speed: a single `_renderWorld()` call may only start a time-sliced build. Measure first feedback and complete correct view separately, including the matching world/camera revision and final presentation. The existing five-sample p95 formula also needs an explicit estimator or relabelling; retain raw samples and median/max. Do not describe headless rendering as native end-to-end FPS.

### Implement the review slice

Build a small shell around current actions and the existing `ui.library.Library`, `ui.preview_browser.PreviewImages`, shared chrome/fonts and input resolver. No parallel content browser, UI framework or second undo-command system.

The working slice must support the full chain: choose a block, place it, use a contextual option, undo/redo, open a content browser, inspect its side preview, cancel without replacing the world, save, reveal/pin controls, and change between Contextual and Always visible presentation. All existing capabilities remain reachable during migration.

Recommended layout behavior:

- Persistent labelled Build, Library and Menu entry points, a visible Controls/Show controls action, selected material/tool identity and relevant save/error/loading state. Existing World Map and tutorial entry points remain accessible; their gameplay is unchanged.
- Contextual tool options in stable positions, including visible non-default mirror/fill/selection/structure-placement states. Do not hide an active operation or place an opaque card over its target.
- One intentional Library view with retained Worlds/Biomes/Structures/Saved Builds, a meaningful preview and explicit Open versus Place actions. Preserve current import and replacement protections. A preview or selection never mutates the editor.
- Pinning and Always visible use the same underlying widgets/actions. Start the review build with controls revealed. An approximately 4-second idle delay and 150–200 ms opacity transition are prototype settings, not fixed requirements.

Freeze visibility while a control is hovered/focused, a drawer is open, typing/dragging occurs, an operation is active or an error requires attention. Hidden widgets must not intercept input. Consume the whole UI gesture so a disappearing panel cannot cause a world edit on release. Reuse layout rectangles for rendering, hit testing and keyboard focus. Reveal/hide must not recenter the camera, rebuild the world or change the active tool.

Keep familiar textured accents and block icons, but unify spacing, typography, selected states and panel treatment. Preserve the side-preview idea. At small windows or increased text scale, reflow rather than shrink important text to illegibility. Use readable backgrounds and non-color-only states. Show actual contextual key meanings; preserve existing chords and Escape behavior unless a change is explicitly approved.

### Pass A evidence and acceptance boundary

Run focused regression tests for affected behavior and inspect a native walkthrough. Supply a compact capture set showing quiet canvas, revealed controls, active tool, pinned drawer, populated Library with preview, enlarged text and a long-operation/error state. Include a short recording of the fade/reveal and pointer/focus transitions. Static screenshots alone cannot establish correct contextual behavior.

Ask the owner to judge the real slice before completing wholesale panel migration. A technical PASS does not accept the art direction. Do not silently promote the prototype, replace the installed app, or continue into broad refactoring while waiting for that decision. Useful independent profiling and baseline documentation can continue without changing the rejected/unreviewed design.

## Pass B: complete the accepted presentation and remove measured stalls

After the owner accepts the UI direction, finish migrating the remaining controls using the same shell/chrome/action paths. Do not leave conflicting old and new menus as permanent interfaces. Preserve the full functionality inventory and existing session restoration.

Select optimizations from the measured bottleneck, not from this list by default:

- Prevent purely visual UI changes from invalidating scene/camera geometry or restarting incremental work.
- Investigate preview completion's main-thread bounds scans. If significant, return pure bounds data from the existing staging worker and keep Pygame presentation on the display thread.
- Investigate stable full-screen shade/text/surface reuse, preview source-version keys, canonical sizes and byte-budgeted eviction. Keep selected previews ahead of optional prefetch and avoid delaying an explicit world load behind background thumbnail work.
- Optimize a proven candidate-planning/indexing/compositing hotspot locally, preserving scene output. Include marshalling overhead when comparing the current native adapter with Python fallback.

One optimization should have one causal before/after comparison. Discard regressions and inconclusive complexity. The owner's report that a lighting change was slower is a reason not to retry it speculatively. Never make performance gains by omitting blocks, reducing capture fidelity, altering physics timing or weakening correctness checks.

### Test and review matrix

| Area | Required evidence |
| --- | --- |
| Discoverability | A user unfamiliar with shortcuts can find a block, tool, save, Library and Show controls. Labels and help reveal the same actions as the keyboard routes. |
| Contextual visibility | Fake-clock/state tests plus native interaction for idle, hover, keyboard focus, text entry, drag, active tool, pinning and error persistence. Hidden controls cannot consume world input; a UI click cannot leak through. |
| Layout and input | Native 960×640, 1200×800 and 1920×1080 checks; actual Windows 100/125/150% scaling where available; enlarged text; resize/fullscreen/minimize/focus return; correct hitboxes and focus restoration. Record combinations not exercised. |
| Editing | Placement/removal, stairs/slabs/doors, brush/fill/mirror/selection/replace/blueprint/measurement and other inventoried tools retain behavior and undo/redo. Button and keyboard routes agree. |
| Content and replacement | Browse/filter/select without mutation; explicit Open/Place; save failure and cancellation preserve current data; stale load/preview completion cannot affect a different session. |
| Existing sessions | Tutorial, World Map and lab return restores editor world, camera, hotbar, undo and preferences. Preserve the engineering regressions rather than claiming their fixes anew. |
| Visual/cache equivalence | Compare cold/warm/edited views, rotations and zoom. Confirm painter order, picking, transparency, lighting and animated content. UI cache changes must not alter source scene content. |
| Responsiveness | Separate feedback, staging, commit, first useful view, fully ready view and steady interaction. Record cancellation and worst stalls; do not sum unrelated timings into a fabricated speedup. |
| Memory | Repeat browse/load/edit/close cycles; record process/native footprint and relevant surface/cache bytes as well as Python allocations where useful. Verify bounded retention, not merely a successful cache lookup. |

Extend `tests/test_ui_consistency.py`, `test_input_commands.py`, `test_app_integration.py` and relevant existing cache/load tests. Add a small shell-specific test file only if it improves clarity. Do not introduce a general validation framework. Run targeted suites during iteration and the complete intended suite once the batch stabilizes; rerun when subsequent changes or failures justify it.

### Performance targets and truthful reporting

Verify on the owner's actual laptop, principally at 1080p. Use approximately 16.7 ms as the 60 Hz frame budget, with provisional steady processing targets of p95 ≤16.7 ms and p99 ≤25 ms. Record frame intervals and pacing separately, with all >50 ms and >100 ms events. Use sustained samples for percentiles, at least several runs, and all individual observations for small cold-operation samples.

Aim for local UI acknowledgment within 100 ms at p95, without disguising total scene-ready time. Record unprofiled timing and exact environment/dataset/settings. No simultaneous builds or heavy background tasks during comparisons. Profile to explain costs, not to manufacture comparative speed numbers. Failure to meet a target is a reported limitation, not permission to reduce fidelity.

Python/Pygame and the existing optional native adapter remain the baseline. Do not add an engine, general UI dependency, process pool, GPU migration or compiled subsystem without a separate demonstrated need and owner decision. Review current requirements after the engineering pass; do not assume the historical venv is reproducible.

## Delivery and approval

Maintain one compact implementation record with the reconciled baseline, changed responsibilities, preserved feature inventory, before/after measurements, native captures and remaining limitations. Keep evidence attributable to the exact candidate. Distinguish SOURCE/TEST, NATIVE RUNTIME, ARTISTIC/USABILITY and INSTALLED RELEASE outcomes. Do not cite test counts as proof that users can find controls or that the UI looks good.

No installed-release approval is conferred by this handoff. Once the owner authorizes delivery, follow the existing root EXE/installer/Start Menu procedure and verify the actual launched version and path, save/config preservation and a real build/edit/save/reopen interaction. Preserve the known-good executable until the candidate is accepted. Keep `main` as the accepted viable source, with unaccepted experiments isolated.

The full-monolith refactor remains deferred after this work. Document only the useful future seams and concrete coupling problems encountered; do not turn that note into an automatic next phase.
