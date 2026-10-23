# 3.1 preservation and public-tree audit

23 October 2026. Baseline: `46324ef4f26ecaeaefe6cf5f22524f0be4c03251`.
The owner subsequently authorized coherent staging and development publication.
The owner accepted this preservation approach on 23 October 2026 and authorized
release promotion and installation. See [release delivery](RELEASE_3_1.md).

## Tracking and restoration

The baseline contains 16,351 tracked files / 1,679,193,690 Git-blob bytes.
Final review retains the 88,418,582-byte `References/Darkness.gif` because README
embeds it. Thus 14,120 index removals account for 1,139,280,556 bytes, leaving
539,913,134 bytes of baseline content before additions/edits. The exact final
tree and classified totals are in [final review](FINAL_REVIEW_3_1.md).
Every removed original remains
at its existing local path. This reduces the next tree, not published history,
clone download history or local disk usage.

Private recovery records under `.qa/consolidation-3.1/`:

| Archive | SHA-256 | Verification |
| --- | --- | --- |
| `archive/preservation-v2.zip` | `c2ce73269541b3073cd4b1edd21f88e6473024860ff0c9b8145cefacd1883ac2` | 1,406,221,066 bytes; independent extraction and every working-file SHA-256 matched |
| `archive/private-source-media.zip` | `dd28a0bffe74a2b3b5e93911667ab5db6107f86077352a98c357318aef45b237` | 9,480 extracted-source/private-audio files, 28,154,121 working-file bytes; extraction/digests matched |
| `rollback/source-and-research.bundle` | `406df218e38dfeace294ed4b2c26f534ed8631c5b27928e0711a453f4f36ed0a` | Complete history and refs; `git bundle verify` passed |

The first archive attempt used Git-blob sizes to check Windows CRLF working files
and failed its size check. It was retained as failed evidence. The corrected
manifest records Git and working-file sizes separately; the second extraction
passed before untracking. No missing source bytes were waived.

`archive/manifest.json`, `archive/private-source-manifest.json` and
`untracking-manifest.json` enumerate paths and hashes. Their embedded ZIP manifests
permit independent restoration. Extract the desired recorded path into a separate
directory, compare size and SHA-256, then copy it to its original relative path.
Do not overwrite a newer save or original. The accepted root EXE, installed tree,
source history, user data and prior 3.0 recovery remain local rollback inputs.

## What changed

Untracked all remaining `.qa` files, old `visual-checks` outputs, large legacy
reference GIFs/video except the README-linked animation, redundant review recordings/profiles/JUnit output and the
local editor configuration. Source worlds, original Panoir recording, research,
historical handoffs and old scripts remain privately preserved; no original was
deleted. The three reference directories were neither moved nor consolidated.
Current 3.0 gallery media and useful compact review records remain public.

Archived historical internal handoff files are no longer current public
guidance. The current roadmap uses neutral names. Forty historical documents had
machine-specific username prefixes replaced with `<user>`; original texts remain
in the verified archive. Dates, findings, source identities and historical outcomes
were retained. The inventory is `path-sanitization.json`. No credential disclosure
was established by the limited textual scan; this is not a full secret-history scan.

Ignore rules now cover those preserved paths, opening preferences, plain personal
save JSON, extracted source libraries and recorded-audio derivatives. Visual
scripts default to `.qa`. Selected evidence must be consciously copied to a
compact public report; never force-add an entire QA directory.

## Third-party media and privacy

Owner clearance continues to authorize local development, testing and compiled
review builds. It is not interpreted as permission to publish raw third-party
source assets. The local private asset register and `docs/design/ASSETS.md`
distinguish these scopes.

- The tracked Panoir WebM and downloader metadata were inside `.qa/tutorial-294`.
  They are preserved and untracked, with no change to optional opening playback.
  The inspected records establish local provenance/clearance, not a separate
  public raw-recording redistribution grant.
- Extracted `Assets/Extensive Library`, original NBT templates, special Mine
  Crafter textures and private recorded-audio derivatives are now local inputs.
  Exact runtime files remain present; builds still validate required media.
- Bundled IBM Plex Sans keeps its public OFL license. Zekton, skyboxes,
  WorldBuilder UI/audio, the rig and original selected recordings stay private.
  Owner artwork and application screenshots retain their accepted presentation.
- Save backups, world player records and machine paths inside the old QA tree
  are private preservation material. They are not republished in the new report.

Previously published objects remain obtainable from Git history, tags and clones.
Any request to remove historical raw recordings, extracted assets or personal
records requires a separately scoped inventory/remediation decision. This review
does not rewrite history, delete releases/tags or claim that untracking retracts
publication. No new public media was uploaded.

## Research branch and independent recovery

`docs/builder-ux-research-20261020` has nine unique commits, touching seven
research/handoff documents. Six files containing earlier UX/performance,
fidelity/audio/motion and creative briefs are absent from current development;
the continuation file also differs. Thus it is not an empty or safely disposable
branch. Its refs/history are in the complete verified bundle. Retain it pending
owner review; a later retirement should first preserve a neutral historical
research export and prove restoration. No remote branch was changed.

Only the local C: device was available for recovery verification. OneDrive path
placement does not prove remote synchronization or off-device restoration.
**Independent backup is unverified** for original/private recordings, opening rig,
font/license records, skybox/WorldBuilder archives, all three reference collections,
source capture worlds, personal builds/settings, rollback installations and these
recovery archives. GitHub verifies public source identity, not those private bytes.
Before machine reset or deletion, copy them to independent storage, compare hashes
and restore a sample including a world, original media and the accepted executable.

## Final removal classification

Counts below describe the final 14,120 removals. Bytes are Git-blob sizes, not
Windows working-file sizes or compressed archive sizes. Every path was read from
its archive and compared with both its current original and extracted restoration;
archive digests, duplicate names and traversal/absolute-path safety also passed.
No removed file depends on an incomplete or unsafe archive.

| Directory | Files | Git bytes | Ownership / retention class |
| --- | ---: | ---: | --- |
| `.qa/` | 4,494 | 736,735,168 | Project-generated QA; includes private saves, paths and third-party recordings |
| `.vscode/` | 1 | 245 | Private editor configuration |
| `References/` | 7 | 286,676,346 | Third-party reference media, local owner clearance |
| `docs/handoffs/` | 1 | 16,121 | Historical project handoff |
| `docs/reviews/` | 50 | 58,405,240 | Historical project QA; recorded audio may derive from private inputs |
| `visual-checks/` | 87 | 29,391,433 | Project-generated screenshots |
| `Assets/Extensive Library/` | 8,662 | 25,295,668 | Minecraft-extracted source assets |
| `Assets/Extras/structures_NBT (original)/` | 806 | 2,394,031 | Minecraft-extracted original templates |
| `Assets/Texture Hub/` | 7 | 1,812 | Minecraft-extracted special textures |
| `Code/ui/audio/` | 5 | 364,492 | Owner-cleared recorded/derived audio; private originals retained |

All 15 bundled world files, 16 bundled save examples and 876 biome-capture files
remain tracked, along with production code, tests, documentation and asset
recovery scripts. Private originals remain at their original paths; release
preflight requires them and fails explicitly in a source-only checkout.

The final link audit found no newly broken relative Markdown/media links and none
in active documentation. Sixteen historical documents now describe local-only
artifacts as paths and link to recovery guidance; their pre-edit bytes are archived
in `.qa/final-review-3.1/link-originals.zip`. Eighteen pre-existing missing plot
examples remain confined to `References/Excess/exampleREADME.md`, an unrelated
historical sample, not application documentation. README itself is unchanged.
