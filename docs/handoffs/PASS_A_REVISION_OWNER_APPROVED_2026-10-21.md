# Bloc Fantôme | Consolidated Pass A-R implementation
**Owner decisions finalized 21 October 2026. ONE coherent Codex development pass; not an experimental UI study.**

## Repository / precedence

Repository: IsolatedSingularity/Bloc-Fantome.
As of handoff drafting, existing development branch was codex/pass1-owner-review-2026-10-20 at e301fcbcb90c0ab3812be56c58c801d27578392c; owner Pass A implementation is aa5f6f9fb9a7f450df5e6f382bef7d6a3000357e; accepted main is 175686c21649a8d37826f8a22850c85482a69fd9. **These are historical references: check live HEAD, status, owner edits and local AGENTS.md, preserve existing work.** Read CONTRIBUTING.md branch policy, [full owner roadmap](OWNER_ROADMAP_AFTER_PASS_A_2026-10-21.md), [Owner Pass A review](../reviews/owner-pass-a/REVIEW.md), current implementation, and applicable design-system notes. Do not infer installed acceptance.

BRANCH POLICY: Do not create another topic branch. Use the existing active development ref for this task. Prefer a single neutral-name development branch, not agent/tool-prefixed names. A safe rename to development may be performed only after checking remote/local worktrees, refs, collaborators, and whether it would create stale duplicate branches. Existing historical branches must be consolidated/retired carefully, never by speculative deletion/rewrite. Do not rename just to satisfy this instruction if unsafe. Main remains accepted, preserved.

## Goal and priority

Pass A is **ON HOLD** after the owner's physical playtest. Fix real large-world edit/input and camera lag FIRST, then a thoughtful full-application UI craft revision. The visual target is the same modern Segoe, subdued dark UI the owner likes, **slightly blue and translucent, tighter, and extraordinarily crisp**. Do not begin Pass B audio/cinematics or the original-creature replacement.

**Time/scope discipline:** two coherent internal slices within this single assignment: (1) performance and user-visible correctness, (2) design/interaction polish and QA. Keep scope bounded; no engine rewrite, new GUI framework, asset pack replacements, excessive tests without purpose, endless branches or unreviewed ancillary features.

## 1. Large-world stalls and blocks that do not place

The owner still sees large stalls loading, zooming, panning and editing. In some worlds, placement appears to do NOTHING. Primary reproduction target: **underwater Ocean Monument world, ocean_monument_1161**, both in the tutorial liquids lesson and the ordinary loaded scene (as available). Also test village_plains_1161, Ancient City, Trial Chamber as representative larger cases. Preserve saves and editable full-world fidelity.

Read Pass A profiling, particularly staging-versus-activation-versus-first-paint timings. Pass A used paged draw orders and incremental edits, but a nominal ~0.6-1.2 ms placement handler does NOT prove the user sees a placed block; a sampled ocean-monument edit+render took ~720 ms, first complete image ~1.16 s, and camera frames reached ~406 ms. Atomic full repaint hides the sweeping redraw but may produce disruptive blocking instead.

Trace the full path:
- Real mouse/OS input -> hit tests, overlay capture, world-to-screen/pick target -> requested operation -> world revision/cell mutation -> actual rendered pixel result -> undo/save/reopen.
- Confirm whether the failure is blocked/occluded placement, stale hitbox, input priority, worker transition, valid edit delayed by render, unwanted water/terrain interaction or incorrect staging. Record a genuine failing example and repair the cause; don't guess.
- Measure the expensive full-screen traversal/composition path for pan, zoom, fit, and rotation, including cache selection/invalidation. Implement a measured, bounded improvement (chunk/viewport/local repaint or other equivalent proven path) while preserving exact global painter order, glass/liquids, all rotations, special materials, world selection and native/Python fallback.
- Do not fake smoothness by concealing UI operations, changing world fidelity, dropping blocks or displaying stale images as final output. Preserve a responsive progress/loaded indicator if initial staging is intrinsically expensive.
- Native regression must place a block in the ocean-monument world with a human-like actual click and verify the cell and visible projection, then pan/zoom and verify it persists, undo/redo, save/reopen. Give before/after camera/first-frame/edit timings, input-to-visible-change, p95/max, and visual proof at realistic viewport complexity. Do not extrapolate robust p95 from 2-5 samples. If performance still holds, report HOLD accurately, not success.

## 2. Real pixel-art fidelity, no texture pack

