# Bloc Fantôme: fidelity, feedback, motion and maintainable authoring

Date: 2026-10-20. Status: browser research and proposed design, not an implemented release.

Read alongside [the UI/performance study](BUILDER_UX_PERFORMANCE_2026-10-20.md). The updated [Codex handoff](../handoffs/BUILDER_UX_PERFORMANCE_HANDOFF_2026-10-20.md) is the execution entry point and resolves scope precedence.

## 1. Decision and evidence boundary

Keep one excellent creative builder. Make its actions legible, tactile and dependable; reserve horror for authored atmosphere and encounters, not unreliable editor behavior. The browser supplies research, design decisions and independent artistic judgments. Codex implements, measures, renders and produces review evidence. An instruction such as "make it procedural" is not an adequate creative specification.

The owner has reopened research into block fidelity, sound, Ponder-style presentation, the reference creature and eventual modularization. This does not automatically authorize replacing the opening, integrating an unaccepted creature, broadly extracting the monolith or changing the installed application. Finish and reconcile the current engineering work first.

Published runtime source was rechecked at `main@175686c21649a8d37826f8a22850c85482a69fd9` (2.9.8). The separate research branch began this extension at `f524492b13528b447bd48d0783755aef0bb23a0b`. The owner's local Codex report describes additional fixes and a separated creature draft, but those unpublished changes and their renders were not independently inspected here. Historical screenshots and handoff measurements are not new installed-runtime evidence.

### Source findings that materially change the next task

| Area | Verified published-source observation | Design consequence |
| --- | --- | --- |
| Block sounds | `blocFantome.py` has an early table, later overrides and additional family assignments. The later table corrects chest/Ender Chest placement, deepslate families and fire events; `tests/test_audio.py` checks several of them. | Audit the final resolved mapping and actual selected samples, not the first matching line. Do not reintroduce an interaction sound on placement. |
| Remaining sound candidates | Later assignments still put red sand, bamboo and coral blocks into the grass family. This is a concrete verification lead, not a completed version-matched listening audit. | Compare those mappings with the selected Java reference version and local assets before correcting them. |
| Light emission | The published Ender Chest definition omits `lightLevel`, whose dataclass default is zero. Fire, soul fire and End Portal definitions also omit it. The October 18 audit records source-derived expectations of 7, 15, 10 and 15 respectively. | Recheck against the post-engineering runtime, then test emitted light and rendered neighboring illumination. Do not infer completion from adding a number to a table. |
| State-dependent properties | The catalog is largely block-type based; the existing world and redstone systems already maintain stateful behavior. | A constant property export alone cannot correctly describe charged/lit/powered/connected variants. |
| Sound routing | `engine/audio.py` already has bounded named channel groups, panning and per-group gain; tests check saturation behavior. | Extend the existing router. Do not add a second mixer or middleware just to obtain UI feedback. |
| Pistons | `engine/redstone.py` already defines `MovingCell` and a time-based `PistonMotion` over committed state, with a default 100 ms visual duration. `piston_models.py` contains source-derived geometry. | Improve and validate the existing simulation/presentation boundary; do not announce pistons as a missing feature or recreate their simulation inside a cinematic. |
| Creature asset path | The published `opening_rig.py` loads a project-specific NPZ rig and uses source-specific joint indices. | A downloaded GLB/FBX is not presently a demonstrated drop-in asset. Plan a bounded offline conversion, not an assumed universal importer. |
| Modularity | Domain, world, projection, audio, undo, input, UI and tutorial modules already exist; substantial catalog/asset/application work remains in the entry file. | Identify live owners and preserve compatibility. The local engineering pass may already remove shadowed definitions; do not repeat or reverse that work. |

