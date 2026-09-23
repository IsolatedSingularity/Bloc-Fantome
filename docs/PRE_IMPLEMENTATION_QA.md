# Pre-Implementation Adversarial QA

Date: 2026-09-23

## Baseline reviewed

- Repository: `IsolatedSingularity/Bloc-Fantome`
- Branch: `main`
- HEAD: `0391259c5ebc0519feb324477fdc1f62bc66ccb7`
- HEAD only adds `References/Excess/Shader.png`. The current application/test baseline is therefore the preceding code/QA checkpoint `1e5872617dc2f386b1d26b29abd3a4fa68f2db86`.
- The current `Code/blocFantome.py`, `Code/engine/build_io.py`, main integration tests, and recorded release QA all last changed at that same checkpoint.
- Recorded authoritative release suite: **333 passed** in `.qa/revision-292-packed-full.txt`. A separate earlier/focused final-suite artifact records 331 passed.
- GitHub Actions/CI: none present. Current HEAD has no workflow runs or status checks.
- Tree size inspected: about **19,580 tracked files / 3.49 GB**. `.qa` alone is about **8,649 files / 2.82 GB**.

This pass was read-only until this handoff was written. No implementation code was changed.

## What was inspected / tested

Inspected the repository tree, recent history, README, CONTRIBUTING, CHANGELOG, `nextIdeas.txt`, `.gitignore`, current handoffs, the refactor plan/open-problems files, requirements, runtime paths, source/frozen build scripts, installer/native acceleration, asset setup, persistence, world/snapshot/index code, undo, scene cache, asynchronous world/biome loading, world-library event handling, public-contract/integration/build-I/O/cache tests, and recorded release evidence.

The connected GitHub surface does not provide a runnable checkout here, so the complete suite and packaged Windows executable were **not re-executed** in this audit. The recorded 333-pass suite is applicable to the current code baseline because no code/test change occurred after it. Static/control-flow findings below were checked against current HEAD. A truncated-gzip behavior used by the loader was also reproduced independently: Python `gzip` raises `EOFError` for a truncated stream, which the current load path does not catch.

## Finding classes

- **Reproduced**: directly demonstrated in this audit or existing evidence.
- **Static proof**: follows directly from current control/data flow.
- **Hypothesis**: credible runtime failure still needing a focused reproduction.
- **Architecture/governance**: raises failure probability or agent ambiguity without being one immediate runtime bug.

# P0 — resolve before substantial further implementation

## P0-1 — Rolling backups are not equivalent to normal saves and can lose most of a large world

**Class:** static proof.

Normal saves use `engine.build_io.write_build()` and write v5: bounds, `min_y`, scene metadata, structure roles, liquid state, and modern block state.

`BlocFantome._saveBackup()` still writes a separate **v3** payload containing only dimension, coordinates/type, and a small subset of facing/open/slab state. It omits v5 bounds and scene metadata, liquid state, redstone state, piston/comparator/repeater state, oxidation, source provenance, structure roles, and other modern state.

On restore, v3 has no bounds, so `read_build()` uses the legacy default `12 x 12 x 12` canvas. Blocks outside that default are skipped. A rolling backup of a 64/128/256-sized editable world can therefore restore as a tiny, heavily truncated build.

There is no backup-specific regression test in the current suite.

**Acceptance:** generate a >12 world with negative `min_y`, liquids, door/stair state, redstone component state, structure roles and scene metadata; create a rolling backup; restore it; assert exact bounds, block map and serialized state. Prefer one serializer (`write_build`) for ordinary saves, autosaves and backups.

**Timing:** fix now.

## P0-2 — Autosave and backup rotation can report success after failed persistence

**Class:** static proof.

`_autoSave()` ignores the boolean result of `_saveBuilding(..., silent=True)`. It always advances `lastAutoSaveTime` and shows the Saved indicator even when the write failed.

Rolling backup rotation deletes the oldest backup **before** proving the replacement backup was written. `_saveBackup()` catches write failures internally and returns no success result, so the caller cannot distinguish success from failure.

