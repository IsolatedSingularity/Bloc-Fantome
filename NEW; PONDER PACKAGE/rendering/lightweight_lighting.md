# Lightweight lighting: a bounded menu, not a new engine

**Scope:** possible future CPU/2.5D experiments. The current lighting implementation was not exhaustively audited, so these are not missing-feature claims. Ponder's fake-light rendering and the shader source are references for presentation choices, not proof of a physically accurate CPU lighting solution. [Ponder](../SOURCES.md#p-section), [shader](../SOURCES.md#v-final).

## Separate the contributions

A useful conceptual model is base texture × face shading × local illumination, with emissive contribution and atmosphere handled explicitly. A bright-looking glowstone texture, a halo around it, illumination of neighboring faces, and a cast shadow are four different effects. Name them separately in code and acceptance criteria.

**Directional face shading:** reuse the renderer's existing per-face information. A bounded face-normal dot product or an authored small set of brightness factors can make a cube readable without a light transport solver. Keep source textures crisp; do not accidentally interpolate their pixels because a light mask is smooth.

**Local illumination:** for a small scene, evaluate a bounded influence field around a few emitters and cache it. Distinguish radial falloff from occlusion. A light passing through a wall is a modeling limitation, not corrected merely by adjusting the falloff exponent. Use known occupancy/model geometry where a later experiment needs blocked light.

**Ambient contact darkening:** a few neighboring occupancy tests or a precomputed corner mask can emphasize contact. It is not directional cast shadow. Dynamic edits require local invalidation. Slabs, glass and non-cube models need different rules from opaque cubes.

**Emissive compositing:** keep a bright source core and a restrained separate halo; composite in a defined order with transparent geometry and fog. A large unconditional screen-space glow may brighten UI or shine through an occluder. Prefer a small masked pass and verify it under overlap.

## Color math

As an implementation proposal, perform light mixing in a consistent linear-light representation and convert to display space once. If the existing renderer uses integer tint multiplication, document the approximation rather than mixing conventions invisibly. Lookup tables can avoid repeated nonlinear conversions in a Python loop. Neither a gamma-correct formula nor a GPU-style tone mapper compensates for stale geometry or wrong depth order.

## A small acceptance scene

Use one luminous block, a wall, a slab, a transparent block and a moving piston payload. Capture all supported views with lighting on/off and after an edit. Check that the texture remains legible, the source and neighboring faces are distinguishable, an occluder behaves according to the declared model, and a moving payload does not retain a stale lighting state. Do not redesign the tutorial to run this test.

## Avoid scope creep

Do not introduce OpenGL/WebGL, a deferred G-buffer, ray-traced global illumination or a new asset pipeline just to imitate a screenshot. A GPU shader may inspire coordinate quantization or palette treatment while none of its runtime architecture is appropriate to this project. Select one measurable improvement, leave current behavior as a fallback, and stop before adding unrelated effects.
