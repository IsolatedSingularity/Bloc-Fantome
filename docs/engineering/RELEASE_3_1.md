# 3.1.0 release delivery

23 October 2026. The owner accepts the engineering candidate, lifecycle correction,
documented performance limits and preservation approach. This authorizes the
complete release, including main, the annotated `v3.1.0` tag, source-only GitHub
release, root executable, Windows installation and actual Start Menu launch.
The accepted development review is `d5e54e8ba80078338a659f1fcef6ce18bc00d44b`.
The release tag identifies the final documentation correction on top of that
review; production code and version resources are unchanged by this correction.

## Public documentation and preservation

Historical handoffs and research retain technical findings, measurements, dates,
source commit identities, license credits and explicit verification limits.
Descriptions of historical review work and branch roles now use neutral wording.
The Ponder entry points are `RESEARCH_GUIDE.md` and `research_index.json`, with
references updated. Original documents remain privately archived with SHA-256
manifests and verified restoration under `.qa/release-3.1/`. Literal local
configuration filenames in ignore rules remain functional exclusions. Hardware
product names and music provenance statements remain truthful.

The prior 14,120 untrackings remain recoverable from the verified archives in
[the preservation report](PRESERVATION_3_1.md). All originals remain local.
Source worlds, biome captures, tests, production code and the README-linked
`References/Darkness.gif` remain tracked. README is unchanged. No reference
directories, old tags or published history were rewritten or removed.

Final release Git tree: **539984242 bytes / 2245 files** (sum of blob sizes).
This measures the current tree, not compressed clone size or historical storage.
No newly broken relative documentation/media links are permitted. The 18 known
missing example plots in `References/Excess/exampleREADME.md` predate this work.

## Verification and delivery record

The accepted review passed 651 local tests, source/frozen runtime checks and
Windows/Linux source CI. The final correction repeats focused and complete local
tests, clean-source asset diagnostics and the asset-independent CI subset.
Local media-dependent coverage is larger than CI; the two must not be conflated.
Source-only asset diagnostics must fail explicitly for missing private/generated
inputs. They do not download or silently replace private media.

Private final evidence lives under `.qa/release-3.1/`: test logs/XML, archive and
link audits, source/build identity, installer inputs, runtime probes, shortcut
readback, executable hashes and `release-receipt.json`. The release receipt is
written after actual installation and Start Menu verification; this document
does not turn a prepared executable into proof of completed delivery.

Delivery checks cover startup/Goodbye, exact save/reload, Library and World,
window controls, native acceleration and Python fallback, audio routing, runtime
asset paths and clean shutdown. The final executable must be built from the
committed release source and match both root and installed SHA-256. The existing
application identity and configuration are preserved during the upgrade.

Accepted 3.0 rollback source is `46324ef4f26ecaeaefe6cf5f22524f0be4c03251`.
Its executable and complete installation remain in the verified private
`.qa/consolidation-3.1/rollback/` alongside the complete source/research bundle.
Additional earlier rollback material under `.qa/release-3/` remains intact.
The accepted 3.1 source, executable, installation and private-data manifests
become the next rollback baseline after successful delivery.

## Known limitations and next checkpoint

Large-world camera, editing and loading costs remain accepted limitations.
[Issue #1](https://github.com/IsolatedSingularity/Bloc-Fantome/issues/1) remains open.
Human listening, conclusive physical keyboard input, Windows Snap, trackpad,
multiple monitors, other OS DPI settings and independent/off-device recovery
remain unverified wherever not actually tested. Automated mouse interaction and
decoder/channel checks do not establish human listening or physical keyboard use.
Same-device rollback and OneDrive placement do not prove independent backup.

3.2 remains a separate project combining measured large-world performance work
with moderate architectural refactoring. Its next checkpoint is the bounded
measurement and ownership plan in [the 3.2 contract](ARCHITECTURE_3_2.md), followed
by explicit acceptance before its complete source/tag/root/install/Start Menu
delivery. No 3.2 implementation is included here. Cathedral, creature redesign,
Redstone Lab expansion and major visual changes remain deferred.