A disk-full, permission, antivirus/OneDrive locking, or other write failure can therefore both reduce recovery history and positively tell the user that a save succeeded.

**Acceptance:** inject a write/replace failure. Assert no Saved indicator, no autosave timestamp advancement, and no deletion of an older recovery point until the new backup has been atomically committed and validated.

**Timing:** fix now, together with P0-1.

## P0-3 — Malformed-but-shaped saves do not fail closed

**Class:** static proof, with one underlying exception behavior reproduced.

`read_build()` skips invalid block rows individually. A payload with a non-empty `blocks` list where every row is invalid/out of bounds/unknown produces an empty snapshot and returns success. The app can then replace the live build with an empty canvas rather than preserving it.

Duplicate coordinates are also unsafe. `_snapshot_from_staged()` overwrites `blocks[position]` with the later row but only writes properties/liquid/role state when present. An earlier water/door/role row followed by a later plain block can leave stale liquid/properties/structure state attached to the later block.

Future save versions are not rejected: any `version >= 5` is parsed as the current v5 shape. This is unsafe forward compatibility.

Finally, a truncated gzip stream raises `EOFError`; `read_build()` and `_loadBuildingFromPath()` do not include `EOFError` in their expected corruption path, so a truncated compressed save can escape the normal transactional failure handling.

**Acceptance matrix:**
- non-empty input with 100% invalid rows must fail without changing the live world;
- duplicate coordinates must be rejected or normalized with one complete last/first-row state, never mixed state;
- unsupported future schema versions must fail explicitly;
- truncated gzip, invalid UTF-8/plain JSON, corrupt gzip and partial JSON must all return failure with the live world unchanged;
- define whether a deliberately empty valid build is supported, and test that separately.

**Timing:** fix now.

## P0-4 — Async World loading can overwrite edits or a newly entered app mode

**Class:** static control-flow proof; runtime reproduction still recommended.

Biome loading and tutorial loading have explicit input guards/cancellation. World loading does not.

After the Worlds modal returns `("open", entry)`, it closes. `pendingWorldLoad` is created, but `_handleEvents()` has no corresponding guard for it. The old editor remains interactive while the worker stages the new world. The user can place/remove blocks, save, open another mode, or otherwise change state. `_update()` polls the future every frame and applies the completed world unconditionally.

At minimum, edits made after clicking “Replace Canvas and Open” can disappear. Worse, entering World Map/tutorial/lab while the load is pending can allow the stale load result to land in the wrong session.

**Acceptance:** use a controllable delayed future. While a world load is pending, prove that editor mutations and incompatible mode transitions are blocked or that the load is explicitly cancelled. Escape/cancel behavior must be deterministic. Completion of a stale/cancelled future must never replace the current session.

**Timing:** fix now.

# P1 — concrete bugs and high-value adversarial tests

## P1-1 — `BatchCommand` is not transactional on partial failure

**Class:** static proof.

`BatchCommand.execute()` continues after a child command fails, returns `False`, and sets itself executed. `UndoManager.execute()` only records the command when the return value is true. Therefore a batch with one failing child can leave earlier/later successful edits applied while adding **no undo record**.

This is especially dangerous because app call sites describe several batches as transactional.

**Acceptance:** a batch with success/failure/success must either roll back all successful children or be retained as a fully undoable partial result with explicitly defined semantics. No failed `UndoManager.execute()` may leave untracked world mutations.

**Timing:** before more editor/tool work.

## P1-2 — Derived scene-cache hits are not semantically equivalent to cold v5 loads

**Class:** static proof.

The `.bfc` record format preserves only a subset of `BlockProperties` (basic facing/open/slab/stair/door plus liquid and visibility flags). It does not serialize modern v5 state such as redstone power, repeater delay/lock, comparator mode, piston extension/sticky state, oxidation stage, or source-capture provenance.

A bundled world containing those states can therefore load correctly from JSON on the cold path and differently on a subsequent cache hit.

