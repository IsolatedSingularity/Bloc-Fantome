# Codex next-pass handoff: a coherent builder, accurate feedback and measured responsiveness

Updated 2026-10-20 after the owner's expanded research request.

Read [UI/performance research](../research/BUILDER_UX_PERFORMANCE_2026-10-20.md) and [fidelity/audio/motion research](../research/BUILDER_FIDELITY_AUDIO_MOTION_2026-10-20.md). This handoff is the execution entry point. Its updated scope takes precedence over the earlier narrower handoff and historical refactor/Ponder proposals. Research is not a release approval.

## Owner intent and current boundary

Build one excellent creative builder, with horror and light story around that core. Preserve all existing functionality, source assets, save compatibility and recognizable identity. Redesign the mixed UI into a quiet, contextual and discoverable interface. Keep the valued side previews. The browser specifies direction and judges actual rendered/listened results; Codex implements, tests, profiles and produces evidence. Do not substitute a generic mesh, two moving parts or test counts for artistic work.

The owner has reopened research/planning for sound coverage, source-derived block fidelity, Ponder presentation, the original reference creature and eventual modularization. They have not authorized interrupting the active engineering pass, replacing the installed app, silently merging experiments to main, a full Minecraft reimplementation or a broad monolith rewrite. The next builder pass is defined below. Creature integration and wholesale refactoring remain separate decisions; their detailed follow-on specifications are now available instead of being left to improvisation.

Published runtime baseline inspected by the browser: `175686c21649a8d37826f8a22850c85482a69fd9` (2.9.8). Research is on `docs/builder-ux-research-20261020`, not main. Recheck actual refs before beginning.

## Reconcile the current engineering pass first

Read local `AGENTS.md`, current branch/HEAD/status, the final engineering handoff and relevant tests. Preserve user changes, the original asset library, known-good executable and separated local creature draft. The owner reports archive verification, shadowed-definition removal, asynchronous-load extraction, undo/redo exception fixes, stale biome-load protection, atomic settings writes and temporary-session preference isolation. These are not independently verified published changes in this browser research. Inspect the final diff and preserve the fixes; do not restart the same audit or restore removed definitions.

Fetch and incorporate the docs changes without replacing newer engineering work with the older research baseline. Do not reset/clean/stash an active working tree as a shortcut. Reuse one coherent review branch; do not create a branch per tiny task. Historical `.qa` mutators are not current tools. Preserve source worlds, captures, research, licenses, audio sources and user data. No further untracking/cleanup is implied.

## Pass A: a real builder slice with trustworthy feedback

### A1. Baseline and fidelity map

Capture the current native editor, selected/active tools, Library, settings and tutorial at 960×640, 1200×800 and 1920×1080. Record actual Windows scaling and text size. Use the existing safe QA approach for saves/preferences; never restore an old config over later owner changes.

Inventory every existing clickable action, shortcut and mode-specific state, including less prominent building tools. Map each to a destination in the proposed UI. Record already implemented search/favorites/hotbar behavior rather than proposing duplicates. Keep all current capabilities reachable during migration.

Audit the FINAL resolved block/property/sound mappings, including later overrides. `tests/test_audio.py` already checks corrected chest, Ender Chest, deepslate and fire mappings. Do not patch an early obsolete table and claim a new runtime fix. Produce one compact difference/coverage report for the current catalog, distinguishing verified, source-derived, approximation, fallback, unsupported and missing-source-asset cases.

Recheck the published constant-emission leads against the reconciled checkout: Ender Chest, fire, soul fire and End Portal. Compare with version-matched local source/export data before changing them. Test the actual world-light path and rendered neighboring cells, removal and undo, not just catalog constants. Keep stateful emitters such as lit furnaces, charged anchors and powered lamps separate from constant emitters.

For sound, verify event identity, actual resolved sample assets and runtime action. Include red sand/bamboo/coral and deepslate/tuff families as targeted comparison cases. Placement/breaking/opening/closing/extension/retraction are distinct. A fallback sample is not a fidelity PASS.

Use existing reference/extraction tools first. Where a small offline runtime export removes manual duplication, pin the version, source hashes and exporter and keep it out of the shipped runtime. Do not silently choose the newest Minecraft installation. Preserve namespaces and resource paths; resolve sound definitions through the selected installation's indexed assets. Do not create a live Java sidecar, general mod framework or full-game simulator.

### A2. Working UI and sound direction

Implement a small shell around existing `ui.library.Library`, `ui.preview_browser.PreviewImages`, shared chrome/fonts and `engine/input_commands.py`. No duplicate browser, new GUI framework, second undo-command system or bulk extraction of `blocFantome.py`.

