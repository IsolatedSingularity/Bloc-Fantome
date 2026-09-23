# Ponder Reference Bridge for Bloc Fantôme

Date: 2026-09-23

Current repository baseline for this bridge: `main` at `019c049f99ef91ba55452f638460dd099504dec3`.

This is a **design/reference handoff**, not a debug report and not an implementation plan. The material in `NEW; PONDER PACKAGE/` should be treated as a selective reference library. It does not supersede `docs/PRE_IMPLEMENTATION_QA.md`; implementation work still resolves that document's P0 items first.

## What the reference is actually useful for

The strongest match is not “add Create to Bloc Fantôme.” It is Ponder's **presentation grammar**:

- a small, readable world shown from a deliberate viewpoint;
- parts revealed in a controlled order rather than all competing for attention at once;
- related geometry moving as one coherent visual group;
- one visible cause followed by one visible effect;
- text, outlines and prompts attached to the thing currently being demonstrated;
- enough pause around motion for the player to understand it;
- the demonstration isolated from the player's real build and restored cleanly afterward.

That is close to what Bloc Fantôme has already been moving toward with its 2.5D renderer, Redstone Lab, editable large worlds and staged tutorial scenes. The package is most valuable when it helps those existing systems become more coherent, not when it becomes a second framework.

## Strong fits

### 1. Pistons and other moving assemblies

This is the most direct fit.

Bloc already has canonical piston simulation and a 100 ms interpolated `PistonMotion`. Ponder adds a useful way of thinking about the **display** of that motion: the head, rod and moved payload are one presentation event, sampled from one phase, while canonical world state remains owned by the simulator.

The first future agent should therefore inspect the current render path for:

- one shared motion progress value for head / rod / payload;
- suppression of duplicate source/destination geometry during transit;
- correct painter ordering against stationary foreground blocks;
- cache invalidation only where the moving presentation actually changes;
- clean reversal/interruption without creating a second motion clock.

If existing Bloc interpolation already satisfies those requirements, do not build a new animation system merely because Ponder has one.

### 2. A tiny presentation-section concept

Ponder's most portable abstraction is an independently presented selection of geometry.

For Bloc, the useful interpretation is deliberately smaller:

> a temporary set of existing draw/model descriptors that can share one visual transform without moving the canonical world twice.

Translation is the obvious first boundary. It matches pistons, sliding doors, simple lifts and tutorial choreography while remaining compatible with a 2.5D painter renderer.

Do **not** assume a whole assembly can be flattened to one topmost sprite. If the group crosses static geometry, its pieces still need correct depth relationships with the world.

Arbitrary 3D rotation is a different problem. A cached flat isometric sprite cannot reveal newly exposed faces. Bearing-style rotations are worth studying as choreography references, but not as an automatic next implementation.

### 3. Redstone Lab as a Ponder-like explanation surface

The Redstone Lab is probably the best existing place to borrow Ponder's explanatory style.

Useful ideas:

- reveal the relevant circuit subset before activation;
- frame the important component;
- highlight the input;
- let one transition happen;
- pause on the consequence;
- optionally gate progression on one real user action;
- keep simulation ownership in the existing redstone engine.

This should improve legibility without turning the Lab into a scripted fake simulator. A tutorial may deliberately script presentation, but that distinction should remain explicit.

### 4. Tutorial scenes without a second tutorial engine

Bloc already has snapshot/restore, staged lesson scenes and event observation. That is the correct foothold.

The useful future direction is a very small scene vocabulary layered on top of the existing runtime, for example:

`frame → reveal → annotate → animate → wait → optional action gate → continue → restore`

This could make selected tutorial moments feel like Ponder while preserving ordinary editable scenes and the existing navigation/session machinery.

Do not replace the current tutorial with a general-purpose storyboard engine before one bounded scene proves that such a vocabulary is genuinely useful.

### 5. Controlled framing

Ponder's camera contributes heavily to the effect even though it is less technically exotic than the renderer.

For Bloc this means studying:

- when a demonstration recenters;
- how much empty space surrounds the mechanism;
- when a view changes before rather than during an action;
- how long the scene rests after motion;
- whether the important mechanism is isolated visually from unrelated blocks.

The transferable lesson is **deliberate framing**, not a free 3D orbit camera. Bloc's four established isometric views are part of its identity and renderer assumptions.

### 6. Annotations that follow displayed geometry

Any outline, arrow, tooltip or interaction prompt attached to a moving part should reference its **displayed pose**, not only the canonical source cell.

This is a small principle with broad payoff in pistons, tutorial scenes and future animated previews.

