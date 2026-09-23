# Fog and atmosphere under a CPU budget

## What the reference supports

The Silent Hill 2 Enhanced Edition maintainers compare fog thickness, movement speed and on-screen amount with the PS2 version. Their comparison treats those visual characteristics as important, not merely maximum view distance. It is an older platform comparison, not evidence of a CPU-only original renderer or a modern performance claim. [Maintainer comparison](../SOURCES.md#sh-fog).

Voxel Vibes provides a directly inspected contrasting implementation: distance is reconstructed from depth and scene color is blended toward the sky color using a distance-dependent power curve. This establishes an actual example of coupling haze to the background palette. It does not implement all of Silent Hill's atmosphere. [Shader](../SOURCES.md#v-final).

## Own proposal: combine depth cueing and slowly changing structure

Start with a declared depth convention. For a camera-facing isometric view, use distance along the viewing direction or another intentionally chosen scene-depth measure. World height alone is not camera depth; Euclidean distance and view-axis depth also produce different results.

A simple illustrative model is

```text
T(d) = exp(-density * max(d, 0))
C_out = T(d) * C_surface + (1 - T(d)) * C_fog
```

`T` is transmission. With zero density, the original image is preserved; increasing depth moves it toward the fog color. This is a design model for a later experiment, not a transcription of Silent Hill code. Calculations should use a consistent color space.

For more character, add a few slowly drifting low-resolution density layers or authored masks. Vary their scale and speed rather than generating unrelated noise every frame. Match the fog color near the horizon to the selected skybox. Keep the nearest interaction target readable instead of laying a uniformly opaque rectangle over the entire screen.

## Depth-aware does not mean physically volumetric

A background-only veil can soften the sky and distant scenery but cannot fog objects at different depths correctly. A single full-screen overlay also treats foreground, background and UI alike unless explicitly masked. A painter-ordered engine can instead use a few depth bins, per-object tint factors or correctly interleaved layers. Each approximation needs a declared limitation where objects overlap.

One practical progression: first test static depth tint; then add one or two slow density masks; only afterward decide whether a low-resolution depth surface is worth its cost. Do not implement all three approaches simultaneously. Clouds in the skybox and fog around blocks are different layers and should not accidentally double the opacity.

## Stable noise and edges

Ordered dithering can soften banding in a coarse gradient. Anchor the pattern deliberately: screen space may appear to slide over the world; world space can reveal grid changes as objects move; texture space adheres to a surface but is not a volume. Keep the convention explicit. Preserve cutout transparency and avoid dark fringes from mixing straight-alpha and premultiplied-alpha assumptions.

A low-resolution fog mask can be updated less often than the foreground scene, then smoothly reused. This is a performance hypothesis; no frame-time result was measured. A slow-moving veil can still be expensive if it invalidates a large cached world surface on every update.

## Evaluation, not horror direction

Try one open horizon, one near wall and one moving payload. Check clear near controls, gradual distant loss of contrast, stable edges during camera movement, correct compositing through cutouts and no abrupt view-distance boundary. This research does not add horror cues to the opening. Silent Hill is a technical atmospheric reference, not an instruction to change the tutorial's mood.