The slice must demonstrate the complete chain: choose a block, place it, change a contextual property, cancel a multi-step tool, undo/redo, open the Library, inspect a side preview, leave without replacing the world, save, reveal/pin controls and switch between Contextual and Always visible presentation. All existing functions remain accessible.

Use persistent labelled Build, Library and Menu routes, a visible Controls/Show controls action, selected material/tool identity and relevant save/error/loading state. Retain access to existing World Map, tutorial and lab without expanding their gameplay. Non-default mirror/fill/selection/structure-placement states must remain visible until resolved.

Use deliberate drawers and stable contextual options. Preserve side previews and explicit Open versus Place actions. Selection/preview never changes the editor. At small windows or enlarged text, reflow rather than making important text illegible. Maintain the project's block imagery and restrained textured framing, with consistent spacing, type and focus/selection states.

Start the review build with controls revealed. Pinning and Always visible use the same widgets/actions. A roughly 4-second idle delay and 150–200 ms opacity transition are prototype values, not fixed requirements. Never hide while hovering/focused, reading an explicitly opened panel, dragging, typing or completing a tool. Hidden controls cannot intercept input. Consume a whole UI gesture so it cannot become a world edit on release. Shared layout rectangles drive drawing, hit testing and focus. Reveal/hide must not recenter the camera, change tools or invalidate world geometry.

Implement the semantic feedback grammar in the new research document. Begin by auditioning focus/select/open/cancel/success/failure as a coherent family, then route material and mechanism events correctly. Trigger feedback from actual outcomes, once per action, whether mouse or keyboard. Silence blank clicks and unchanged state. Aggregate bulk edits, suppress repeated hover/invalid-operation spam and retain voice capacity for important UI feedback. Preserve existing mixer/channel ownership; do not add middleware.

Failed persistence must never produce a success cue. Routine autosave remains quiet by default. All important audio information also has a visual state. Retain current audio preferences and add independent UI feedback control only through the existing configuration path. Do not change the opening music, encounter mix or story audio as part of this pass.

### Pass A review gate

Run focused regressions and a real native walkthrough. Supply a compact capture set: quiet canvas, revealed controls, active tool, pinned drawer, selected Library preview, enlarged text, and loading/failure state. Supply a short motion capture of fade/reveal and pointer/focus behavior, plus a short labelled UI/building audio audition in actual context. No synthetic mouse helper result alone proves native behavior.

Pause wholesale panel migration for owner visual/usability and listening judgment. A static screenshot is insufficient for dynamic hiding; decoded samples are insufficient for sound acceptance. Do not install or promote an unaccepted prototype. Independent profiling and baseline reconciliation can proceed without redesigning a rejected candidate.

## Pass B: complete the accepted experience and remove measured stalls

After the owner accepts the direction, migrate the remaining controls using the same shell, action routes and sound grammar. Do not leave competing old/new menu systems permanently. Preserve the complete feature inventory and existing session restoration.

Correct benchmark semantics before claiming optimization. A single `_renderWorld()` invocation may only start incremental compositing. Measure dispatch/acknowledgment, staging/application, first useful image and a fully completed correct view separately. Require matching world/camera revision and final presentation, not just clearing a pending flag. The existing five-sample p95 calculation needs a documented estimator or relabelling; report raw samples and median/max for small cold samples, sustained p95/p99 for steady interaction.

Investigate measured costs, not every hypothetical optimization: UI-only invalidation causing scene rebuilds; preview-completion bounds scans on the display thread; cold drawing repeatedly restarted by animation; content-aware preview keys and bounded byte retention; stable shade/text/surface reuse; and true candidate-planning/indexing/compositing hotspots. Preserve staging ownership and reject stale results. Include marshalling/copying costs when comparing the existing native adapter with Python fallback. Keep Pygame presentation work on the display thread.

Discard slower or inconclusive complexity. Do not retry the reported rejected lighting optimization speculatively. Do not reduce scene contents, change timing rules, omit effects or weaken tests to obtain a PASS. No engine/GPU migration, process pool or new compiled subsystem without a demonstrated need and separate decision.

### Test and review matrix

| Area | Required evidence |
| --- | --- |
| Discoverability and coverage | An unfamiliar user can find a block, active tool, save, Library and Show controls. Every inventoried capability has a working route. |
| Visibility/input | Fake-clock/state tests plus native hover/focus/type/drag/pin/error behavior. No invisible interception or UI click-through. Contextual hints agree with the existing shortcut resolver. |
| Layout | Supported resolutions, enlarged text and actual Windows scaling where available; resize/fullscreen/minimize/focus return. Record combinations not exercised. |
| Editing/session integrity | Existing placement/removal/special blocks, brush/fill/mirror/selection/replace/blueprint/measurement and other tools; undo/redo; tutorial/map/lab return restores world/camera/hotbar/history/preferences. |
| Fidelity | Final resolved metadata and source-version comparison; correct sample/event selection; light/culling/shape behavior for the chosen cases; unsupported/fallback cases remain explicit. |
| Audio | No double trigger, false success, unbounded overlap or missing critical cue under saturation; mute/volume/mono behavior; large edit aggregation; actual contextual listening. |
| Loading/cache correctness | Save failure/cancel/stale completion preserves live data; cold/warm/edited views agree; painter order, picking, transparency and animation remain correct. |
| Performance/memory | First feedback versus full readiness, worst stalls, repeated browse/load/edit cycles, process/native footprint and relevant cache bytes. Python allocation traces are not total SDL/GPU memory. |