Owner wants recognizable original Minecraft pixelated art, not a finer texture pack and not newly invented HD textures. Current zoom still looks low-quality. Investigate exactly which stage blurs or damages the original: source resolution, sprite face projection, nearest/smooth scaling policies, intermediate surface resampling, subpixel positions, repeated transforms, alpha/camera compositing and DPI. Distinguish intentional source pixels from unintended interpolation blur, shimmer/aliasing, jagged projection and low-resolution UI chrome. Use a small side-by-side native zoom comparison (near, normal, far) to choose the best faithful output. Bound cache costs, preserve texture/source bytes, transparency, picking alignment and frame-rate. Do NOT vectorize Minecraft bitmap textures or silently insert a resource pack.

## 3. One cohesive UI design system, sharp at all scales

Inspect the CURRENT native screenshots at 960x640, 1200x800, 1920x1080, 100/125/150% in-app text, windowed/fullscreen. Verify OS DPI at 100/125/150/200% only where actually possible. Reference:
- Apple HIG Layout: https://developer.apple.com/design/human-interface-guidelines/layout
- Fluent 2 layout: https://fluent2.microsoft.design/layout
- Fluent 2 tokens: https://fluent2.microsoft.design/design-tokens
- Fluent 2 typography: https://fluent2.microsoft.design/typography
- Pygame gfxdraw: https://www.pygame.org/docs/ref/gfxdraw.html
- Pygame freetype: https://www.pygame.org/docs/ref/freetype.html
- Pygame transforms: https://www.pygame.org/docs/ref/transform.html

Translate these into a small shared set of meaningful tokens: slightly **NAVY dark, semitranslucent** matte panels, consistent padding, gutters, measured type scale/line-height, purposeful hierarchy, careful focus/hover/pressed states, corner radii, semantic accents and animation timings. Favor a 4px baseline spacing ramp (with small optical adjustments), but **do not mechanically make every box identical**. Panels should fit text and content closely without vast header/footer or dead areas. Save clear readability over bright and dark backgrounds. Keep Segoe UI native and never redistribute Microsoft's proprietary font.

Current rounded edges and some labels visibly rasterize poorly. Use resolution-independent shape/icon definitions with scale-specific native-pixel-density antialiasing, correct DPI transforms and measured font rasterization. Pygame is eventually raster; 'vector-quality' means final native-resolution raster rather than scaling a bitmap of the UI. If small reusable corner/icon buffers need supersampling, keep them bounded and cache by scale. Do not supersample the whole world/UI each frame, break event hit boxes or introduce an incompatible GUI toolkit.

Keep the four-second inactivity fade/reveal behavior, fast any-motion reveal, reduced-motion, keyboard/F1 recovery and correct hidden hitbox suppression. Allow contextually necessary active tools but remove repetitive prose/noisy status. Preserve block-art hotbar and real tool/property access.

## 4. Build: actual vertical category navigation

CURRENT app has TWO horizontal category tabs and a next arrow. Owner wants a **genuine VERTICAL icon-and-text category rail** integrated into the Build drawer, not another horizontal tab strip. On wide layouts leave adequate thumbnail grid area; at 960x640 / 150% text switch to compact two-step category -> material gallery if a rail would crush cells. Keep 464 material identities and full catalog, search, favorites, preview, property and hotbar assignment. No visible 'Recent' category; internal history can remain.

Remove footer prose like '7 materials · Favorite / Ctrl+D', 'Favorite', contextual instruction counts and redundant yellow selected-material labels. Restore logical focus/discoverability through tooltips/Controls without replacing one noisy instruction with another. Preserve deliberate thumbnails; no list of bare filenames.

## 5. World: Control Center, genuinely icon-only

Use an intentional grid of distinct rounded control tiles, whose PRIMARY toggles contain a **centered ICON ONLY** and no permanent text, state indicators or labels cluttering the surface. Tooltip on hover and keyboard focus communicates concise name and state; meaningful selected/off color remains. The icon itself must be visually unambiguous and nonrepeating across functions. In-tile motion should reflect *real active states*, e.g. droplets for rain, unique snow, rotating sun/moon, cloud drift, flicker/rays for lighting, liquid flow. Disable unnecessary motion under reduced motion. No generic oscillation for every tile. Make icon/tile overlays delicately translucent but legible.

Dimension changes, terrain generation/noise, sky selection and destructive actions are NOT toggles; put them in a compact separate action area with smaller controls, not a never-ending command list. Preserve all actual World capabilities.

## 6. Library: detached illustrated four-choice home and meaningful transformation

Opening Library should NOT launch the current enormous tabbed file-explorer pane. Instead show a **floating, compact landing palette** detached from top bars, with FOUR large category tiles: Worlds, Biomes, Structures, Saved Builds. Each has a unique original illustration/icon plus ONE word underneath. Favor **one horizontal row of four tiles** when enough room; use 2x2 responsively when that produces a better composition. The owner considers both; prioritize clear compact beauty rather than religiously enforcing an orientation.