## Useful later, but separate

These references should remain independent experiments rather than being bundled into a “Ponder overhaul.”

### Pixel-locked shadows / lighting

The package's shader notes contain useful ideas about anchoring shading to block/face coordinates so visual detail does not swim with the camera. That could suit Bloc's pixel-art aesthetic.

It is not part of the piston/Ponder bridge. Treat a tiny face-local lighting or mask experiment separately and retain the current renderer as fallback.

### Fog / atmosphere

Depth-aware fog and stable low-resolution atmospheric layers may improve larger scenes. Again, this is orthogonal to Ponder's scene organization.

Do not use the new reference package as justification to combine motion, shadows, fog, skyboxes and sound into one visual rewrite.

### Other Create scene families

If a future Bloc behavior needs them, selectively inspect:

- `GantryScenes` for guided translation;
- `PulleyScenes` / elevators for vertical motion;
- `BearingScenes` for coordinated pivots and framing;
- `ChassisScenes` for visual assembly membership;
- `BeltScenes` / movement actors for many objects sharing a path.

These are references to answer a concrete question, not a backlog of features Bloc should acquire.

## Things that are *not* good fits

### Do not port Ponder's virtual Minecraft world

Bloc already owns its world model, snapshots, importers and simulator. Ponder's `PonderLevel` exists because Ponder runs inside Minecraft. It is not a missing abstraction here.

### Do not import Create mechanics

Kinetic networks, Create block entities, mechanical piston rules, belts, trains and similar gameplay belong to Create. The value here is how those ideas are **shown**, unless Jeff separately decides he wants a specific mechanic.

### Do not build a generic timeline/scheduler first

Ponder's scheduler is useful evidence for scene semantics, but Bloc does not need to clone its tick machinery in order to stage one motion, prompt or reveal.

Start with the smallest vocabulary demanded by one approved demonstration. Generalize only after a second real scene needs the same concept.

### Do not replace the 2.5D renderer with Minecraft/Ponder rendering

The reference kit is not a migration argument. Bloc's software renderer, model geometry, painter order, world caches and native acceleration are valuable existing architecture.

### Do not copy Create's Ponder assets casually

The Java/Ponder code and Create resource assets do not share one simple reuse scope. The package already records the license boundary. Study the choreography and architecture; do not assume scene NBT, textures or other assets are distributable just because the code is inspectable.

### Do not treat the audio/skybox/shader branches as required Ponder dependencies

Those are intentionally adjacent reference libraries. They may inspire separate polish passes, but Ponder-style scene clarity does not depend on adopting them.

## Where this could eventually unify the app

If the ideas prove useful through small experiments, one **presentation vocabulary** could eventually serve several existing surfaces:

- live piston/redstone motion in the editor;
- Redstone Lab explanations;
- selected tutorial demonstrations;
- richer structure/block previews;
- possibly short World Map explanation moments.

The common layer would own only temporary presentation concerns: selected geometry, displayed transform, framing/annotation state and timing. Simulation, save state, undo, world topology and canonical block state remain with their existing owners.

That is the coherent direction. It avoids a Frankenstein outcome where the tutorial, Lab, previews and live editor each invent separate animation systems.

## Recommended reading order for future agents

When the task concerns Ponder-like presentation:

1. Read `docs/PRE_IMPLEMENTATION_QA.md` and respect its implementation gate.
2. Read this bridge.
3. Read `NEW; PONDER PACKAGE/README_FOR_AGENTS.md`.
4. For piston/motion work: `ponder/piston_redstone_deep_dive.md` → `ponder/animation_primitives.md` → `ponder/rendering.md`.
5. For tutorial/Lab work: `bloc_fantome/ponder_mapping.md` → `bloc_fantome/opportunities.md`.
6. Fetch/read additional Create scene source only when a concrete Bloc question points to it.

Do not mechanically consume all 47 scene files.

## First eventual implementation experiment, when approved

This document does **not** authorize implementation. When the QA gate is clear and Jeff explicitly asks to pursue this direction, the first experiment should stay narrow:

**One piston scene, one fixed Bloc view, existing canonical piston behavior, and one measured presentation pass.**

Compare extension start, intermediate frames, endpoint, retraction, interruption and an occluded foreground case. Determine whether existing interpolation/compositing already produces the desired coherent motion.

Only if it cannot should the next agent prototype a translation-only visual section.

The desired result is not “Bloc Fantôme has Ponder.” It is that the mechanisms in Bloc Fantôme read with the same immediate clarity and satisfying physical coherence that made Ponder stand out in the first place.
