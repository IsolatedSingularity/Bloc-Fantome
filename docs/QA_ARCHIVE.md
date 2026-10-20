# Generated QA evidence recovery

The October 20 engineering review archived 4,899 tracked, derived files
(2,197,710,239 bytes). These are rendered PNG/GIF/video checks, derived scene
caches, profiles and JUnit reports. Every original remains at its existing local
path. Only their Git index entries were removed.

The local recovery archive is
`.qa/repository-archive-20261020/generated-evidence.zip` (2,199,444,318 bytes).
SHA-256: `aa4beeaba806bb9073a2bf136e09bf1bc6bf27581941596cdda8b80ef17390e1`.
The independent extraction is in the sibling `verified-extraction` directory.
Every extracted file matched its original byte count and SHA-256.
[The manifest](QA_ARCHIVE_MANIFEST.json) records every relative path and digest.
The ZIP contains its own `MANIFEST.json` as well.

Recover an individual file by extracting its recorded path into a separate
directory, checking its SHA-256, then copying it to the required location. All
files also remain recoverable from Git at baseline
`175686c21649a8d37826f8a22850c85482a69fd9`.

Retention was conservative. The `natural-292/world`, `biome-capture-281/world`,
`void-capture-281/world` and `worldmap-vanilla/reference-world` source worlds,
their surrounding capture records, every script, human-readable handoff, audio
source, research/reference library, save and setting remain tracked or in their
original private location. Unknown JSON/text ownership was retained. Historical
handoffs remain at `.qa/consistency-290-handoff.md`,
`.qa/revision-292-handoff.md` and `.qa/tutorial-preview-291-handoff.md`.

Old documents' links to archived images/profiles resolve through this path index.
No source asset, world capture or sole evidence copy was deleted. The current
Git tree shrinks; historical Git blobs and clone download history do not. Local
disk usage increases because originals, ZIP and verification extraction are all
retained. No history rewriting or garbage collection was performed.