On selecting one tile, transform/expand/recompose THIS palette into a browse gallery with actual previews and selection information; make back/close motion feel reciprocal and responsive, not arbitrary teleport or long uninterruptible transition. Inspiration: the functional reveal/transform rhythm of **Ratchet & Clank (2002) Gadgetron store**, not its licensed artwork, sounds, colors, characters or exact UI. If actual 2002 interaction footage is unavailable, say so rather than pretending newer Ratchet interfaces prove the original transition.

Browse panel should prioritize thumbnail imagery, short names and a clean selected preview; avoid a spreadsheet/file tree, permanent wide tab row, giant empty side pane or verbose headers. Explicit Open versus Place. Simply clicking a tile must NOT replace a world, place a structure or mutate saves. Preserve import/cancellation and all four source categories, with realistic performance. No new third-party sprites without licenses.

## 7. Menu, Tools and canvas actions

MENU should be a compact grouped command dashboard, not a monotonous list. Strong primary actions (Save, Open, Settings); secondary clusters for view/fullscreen, tutorial/help, history, quick save/load etc. Every action from the prior capability map must remain reachable and functional. This is ordinary consistent navigation; **Library alone** gets the distinctive transforming gallery animation.

TOOLS stays a right-anchored panel with separate tool and keyboard/shortcut scrolling, but move every little diagonal tool-specific glyph INSET from the LEFT side of the row to the RIGHT; refine material, silhouette contrast and consistency. Label lower section 'Hotkeys', display key chords prominently (short keycaps) and subdued italic descriptions. Keep correct shortcuts including prominent Ctrl+Z Undo.

Bottom-right plus / minus / terrain noise actions MUST regain meaningful colored 3D terrain/isometric thumbnail previews. Render clean scale-aware thumbnails; do not replace with bare plus/minus glyphs.

Shrink Canvas: remove verbose confirmation modal. **Never silently delete user blocks:** if the requested shrink would clip occupied cells, safely refuse or otherwise preserve through existing undo/rollback and give a SMALL non-modal contextual cue. Allow ordinary safe shrink directly. Decide by inspecting actual world bounds/undo ownership.

Remove bottom-left redundant Fill/More tools/selected-item prose; when HUD hides, no lingering material identity or Unsaved text should remain. Preserve special block actions via tools/hotkeys/properties, actual save state and undo internally.

## 8. Verification and delivery

- Begin from a known-good actual checkout and owner private assets. Preserve installed/root EXE, user data, history, prepared tutorial caches (rebake if fingerprints change), playback/media provenance. Reversible isolated review package only; no installed replacement or main promotion.
- First reproduce actual ocean-monument failure and benchmark the lag on the exact baseline BEFORE modifying it, then implement the smallest compatible fix.
- Real native screenshots must cover Build vertical rail and narrow fallback, Library home -> transition -> gallery -> back, icon-only World on/off, Tools hotkeys right icons, compact Menu, plus/minus/noise thumbnails, clean/hide state, terrain/content bright/dark, sharp close-up font/rounded corners, source block zoom comparisons, saving/errors.
- Use actual OS mouse and keyboard where possible, not just scripted object calls. Record any unavailable physical trackpad or OS DPI target honestly. Preserve legacy source evidence and regression history, run focused tests and one final full suite.
- Verify visible placement/persistence and responsiveness, not just automated pass counts. Report SOURCE, TEST, NATIVE USER INPUT, VISUAL, PERFORMANCE, INSTALLED separately; full equality, pixel differences and slowdown tails must be accounted for. Explicit HOLD if unresolved. A human owner review is the final artistic acceptance gate.
- One coherent review commit/checkpoint on the same active branch, with a short evidence index and rollback status. Do not start Pass B, creature redesign, Redstone Map, or unrelated block behavior rewrites.

**Future roadmap:** Pass B = professional modern UI sounds, correct Minecraft-world block/environment sound classification, monumental localized cathedral impact/reverb and deep heterogeneous human creature vocals, a single temporary rig animation, moving faceted black sea and full-intro Skip. Pass C = engineering/UX/consolidation. Pass D = wholly ORIGINAL dark low-poly horror creature replacing recognizable Twilight Thorn IP, with planted IK/supports, pronounced asymmetry, architecture and actual rendered creative reviews. Later = wider block mechanics/fidelity backlog. Full owner decisions: OWNER_ROADMAP_AFTER_PASS_A_2026-10-21.md.
