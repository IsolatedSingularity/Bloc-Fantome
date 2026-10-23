> Historical evidence. Status and branch names below apply to the recorded date.
> Current direction: [roadmap](ROADMAP.md). 3.0 is accepted; 3.1 is engineering review.

# Engineering review, October 20, 2026

**Disposition: Engineering HOLD on existing performance gates. Functional fixes
are verified on a review branch. Creature development is deferred to the owner's
later chat; the active 2.9.8 opening remains unchanged.**

Start: `main@175686c21649a8d37826f8a22850c85482a69fd9`.
Verified functional source: `e108c0130a26275e688c081e85072d1cbac71279`.
Branch: the historical engineering consolidation branch. Final publication SHA is in the chat handoff.

Origin's main baseline was verified live. Embryo started clean with one worktree.
The secondary GitHub checkout was at `68cb7a9a85a75449ed47eaefd9feed9fee612a31`
with untracked `Assets/Opening/`; it was inspected without modification. README,
main, the installed application, root EXEs and rollback installers are preserved.

## Significant corrections

- Undo/redo retains commands on exceptions. Biome loads reject stale edit,
  canvas or mode results. Finished/cancelled guards release old world references.
- Atomic preference writes preserve previous JSON on failure. Tutorial, map and
  lab sessions retain and restore editor sky selections.
- Compact captures now verify payload hashes, recovering from altered
  same-length, missing, truncated or damaged derived records through exact source
  data. All 95 compact metadata records were regenerated without changing cells.
- Prepared lessons validate schema/Python, paths, digests and source fingerprints.
  Partial rebakes retain compatible lessons; exact fallbacks remain and builds
  reject damaged/incomplete bundles. Pickle remains trusted build output. NumPy
  was declared and the venv repaired; runtime/test/build requirements are separated.
- Shadowed legacy enum, World and renderer definitions were removed; canonical
  owners/public imports remain compatible. Async completion moved to
  `engine/world_loading.py`, reducing the composition root by about 1,100 lines.
  The inherited tutorial implementation remains in use.
- Cleanup now tolerates a source checkout without installers. Its dry run,
  tracked-file protection and bounded removal are tested. Workspace cleanup was
  dry-run only.

## Consolidation

The baseline had 20,414 tracked files / 3,610,153,054 bytes. The current tree is
about 1.413 GB. [The recovery index](QA_ARCHIVE.md) covers 4,899 generated
artifacts / 2,197,710,239 bytes, including 723 duplicate-content copies.
Independent extraction and SHA-256 comparison preceded untracking. Originals,
ZIP, verified extraction and baseline history remain available.
Source worlds/captures, scripts, audio sources, research, saves and unknown
ownership were retained. About 736.7 MB of tracked QA remains intentionally.
Historical clone size is unchanged; local disk use increased with recovery
copies. No history rewriting or garbage collection occurred.

## Controlled performance

Windows x64, Ryzen AI 7 350, 32 GB RAM, Radeon 860M, Python 3.12.10 and Pygame
2.6.1. Large-world runs used Rust acceleration, 1200x800, isolated writable caches
and five repetitions. Cold composition now waits for complete surfaces and clears
the whole-view reuse cache; former first-batch timings were misleading.

| Measurement | Before | After |
| --- | ---: | ---: |
| Lighting-scene view-index median | 279.34 ms | 215.65 ms |
| Exact lighting-source preparation median | 3.179 s | 2.918 s |
| Ancient City cached-load median | 1,501.8 ms | 1,441.6 ms |
| Trial Chamber cached-load median | 1,800.2 ms | 1,748.3 ms |

The lighting comparison alternated implementations after warmup in one process.
Visibility, painter orders and the 287,831-cell light map matched exactly across
the 325,478-cell scene. View rebuilding improved 22.8%; overall preparation
improved 8.2%. Queue deduplication was separately measured slower and discarded.
Large-world cached-load gains are modest and remain above the 1,000 ms gate.
After-change stable editor p95 was 1.74/1.70 ms; world surfaces used 14.33 MB.
Results depend on these conditions.

Final lighting timings: 1.088 s first bundle read/fingerprint/decode on the worker,
3.024 s median warm-source preparation, and 273 ms main-thread application.
The standalone native 1080p encounter profile measured p50 8.80 ms, p95 16.61 ms,
maximum 17.93 ms over 180 samples with `glFinish`, and zero GL errors.

## Verification and remaining gates

- Full suite: **417 passed**. Tracked-source export without private media or
  prepared bundles: **159 passed, one explicit skip** for the optional local Java
  reference corpus. Python acceleration fallback: **18 passed**. The original
  baseline's nine temp-directory failures were setup issues, resolved by workspace
  fixture roots. Diff/compile checks passed.
- Inspected completed UI captures at 960x640, 1200x800 and 1920x1080; generated
  75 UI and ten complete representative world images. The eight-frame camera
  assertion is retained: plains still requires nine frames after a settled load,
  or 26 initial batches for 20,150 cells. This remains a HOLD, alongside cached
  loading. No budget/assertion was relaxed.
- Hidden real startup and the full original encounter passed focus-loss, two GL
  context recreations, world/revision/camera/window/tutorial restoration and audio
  channel cleanup. Its capped application clock p95 was 20 ms over 2,577 frames;
  distinct from standalone rendering above.
- Isolated one-file diagnostic build and archive checks passed. NumPy, native
  acceleration and prepared lessons were present; deferred creature modules were
  absent. An 18-second hidden packaged startup used a workspace asset junction,
  logged no fatal errors and left zero processes. Installer/installed-launch
  verification, subjective audio and a long RSS soak were not performed.
- All 45 monitored save/settings/rollback files retained their hashes. Installed
  2.9.8 retained SHA-256
  `b90eeba07012c3e1818aafcd4e275673fa66e3e59d0d3cd5221a12337da040c7`.

Evidence is local under `.qa/engineering-audit/`: `stabilized-full.xml`,
`clean-stabilized.xml`, `visibility-comparison.json`, `benchmark-before.json`,
`benchmark-after.json`, `source-flow.json`, `package-startup.json`,
`native-final/native-profile.json`, `lighting-final/timings.json` and
`preservation-final.json`. Deferred drafts: `deferred-creature/`; unaccepted.
No installation or Start Menu changes were made.
