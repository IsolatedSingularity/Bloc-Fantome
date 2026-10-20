# Bloc Fantôme: builder-first UX, performance and architecture research

Date: 2026-10-20  
Status: research-backed design proposal, not an implemented or artistically accepted release.  
Published-source baseline: `175686c21649a8d37826f8a22850c85482a69fd9` (2.9.8).  
Execution brief: [Codex handoff](../handoffs/BUILDER_UX_PERFORMANCE_HANDOFF_2026-10-20.md).

## 1. Owner decisions and scope

Build one excellent creative builder, with restrained horror and light story around that core. Do not split the product into separate builder, exploration and horror games. Different UI contexts may expose different controls while retaining the same editor, data model, saves and tools. Preserve the current opening and its identity.

A substantial UI redesign is welcome, but existing functionality and recognizable character must survive. The owner values the side previews in the world/terrain browsers, dislikes the mixed and contrived overall interface, and cites Horizon's contextual HUD as a behavioral reference. Minimal UI must not make controls impossible to find or test.

Architecture and performance belong in this pass. Broad extraction or refactoring of `Code/blocFantome.py` does not. New creature development, creature-reference interpretation, encounter changes, Redstone Map expansion, engine migration and a general-purpose UI framework are outside scope. Small integration edits to the application are necessary; moving large existing subsystems to new files is not authorized by this document.

The recommendations below are proposals unless explicitly identified as owner decisions. Numeric budgets and interaction timings are starting targets for testing, not measured achievements or universal usability laws.

### Concurrent Codex work

The owner supplied an in-progress local report describing archive verification, removal of shadowed runtime definitions, asynchronous-load extraction, undo/redo exception fixes, stale biome-load protection, atomic settings changes and isolation of temporary sky preferences. The report also says a measured lighting optimization was discarded and the creature draft was separated from engineering work. These are owner-provided reports, not changes independently verified on a published branch during this research pass.

At the initial remote recheck, only `main` was published and still pointed to the baseline above. Codex must reconcile its eventual engineering commit before applying this plan. Do not redo completed work, restore removed legacy definitions, disturb the local creature draft, rerun historical `.qa` mutators, or overwrite user changes. The installed application remains unchanged during research/prototyping.

## 2. Product direction: creation first, atmosphere second

The primary loop should be: find a material or structure, understand its placement, make an edit, inspect it, revise it, and save something worth returning to. The interface should support that loop with immediate spatial feedback and reversible actions rather than constantly asking the player to manage panels.

A useful design test is whether a first-time user can build a small recognizable object, repair a mistake and reopen the result without memorizing shortcuts. A useful expert test is whether the same interface supports rapid repeated placement, selection, mirror/fill operations and navigation without unnecessary clicks. Neither test needs resource grinding, new progression systems or another game mode.

Townscaper's publisher describes a deliberately simple, direct building toy [S3]. The transferable idea is a short path from intention to visible creation, not replacing Bloc Fantôme's detailed tools with automatic architecture. Preserve explicit block choice, special-block states, source scenes, undo and advanced editing. Do not infer that a successful simple toy proves advanced features should disappear.

Horror can later use architecture, environmental details and optional discoveries around this dependable creative activity. It should not make a real save failure, undo outcome, selected tool or destructive confirmation ambiguous. This is a proposed product boundary, not a new horror implementation task. No story system, creature or audio changes are part of this pass.

## 3. What the actual project already provides

All paths in this section refer to the pinned baseline, not an assumed future checkout. The earlier reconnaissance and this pass read the relevant source, tests and handoffs. Existing repository screenshots were inspected as historical visual evidence, not as proof of the currently installed UI.

