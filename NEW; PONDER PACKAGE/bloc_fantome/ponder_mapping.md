# Mapping Ponder onto the existing project

All entries in the right-hand column are **proposals**, not changes made by this kit. Existing behavior is grounded in the linked baseline notes and sources.

| Ponder concept | Existing Bloc foothold | Small compatible extension to investigate |
|---|---|---|
| Independent visual section | Model geometry plus moving payload descriptors | A transient group transform, initially translation-only |
| Tick state + partial tick | Elapsed-ms `PistonMotion.progress` | Shared visual phase for payload/head/rod; no second competing timer |
| Section cache/redraw | World render caches and electrical-only draw-list reuse | A defined presentation-only invalidation path |
| Scripted explanation world | Tutorial snapshot/staging runtime | Isolated demonstration state with reliable restore |
| Input prompt followed by action | `tutorial.record(...)` and `observe(...)` | An explicit gate for one existing interaction event |
| Text/outline tied to a target | Existing UI and component positions | Attach annotations to the displayed transform, not stale source cells |
| Ponder camera orbit | Bloc's established rotated isometric views | Bounded framing/transition work, not automatic 3D camera replacement |
| NBT starting schematic | Existing world/model/import infrastructure | Reuse loaders when compatible; do not assume Create block dependencies exist |

Sources: [Ponder architecture](../ponder/architecture.md), [Ponder rendering](../ponder/rendering.md), [Bloc baseline](current_architecture.md).

## Two owners, one consistent picture

**Recommendation:** let the simulation own canonical block/state changes and let presentation describe a transition between two valid states. The visual transition should not itself execute a second piston push or recalculate a circuit. Conversely, an explicitly scripted tutorial demonstration may choose displayed states independently, but it should be labelled and isolated from live editable builds.

For a proposed moving group, useful data might be membership, start/end pose, progress source, pivot, and destination suppression. That is an inventory of responsibilities, not a prescribed new class hierarchy. Search the existing application for those responsibilities first and consolidate only where needed.

For a proposed interaction gate, distinguish the explanation clock from the user's response time. Waiting for a click should not continually trigger the same cue or replay a sound every frame. Cancel, skip and exit must restore control and scene state. The current tutorial snapshot/event machinery already offers an integration point. [Source](../SOURCES.md#b-tutorial).

## Fidelity boundary

First match one inspected behavior closely enough to compare it. A scripted group translation is a good candidate because it does not require all Create models or arbitrary 3D rotation. Record timing, visibility, direction and end state before trying a new artistic treatment. Do not import Ponder's entire visual identity, reinterpret the introductory disc design, or replace existing gameplay with demonstrations.

A source importer is not an automatic port. Storyboards contain Java callbacks, loops, mod block IDs and Create-specific helpers. A filename/method index can guide an agent to the right code, but it cannot reliably translate all callbacks into an engine-neutral timeline without semantic analysis.