The cache loader also caps width/depth at 256 while ordinary v5 saves allow 512, causing future >256 bundled worlds to regenerate/reject cache repeatedly.

**Acceptance:** for every serializable `BlockProperties` field, compare cold JSON load with subsequent cache-hit snapshot byte/field-for-field. Either extend the cache format and bump its magic or deliberately exclude unsupported scenes from caching. Align cache dimensions with the supported build contract.

**Timing:** before adding more bundled scene/state complexity.

## P1-3 — Fresh asset setup does not correctly reconstruct Java sound assets

**Class:** static proof plus external format verification.

`setup_assets.py` says it extracts Java sounds from the selected version JAR and scans for `assets/minecraft/sounds/*.ogg`. Modern Java sound/music assets are indexed under `.minecraft/assets/indexes` and stored hashed under `.minecraft/assets/objects`; they are not reconstructed by scanning the version JAR this way.

The script even contains the comment “Sounds need to be extracted from the assets index” but then uses the JAR path instead.

Reference: Minecraft Wiki, “Tutorial:Sound directory” (`https://minecraft.wiki/w/Tutorial:Sound_directory`).

Additional setup risks:
- it selects the numerically newest release >=1.21.1 rather than a known-compatible version;
- extraction writes directly into the live asset tree, so a mid-run failure can leave a mixed/partial install;
- texture destinations are flattened to basenames, allowing silent name collisions;
- Pillow is optional, so the promised block-texture upscaling silently does not happen when it is absent.

**Acceptance:** a fresh supported Minecraft installation and empty Texture/Sound Hubs must produce the required runtime asset manifest, including known music and block sounds, with zero collisions and no stale files. Stage/validate then swap. Pin or validate supported source versions.

**Timing:** before claiming source/fresh-install reproducibility.

## P1-4 — Documented developer environment cannot reproduce documented QA gates

**Class:** static proof.

`requirements-dev.txt` installs only runtime requirements plus pytest. `tests/render_visual_checks.py` imports Pillow at module start, but Pillow is not declared. Other build tools use NumPy/Pillow as well.

Many integration tests instantiate the real app and require gitignored, locally extracted Minecraft assets. There is no CI, fixture asset subset, or documented bootstrap that makes the strongest test surface self-contained.

The recorded owner-machine suite is meaningful, but a clean clone is not independently reproducible from the declared dependency files.

**Acceptance:** from a clean environment, one documented bootstrap must make all intended automated gates runnable. Split optional visual/build-tool requirements if desired, but make the commands in CONTRIBUTING accurate. Add CI for all asset-independent tests at minimum.

**Timing:** before relying on green tests as a handoff gate.

## P1-5 — Native build can silently package a stale tracked DLL

**Class:** static proof / architecture risk.

`Code/native/bin/bloc_fantome_native.dll` is tracked. `build_native.py` treats an existing DLL as success when Cargo is unavailable. If Cargo compilation fails, the packaging path can also continue while an older DLL remains on disk. `build_exe.py` can then include that stale binary.

This defeats the intended “optional native acceleration with Python fallback” contract: the safer result of an unbuildable accelerator is to omit it, not silently package an unknown previous build.

**Acceptance:** modify Rust source, force Cargo unavailable/failing, and prove a release cannot package the pre-change DLL as if current. Either verify the binary against source/toolchain metadata or remove it before attempting a build and omit it on failure. Keep Python fallback tests mandatory.

**Timing:** before the next packaged release.

## P1-6 — The modularization is incomplete enough to mislead implementation agents

**Class:** architecture/governance.

The refactor plan explicitly targeted a roughly 3,000–5,000-line composition root and Phase 8 removal of the in-file legacy `World`, renderer, and legacy loaders.

Current `Code/blocFantome.py` is about **23,499 lines / 1.11 MB**. It still contains complete legacy `World` and `IsometricRenderer` implementations, then later rebinds those names to `engine.world.World` and `engine.renderer.IsometricRenderer` immediately before `BlocFantome`. Multiple `_legacy...` paths also remain.

