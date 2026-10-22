# Asset and preservation register

## Owner-selected UI audio

[Machine-readable inventory](selected-audio.json) records all eleven originals:
filename, semantic assignment, PCM codec, duration, rate, channels, sample width,
bytes, peak/RMS and SHA-256. `Sounds/` remains unchanged. Byte-identical permanent
copies live in `Assets/Sound Hub/ui/selected/`, including `Extra/`.

The owner's private records clear these media for local development, QA and compiled
releases. Author names, download URLs and verbatim license terms were not supplied
with this folder; do not invent them. No separate source-asset redistribution grant
is inferred. WAVs remain private/ignored; the inventory and tooling are tracked.
This is not a blocker to the authorized build integration.

`Code/tools/preserve_selected_audio.py` verifies source/runtime hashes and a ZIP
round trip. Local backup: `.qa/pass-b/selected-audio-originals.zip`; verification
and ZIP hash: `.qa/pass-b/audio-backup.json`. This is a same-laptop recovery copy,
not evidence of an off-device backup. Before a reset, copy that ZIP and private
license records to independent storage, verify its hash, and test extraction.
Restore `Sounds/`, rerun the script, then validate required runtime media before
packaging. Git alone does not restore these sounds. Do not clean originals,
runtime copies or the recovery ZIP as disposable generated data.

Unassigned extras remain unassigned: Piano_Ui (6)/(7) could be auditioned for rare
milestone or library-confirmation alternatives; SkywardHero_UI (13)/(14) could be
auditioned for explicit transitions. These are proposals, not runtime mappings.

## Other preserved inputs

- Variant D PNG: owner-provided visual concept, tracked unchanged under references;
  exact hash and interpretation in DESIGN.md. No replacement image was generated.
- Segoe UI: use the installed system font; do not redistribute its font files.
- Zekton: local licensed fallback, `Assets/Fonts/Zekton/Zekton-Regular.otf`, private.
- Minecraft textures/sounds, WorldBuilder map/UI/MP3s, skyboxes and temporary Thorn
  rig: existing owner-cleared local release inputs; retain their existing records.
- Existing opening source recordings: `Assets/Sound Hub/opening/encounter-sources.json`
  holds creator/source/license metadata. The twelve used source recordings and
  their MP3 downloads now have byte-identical permanent copies under
  `Assets/Private Sources/Opening/`; earlier `.qa/encounter/audio/sources/` copies
  remain untouched. These private sources are ignored and excluded from installer
  file rules. `Code/tools/prepare_pass_b_audio.py` records reproducible filters,
  hashes and attribution for fourteen separate runtime WAVs under
  `Assets/Sound Hub/opening/pass-b/`; it never overwrites the older score.
  Its ZIP round-trip backup is `.qa/pass-b/presentation-recordings.zip`, including
  sources, outputs and attribution, with hashes in `presentation-backup.json`.
  This is also a same-laptop copy: move it to independent storage before a reset.
  Restore the archived paths before regenerating or packaging. The twelve source
  records identify their creators and individual Creative Commons terms, including
  attribution and noncommercial variants; owner private release clearance
  remains the authority for this build, with no additional public asset upload.
- Installed/root executables, earlier review packages, saves and settings are
  preservation inputs. Pass B review packaging must not update the installed app,
  Start Menu route, rollback builds or main branch.