| Existing owner | Verified observation | Consequence |
| --- | --- | --- |
| `Code/ui/library.py` | A shared `Library` already covers Worlds, Biomes, Structures and Saved Builds, including a selection list, detail preview and distinct activation paths. | Improve this browser. Do not introduce another unrelated content-library implementation. |
| `Code/ui/preview_browser.py` | Inline shelves use `Library`; `PreviewImages` shares previews, stages file data through the load executor and time-slices sprite drawing. | Consolidate presentation while retaining content providers and caching. Do not describe previews or incremental drawing as missing features. |
| `Code/ui/chrome.py`, `Code/ui/fonts.py` | Shared panel/button drawing and font helpers already exist. | Establish a coherent visual language here instead of adding a new UI dependency. |
| `Code/engine/input_commands.py` | Immutable input context, semantic commands and explicit Escape precedence already resolve several conflicting shortcuts. | Reuse this seam. Buttons and keys must reach the same existing action behavior. |
| `Code/engine/world.py`, `renderer.py`, `performance.py` | Modular world/projection/cache infrastructure exists alongside substantial application orchestration. `renderer.py` owns projection geometry, not the entire editor drawing pipeline. | Map ownership accurately. A renderer rewrite or a monolith line-count target would be premature. |
| `Code/engine/native_acceleration.py` | Optional native sorting and cubemap functions already have Python fallback routes. | Benchmark existing native and fallback paths before proposing another language or GPU backend. |
| `tests/test_ui_consistency.py` | Tests already cover modal click isolation, rendered slider hitboxes, rotation, cancelled loading, demand-driven animation and incremental render completion. | Extend these meaningful checks rather than replacing them with a new harness. |
| `tests/benchmark_large_world.py` | Existing measurements cover loads, rotation, fit, overview, edits, zoom and sprite-cache statistics. | Retain the benchmark, but strengthen what its labels actually establish. |

The examined `visual-checks/panel_controls.png`, `settings.png` and `tutorial_window.png` show several competing groups of controls and different presentation densities. They also show useful recognizable block artwork, framed controls and readable selected states. The tutorial capture predates the later handoff's lower-left arrangement; it must not be presented as a newly reproduced current defect. Obtain fresh screenshots after the concurrent engineering pass.

The 2.9.8 handoff reports a heavy tutorial page taking 5.38–6.77 seconds and maximum loading frames of 99–307 ms, while explicitly rejecting a controlled speedup or instantaneous-loading claim. These are historical reported results, not this pass's measurements. They reinforce the need to measure loading responsiveness separately from steady rendering.

### Concrete investigation leads, not invented performance diagnoses

`PreviewImages.get()` uses `(entry key, size)` for cached images and an item-count limit. Verify content-version invalidation, namespace collisions and actual resident bytes before changing policy; this inspection alone does not prove a visible stale-preview bug. When a file-staging future completes, the same method performs multiple bounds scans on the display thread before the approximately 2 ms drawing loop. That loop's budget therefore does not bound the entire completion frame. Moving pure bounds preparation into the existing worker result is a plausible small optimization to measure.

`Library.render()` allocates a screen-sized translucent shade during rendering. Reusing it for a stable size is a candidate, not evidence that it dominates frame time. Its benefit must be measured against retained memory. Preview generation also contains projection literals; verify proportions against the editor's actual metrics before claiming geometric preview equivalence.

The pinned runtime requirements list only Pygame and PyInstaller, while the opening source imports NumPy. The concurrent report already identifies dependency/reproducibility work. Reconcile that outcome rather than starting a competing dependency migration.