Evidence: [catalog and application](https://github.com/IsolatedSingularity/Bloc-Fantome/blob/175686c21649a8d37826f8a22850c85482a69fd9/Code/blocFantome.py), [definition defaults](https://github.com/IsolatedSingularity/Bloc-Fantome/blob/175686c21649a8d37826f8a22850c85482a69fd9/Code/domain/block_catalog.py), [audio regressions](https://github.com/IsolatedSingularity/Bloc-Fantome/blob/175686c21649a8d37826f8a22850c85482a69fd9/tests/test_audio.py), [maintenance audit](https://github.com/IsolatedSingularity/Bloc-Fantome/blob/175686c21649a8d37826f8a22850c85482a69fd9/docs/handoffs/MAINTENANCE_AUDIT_2026-10-18.txt), [redstone motion](https://github.com/IsolatedSingularity/Bloc-Fantome/blob/175686c21649a8d37826f8a22850c85482a69fd9/Code/engine/redstone.py), [piston geometry](https://github.com/IsolatedSingularity/Bloc-Fantome/blob/175686c21649a8d37826f8a22850c85482a69fd9/Code/engine/piston_models.py), [published rig loader](https://github.com/IsolatedSingularity/Bloc-Fantome/blob/175686c21649a8d37826f8a22850c85482a69fd9/Code/ui/opening_rig.py).

## 2. UI/UX: a stable interaction language, not disappearing functionality

Progressive disclosure means placing advanced controls behind understandable entry points, not making basic actions undiscoverable [S1]. The previously proposed Build/Library/Menu anchors, Show controls action, contextual options, pinned drawers and Always visible preference remain the direction. A quiet screen is an outcome of good hierarchy, not the primary success metric.

Organize around the user's questions: What am I holding? Where will it go? What will this click change? Can I reverse it? Where did my work go? Show the selected material/tool, placement validity and consequential non-default state close enough to the work to answer those questions. Keep occasional configuration in drawers. Avoid a toolbar that follows the pointer and covers the intended placement cell.

A contextual panel should remain visible while hovered, keyboard-focused, being read after explicit opening, pinned, dragged or used for a multi-step action. Do not make an idle timer compete with reading. Reveal/hide must not change hitbox ownership halfway through a gesture or cause camera reframing. Keep click targets and focus order stable for the duration of an action. Never interpret a UI mouse release as a placement just because its panel became invisible.

The Library should preserve its side preview and a stable selected item. Selection is inspection; activation is a separate, clearly named action. "Place structure" enters a cancellable placement preview. "Open world/build/biome" may replace a document and must use the existing save/cancel protections. These are different consequences and should not share an ambiguous generic Play icon.

Use one shared visual vocabulary: restrained framed surfaces, native-size readable type, recognizable block thumbnails, consistent spacing and selected/focused/disabled treatments. Keep texture in accents rather than behind every paragraph. Do not copy Horizon's sci-fi graphics or turn this into a generic dashboard. UI motion should explain a change of state, not compete with the architecture. Reduced-motion presentation should preserve the same information without sliding panels or decorative movement.

### Review tasks that determine whether the design works

An unfamiliar user must be able to find a material, place it, change a special-block orientation, cancel a tool, undo a mistake, preview another scene without opening it, save, and recover the controls after they settle away. An experienced user must be able to repeat those operations without additional modal interruptions. Record wrong clicks, accidental world edits, failed discoveries and recoveries, not merely completion time.

Review at the supported minimum window, the usual desktop size and 1080p, including enlarged text and actual Windows scaling. Test mouse routes and keyboard menu focus separately. No claim of fully keyboard-accessible building follows from a navigable menu. Preserve the current source behavior unless a demonstrated defect or an approved design change justifies altering it.

## 3. Sound: coverage for meaningful actions, deliberate silence elsewhere

Interpret "sounds for everything" as **every meaningful interaction has an intentional feedback decision**. It does not mean every event, empty click, pointer movement or rendered frame emits a sound. Blank panel clicks are deliberately silent in existing tests. Repetitive decoration must not drown out placement, an invalid operation or a failed save.

The proposed sound character is tactile and restrained: dry wood/stone contact, a short soft mechanism latch, a subtle glass or ceramic accent for selection, and little unnecessary reverberation. Do not use the opening's frightening sounds for ordinary errors. Preserve the selected opening music and current cinematic mix until their own review. These are authored proposals, not a claim that one sound palette is universally best.

### Feedback grammar to implement and audition

| Semantic event | Proposed audible treatment | Trigger and suppression rule |
| --- | --- | --- |
| Focus changes to an actionable item | Very quiet, short tactile tick; optional in preferences | Once per newly focused item, not every mouse-motion event. Keyboard and mouse focus use the same meaning. Suppress automatic relayout/fade-induced churn. |
| Select block or tool | Soft dry contact with a little more definition than focus | Only when selection changes. Do not play again when selecting the already active item. |
| Open/close a drawer | Related pair of restrained mechanical/air gestures | At intentional transition; not during every fade frame. Do not add a dramatic whoosh. |
| Toggle or cycle a property | Clearly related on/off or step variants | After the state actually changes. Show the value visually; pitch alone must not carry the meaning. |
| Slider adjustment | Quiet bounded feedback, or a deliberate audition when released | Never start a sample per pixel of dragging. Audio controls must not recursively trigger their own playback. |
| Valid placement/removal | Correct material/event sample, localized to the action | Only after a committed edit. A preview is not a placement. Keep placement, breaking and interaction events separate. |
| Invalid placement/action | Short muted rejection, with visible reason | Once per failed gesture or bounded held-input interval; no alarm machine-gun while a button is held. |
| Undo/redo | Related backward/forward tactile cues | After successful history change. Do not replay thousands of original placement sounds for a bulk undo. |
| Save/open succeeds | Subtle completion accent when useful | Only after real success. Routine autosaves should remain quiet by default; their state remains visible. |
| Save/load fails | Distinct restrained warning plus persistent visual explanation | Never play success first. Coalesce repeated identical failures until the user retries or the state changes. |
| Piston/door/chest interaction | Source-correct mechanism event | Once at the corresponding semantic transition; opening and closing cannot be one random mixed pool. |
| Large brush/fill/structure action | One leading material contact and bounded supporting texture if needed | Aggregate a transaction, not one equally loud sample per affected cell. Preserve material meaning without unbounded overlap. |
| Cancel/back | Soft release, quieter than completion | Successful dismissal/cancellation only; no error-like punishment for changing one's mind. |
| Quiet canvas, unchanged hover, blank UI, cached redraw | Silence | Silence is intentional coverage, not a missing asset. |

The acoustic descriptions above are the design to audition. Durations, loudness and variations must be tuned in context. A useful first audition compares six core cues (focus, select, open, cancel, success, failure) before populating the entire interface. Match perceived loudness during comparison so the louder candidate does not win merely by level. Do not normalize every sound to identical peaks: a brief click and a long scrape have different perceptual weight.

### Integration and mixing

Have successful actions emit semantic feedback once, regardless of whether they originated from a button or keyboard shortcut. Do not attach one sound to the widget and a second to its command. Rendering, hover polling, cache completion and state restoration must not replay old actions. Any event replay system needs explicit silent seeking/reset behavior.

Retain the current named router and reserve capacity for high-priority feedback. A full effects pool should not make a save failure or essential confirmation inaudible. Use a small policy: low-priority focus/ambient cues may be dropped; a new essential UI cue may replace an older low-priority UI cue. Do not raise all voice limits as a substitute for prioritization. Keep UI centered, while world actions can use restrained camera-relative stereo placement. Do not call stereo panning full physical 3D acoustics.

Expose independently adjustable UI feedback and building effects if the existing Effects grouping prevents a useful balance; retain music/ambient controls and preserve old preference defaults. Important state also needs visual feedback. Microsoft's audio guidance supports separated volume control and a mono option [S2]. A mono presentation must retain all meaningful cues. Avoid mandatory bass-only information or sudden large volume jumps to manufacture horror.

Variant selection should reduce repetition, but preserve the selected source event's meaning. In a fidelity mode, use source weights/pitch/volume; a non-repeating shuffle or added pitch variation is an explicitly documented artistic policy, not exact vanilla behavior. The Pygame mixer has bounded channels and a latency/buffer tradeoff, and exposes no general per-channel pitch setter [S3]. Do not write fictitious `set_pitch` calls. For required source pitch, use bounded preprocessed variants or measured PCM conversion outside the interactive hot path, with duration/channel tests. Do not introduce a new audio backend without a demonstrated limitation.

Acceptance requires a real listening pass: repeated building, a large fill, rapid menu navigation, background music/rain, mute/volume changes and cancellation. Check that the sound corresponds to what visibly happened, not just that a file decoded. Peak/voice-count tests cannot establish tasteful balance. This browser pass did not listen to the local sound bank or the owner's installed app.

## 4. Stop maintaining Minecraft facts by hand

### Recommended approach: source-derived data plus selective simulation

The efficient middle ground is **extract the facts, simulate the supported behaviors, and use the real game as an offline reference where needed**. Bloc Fantôme already has a selective world/redstone/liquid implementation. It does not need every Minecraft subsystem merely to obtain an Ender Chest's luminance or a material's sound events.

| Approach | Benefit | Cost and recommendation |
| --- | --- | --- |
| Manually maintain every block property and special case | Immediate small edits, no new tooling | Continual drift and duplicated facts. Keep only explicit project-specific overrides here. |
| Versioned export from the owner's Minecraft resources/runtime, consumed by the existing Python engine | Correct reusable metadata, auditable differences, no Java needed during ordinary play | Best fit. Requires a bounded extraction/verification tool, not a new full engine. |
| A live Java/Minecraft sidecar driving every edit | Can delegate much real behavior | Introduces runtime/startup/packaging/synchronization and version coupling; custom rendering and presentation still need work. Not recommended for the next pass. |
| Rebuild the product as a Minecraft mod | Native engine behavior and mod integration | A different product/architecture decision. It does not preserve the current lightweight Python application automatically. Out of scope. |

Minecraft distinguishes a block, its state and world-dependent queries. The versioned Yarn API exposes state luminance, sound groups, collision/outline/culling shapes and piston behavior; NeoForge's block documentation separately describes properties and state-dependent light [S4, S5]. This supports exporting resolved facts from a version-matched runtime. It does **not** mean all gameplay can be serialized into a single JSON file.

### Two data sources, not one magical JAR scrape

**Resources:** preserve namespaced model/blockstate paths, texture references and animation metadata; obtain sound definitions and their audio objects through the selected installation's resource/asset-index resolution. Resolve parent models, texture aliases and applicable variants/multipart rules. Do not flatten everything to a basename or assume a model JSON describes collision, emitted light or behavior. The current setup path's JAR-only sound assumptions require reconciliation with the engineering pass.

**Runtime facts:** a small offline exporter against a deliberately selected reference version can query block IDs, supported state combinations, luminance, sound group events and selected behavior properties. Reuse existing local reference tooling first. Add an observer/exporter only where it removes real manual work. Do not inject a new mod-loader dependency into the shipped Python runtime. Record context-dependent queries as such; connection/collision behavior may need controlled neighbor fixtures rather than a universal constant.

Preserve the source's semantic sound event IDs. `sounds.json` can reference other events and contains weighted alternatives and playback metadata [S6]. A folder called `block/deepslate` is not a complete sound definition. Resolve event references with cycle detection, keep namespace/path identity, distinguish a missing asset from an intentionally empty event, and validate the exact selected installation. Avoid guessing `break1.ogg` through `break4.ogg` when the source definition says otherwise.

The asset-index mechanism is independently visible in Prism Launcher's `AssetsUtils` implementation [S7]. Use the local indexed objects and verify their manifest hashes; do not copy launcher implementation or download unrelated asset collections. Stage extraction and swap only after required resources validate. Keep the owner's asset library and original files intact.

### Version and provenance rules

The project contains Java 1.16.1 behavioral/source scenes alongside later palettes. Pin the existing supported behavior contract and explicitly identify the resource version for each imported palette. Do not silently select "the newest installed version" or apply modern block states to an older simulation contract. A block absent from a chosen version is unsupported in that export, not automatically stone.

Record game edition/version, resource-pack precedence, source hashes, exporter revision and deliberate project overrides. Keep stable internal `BlockType` numeric values and old saves. Map namespaced source identifiers to that compatibility layer rather than renumbering every block. Never replace unknown state with an apparently valid default without reporting the loss.

A practical generated catalog needs: source identifier/version; valid and supported state schema; sound-group event IDs; emission by state; render/model reference; explicit collision/culling/transparency distinctions; and implemented behavior capabilities. Keep large source meshes/audio outside the code catalog. Mark unsupported or context-dependent results explicitly.

The exporter supplies facts; small capability handlers supply the supported behavior. Existing piston, liquid and redstone handlers remain their owners. A fence connection handler, a chest interaction handler or a lit-state emission rule can cover a family without one bespoke class per block. Do not create a generic plugin/DSL framework before two real families demonstrate the need.

### Fidelity categories and first verification set

For each block/event, report `verified`, `source-derived but not runtime-verified`, `intentional approximation`, `fallback`, `unsupported`, or `missing source asset`. No green coverage percentage may count fallback stone sounds as faithful support. Emit a compact actionable difference report over the whole current catalog, then prioritize by user-visible impact.

| Case | Required check |
| --- | --- |
| Ender Chest, fire, soul fire, End Portal | Reconcile the audited constant emission values with the selected source version; test removal/undo and neighboring light, not just the emitter's own bright sprite. |
| Furnace, redstone lamp, respawn anchor, copper bulbs | Evaluate lit/powered/charge/oxidation combinations that the app actually supports. Do not assign a universal maximum to every state. |
| Sculk catalyst/sensor/shrieker | Distinguish static presentation from supported activated/blooming behavior. A constant glow is not proof of state parity. |
| Glass/glowstone/ice | Distinguish placement from breaking events; do not assume both select the same sample because the material family matches. |
| Red sand, bamboo, coral; deepslate/tuff variants | Verify the final resolved mappings against a pinned reference, including step/place/break semantics when those actions exist. |
| Chest/Ender Chest/door/piston | Placement, removal, opening, closing, extension and retraction are separate semantic actions. Do not randomly select an opposite interaction. |
| Walls/fences/panes/stairs/slabs | Test supported neighbor/state geometry, picking and culling separately. Alpha transparency, light obstruction and collision are not the same boolean. |

Use minimal reference fixtures and compare state, sound event ID, effective light and geometry. Use the actual Minecraft runtime as an occasional oracle for tricky interactions, not a dependency that must run every time Bloc Fantôme launches. Do not promise full vanilla parity, inventories, crafting, survival, mobs or every redstone edge case as a side effect of this work.

## 5. Ponder: borrow its presentation grammar, not a second simulation

The repository already preserves a Ponder research packet and integration bridge. Its pinned source map identifies Ponder `89819291b726708d119b118dea01667eae0b64c9` and Create `fc9535d82a29419164a1e9dc9c678bdcddeab30d`. These pins were resolved during this pass. Some abbreviated source-map paths omit `foundation/`; the checked animation class is `common/src/main/java/net/createmod/ponder/foundation/instruction/AnimateElementInstruction.java` [S8]. Do not trust a plausible historical path without resolving it.

That class advances a resolved element by a per-tick delta and ends at an exact target. It does not establish that all Ponder movement is eased. The useful ideas are individually addressable sections, known origins/pivots, staged reveals, controlled framing, clear causal order and resettable authored time. Mechanical-piston tutorial choreography is not the same as vanilla piston behavior.

For Bloc Fantôme, use three responsibilities: the existing simulation owns facts and committed state; presentation samples motion between those facts; an optional authored demonstration controls camera, section reveal and annotations. Never animate by repeatedly editing the live world or polluting undo history. A demonstration must operate on an isolated snapshot and restore the editor through existing session logic.

### Proposed 8-second mechanism proof, not a new game mode

Use one existing small supported piston assembly in an isolated preview. Start with a readable three-quarter view and an intact grounded base. For about 1.5 seconds, hold still long enough to understand the closed state. Reveal the actuator/connection if occluded, using one clean section offset or cutaway, not an explosion of every block. Activate the actual supported mechanism once; let its existing simulation timing drive its moving cells and event sound. Hold the extended state briefly, retract once, restore the original section transform and hold the complete result.

Keep the camera still during the mechanism's decisive travel. Show the rod remaining connected to its body, correct carried blocks, complete visible faces and consistent light. Avoid overshoot or elastic stretching on a rigid piston. At ordinary playback speed, no destination duplicate may appear before the moving cell arrives. Demonstration slow motion, when used for inspection, must be labelled and must not alter the editor's simulation rules.

The proof is accepted only after all four editor rotations and a near/far view read correctly, reset/replay produce the same initial state, audio does not double-fire, and leaving the preview restores the editor. This is a small presentation pilot, not permission to reopen Redstone Map development or copy Create's kinetic machines wholesale.

For future tutorial sequences, prefer a small declarative cue list: section transform/reveal, camera target, annotation, action gate and sound marker. Sample time deterministically or restore a snapshot then replay bounded state changes. A looped incremental transform must not accumulate drift. Seeking must reconstruct visuals without emitting every past sound. Reuse existing scene isolation and timeline capabilities before adding another engine.

Ponder's checked license is MIT. Create's checked license assigns MIT to code outside its designated asset directory, but `src/main/resources/assets/` is All Rights Reserved [S9]. Therefore code ideas, scene Java, textures and scene NBT are not interchangeable reuse categories. Preserve notices for adapted code; use original scene layouts and the owner's appropriately sourced assets. The packet itself already records this distinction.

## 6. Creature: the mesh must earn the animation

### What is actually visible in the owner's reference

The supplied 400×400 image was inspected directly. It shows a dark faceted figure with a substantial folded upper body, broad angular shoulder masses, a recessed head region, long tapered appendages, hooked/angled contact ends and a comparatively compact interior. The frightening impression comes from an ambiguous heavy shape supported by improbable long limbs, not from uniformly thin sticks. A single view does not uniquely establish the hidden anatomy or exact limb count.

The owner's description that the local candidate is skinny and unconvincing is feedback, not a render this browser has independently inspected. Do not diagnose the unseen draft as a proven rig bug. First compare its silhouette and body mass with the reference, then decide what can be preserved.

### Original-model brief

Develop an original four-primary-contact interpretation: two exceptionally long load-bearing forelimbs and two bent rear supports surrounding a compact suspended trunk. Smaller folded structures may suggest additional anatomy, but do not add another limb system merely for complexity. This topology is a proposed original interpretation, not a claim about the reference's unseen construction.

Give the shoulders and upper back a continuous, broken wedge-like mass. The body must remain substantial in silhouette at encounter distance. Keep the head recessed and difficult to parse; avoid a normal human face, cartoon eyes or a familiar third-party character's markings. Use dark charcoal planes with enough value separation to survive the abyss lighting, not pure black everywhere or emissive outlines.

Model broad tapered cross-sections and asymmetric folded plates, not a row of equal-radius tubes. The reference's visible triangulation should not become a compulsory wireframe texture. Large planes and controlled edges should carry the form. Avoid random spikes, noisily subdivided topology, a tiny exposed ribcage, floating armor scraps and exaggerated muscle anatomy. Keep joints structurally connected through their full intended range.

As a blockout hypothesis, let shoulder span occupy roughly 0.35–0.5 of total standing height and the central solid mass occupy roughly 0.2–0.3 of height in width. These are proposed starting proportions, not measurements of the image or fixed success thresholds. Adjust after silhouette review. Long limbs should taper visibly but retain weight at their roots. Polygon/bone counts are performance constraints to measure, not artistic acceptance criteria.

### Authoring route and downloadable alternatives

Prefer an authored low-poly mesh and a small purposeful rig, with editable source retained. Blender supports mesh/skinning/keyframe export through glTF [S10]; Blockbench offers mesh-based low-poly modeling and keyframe animation [S11]. Blender is the preferred authoring route for this nonhuman folded silhouette; Blockbench is a reasonable alternative for rigid articulated parts. Neither requires changing the game engine.

The current runtime consumes a custom NPZ rig. A controlled offline converter may turn an approved original mesh, bind transforms, weights and named joints into the existing rendering contract. First prove bind pose, coordinate handedness/up axis, scale, normals, material boundaries and one articulated chain. Do not reuse Thorn-specific bone numbers or assume a Blender IK controller is an exported runtime solver. Bake authored motion where needed and implement the limited runtime contact solver explicitly. A universal GLB importer is not required to obtain one original creature.

Two inspected publisher listings provide useful acquisition comparisons, not approved final art:

| Candidate | Verified listing facts | Decision |
| --- | --- | --- |
| Quaternius Animated Monster Pack (2018) | Four animated models; FBX/OBJ/Blend; the specific pack page declares CC0 [S12]. | A low-friction rig/asset-pipeline study candidate. Its page metadata does not establish a match to the owner's silhouette. Do not substitute it for the model brief without a rendered comparison. Do not assume newer Quaternius packs share this license. |
| heyheythere PSX Monsters | Listing describes rigged FBX/GLB/Blender characters and six clips per monster; permission for game use but not source-asset redistribution; AI-assisted/code-generated content is disclosed [S13]. | Not recommended as the immediate solution to dissatisfaction with simplistic generated motion. Listing claims are not an animation-quality review. No purchase, archive inspection or successful import is claimed. |

The current Quaternius Bestiary listing instead describes a humanoid rig, QAL terms and no included animations [S14]. That makes it a different proposition from the older CC0 animated pack. Avoid treating "rigged" as "has suitable motion" or "downloadable" as "usable in this renderer." No sufficiently close, legally and technically inspected ready-made replacement was established in this pass. Custom authored mass and pose design is the stronger recommendation, not more random asset hunting.

### Motion architecture: authored intent plus procedural adaptation

Procedural animation should decide how a deliberate action fits the actual contacts and scene. It should not replace pose design with sinusoidal movement. Rosen's GDC presentation describes procedural techniques using a small number of authored keys [S15]. The Ozz foot-IK example explicitly distinguishes an IK demonstration from a full planting system: contact activation, unreachable targets and base animation still need design [S16]. These are reasons to use a hybrid approach, not to claim that installing a solver creates a performance.

Author at least six distinct full-body targets before interpolation: compressed stillness, load transfer, exploratory reach, committed brace, wound-up distortion and recovered stillness. Each needs a different shoulder/trunk relationship and readable contact intention. Use quaternion rotation blending and a coherent local hierarchy; avoid per-frame vertex noise. Different phases need different timing, not one easing curve applied everywhere.

Use a small explicit state machine: `observe -> prepare_support -> release -> reach -> acquire -> load -> settle`, plus an authored contortion branch and recovery. At each step, choose a reachable contact with clearance, transfer visible body weight away from the limb being released, then move that limb through a lifted arc. Acquisition fixes the endpoint in world or support-local coordinates; subsequent body motion bends the chain rather than dragging the contact. Release must be explicit. Moving supports require storing the contact in support-local coordinates, not freezing it to the old global position.

For two-segment load chains, use analytic two-bone IK with a controlled pole direction. A constrained FABRIK chain is a candidate for the longer torso or an extra articulated chain, not automatically a better solver for every limb [S17]. Enforce segment lengths, angular limits, stable bend-side choice and sensible handling of unreachable targets. Clamp/replan the target or reduce the body move; never stretch the mesh just to satisfy a target numerically.

Shift the trunk before a supporting limb lifts. For slow grounded poses, the projected body mass relative to the supporting contacts is a useful visual stability check. It is not a complete physical stability proof, especially during a strike, a climb or non-coplanar contacts. Do not claim simulated forces from a decorative support polygon. The performance must show why each contact bears weight.

Use asymmetric attention: the recessed head can orient first, the shoulder follows late, and a rear support may remain still. A sudden distortion should travel through a short joint sequence, preserve the planted supports and land in a new silhouette. Avoid synchronized all-limb oscillation, endless breathing bob, continuous random twitching or mirrored left/right stepping. One unsettling act after a long stillness is more appropriate here than perpetual thrashing; this is the proposed direction for owner review.

### Concrete motion proof before any 44-second integration

Produce an approximately 9-second isolated proof on a simple floor with a small raised ledge. Keep the main camera static and show the entire creature, including contacts. The following timing is an authored test proposal, not a new encounter script:

| Time | Performance requirement |
| --- | --- |
| 0–1.5 s | Readable compressed stillness. No idle sway disguising the silhouette. |
| 1.5–2.3 s | Trunk shifts onto the remaining supports; one forelimb visibly unloads before lifting. |
| 2.3–3.2 s | That limb searches forward, clears the surface and plants deliberately on the ledge. Other planted contacts remain fixed. |
| 3.2–4.6 s | New contact takes weight; the shoulder/body follows with a restrained settle, then holds. |
| 4.6–5.8 s | A different rear support adjusts asynchronously, after its own weight transfer. No mirror gait. |
| 5.8–6.5 s | A coil/anticipation changes the body silhouette while contacts remain meaningful. |
| 6.5–6.7 s | One abrupt but continuous full-body contortion, with joint limits and contact constraints preserved. |
| 6.7–9 s | Nonuniform recoil and a changed still pose. A delayed small head adjustment may close the beat; do not restart the opening pose as an obvious loop. |

Render the same proof in neutral clay, silhouette and intended lighting. Inspect front/side/three-quarter views and actual encounter distance. A close-up can diagnose a joint, but cannot substitute for scene-scale readability. Include one contact/joint debug overlay separately; the artistic clip must be judged without it.

Required technical evidence: bounded segment-length error, stance-contact drift, reachable-target handling, deterministic seek/replay, no NaNs, no obvious ground penetration, and stable behavior across sampled frame rates. Choose tolerances relative to body scale and screen projection, and report them. Passing these only establishes motion integrity. Artistic acceptance requires the owner to judge mass, threat, timing and the reference relationship from the actual clips.

The first acceptance gate is static form. The second is this short motion proof. Only after both pass should a separate integration pass replace the encounter creature, retime the camera or edit its audio. Do not spend another full 44-second implementation on an unaccepted silhouette.

Creature sound, when separately authorized, should follow real contacts and articulations: a heavy contact may have a brief low body component, a dry surface layer and a restrained structural creak. Do not emit a thud for a foot that is only hovering. Hold quiet intervals; do not add a full-volume voice or bone crack to every procedural correction. Actual listening remains mandatory.

## 7. Future modularization: remove ownership ambiguity, not merely lines

A giant file is a risk, but moving arbitrary methods into mixins preserves its hidden state and dependencies. The useful success criteria are one obvious owner for a behavior, a small explicit interface, tests at that boundary and preserved runtime/public compatibility. File length is only a symptom.

The first future extraction should be chosen after the engineering baseline is reconciled. The most coherent candidates are:

| Boundary | Owns | Must not own |
| --- | --- | --- |
| Catalog and fidelity adapter | Final block/material/event facts, source-ID compatibility mapping and explicit overrides | Pygame surfaces, mutable world state, imports from the application entry point |
| Asset/audio facade | Resource resolution, bounded decoded/cache lifetime and semantic event playback through the current router | Editing rules, duplicated save/load behavior or an independent mixer |
| Editor shell | Layout, focus, visibility and translation from UI gestures to existing actions | Another world, undo stack or catalog implementation |
| World presentation | Candidate planning, compositing/cache invalidation and motion sampling | Simulation truth, arbitrary persistence or a second camera-state owner |
| Application orchestration | Startup, frame sequencing, scene/session lifecycle and compatibility exports | Reimplementation of the systems above |

Adopt inward dependencies: entry point composes UI/assets/engine; engine and adapters depend on stable domain data; extracted modules never import `blocFantome` to obtain their own dependencies. Pass catalog/projection/action interfaces explicitly. Preserve existing public imports used by tests/tools, enum values, save formats, runtime paths, frozen builds and source launch.

Before moving a system, characterize the current behavior, identify all callers and mutable fields, and verify one end-to-end user task. Extract one coherent owner while keeping its adapter. Then test import cycles, a clean process launch, old saves, native/Python fallback and the same visible task. An extraction commit should not also redesign the UX or change mechanics. Remove a compatibility path only after its users are accounted for.

For the next builder pass, small seams needed by sound/catalog/UI work are reasonable proposals. The wholesale AssetManager, renderer and application split remains a separately approved phase. Do not adopt an ECS, event bus, plugin architecture, a new GUI dependency or a new save schema merely to make the directory tree look modern. Preserve user-owned edits and the current engineering fixes.

## 8. Coherent next work and acceptance

The next implementation handoff combines the previously researched UI slice with a source-backed fidelity/feedback slice, not an everything-at-once rewrite. It should first reconcile the active engineering branch, then deliver a real builder interaction that demonstrates the design. A coverage report over all blocks can accompany a bounded initial correction set; the report must identify unresolved cases rather than pretending all parity is complete.

After the owner accepts the UI/sound direction, complete the presentation and apply measured responsiveness improvements. Use the existing benchmark corrections: dispatch, first useful view, complete view and steady rendering are distinct; headless timing is not installed input-to-display behavior. Preserve scene fidelity and existing native fallback. Do not optimize invisible test-only paths while the real browser, sound or loading interaction still stalls.

Ponder demonstration, creature proof and broad refactoring are separately scoped follow-ons, described here so Codex does not invent their direction. They do not automatically run because a broad research document mentions them. The voice-dictated phrase "wall footage" was not resolved into a concrete feature or file; it creates no implicit implementation task.

Maintain separate judgments for SOURCE/TEST, NATIVE RUNTIME, VISUAL/USABILITY, LISTENING and INSTALLED RELEASE. A test count cannot establish that the creature is frightening, the UI is discoverable or the sound mix is pleasant. Keep the installed known-good app and accepted `main` until the appropriate review/release authorization.

## 9. Sources and limits

Sources consulted on 2026-10-20. Recommendations and timings are original design proposals unless explicitly attributed. No full-game emulation, runtime exporter, sound-bank audition, asset archive import, native benchmark or installed playthrough was performed by this browser pass. The uploaded reference image was visually inspected; downloadable model listings were checked for stated contents/terms, but their actual meshes and animations were not verified. GDC session descriptions were read, not full talk videos. This avoids confusing research with acceptance.

- **S1:** Nielsen Norman Group, [Progressive Disclosure](https://www.nngroup.com/articles/progressive-disclosure/). Supports separating common from advanced controls, not invisible basic actions.
- **S2:** Microsoft, [Xbox Accessibility Guideline 105: Audio accessibility](https://learn.microsoft.com/en-us/xbox/accessibility/xbox-accessibility-guidelines/105). Independent volume categories and mono presentation.
- **S3:** Pygame, [mixer reference](https://www.pygame.org/docs/ref/mixer.html). Channel reservation/control and buffer-latency tradeoff; check the installed version before implementation.
- **S4:** Fabric Yarn, [AbstractBlockState, 1.21.1+build.3](https://maven.fabricmc.net/docs/yarn-1.21.1+build.3/net/minecraft/block/AbstractBlock.AbstractBlockState.html). State luminance, sound and contextual shape APIs. This is an API reference, not an exported vanilla data set.
- **S5:** NeoForge, [Blocks, 1.21–1.21.1](https://docs.neoforged.net/docs/1.21.1/blocks/). Property/state distinction and configurable block properties. Using this documentation does not prescribe shipping NeoForge.
- **S6:** NeoForge, [Sounds, 1.21–1.21.1](https://docs.neoforged.net/docs/1.21.1/resources/client/sounds/). Sound events, definitions, nested event references and sample metadata.
- **S7:** Prism Launcher, [AssetsUtils.cpp at inspected search revision](https://github.com/PrismLauncher/PrismLauncher/blob/1b09df1ddc426caa399efa3b710c8a98ef1d63d3/launcher/minecraft/AssetsUtils.cpp). Indexed-object/path handling; this pass inspected connector excerpts, not the entire launcher. Reference only, not copied implementation.
- **S8:** Ponder, [AnimateElementInstruction.java at packet pin](https://github.com/Creators-of-Create/Ponder/blob/89819291b726708d119b118dea01667eae0b64c9/common/src/main/java/net/createmod/ponder/foundation/instruction/AnimateElementInstruction.java). Actual tick-delta/target behavior. Project context: [packet source map](../../NEW%3B%20PONDER%20PACKAGE/ponder/source_map.md) and [integration bridge](../PONDER_REFERENCE_BRIDGE.md).
- **S9:** [Ponder license](https://github.com/Creators-of-Create/Ponder/blob/89819291b726708d119b118dea01667eae0b64c9/LICENSE); [Create license overview](https://github.com/Creators-of-Create/Create/blob/fc9535d82a29419164a1e9dc9c678bdcddeab30d/LICENSE.md). Exact pinned notices read. Preserve their distinct code/asset scopes.
- **S10:** Blender, [glTF 2.0 exporter manual, 4.4](https://docs.blender.org/manual/en/4.4/addons/import_export/scene_gltf2.html). Indexed official excerpts establish mesh, keyframe and skinning export. Full page retrieval failed; no version-upgrade or exact export-setting claim is made.
- **S11:** [Blockbench](https://www.blockbench.net/), official modeling/animation feature description. Tool capability is not proof of a completed compatible export.
- **S12:** Quaternius, [Animated Monster Pack](https://quaternius.com/packs/animatedmonster.html). Specific 2018 pack contents, formats and CC0 declaration; archive not downloaded.
- **S13:** heyheythere, [PSX Monsters](https://heyheythere.itch.io/psx-monsters). Publisher-stated rig/format contents, terms and AI-assistance disclosure; not a quality endorsement or purchase recommendation.
- **S14:** Quaternius, [Bestiary: Dungeon Monsters Kit](https://quaternius.itch.io/bestiary-dungeon-monsters-kit). Current listing distinguishes a humanoid rig, QAL terms and absence of included animation.
- **S15:** GDC, David Rosen/Wolfire, [Animation Bootcamp: An Indie Approach to Procedural Animation](https://www.gdcvault.com/play/1020583/An), 2014. Session description only; supports the hybrid authored-key/procedural direction, not a claim to have reproduced Overgrowth.
- **S16:** Guillaume Blanc, [Ozz foot-IK sample](https://guillaumeblanc.github.io/ozz-animation/samples/foot_ik/). Primary implementation explanation, including its stated limits as a complete planting system.
- **S17:** Andreas Aristidou and Joan Lasenby, [FABRIK project and constrained extension](https://www.andreasaristidou.com/FABRIK), original 2011 method and later extension. Author's overview/abstracts read. Solver choice does not establish gait, performance or artistic quality.

Additional UI-audio articles from Audiokinetic were identified, but repeated full-page retrieval returned HTTP 403 in this extension. They are not used as the sole basis for a design claim or presented as newly read in full. The feedback grammar above is an explicit proposal to be auditioned.
