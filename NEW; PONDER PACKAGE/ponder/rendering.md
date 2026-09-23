# Rendering: what makes the scene maintainable

## Observed render organization

`PonderScene.renderScene` runs visible scene elements through an initial stage, per-block render layers, and a final stage, then renders world entities, particles and outlines. Overlay elements are handled separately. This separation lets meshes, special component renderers and explanatory UI coexist without representing the tutorial as flat recorded frames. [Source](../SOURCES.md#p-scene).

`WorldSectionElementImpl` masks the virtual world to a selection when building a structure buffer. Buffers are cached per section and render layer; queued redraw invalidates the relevant cached geometry. Translation/rotation updates modify presentation transforms rather than inherently requiring all block models to be rebuilt. Block entities use their dedicated Minecraft renderers. [Source](../SOURCES.md#p-section).

The world/section code can push a temporary light value. Parts of the reveal/fade treatment manipulate brightness, including a 5-to-15 light-level interpolation, rather than behaving like a single generic opacity fade. Do not reproduce every appearance transition by multiplying alpha and assume fidelity. [Section](../SOURCES.md#p-section), [virtual level](../SOURCES.md#p-level).

## Inference: why the result is readable

Small scenes, controlled viewpoints and authored pauses reduce visual competition. Independent geometry permits a coherent assembly to move without rebuilding its logical arrangement. A visible target and its label can share a stable location. The inspected piston and bearing storyboards reveal parts before operating them and leave time after a movement to understand its consequence. These are source-based interpretations, not a user study or an exhaustive aesthetic ranking. [Piston](../SOURCES.md#c-pistonscenes), [bearing](../SOURCES.md#c-bearingscenes).

## Translating the architecture, not the graphics backend

**Proposal:** retain Bloc's current model renderer and cached draw lists. For a small moving assembly, a transient group can own selected draw descriptors, a pivot, current/previous pose and an occlusion policy. Static geometry remains cacheable. This does not require importing Minecraft, running Ponder inside Pygame, or migrating to a GPU engine.

The important constraint is depth ordering. Blitting one precomposed group sprite over the whole static world can make foreground blocks disappear behind it. A group that crosses static geometry needs either depth-aware compositing, a correct insertion into the existing painter ordering, or a deliberately staged scene where such intersections cannot happen. A single group sort key can also fail when geometry spans both sides of an occluder. Measure and test this before choosing the cheapest representation.

A transform-only cache is useful only when the cached representation supports that transform. Translating a flat isometric sprite is straightforward. Rotating it on screen does not reproduce a rigid 3D bearing rotation: newly exposed faces need appropriate model projection. For this project, translation-only moving groups may be the best first boundary, but that is a future experiment.

## Visual invariants for a later implementation

The source cell and destination cell must not both show the same payload during transit. The rod, head and payload should agree on pose. A foreground opaque block should continue occluding the correct portion of the moving object. Selection outlines should follow the displayed object. Reset, cancel, fast replay and save/load should not leave orphan visual groups. Static-world caches must be invalidated only when their content actually changes.

These acceptance criteria are proposed for Bloc. They are not evidence of current bugs. Its existing electrical-state render cache already explicitly preserves painter order, so bypassing that architecture to add a new topmost animation layer would be a regression risk. [Source](../SOURCES.md#b-cache).

## What was not verified

No Ponder runtime, mod client or Bloc renderer was launched. The exact observed video segment was not frame-measured. Exact UI fade curves, full camera-matrix composition and arbitrary-block render compatibility were not exhaustively audited. Use the pinned source map to resolve those details before claiming pixel-identical output. Platform-shadow UI decoration, Minecraft block light and real cast shadows must remain distinct concepts.
