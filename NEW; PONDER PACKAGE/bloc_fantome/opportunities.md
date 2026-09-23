# Bounded future opportunities

These are an ordered inspection agenda, not a request to implement everything. Each experiment should be separately approved and preserve the last working baseline.

## First: audit the existing piston presentation

Read the local application call sites that this run could not obtain. Use the already-existing motion descriptors and regression tests. Check actual frames at extension start, midpoint, completion, reversal, and interruption. Include foreground occlusion and a long payload. The smallest useful result may be a corrected cache boundary or shared progress sample rather than a new subsystem.

**Acceptance:** no duplicate payload, no floating head/rod mismatch, correct foreground order in every supported view, correct final state, unchanged simulation/save/undo behavior. Frame-time evidence matters more than a syntactically valid implementation.

## Second: one independent translated group

Only if the current representation cannot express the needed visual transition, prototype a small presentation-only group using the existing model renderer. Start with translation, not free rotation. Make reset/cancel deterministic. Track whether geometry is rebuilt unnecessarily during motion and verify that static caches remain reusable.

**Acceptance:** the group and static occluders interleave correctly; its annotations and picking agree with the displayed pose. Do not silently substitute a topmost flat sprite when depth intersections matter.

## Third: one optional tutorial gate

Use an existing scene and existing progress event to test `play → wait for action → continue`. Do not design the full opening here. Reuse tutorial snapshots, tool cleanup and user-state restoration.

**Acceptance:** waiting does not advance the gated event; a single correct action advances once; replay/skip/exit are well defined; ordinary editing still works after exit.

## Later, independent atmosphere trials

Try one normalized skybox through the existing atlas path. Separately compare a face-anchored light mask or two-layer depth-aware fog. Do not combine sky, lighting, sound and motion changes in one opaque “polish overhaul.” Each should have an off switch and a before/after capture using a constant camera and scene.

The tutorial should remain quiet and welcoming in this phase. Horror foreshadowing, psychological content and a detailed monochrome disc layout are explicitly deferred to Jeff's artistic direction.

## Measurement boundary

No suggested CPU method has been benchmarked in Bloc Fantôme. Record scene size, viewport size, view rotation, cold/settled frame time, native/fallback path and memory use. Avoid promising 60 FPS from an algorithmic sketch. Preserve source-fidelity tests separately from subjective visual preference.
