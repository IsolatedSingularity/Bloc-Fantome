# Open Problems: Bite-Size-Minecraft (Bloc Fantôme)

This document catalogs open problems, unresolved challenges, and improvement areas for the **Bite-Size-Minecraft** (Bloc Fantôme) isometric 2.5D voxel building sandbox.

---

## 1. Algorithmic & Implementation Problems

- **3D Isometric Depth Sorting (Painter's Algorithm Limitations)**
  - **Problem**: Standard Painter's Algorithm depth sorting fails when rendering cyclic overlaps, complex overhangs, or multi-block stair/slab intersections in 2:1 dimetric isometric projection.
  - **Context**: Currently relies on heuristic $(x + y + z)$ ordering and tie-breaking. A topological sort or screen-space span buffer is needed to resolve visual glitching on dense custom structures.
- **Liquid Flow Simulation Scalability**
  - **Problem**: Improving the cellular automaton liquid flow simulation (water and lava) without stalling frame rates on large voxel grids.
  - **Context**: Currently capped at 8 batch updates per tick. Needs a spatial worklist or dirty-chunk queue to simulate realistic propagation across multi-level basins.
- **Multi-Block Selection Memory Efficiency**
  - **Problem**: Optimizing undo/redo memory footprint during large-scale selection box operations (fill, copy, paste, delete).
  - **Context**: With a 100-step undo history, storing full sparse-dictionary snapshots after massive volume fills causes high RAM usage and garbage collection pauses.

---

## 2. Bugs & Unresolved Issues

- **Face-Based Raycast and Click Detection at Extreme Z-Levels**
  - **Problem**: Selecting specific faces (top, left, right) of blocks at high Z-coordinates or near screen edges can miscalculate target voxels due to sprite bounding box overlap.
  - **Status**: Requires sub-pixel polygon mask hit-testing rather than bounding-box or heuristic distance checks.
- **Asset Extraction Resilience (`setup_assets.py`)**
  - **Problem**: Handling incomplete, modified, or resource-pack-overridden Minecraft 1.21.1+ JAR archives during local texture and audio extraction without crashing sprite initialization.

---

## 3. Theoretical & Scientific Problems

- **Non-Injective Dimetric Coordinate Inverse Mapping**
  - **Problem**: Resolving the mathematical ambiguity of projecting continuous 2D screen coordinates $(X, Y)$ back into discrete 3D voxel coordinates $(x, y, z)$.
  - **Context**: In 2:1 dimetric projection, infinitely many 3D grid points project to the exact same 2D screen pixel. Formal mathematical invariants are required for deterministic ray-voxel intersection.

---

## 4. Code Maintenance & Refactoring Opportunities

- **Monolithic Codebase Decomposition (`blocFantome.py`)**
  - **Opportunity**: `Code/blocFantome.py` is currently a monolithic file (~800 KB). Although modular directories (`engine/`, `ui/`) exist, core loop logic, rendering, UI event handling, and world state should be cleanly separated.
- **Adaptive Sprite LRU Caching**
  - **Opportunity**: Replace the hardcoded 500-entry LRU eviction limit for lit block sprites with a dynamic, memory-budget-aware cache to accommodate high-resolution texture packs.
