# Animation primitives: exact behavior versus extensions

## Translation and rotation

`AnimateElementInstruction` is nonblocking. For a positive duration `N`, its constructor stores `deltaPerTick = totalDelta / N`. On the first tick it resolves the element and captures an endpoint, `target = getter(element) + totalDelta`. On each noncompletion tick it adds `deltaPerTick` to the value returned by the getter; the completion branch instead sets the captured endpoint. In the inspected revision, that completion branch invokes the setter twice. This basic isolated motion is **linear**, not a spring, Bezier curve or universal ease-in-out system. [Interpolator](../SOURCES.md#p-animate).

`TickingInstruction.tick` calls `firstTick` before decrementing `remainingTicks`; the derived animation then checks whether the remaining count is zero. It does not recompute a base-plus-elapsed-fraction value on every tick. A zero-duration instruction takes the endpoint branch immediately. The section adapter passes `force=true` for zero duration, synchronizing previous and current presentation values so the immediate move is not interpolated from stale state. [Tick lifecycle](../SOURCES.md#p-ticking), [adapter](../SOURCES.md#p-move).

For an isolated instruction, a useful continuous explanation is

```text
u = clamp((time - start) / duration, 0, 1)
position = base_position + delta * u
```

This is an explanatory equivalent for positive duration, not the exact source algorithm or a first-tick scheduling specification. The distinction matters if multiple instructions write the same property: incremental getter-based updates may accumulate other modifications, while their separately captured endpoints may conflict at completion. Do not silently substitute an absolute tween and claim identical overlapping-instruction semantics. For a future Bloc implementation, explicitly choose a single owner or composition rule for each animated property.

## Tick state and displayed state

Sections retain previous/current translation and Euler rotation. Rendering interpolates between them using the partial tick. The world selection's geometry can remain cached while its presentation transform changes. A section begins with a pivot derived from its selection; the storyboard can set a different center of rotation. Picking uses inverse transforms. [Source](../SOURCES.md#p-section).

**Proposal for Bloc:** calculate every visible part of one piston event from one sampled progress value. Do not let the payload read one clock, the head another, and cache invalidation a third. A fractional position should survive through projection until the rasterization boundary. These are diagnostic requirements, not claims that the current renderer violates them.

## Primitive inventory

| Primitive | Observed role | CPU/2.5D adaptation consideration |
|---|---|---|
| Select a region / independent section | Group visible geometry without moving canonical schematic cells | Reuse existing model/draw descriptors; stable IDs and membership |
| Reveal / hide / merge | Stage complexity and assemble a group | Keep visual membership separate from editable world topology |
| Translate / rotate about pivot | Rigid group motion | Translation is much cheaper than arbitrary 3D rotation of a cached flat sprite |
| Change block state / block entity data | Explain a mechanism's state | Decide explicitly between a scripted demonstration and live simulation |
| Camera turn / framing | Reveal otherwise hidden structure | Preserve Bloc's established view model; do not impose full 3D free orbit |
| Text / outline / input prompt | Identify target and requested action | Render after world geometry; hit targets must track transforms |
| Keyframe / reset / seek | Navigate explanation | Snapshot and replay policy; not arbitrary reverse execution |
| Effects / particles | Mark a state change | Bounded, reusable effects rather than continuous decoration |

Inventory is grounded in [SceneBuilder](../SOURCES.md#p-api), [PonderSceneBuilder](../SOURCES.md#p-builder), [section implementation](../SOURCES.md#p-section) and [Create helpers](../SOURCES.md#c-builder). It is not a promise of a one-to-one portable API.

## Pivots and rotations

For column vectors, a useful own-engine convention is `M = T(offset) T(pivot) R T(-pivot)`. Document the chosen rotation order. Ponder's section code uses Euler-component transforms; an independent implementation must not assume all matrix libraries multiply in the same order. Replacing it with quaternion shortest-path interpolation could incorrectly turn a deliberately scripted 540-degree rotation into a shorter spin.

Bloc uses a different axis convention from Java model coordinates. Establish the Java `(x,y,z)` to renderer `(x,z,y)` mapping before transferring a direction, pivot or offset. Preserve the existing conversion instead of scattering special cases through animations. [Model reference](../SOURCES.md#b-models), [renderer excerpt](../SOURCES.md#b-model-renderer).

## Easing is an optional artistic change

First reproduce a bounded reference with the source's timing and interpolation. Only then compare alternatives. A slow educational reveal and a 100 ms gameplay piston have different purposes. Do not change simulation speed to make a tutorial look graceful. A new display easing function must still end on the exact canonical pose and handle interruption/retraction without a discontinuity. No new easing code is included or recommended as an automatic fix.
