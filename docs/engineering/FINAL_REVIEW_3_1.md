# 3.1 final correction and release review

23 October 2026. Development review only. The owner artistically accepted the
candidate subject to the cube adjustment and authorized development publication.
Main promotion, 3.1.0 tagging/release, root replacement and installation still await
acceptance of the final source and preservation evidence. No 3.2 work began.

## Correction and regression coverage

Splash and Goodbye geometry scale changes from 1.18 to 1.239, exactly 5% larger.
Only the decorative clock runs 6% faster. Cube centers, colors, ballistic motion,
compression/recoil, individual sequencing and reversed Goodbye order remain.
Loading dwell, audio timing, three-second Goodbye/fade and Reduced Motion are
unchanged. Three separate cube masks remain throughout 120 Hz sampled sequences.

Actual production frames and six silent 60 FPS recordings at 960x640, 1200x800 and
1920x1080 were generated. Full frames and decoded motion sequences were inspected:
no cube collisions, clipping or text obstruction. No size/rate adjustment beyond
the proposed values was needed. Recordings are rendered evidence, not physical
input or subjective audio approval.

The final audit also found integration tests persisting map/rotation preferences
into the source checkout. The fixture now isolates preferences, saves and cache,
and drains its loader. Original settings were restored to their pre-work SHA-256.
The packaged handoff probe now saves, edits, reloads and compares exact blocks and
bounds, in addition to cancellation, error, map, encounter return and shutdown.
The older Library probe required eleven cues while exercising seven. It now
explicitly auditions the four unvisited decoder/channel contracts, records those
separately from UI playback and retains the complete coverage assertion.

## Final evidence

Private evidence root: `.qa/final-review-3.1/`.

| Check | Result |
| --- | --- |
| Lifecycle and associated focused contracts | 56 passed (`focused-final.log`) |
| Isolated integration fixture | 128 passed (`integration-isolated.log`); original preferences hash unchanged |
| Full release suite | 651 passed in 453.12 seconds (`full-isolated.log/xml`); later diagnostic-only cue coverage extension checked separately in source/frozen runs |
| Source-only checkout | 180 passed, one optional local-reference skip (`clean-core.log`) |
| Explicit native fallback | 5 contracts passed (`fallback.log`), plus real disabled-native source save/reload, map, encounter and shutdown (`python-fallback-runtime/checks.json`) |
| Source and frozen lifecycle/controls | Passed automated startup/Goodbye, World/settings matrix, fullscreen and exact geometry restore (`runtime-final-checks.json`). Reviewed package save/reload and Library checks are in `runtime-reviewed-checks.json`. |
| Installer inputs | 7,556 files / 724,050,925 bytes copied to a separate layout and hash-verified; exact candidate runs from that layout. Inno compilation verifies inputs; Windows installation itself is deferred. |
| Assets | Local release preflight: zero missing paths. Source-only preflight correctly fails with 73 missing private/generated inputs; synthetic Java recovery tests pass. |

Final executable: `package-reviewed/BlocFantome.exe`, version 3.1.0, 282,053,488 bytes,
SHA-256 `826a50e7f511d00039c829a97d372f7406a97ed5db79ce10b61b9fe26da8a407`.
Installer: `installer-reviewed/BlocFantome_Setup_3.1.0-review.exe`.
Installer size: 681,686,403 bytes; SHA-256
`b2efecf27c48f4a22e700fcaf80ac15f7ee20370a052bea4b33ac99e00ec4e35`.
This supersedes earlier candidate executables; keep its adjacent Assets junction.
Comparison of all 443 bundled Python modules and the main script shows that only
the diagnostic cue-coverage module changed after the complete control matrix;
production application code is identical (`package-module-comparison.json`).

## Preservation and publication boundary

Final Git tree: **539978836 bytes / 2244 files**, measured as the sum of all tree
blob sizes, not compressed clone size or local disk usage.

Final removals: **14,120 files / 1,139,280,556 Git bytes**. The README-linked
88,418,582-byte Darkness GIF remains tracked. [Classification and recovery](PRESERVATION_3_1.md)
give directory counts, bytes, ownership and archive hashes. Every removed original,
archive member and extracted restoration matches; archive path safety passed.
All source worlds/captures, code, tests and recovery documentation remain available.
Final preservation recheck found zero differences across 24,882 overlapping
baseline records of user data, private inputs and installation.
No unsafe/incomplete archive is the sole recovery route. Original media, historical
QA and complete 3.0 rollback remain local; no history or tags were rewritten.

Sixteen historical documents now identify local-only evidence explicitly instead
of linking to removed files. No newly broken relative Markdown/media links remain.
Eighteen pre-existing missing plots are confined to an unrelated historical sample
README. The application README and owner `night.png` are unchanged.

HOLD/unverified: human listening; conclusive physical keyboard, Snap, trackpad,
multiple monitors and other OS DPI settings; independent/off-device restoration.
Private original media, licenses/fonts, reference collections, source captures,
personal builds/settings, recovery archives and rollback installations still need
verified independent backup. Same-device copies and OneDrive placement are not
proof. Existing large-world performance failures remain explicit in issue #1.

Both root and installed application remain accepted 3.0.0. After final acceptance,
publish matching main/tag/release, replace the root EXE, upgrade the installation,
verify its actual Start Menu target/icon/working directory, executable identity,
version and gameplay, and recheck private-data hashes. Preserve 3.0 rollback.
The same complete delivery contract applies to eventual 3.2, with accepted 3.1
retained as rollback; see [the architecture/performance plan](ARCHITECTURE_3_2.md).
