# Pixel-aligned shadows without a shader migration

## Observed: two actual implementations

**Pixel Perfect B** forms a camera-relative sample position from a quantized absolute position, then preserves components selected by the surface normal. The inspected expression is equivalent to

```text
q = ceil((p + c) * N) / N - c
m = ceil(abs(n))                    # componentwise
shadow_position = (1 - m)*q + m*p
```

Here `p` is the original camera-relative position, `c` is camera position, `N` is the configured grid density, and `n` is the normal. On an axis-aligned cube face the normal coordinate stays unchanged while the two tangent coordinates snap. The add/subtract of camera position anchors the quantization to the world. This is not a screen-space mosaic. [Exact implementation](../SOURCES.md#x-fragment).

Its language file describes matching shadows to block pixels and acknowledges Complementary as inspiration for its own implementation. A shadow-noise path also derives its sample coordinate from absolute position. The inspected code does not establish that arbitrary rotated meshes or every texture resolution receive perfect UV-space alignment. [Author description](../SOURCES.md#x-language), [noise excerpt](../SOURCES.md#x-shadow).

**Voxel Vibes** reconstructs a camera-relative position from depth, adds camera position, quantizes using `mod(..., 1/16.)`, then transforms the result into shadow-map space. Its source includes a `.999` position factor, an additional offset expression, a fixed bias and a shadow-distance cutoff. It compares that sampled shadow depth and applies an artistic color/exponent treatment. Its fog mixes towards sky color as distance increases. These are GPU implementation details to study, not a ready CPU library. [Source](../SOURCES.md#v-final).

The exact quantization line in that prototype contains both `1/16.` and `1/16`. Do not silently rewrite these literal types while claiming a bit-exact port; validate the intended offset in the target language. The useful common principle is a stable receiver-space lattice before shadow sampling, not wholesale copying of its artistic exposure treatment.

## Derivation of a CPU analogue (proposal)

For a block face with origin `o`, tangent basis vectors `a,b`, and source resolution `Nx,Ny`, evaluate a representative surface point per source texel:

```text
p(i,j) = o + ((i+0.5)/Nx)*a + ((j+0.5)/Ny)*b
```

Compute a coarse visibility or light value `M[i,j]` at those points, store it in the face's own mask, and sample that mask with the same UVs used for the face texture. The rasterized face and its lighting pattern then move together. This is a new adaptation proposal, not a claim that either cited shader implements this exact formula.

A world-grid quantizer works naturally for aligned Minecraft-like cubes. A face-UV mask is safer when a model has unusual UVs, rotated elements, or a different texel density. Choosing `N=16` because a block often has a 16-pixel texture is not enough for every model. The normal-preservation trick in Pixel Perfect also has special behavior for non-axis-aligned normals; do not generalize it without testing.

A shadow *grid* is not a shadow *solver*. The mask still needs a visibility source: an authored mask, a cached coarse ray query, a simple projected occluder, or a deliberately limited analytical approximation. Snapping coordinates alone does not make a block cast a shadow.

## Practical budget

A 16×16 mask holds 256 samples per face. Three visible faces across 1,000 blocks imply 768,000 samples before considering occlusion, sharing or caching. Recomputing those rays every frame is not “cheap” merely because the mask is small. Update only affected visible surfaces when geometry/light state changes, share appropriate reusable masks, and measure native and Python fallback costs separately.

For an animated object, decide whether a mask is attached to the moving object, recomputed from its world pose, or intentionally simplified. Otherwise its shadow can swim or remain behind. World-aligned noise can be stable under camera movement yet still change when the object crosses a lattice boundary. A texel-anchored mask solves a different stability problem.

## Keep these effects distinct

| Technique | What it quantizes | What it cannot guarantee |
|---|---|---|
| World/face anchored shadow samples | Receiver coordinates | Correct visibility without a shadow computation |
| Low-resolution shadow map | Light-space depth image | Alignment with every block texture |
| Discrete light levels | Brightness values | Fixed spatial edges |
| Ordered dithering | Distribution of quantization error | Real geometric occlusion |
| Downscaled final image | Screen coordinates | Surface-locked shadows under camera movement |

The first candidate for Bloc is a tiny face-local mask experiment using existing model UVs, not a full deferred renderer. Keep it separate from the piston work. No performance or visual-parity claim has been tested here.