Repository evidence: [Library](https://github.com/IsolatedSingularity/Bloc-Fantome/blob/175686c21649a8d37826f8a22850c85482a69fd9/Code/ui/library.py), [preview browser](https://github.com/IsolatedSingularity/Bloc-Fantome/blob/175686c21649a8d37826f8a22850c85482a69fd9/Code/ui/preview_browser.py), [input commands](https://github.com/IsolatedSingularity/Bloc-Fantome/blob/175686c21649a8d37826f8a22850c85482a69fd9/Code/engine/input_commands.py), [native adapter](https://github.com/IsolatedSingularity/Bloc-Fantome/blob/175686c21649a8d37826f8a22850c85482a69fd9/Code/engine/native_acceleration.py), [UI regressions](https://github.com/IsolatedSingularity/Bloc-Fantome/blob/175686c21649a8d37826f8a22850c85482a69fd9/tests/test_ui_consistency.py), [benchmark](https://github.com/IsolatedSingularity/Bloc-Fantome/blob/175686c21649a8d37826f8a22850c85482a69fd9/tests/benchmark_large_world.py), [2.9.8 delivery record](https://github.com/IsolatedSingularity/Bloc-Fantome/blob/175686c21649a8d37826f8a22850c85482a69fd9/docs/handoffs/ARCHITECTURE_2.9.8_HANDOFF.txt).

## 4. Reference lessons and their limits

| Reference and evidence | Adopt for Bloc Fantôme | Do not import |
| --- | --- | --- |
| Guerrilla's official Horizon Forbidden West accessibility description permits control over which HUD information appears and when [S1]. The owner's reference was Horizon Zero Dawn; this later official account corroborates the configurable-HUD principle, not exact behavior of every Zero Dawn setting. | Contextual visibility with a persistent route back to controls and an always-visible preference. | Combat-specific HUD logic, copying graphics, or assuming hiding everything is good usability. |
| Territory Studio's original Zero Dawn contribution includes spatial UI concepts [S2]. Actual concept images were viewed. | Clearly associate contextual information with the object of attention; protect surrounding negative space. | Treating concept art as proof of shipped interaction behavior, dense holograms, or adopting its sci-fi visual identity. |
| Housemarque's Returnal UI/UX director describes information hierarchy around the player's attention [S4]. | Keep placement validity and active-tool state near the work; move occasional configuration away from it. | Bullet-hell warnings, pervasive glitch treatment, or omitting essential controls for cinematic cleanliness. |
| Factorio's developers describe consistent search across related views and the cost of expanding GUI scope [S5]. | Common selection/search behavior and a bounded migration with complete functional coverage. | Replicating Factorio's density, logistics systems or multi-year UI investment. |
| Microsoft XAGs cover text, contrast, input, navigation and focus [S6]. | Scalable readable text, visible focus, mouse and keyboard routes, stable navigation, and non-color-only state cues. | Claiming accessibility compliance from screenshots or assuming a keyboard-navigable menu establishes fully keyboard-playable building. |
| Pygame and Python document display, event, memory and concurrency behavior [S7–S12]. | Measure the real backend, pump events during work, preserve main-thread presentation, and distinguish dispatch from completion. | Assuming more threads or a faster isolated function necessarily improves player-visible latency. |

These references support design decisions; they do not establish that the proposed interface will be attractive or easy to use. That requires the native prototype and owner review described below.

## 5. Recommended interface: quiet, contextual, recoverable

### 5.1 Three levels of information, one application

**Persistent essentials:** a compact, labelled route to Build, Library and Menu; a visible Controls/Show controls action; the selected material/tool; non-default editing state that can change the next click; and unsaved/error/loading status when relevant. Preserve a small stable camera/orientation affordance. These elements should not require an undisclosed hotspot or memorized key to recover.

**Contextual working controls:** brush size, mirror axes, slab half, stair orientation, selection dimensions, placement/replace behavior and tool-specific confirmation. Show only relevant controls, but keep a stable position for a given tool. A structure-placement or fill operation remains visibly identified until it ends. Contextual means responsive to task state, not a toolbar that chases the pointer.

**Intentional drawers:** the block catalogue, advanced tool choices, the content Library, environment controls and settings. Open these explicitly. Preserve side previews as part of a deliberate browsing layout rather than a large unexpected hover card covering the build. Pinning keeps the chosen drawer open.

A scene can become visually quiet without creating a new Explore mode or copying the world. Existing World Map/tutorial/lab sessions retain their current isolation and return semantics; this pass does not redesign their gameplay.

### 5.2 Visibility policy

Offer `Contextual` and `Always visible` presentations of the same controls, not two separately maintained interfaces. Let the user pin the tools or Library drawer. For the first prototype and owner testing, start with controls revealed; validate contextual hiding deliberately instead of concealing unreviewed functionality.

| Situation | Required behavior |
| --- | --- |
| Quiet canvas, no active operation | Nonessential hints and expanded tool detail may settle away after an initial approximately 4-second delay. Persistent anchors and selected-tool identity remain. |
| Pointer over a control, keyboard focus inside a panel, open drawer or pinned panel | Keep that interface visible. Thinking or reading is not a reason to hide it. |
| Dragging, typing, slider adjustment, selection/fill/stamp preview or other multi-step operation | Do not hide, relocate or change the meaning of the active controls. Preserve pointer capture and active-state labels. |
| User selects Show controls | Reveal controls without changing the selected tool, camera, world, undo history or pending operation. Provide both a visible button and a conflict-checked keyboard route. |
| Load, save failure or destructive confirmation | Relevant state and recovery actions stay visible until resolved. A success toast can expire; a failure cannot silently disappear into contextual hiding. |
| Focus loss or resize | Clear stale held-input state; restore a usable, in-bounds UI and focus on return. Do not apply a delayed click to the world. |

Prototype fade timing around 150–200 ms, with immediate input response and a reduced-motion option. These values are hypotheses for visual testing. Do not use sliding geometry under the cursor. Hidden controls must neither intercept input nor remain invisible click targets. During a fade-out, keep the visible control interactive until hidden and consume its initiating gesture as UI input; never reinterpret that gesture as a world edit. Activation must not wait for the animation to finish.

Automatically fading an overlay must not resize the world viewport, recenter the camera or invalidate geometry. If a deliberately pinned layout changes usable space, preserve the chosen world-space camera anchor. Do not repeatedly auto-fit the world as panels open and close.

### 5.3 Information architecture and functionality preservation

| Destination | Responsibilities |
| --- | --- |
| Build | Block categories/search, hotbar and existing material-selection behavior; placement/removal/interaction; existing brush, fill, mirror, selection, replace, blueprint and measurement tools. Show non-default states beside the relevant tool. |
| Library | Preserve Worlds, Biomes, Structures and Saved Builds with a consistent list/grid, preview, metadata and explicit action. Expose existing imports here. |
| Scene/environment controls | Existing dimension, terrain, weather, lighting, sky and related display controls. Separate visual configuration from actions that replace scene data. |
| Document actions | Existing save, save-as, open, recovery/history and destructive canvas operations, with truthful outcomes. Undo/redo remain quickly reachable while building. |
| Menu and Controls | Settings, audio, help, tutorial/replay entry points and UI visibility preferences. Keep current World Map and other existing feature entry points discoverable without expanding their gameplay. |

This table is a destination map, not a claim that it inventories every current command. Before changing navigation, enumerate every existing clickable control, shortcut and mode-specific action, and assign its destination. Preserve documented and currently working capabilities, including less prominent special-block behavior. No capability may vanish merely because it did not fit a mockup.

Keep existing key meanings unless the owner explicitly approves a conflict resolution. In particular, the current resolver gives `F`, `M`, `Ctrl+B` and `Ctrl+H` different meanings according to context/modifiers. Derive displayed hints from resolved state rather than hard-coding misleading universal shortcuts. Do not seize Tab globally for HUD hiding if it is needed for keyboard focus.

### 5.4 Make the Library feel intentional

Retain the successful idea: browse on one side and understand the selected item on the other. Use the existing Library as the canonical model, and make any compact shelves another view of the same selection and activation rules.

A selected item gets a stable large preview, name, type and concise provenance. Distinguish captured Java scenes, source-informed generated terrain and placeable structures without exposing a wall of engineering metadata. Preserve real source fidelity and user assets. A terrain generator is not the same operation as opening a captured biome.

Use clear action verbs: `Place structure` means a cancellable placement preview in the current build; `Open world`, `Open biome` and `Open build` mean replacing the active document after its existing unsaved-work protections. Selection and preview never activate a replacement. A failed save or cancelled dialog must leave the old world intact. Reuse the concurrent engineering pass's safe loading/commit path.

For common desktop widths, retain two columns. At the minimum supported window or enlarged text, reflow into a list plus a deliberately opened detail view, rather than shrinking text or truncating the action. Keep the back route and selected entry. Search/filter/scroll restoration should be per tab when useful; do not rebuild content unnecessarily on a purely visual transition.

Prioritize the selected preview, then visible thumbnails, then at most a small useful prefetch. Closing the browser must make outstanding work harmless. Empty, loading, cancelled and failed states need distinct labels and retry behavior where applicable. Never show a fake progress percentage.

### 5.5 Visual identity

Retain recognizable block imagery, crisp geometric framing, restrained dimensional color and the project's atmospheric setting. Reduce the visual competition between heavy texture backgrounds, repeated bevels, dense shortcut text and unrelated panel treatments. Prefer one panel family, one spacing rhythm, consistent focus/selected/disabled states and a small number of deliberate type sizes.

Use quieter surfaces behind body text while allowing textured accents and characteristic block icons to carry identity. Do not turn the game into a generic productivity dashboard, nor paste a holographic Horizon interface over Minecraft-derived assets. Avoid dynamic blur as a prerequisite; it adds cost without resolving hierarchy.

Review text at its final rendered size, not after scaling a low-resolution screenshot. At minimum, assess standard informative text against a 4.5:1 contrast target and large text against the applicable 3:1 target from XAG 102, checking the actual rendered background [S6]. Icons, labels and outlines must communicate active/disabled states without relying on color alone. Font size choices require native-size review and configurable scaling; a nominal font size is not a measured glyph height.

### 5.6 Onboarding and mastery

Make the existing tutorial reachable and replayable without turning routine building into a mandatory lesson sequence. Preserve authored lessons and their source scenes. New contextual help should answer the immediate question: what tool is active, what the next click will do, and how to cancel or undo it.

Use brief optional reminders and a consistent Controls surface. Do not repeatedly cover the placement region with unsolicited explanations. Track usability locally during review through tasks and observations; this plan does not authorize analytics, accounts or telemetry.

## 6. Performance: measure responsiveness and completion separately

### 6.1 Tighten the benchmark before trusting new numbers

At the pinned baseline, `cold_render()`, `rotate()` and related measurements time calls that can start incremental drawing without waiting for `_worldSurfaceBuild` to become `None`. Existing UI tests explicitly loop until that state clears. Therefore those benchmark timings alone do not establish time to a complete new view. Similarly, a timed `_render` call does not by itself include the complete input/update/render/present lifecycle.

The percentile expression is `ordered[max(0, int(n * 0.95) - 1)]`. With five ordered samples `[1,2,3,4,5]`, it selects 4; the nearest-rank definition selects 5. With 90 samples, it selects rank 85 instead of nearest-rank 86. Either adopt and test a documented estimator or relabel the metric. More importantly, report all five cold samples with median/max rather than treating five observations as a robust tail estimate.

Keep separate timings for dispatch/acknowledgment, data staging, main-thread application/indexing, first useful visible result, complete correct view, and steady interactive frames. For completion, require the requested world/camera revision, successful final draw and appropriate presented-frame evidence. Clearing a pending flag alone is insufficient. Record cancellation latency and the longest unresponsive interval as well.

Headless SDL measurements remain useful for repeatable CPU regression checks. They do not establish Windows presentation smoothness, native input behavior, GPU cost, DPI correctness or installed-build behavior. Use unprofiled runs for comparative timings; Python's profiler documentation explicitly distinguishes profiling from benchmarking [S10].

### 6.2 Representative workload

Measure a small editable build, an existing medium scene, the bundled Ancient City/Trial Chamber cases where available, and a heavy captured tutorial scene. Include cold process startup, application-warm loading, first view, repeated panning beyond the cache margin, four rotations, cursor-centered zoom, fit, a bulk edit followed by undo/redo, and opening/searching/closing the Library. Test before and after an edit invalidates cached state, not just pristine bundled scenes.

Record exact commit, dataset/content fingerprints, Python/Pygame/NumPy/native versions, source versus packaged execution, SDL/display backend, viewport, actual Windows scaling, render distance, visual settings, AC/power mode and background load. Distinguish a fresh process from a truly cold OS filesystem cache; do not call both cold without qualification. Do not benchmark during packaging or other heavy jobs.

The target machine remains the owner's Ryzen AI 7 350/Radeon 860M class laptop, not an assumed discrete GPU. Verify the actual test machine. Use 1080p as the principal performance target, with 1200×800 and the supported 960×640 minimum for layout and interaction checks.

| Proposed target | Qualification |
| --- | --- |
| 60 Hz steady interaction; approximately 16.7 ms frame budget | Record processing time, frame intervals, pacing/wait and stalls separately. This is not a claim of locked 60 FPS. |
| Steady processing p95 at or below 16.7 ms and p99 at or below 25 ms in representative supported scenes | Use several sustained runs and retain samples; report every over-50 ms and over-100 ms event. A good percentile does not erase a bad visible stall. |
| Local UI/selection feedback within 100 ms at p95 | Measure event receipt to the corresponding rendered/presented feedback. This is not physical input-to-photon latency. |
| Visible acknowledgment of long operations within 100 ms; cancellation remains responsive | Report full ready time independently. No universal subsecond promise for very large scenes. |
| No unbounded cache/memory growth during repeated browse/edit/load cycles | Establish a baseline and byte budgets before choosing limits. No arbitrary process-memory ceiling is asserted here. |

If current scenes exceed these targets, report the miss honestly and improve the measured bottleneck. Do not shrink scene content, remove effects without authorization, change timing semantics or weaken tests to produce a PASS.

### 6.3 Optimization order

1. **Eliminate avoidable repeated work.** Check whether UI transitions, animation, hover or unrelated settings cause world replanning or repeated cold-build restarts. Separate presentation dirtiness from scene/camera/content dirtiness. Retain complete content and painter/picking equivalence.
2. **Keep long work interruptible.** Stage pure data off the display thread where appropriate; apply it through the existing session/revision ownership checks. Bound display-thread preparation and compositing slices, including work outside the existing inner drawing budget. Worker cancellation is not guaranteed once execution starts [S11]. A late result must be rejected safely, not merely hoped away.
3. **Manage preview and surface lifetime.** Test content-aware keys, canonical preview sizes, byte-budgeted eviction, selected-item priority and reuse of stable UI surfaces. Derive memory cost from actual surface pitch/height and avoid double-counting shared buffers. Supplement Python allocation snapshots with process/native memory observations; `tracemalloc` is a Python-allocation tool, not a complete SDL/GPU memory meter [S12].
4. **Optimize a proven hot kernel.** Only after profiling identifies one, compare a local algorithmic change or the existing native adapter with the same output and workload. Include packing/copying/dispatch cost. Preserve and test fallback behavior. Broad multiprocessing, another renderer or a Rust migration are not default next steps.

Factorio's belt work is useful as a primary example of changing the representation of repeated work instead of updating every object independently [S13]. It is not evidence that its speedups transfer to a voxel editor. The analogous question here is which derived view data really changed after one edit or a camera operation.

Pygame-specific boundaries matter: `display.update(rects)` is for software displays and cannot be used for an OpenGL display [S8]. `Surface.blits` and appropriate pixel-format conversion are available tools, not automatic speedups for this workload [S9]. Alpha-path changes can alter pixels and require visual comparison. Continue processing events during loading because the event queue is bounded [S7]. Do not apply a software-display optimization to the separate OpenGL opening or change the opening as part of this pass.

## 7. Architecture without a monolith refactor

Improve the boundaries of the new work, not the file count of the old work. Existing runtime owners remain authoritative. Do not move `AssetManager`, the application lifecycle, world storage or rendering wholesale. Do not create mixin-based file splitting, a service locator, an event bus, an ECS, a plugin framework or a new persistence schema to deliver these UI changes.

Use direct composition and small explicit inputs. A small editor-shell module is reasonable if required for new behavior. Its view model contains only displayable state such as selected tool/material, active operation, relevant options, visibility preferences, document status and loading status. It does not own or clone the `World`. Layout calculation returns the same rectangles used for drawing, hit testing and focus order. UI events return a handled/consumed result and, when appropriate, an existing semantic action. The application remains the place where the action reaches the current editor/load/save implementation.

Extend `engine/input_commands.py` locally where useful; do not replace the established undo-command stack with a second command abstraction. Presentation choices such as pinning do not enter world undo history. World edits do. A keyboard shortcut and its visible button must have the same preconditions, state transition and undo behavior.

Keep preferences separate from temporary presentation context. Pinning/scale/visibility preferences can persist through the existing configuration mechanism; transient hover/focus/selection-in-a-browser cannot overwrite editor settings or the current document. Reuse the engineering pass's atomic configuration and session-ownership work once verified.

For caches and background results, make ownership explicit: source/content identity, relevant revision, rendering configuration and intended consumer. Do not invalidate everything for a hover, or retain derived content after its source changes. Nystrom's command and dirty-flag discussions provide the relevant narrow ideas [S14]; they do not require adopting every pattern in a book.

Document future extraction seams only after observing real pain: asset loading, editor command application, world compositing and persistence orchestration. A later modularization proposal should identify the runtime owner, dependencies, tests and rollback for each extraction. It requires separate authorization. There is no line-count success criterion in this pass.

## 8. Validation and implementation order

Proceed in two coherent passes, detailed in the handoff. First establish the post-engineering baseline and implement a working shell/Library slice with preserved routes to all controls. Review its native presentation and interactions before migrating every panel. Then complete the accepted UI and pursue the measured responsiveness fixes. Preserve the installed known-good application until an explicit release decision.

Acceptance needs four distinct judgments: source/contracts, automated tests, native/installed runtime, and artistic/usability review. None substitutes for another. Use existing tests and targeted additions, not a new contract framework. Keep compact evidence with exact revisions and avoid regenerating or recommitting a large historical QA tree.

The decisive user tasks are: find an unfamiliar block without a shortcut; place/rotate/flip it; use and cancel a multi-step tool; undo and redo a bulk edit; preview a scene without replacing the canvas; save and reopen; recover controls after they settle away; and return from an existing tutorial/map/lab session with editor state intact. Test mouse routes and keyboard menu navigation, hover/focus/drag behavior, minimization, resizing and text scaling. Human review must decide whether the result feels like Bloc Fantôme rather than merely passing interaction tests.

## 9. Sources and research limits

Sources were consulted on 2026-10-20. No source code was executed against the owner's Windows machine during this browser research. No new runtime benchmark, installed-app verification, audio listening or artistic acceptance is claimed. The local Codex report and historical release metrics remain separately labelled. Full talk videos were not watched; the Townscaper demo was not interactively played. External images were inspected as references, not copied into the repository.

- **S1:** Guerrilla, Brian Roberts, [Accessibility features in Horizon Forbidden West](https://blog.playstation.com/2022/02/10/accessibility-features-in-horizon-forbidden-west/), 2022. Official description of configurable HUD visibility and accessibility choices.
- **S2:** Territory Studio, [Horizon Zero Dawn: UI Concepts and Narrative elements](https://territorystudio.com/project/horizon-zero-dawn/). Primary contributor account and visual concepts. The spatial scan-label image was inspected; concept presentation does not establish shipped HUD behavior.
- **S3:** Oskar Stålberg/Raw Fury, [Townscaper publisher description](https://store.steampowered.com/app/1291340/Townscaper/). Used only for the direct-building product comparison, not sales, prices or effectiveness claims.
- **S4:** Housemarque, Johannes Koski, [Unpacking Returnal's UX design](https://blog.playstation.com/2021/05/11/unpacking-returnals-ux-design-gameplay-first-ui-retro-futuristic-tech-and-accessibility/), 2021. Primary account of gameplay-led information hierarchy.
- **S5:** Wube, [Friday Facts #338: The (real) Character GUI](https://factorio.com/blog/post/fff-338), 2020. Shared search, consistency and the engineering cost of UI expansion.
- **S6:** Microsoft Xbox Accessibility Guidelines: [101 text](https://learn.microsoft.com/en-us/xbox/accessibility/xbox-accessibility-guidelines/101), [102 contrast](https://learn.microsoft.com/en-us/xbox/accessibility/xbox-accessibility-guidelines/102), [107 input](https://learn.microsoft.com/en-us/xbox/accessibility/xbox-accessibility-guidelines/107), [109 objective clarity](https://learn.microsoft.com/en-us/xbox/accessibility/xbox-accessibility-guidelines/109), [112 navigation](https://learn.microsoft.com/en-us/xbox/accessibility/xbox-accessibility-guidelines/112), [113 focus](https://learn.microsoft.com/en-us/xbox/accessibility/xbox-accessibility-guidelines/113). Apply the relevant principles without claiming comprehensive compliance.
- **S7:** Pygame, [event reference](https://www.pygame.org/docs/ref/event.html). Event queue limits and regular event handling.
- **S8:** Pygame, [display reference](https://www.pygame.org/docs/ref/display.html). Software/OpenGL distinction and presentation semantics.
- **S9:** Pygame, [Surface reference](https://www.pygame.org/docs/ref/surface.html). Pixel formats, batched blits and alpha behavior. The online pages identify themselves as 2.6.0 documentation; check the installed 2.6.1 behavior rather than treating the documentation label as an environment upgrade instruction.
- **S10:** Python 3.12, [The Python Profilers](https://docs.python.org/3.12/library/profile.html). Profiling locates costs; comparative benchmarks should not inherit profiler distortion.
- **S11:** Python 3.12, [concurrent.futures](https://docs.python.org/3.12/library/concurrent.futures.html). Running tasks cannot generally be cancelled through `Future.cancel()`.
- **S12:** Python 3.12, [tracemalloc](https://docs.python.org/3.12/library/tracemalloc.html). Python allocation tracing and snapshot comparisons.
- **S13:** Wube, [Friday Facts #176: Belts optimization for 0.15](https://factorio.com/blog/post/fff-176), 2017. A primary algorithmic optimization case study, not a predicted Bloc Fantôme speedup.
- **S14:** Robert Nystrom, [Command](https://gameprogrammingpatterns.com/command.html), [Dirty Flag](https://gameprogrammingpatterns.com/dirty-flag.html), and [Architecture, Performance, and Games](https://gameprogrammingpatterns.com/architecture-performance-and-games.html). Indexed primary-source excerpts were available; full chapter retrieval failed. Only the narrow command/undo, cache/source consistency and abstraction-tradeoff ideas are used here.
