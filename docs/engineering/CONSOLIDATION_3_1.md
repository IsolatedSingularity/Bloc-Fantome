# 3.1 engineering consolidation review

Historical first-candidate report. The owner artistically accepted this candidate
subject to a small cube adjustment. [Final review](FINAL_REVIEW_3_1.md) supersedes
its tracking totals, executable identity and publication status below.

23 October 2026. **Review candidate; promotion HOLD pending owner acceptance.**
Accepted development/main source: `46324ef4f26ecaeaefe6cf5f22524f0be4c03251`.
No commit, push, tag, root replacement or installation upgrade occurred.
[Performance issue #1](https://github.com/IsolatedSingularity/Bloc-Fantome/issues/1)
was published with explicit owner approval. No 3.2 implementation began.

## Review artifact

`.qa/consolidation-3.1/package/BlocFantome.exe`: file/product version **3.1.0**,
282,052,373 bytes, SHA-256
`4b2bad55926c23573ab7e757ebf9e4e3d2c3cc5e3f160f6a2f225fca3fbb0c01`.
Keep its adjacent Assets junction intact. This local package uses preserved private
inputs. Appearance, optional encounter, creature and source worlds are unchanged.

## Confirmed fixes

| Defect | Correction and evidence |
| --- | --- |
| Java setup expected JAR sounds, flattened paths and could overwrite assets | Verified Java 1.21.1 indexes/hashed objects, nested native-resolution textures, staged validation, collision/incomplete-output rejection and exclusive creation; 11 synthetic tests |
| Unverified native DLL reuse | Binary/source/builder/Cargo/architecture receipt, runtime mismatch rejection, locked offline Cargo build and explicit Python fallback; four provenance tests, actual rebuild and package inspection |
| Shared save/cache staging names | Unique same-directory staging, flush and atomic replacement; competing-writer sentinel and failure/recovery tests |
| Silent same-length cache corruption | BFC8 checksum, authoritative-source recovery and regeneration; semantic coordinate mutation and exact recovery tests |
| Fresh-checkout pytest failed without temporary parent | Basetemp parent creation; clean exported source passes core contracts |
| Benchmark rotation wrote source preferences | Isolated benchmark preference path; exact original restored from the existing 3.0 backup and verified against the pre-work SHA-256; focused real benchmark rerun |

Earlier undo, save cancellation/rotation, asynchronous generation, stale-result,
shutdown and cache fixes were revalidated. Prepared tutorial data was regenerated
for updated source fingerprints. Renderer methods remain unchanged.

## Verification

Evidence paths below are under `.qa/consolidation-3.1/`.

| Check | Outcome and evidence |
| --- | --- |
| Baseline/full suite | **PASS:** 632 baseline; 650 final tests in 268.94 seconds (`baseline.log`, `final-complete.log/xml`) |
| Clean source/core | **PASS locally:** 180 passed, one optional local-reference skip, 469 deselected (`clean-core-final.log`). Windows/Linux CI prepared; remote CI and Linux execution remain unverified. |
| Native/fallback/package | **PASS:** rebuilt DLL bytes unchanged, valid receipt bundled; explicit fallback contracts pass. Standard EXE integration/edge processes exit zero (`native-build.log`, `native-fallback-contracts.log`, `standard-status.json`). |
| Source/frozen behavior | **PASS automated:** save/cancel/error/close, map, original OpenGL encounter return and worker shutdown; AMD 860M GL error zero (`source-integration`, `standard-integration/checks.json`, `standard-edges.json`). |
| Visual/geometry | **PASS within matrix:** 960/1200/1920 widths, 100/125/150% app text scales, fullscreen/restore; inspected Settings, Library and worlds (`native-source`, `visuals`, `worlds`). Current OS DPI: 125%. |
| Native input | **PARTIAL:** actual mouse drawer/toggle/dismissal, placement, dirty exit and Goodbye verified. Helper Escape inconclusive; Snap, other OS DPI, trackpad/multi-monitor unverified. Injected SDL events are separate (`native-input.json`). |
| Audio | **Signal PASS; listening HOLD:** 34.24 seconds, 48 kHz stereo, peak 0.1874, zero clipped samples/capture errors; human listening required (`audio/loopback.wav`, `audio/analysis.json`). |
| Ten-minute soak | **Completed:** 613 seconds, 21 scene loads, 11 requested music transitions, 123 samples. RSS first/peak/last: 1,557/1,967/1,727 MiB; handles 445 to 442; music cache three entries. SDL closed, two Python threads immediately after shutdown, process exited zero (`soak-v2/result.json`). This does not prove long-term leak freedom. |

Java extraction used synthetic redistributable fixtures, not a newly downloaded
complete installation. Full visual recovery also requires private font, opening,
skybox and audio inputs. Diagnosed failed archive, fresh-export, tutorial-fingerprint,
Assets-junction and soak-harness attempts remain preserved alongside successful
reruns. The benchmark settings incident and exact restoration are retained.

## Performance remains open

After other heavy QA stopped, five repetitions plus warmup alternated accepted/current
renderer and culling methods on shared current dependencies at 1200x800. All final
RGBA images matched. Complete repaint medians in milliseconds:

| World | Pan | Zoom | Edit repaint |
| --- | ---: | ---: | ---: |
| Ancient City | 103 | 126 | 25 |
| Trial Chamber | 191 | 288 | 33 |
| Plains Village | 200 | 225 | 68 |
| Ocean Monument | 136 | 177 | 44 |

These sum incremental rendering work, excluding OS input/display presentation;
they are not physical input-to-photon latency or independent 3.0-process comparisons.
Edit handlers add 0.68-1.22 ms. Visible-plan traversal/rounding remains a measured
cost (`performance-matched/`, `profile_matched.py`). No speedup is claimed.

The separate five-repetition headless benchmark used Python 3.12.10, Pygame 2.6.1,
Rust and a populated isolated cache (`performance-controlled.json`). Load medians:
Ancient City 1,500 ms, Trial Chamber 1,766 ms, Ocean Monument 5,071 ms, all **HOLD**
against 1,000 ms. Cold maxima: 81/121/298 ms, with the latter two failing 100 ms.
Trial exact zoom maximum: 256 ms. Repeated cache-hit medians and early concurrent
QA timings do not establish cold responsiveness. Existing targets remain unchanged.

## Preservation and delivery boundary

Verified untracking removes **14,121 files / 1,227,699,138 Git-blob bytes** from the
next tree, leaving 451,494,552 baseline bytes before small additions/edits. Every
local original remains. Only these owner-approved removals are staged; code/docs
remain unstaged. README and user-owned `night.png` are unchanged.

[Preservation audit](PRESERVATION_3_1.md) records extracted archive hashes, privacy,
raw-media rights and historical remediation limits. Panoir originals, source assets,
saves and QA remain private local inputs. Forty historical documents had username
prefixes sanitized with originals archived. History/tags were not rewritten.
The research branch retains nine unique commits and six absent documents.
Reference directories were not consolidated.

The complete Git bundle verifies; root rollback matches; 7,567 installed rollback
files match. Final preservation checking reports zero differences across 24,882
overlapping records of settings, saves, media and installation
(`preservation-restored-final.log`, `preservation-differences.json`). Review EXE
process count is zero. **Independent/off-device recovery remains
unverified**; same-disk archives and OneDrive paths are insufficient proof.

Root and installed versions remain **3.0.0**. The existing Start Menu target, icon,
working directory and version were checked (`start-menu-preserved.json`); a 3.1
Start Menu launch has not occurred. After owner acceptance and remaining checks,
publish verified source/tag/release, rebuild root, upgrade installation and verify
the actual Start Menu launch/version/gameplay plus unchanged private data.

[The 3.2 plan](ARCHITECTURE_3_2.md) combines measured performance with staged
document/save, load/session, texture and composition ownership, preserving imports,
world semantics, appearance and painter order with rollback at each stage.
[Issue register](ISSUES_3_1.md) and [roadmap](../ROADMAP.md) record remaining work.

Implementation references: [Python atomic replacement](https://docs.python.org/3.12/library/os.html#os.replace)
and [Cargo build options](https://doc.rust-lang.org/cargo/commands/cargo-build.html).