Extend existing targeted tests (`test_ui_consistency.py`, `test_input_commands.py`, `test_audio.py`, `test_app_integration.py` and relevant world/cache/load suites). Add small tests for real new boundaries, not a generic contract framework. Run the complete intended suite once the batch stabilizes, and again only when later changes/failures justify it.

Verify performance on the actual owner laptop, primarily at 1080p, not an assumed discrete GPU. Provisional goals remain a 60 Hz/approximately 16.7 ms frame budget, steady processing p95 ≤16.7 ms and p99 ≤25 ms, and UI acknowledgment within 100 ms at p95. These are targets, not achieved results or physical input-to-photon measurements. Report pacing/frame intervals separately and every >50 ms and >100 ms event. Use repeated unprofiled runs with exact commit, dataset, backend, versions, settings and power/background-load conditions. Do not benchmark during builds.

## Follow-on specifications, not automatic scope expansion

**Ponder presentation pilot:** The research provides an approximately 8-second isolated mechanism proof. Reuse current `PistonMotion` and source-derived geometry. Validate visible causality, carried blocks, connected rod/body, four views, replay/reset, sound markers and editor restoration. Do not build a second simulator, change vanilla timing to match Create kinetic pistons or reopen Redstone Map gameplay. Ponder code and Create resource assets have different license scopes; retain exact notices and use appropriate original/local assets.

**Creature proof:** The owner-supplied image is the reference. Preserve the current separated draft until inspected. The new research specifies substantial folded shoulder/trunk mass, tapered long limbs and an original four-contact interpretation, followed by a roughly 9-second weight-transfer/ledge/contact/contortion proof. First approve static silhouette at encounter distance, then actual motion, then separately authorize encounter integration. No automatic 44-second rewrite. Named authored poses plus constrained contact adaptation are required; sinusoidal limbs, synchronized stepping or numerical IK checks alone do not meet the brief. A downloaded rig is not accepted art or a verified NPZ import.

**Modularity:** Research now identifies catalog/fidelity, assets/audio, editor shell, world presentation and orchestration seams. Small changes required for the accepted builder slice may be proposed; a wholesale AssetManager/renderer/application extraction still requires approval. Preserve public exports, enum/save compatibility and source/frozen launch. No extracted system may import the entry point to recover its own hidden globals. Do not measure success by reducing lines or moving methods into mixins. Keep refactor and behavior/redesign changes separable.

The unclear dictated phrase "wall footage" is not a specified feature. Resolve it only if it becomes relevant; do not invent a new task from it.

## Delivery and release boundary

Keep one compact implementation record: actual reconciled baseline, changed responsibility owners, feature/fidelity coverage, measured comparisons, exact native captures/audio audition and remaining limitations. Distinguish SOURCE/TEST, NATIVE RUNTIME, VISUAL/USABILITY, LISTENING and INSTALLED RELEASE judgments.

No README rewrite, installed replacement or merge of unaccepted art into main is implied. After explicit delivery authorization, follow the existing root EXE/installer/Start Menu process and verify the actual launched version/path plus a real edit/save/reopen task. Preserve user data and the known-good executable. Keep accepted viable source on main and experiments isolated.

## Copy-ready next-chat instruction

```text
Finish and reconcile the current engineering pass before starting this work. Fetch docs/builder-ux-research-20261020 and read docs/handoffs/BUILDER_UX_PERFORMANCE_HANDOFF_2026-10-20.md plus its two linked research documents. Preserve current code, local AGENTS.md instructions, user data and the separated creature draft; do not replace the checkout with the research branch's older runtime baseline.

Begin Pass A: establish the current native/functional baseline, audit final resolved block/sound/light behavior against versioned source data, and implement the coherent contextual UI plus semantic-feedback slice described in the handoff. Reuse existing Library, input, audio, loading and simulation owners. Provide actual native visual/motion evidence and an audio audition for review before broad migration. Do not integrate the creature, broadly refactor the monolith, change the opening, replace the installed app or merge unaccepted work to main. Continue routine authorized work without repeated approval requests; honor the explicit visual/listening/release gates.
```