The public-contract test named `test_dead_duplicate_types_are_not_exported` proves only that the final exported names point to modular classes; it does not prove duplicate implementations are absent. An agent can patch a visually plausible in-file method and change nothing at runtime.

This is the clearest “Frankenstein” risk found: runtime is partially modular, but ownership is not legible from the source layout.

**Acceptance:** before deleting anything, map each legacy implementation to its live replacement/test. Then remove or quarantine proven-dead implementations so there is exactly one obvious runtime owner for world, renderer, build loading, icon/picking paths, etc. Keep the composition root orchestration-only as already specified by the refactor plan.

**Timing:** before broad feature work that touches those systems; do not perform the cleanup blindly.

## P1-7 — Historical QA contains executable source-mutating scripts with no tracked agent warning

**Class:** governance/agent-safety.

There are **73 top-level `.qa/*.py` scripts**. Many are historical patch scripts that perform string replacement and `write_text()` directly against current `Code/` files (examples: `implement_consistency.py`, `implement-tour-291.py`, `open_captured_biomes.py`, `optimize_biomes.py`, `fix-fidelity-291.py`).

Meanwhile current handoffs repeatedly say rules were recorded in `AGENTS.md`, but no `AGENTS.md` is tracked at HEAD and `.gitignore` explicitly ignores it and other agent-instruction files.

A future autonomous agent can reasonably mistake stale mutators for current maintenance tools or believe governance exists when it is absent from the repository.

**Acceptance:** explicitly classify `.qa` as historical evidence by default; quarantine/rename mutators or place a tracked README in `.qa` saying which scripts are archival and unsafe to rerun. Put current agent/release rules in one tracked file that is not ignored.

**Timing:** before agent-driven implementation resumes.

## P1-8 — Repository QA evidence has become a repository-operability risk

**Class:** architecture/governance.

The tracked tree is ~3.49 GB; `.qa` is ~2.82 GB by itself and contains Minecraft worlds/regions, repeated visual outputs, logs, historical scripts and multiple release generations. `References` is another ~391 MB.

This makes cloning, indexing, code search, agent context selection, antivirus/OneDrive activity, and history operations materially harder. It also increases the chance that stale evidence is treated as current evidence.

**Acceptance:** define a retained-evidence policy. Keep compact manifests/hashes/final representative evidence in Git and move bulky regenerable/native-world artifacts to releases/LFS/external archival storage if preservation is required. Do not delete historical evidence until provenance requirements are understood.

**Timing:** plan before another large QA/capture cycle.

# P2 — cleanup, ambiguity, and deferred risks

## P2-1 — README and contributor docs contain incorrect or unsafe implementation guidance

**Class:** stale documentation.

Examples:
- README says undo/redo is “unlimited”; runtime creates `UndoManager(max_history=100)`.
- README says creations are automatically backed up and “never lost”; P0 persistence findings contradict this.
- README projection equations use one height `h`, but runtime uses `tile_height=32` for the XY term and a distinct `block_height=38` for Z. The shown inverse therefore is not the live projection contract.
- README makes broad “same rules as Minecraft” fluid claims that are stronger than the explicit source-style/simplified boundaries elsewhere.
- CONTRIBUTING tells authors to create new structure JSON as **version 3**, while current canonical persistence is v5 and the same document later says v1-v5 semantics/bounds/provenance must be preserved.
- `nextIdeas.txt` still contains items that current releases already substantially implemented.

**Acceptance:** after P0/P1 behavior is settled, update permanent docs to describe live contracts, not historical ones.

## P2-2 — `Code/downloadAssets.py` is a plausible but obsolete/wrong asset entry point

**Class:** governance.

This root-level script downloads a Bedrock resource pack, writes to old `Assets/textures` and `Assets/sounds` paths, and discusses placeholder sounds. The active project contract is Java local extraction into Texture Hub/Sound Hub.

It is not referenced by current setup docs, but its generic name makes accidental invocation by a user/agent credible.

