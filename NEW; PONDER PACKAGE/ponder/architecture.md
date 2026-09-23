# Ponder: architecture and timing

## Observed system

A `PonderStoryBoard` programs a scene through `SceneBuilder`. Scene registration associates a schematic resource with that program. The schematic supplies starting block/state data; the storyboard schedules changes; a virtual `PonderLevel` supplies Minecraft-compatible world access. Visible elements can refer to subsets of that same world. This is live scene rendering, not a stored video or a sequence of image files. [API](../SOURCES.md#p-story), [registry](../SOURCES.md#p-registry), [world](../SOURCES.md#p-level).

`PonderScene` owns the world, element links, active instruction schedule, camera transform, outlines, current/total time and keyframes. `PonderSceneBuilder` exposes separate world, overlay, effects and special-element interfaces. The underlying renderer remains coupled to Minecraft and Catnip. Calling Ponder “standalone” means separate from Create's gameplay mod, not independent of Minecraft's engine. [Scene](../SOURCES.md#p-scene), [builder](../SOURCES.md#p-builder).

## Scheduler semantics that are easy to mistranslate

`idle(N)` inserts a blocking delay. It does not suspend animations already scheduled before it. A movement instruction is nonblocking, so two movements followed by one delay can progress together. Blocking instructions control when later instructions become active. `idleSeconds(s)` expands to `20*s` ticks. [Builder](../SOURCES.md#p-builder), [ticking](../SOURCES.md#p-ticking).

The active-schedule loop processes instructions in order. It ticks an instruction, removes it when complete, and stops traversing at a blocking instruction. **The loop also breaks when that blocking instruction has just completed.** Do not silently replace this with a generic timestamp queue and then claim exact tick-boundary parity. [Source](../SOURCES.md#p-scene).

Conceptual example, not an extracted upstream scene:

```text
start move(A, +2x, 40 ticks)       # nonblocking
start move(B, +2x, 40 ticks)       # nonblocking
show explanation(55 ticks)        # own lifetime
idle(65 ticks)                    # later instructions wait; A and B continue
```

For a port, test the first active tick, completion tick and following-instruction tick explicitly. Numeric timeline totals inferred merely by adding source `idle` calls can miss boundary details, loops and helper-generated instructions.

## Restore and seek

Beginning a scene restores its virtual world and resets elements, links, transform and schedule state. Forward seeking executes ticks to the target and requests geometry redraw afterward. Seeking backward directly raises an error; it requires rewinding/restoring first and then replaying. This is not reverse playback of cached movie frames. [Source](../SOURCES.md#p-scene).

**Adaptation proposal:** use a compact initial snapshot plus reproducible events for a small demonstration. If seeking later becomes expensive, add occasional checkpoints only after measurement. A timeline containing user actions needs an explicit replay policy: replay recorded actions, stop at a gate, or reset to the gate. Never silently re-run arbitrary gameplay edits while scrubbing.

## Scripted does not mean inert

Ponder renders Minecraft blocks, entities, particles and block entities inside its virtual world. Visible section elements can execute block-entity tickers. Create extends the generic scene facade with belt behaviors, kinetic-speed changes, bearing animation and other mod-specific helpers. Some rendering behavior is therefore live code even when the educational sequence is authored. [Section](../SOURCES.md#p-section), [Create facade](../SOURCES.md#c-builder).

**Important separation:** an instruction that explicitly toggles a displayed redstone state is not evidence that a full redstone network solved that state. Conversely, it is inaccurate to say Ponder never invokes real component behavior. Inspect each helper to establish which layer owns the effect.

## The portable idea

The useful abstraction for Bloc Fantôme is a small presentation layer over an existing world, not a second Minecraft implementation. Proposed responsibilities: resolve a stable selection, attach a transform, schedule a visual change, draw an explanatory overlay, and yield to an existing interaction event. Keep canonical world state, simulation, persistence and undo under their current owners. This division is a recommendation, not an upstream Ponder API promised to run in Python.
