# Pistons and redstone: the useful comparison

## Observed Create example: PistonScenes.movement

The scene starts with a five-block-wide platform. It reveals the drive and piston, creates an independent section, offsets that section immediately, and merges additional revealed parts into it. Activation is accompanied by explicit redstone indication, power-state toggles and reversed displayed kinetic speed. The section then moves **two blocks over 40 ticks**. The accompanying text lasts 55 ticks and a 65-tick delay allows movement and explanation to settle. Later movements reverse the same delta. [Source](../SOURCES.md#c-pistonscenes).

The sticky-piston explanation changes the displayed head state after a slime-ball input prompt. A further chassis is introduced as another independent section. Near the end, both groups receive the same translation and duration. There is no `animatePistonHead` helper in this inspected example. The central abstraction is group motion plus explicit state changes, not a new physical piston solver. [Source](../SOURCES.md#c-pistonscenes).

The registry associates `mechanical_piston/anchor` with `PistonScenes::movement`. Its NBT is scene geometry, not a self-contained animation or a standalone model dependency bundle. The Create assets directory has a separate rights declaration from the Java code. [Registry](../SOURCES.md#c-registry), [license](../SOURCES.md#c-license).

## Observed Bloc baseline

`PistonMotion.progress(now_ms)` is a clamped elapsed-time fraction. `iter_moving` interpolates payload coordinates from start to end, and `moving_final_targets` exposes destination cells during active motion. The simulator uses 50 ms logic steps; piston proposal commits create a 100 ms motion. Active payload handling already has regression coverage. This project does not need “its first interpolation system.” [Implementation](../SOURCES.md#b-redstone), [tests located](../SOURCES.md#b-redstone-tests).

The main application's render-loop body could not be read through the connector because the file exceeded its content limit. Consequently, this kit does **not** assert whether every existing visual part uses the interpolated payload correctly. That is the first inspection task for an agent with a local clone.

## Arithmetic comparison, not a benchmark

Ponder uses 20 ticks per second in its builder API. Thus 40 ticks is 2 seconds. Moving two blocks in that time gives 1 block/second. A one-block, 100 ms Bloc event corresponds to 10 blocks/second. The explanatory Ponder motion is therefore ten times slower in this specific comparison. [Tick convention](../SOURCES.md#p-builder), [scene](../SOURCES.md#c-pistonscenes), [Bloc](../SOURCES.md#b-redstone).

At an assumed stable 60 frames/second, the 2-second section movement spans about 120 frame intervals; a 100 ms move spans about six. At 30 frames/second it is approximately three. These are calculated opportunities to display motion, **not measured frame rates**. See [checked arithmetic](../qa/arithmetic.json).

This difference can explain part of the subjective smoothness without establishing a renderer defect. Preserve gameplay timing. A tutorial can choose slower presentation independently, or explicitly demonstrate a slow-motion view without changing canonical simulation semantics.

## Two additional anchors

**BearingScenes.windmillsAsSource:** after assembling sails around a bearing, the storyboard turns the camera by −90 degrees and waits before activation. The bearing and its section receive coordinated 360-degree, 200-tick rotations. Later reverse rotations and an immediate endpoint adjustment are again applied to both. The teaching device is matched animation channels and deliberate framing. [Source](../SOURCES.md#c-bearingscenes).

**RedstoneScenes.sticker/contact:** sticker and attached plank share a pivot. Both rotate while attached; after a scripted detach only the sticker rotates. The contact scene schedules redstone toggles around authored angular crossings. These examples illustrate presentation of causality, not evidence that every result came from unconstrained circuit simulation. [Source](../SOURCES.md#c-redstonescenes).

## Bounded diagnostic protocol for future agents

Use the existing local redstone tests and visual-check entry points. Record one extend/retract cycle with frame timestamps. Inspect the application use sites of `iter_moving`, `moving_final_targets` and `piston_motion_at` before proposing code changes. Establish whether head/rod/payload share phase; whether final-cell geometry is suppressed; whether caching reuses a stale pose; whether a foreground occluder maintains order; and whether a missed frame rather than interpolation caused the jump.

Only after that diagnosis choose a change. A shared presentation transform or corrected draw-cache invalidation may be enough. A whole new scheduler, easing framework or renderer migration is not a justified first response. Keep save/load, undo, destination state and redstone timing unchanged, then compare actual captured frames with the same scene and viewpoint.