**Acceptance:** mark it historical/deprecated prominently, move it out of the active Code root, or remove it after confirming no consumer.

## P2-3 — Shutdown during a running world-stage job is not truly cancellable

**Class:** credible hypothesis.

Shutdown uses `ThreadPoolExecutor.shutdown(wait=False, cancel_futures=True)`. That cancels queued jobs, not a job already running. Current world staging can take several seconds on large scenes. Python executor threads can keep the process alive until running work completes.

**Acceptance:** inject a deliberately blocked/running stage job, close the app, and measure process exit. If prompt shutdown is required, give staging a cooperative cancellation token/checkpoint or isolate work differently.

## P2-4 — Build parser has no practical row/file-size budget

**Class:** credible local robustness/security risk.

Bounds are capped, but the JSON `blocks` list length is not. Duplicate coordinates allow arbitrarily many rows even inside a small declared world. Gzip/JSON decoding and staging can therefore consume disproportionate memory/CPU before the final dictionary collapses duplicates.

**Acceptance:** define maximum input bytes/decompressed bytes and/or maximum records consistent with supported world sizes; reject pathological duplicate-heavy payloads early.

## P2-5 — Known picking edge case remains open

**Class:** existing documented hypothesis, not independently reproduced here.

`References/OPEN_PROBLEMS.md` still records face picking errors at extreme Z/screen edges. Existing tests are extensive but this exact documented limitation should stay visible until a focused regression proves it closed.

# Adversarial test matrix for the next agent

Run cheap/focused tests first. Do not start broad refactoring until the P0 cases are green.

- **Persistence failure injection:** disk-full/permission/`os.replace` failure; autosave must not claim success.
- **Backup equivalence:** large bounds, negative Y, scene metadata, liquids, every `BlockProperties` field; save/backup/restore exactness.
- **Backup retention:** failed new backup must not delete an old valid one.
- **Recovery path identity:** restoring autosave/backup must not make Ctrl+S overwrite the recovery artifact unless explicitly intended.
- **Corrupt saves:** truncated gzip, garbage gzip, invalid UTF-8, partial JSON, non-dict root, missing blocks, all-invalid rows, partially-invalid rows.
- **Schema/version:** v1-v5 fixtures, explicit rejection of unsupported future versions.
- **Duplicate rows:** block type + properties + liquid + role conflicts at one coordinate.
- **Input scale:** very large row count, duplicate-heavy gzip, huge metadata, maximum legal 512 bounds.
- **Async loading:** delayed world future + placement/removal/save/escape/tutorial/world-map/lab/quit; stale future must never land.
- **Batch failure:** success/failure/success child commands; no untracked partial mutation.
- **Cache equivalence:** cold vs cache hit for all serializable state and 256/512 boundary.
- **Native path:** Rust present, Rust disabled, Cargo absent, Cargo compile failure, deliberately stale DLL.
- **Fresh bootstrap:** clean venv + declared requirements + clean asset hubs + supported Minecraft install; source launch, pytest, visual checks, audio.
- **Asset extraction:** index/object sound reconstruction, destination collision detection, interrupted extraction, version switch, missing/corrupt local assets.
- **Packaged app:** source/EXE semantic parity, Start Menu, Tk dialog, save/load, audio, native fallback, active-load shutdown.
- **Agent safety:** verify current implementation ownership before edits; never run historical `.qa` mutation scripts by name alone.

# CI/test relevance

The existing suite is highly relevant to current editor behavior, large-world rendering, world/biome source fidelity, redstone, UI and release packaging. Its 333-pass result should be preserved.

It is **not sufficient evidence** for the highest-risk findings above because it lacks dedicated coverage for rolling-backup fidelity/failure, all-invalid/duplicate/future/truncated save inputs, partial `BatchCommand` failure, pending World-load event races, cache equivalence across all modern state, clean dependency/bootstrap reproducibility, or stale-native-binary packaging.

Green existing tests must therefore be treated as a baseline, not as proof that these failure surfaces are safe.
