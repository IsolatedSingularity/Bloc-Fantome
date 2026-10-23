# Local assets and recovery

Git restores the program and its tracked resources. It does not restore the complete local installation, personal builds, licensed media or reference collections. Keep those in a separate private backup. Paths below are relative to the checkout unless described otherwise.

| Location | Purpose and recovery |
| --- | --- |
| `Assets/Texture Hub/` | Ignored Minecraft block, entity, item, GUI and colormap textures. Recover the validated Java 1.21.1 layout with `Code/setup_assets.py`. Special Mine Crafter textures also require private recovery; ordinary releases do not supply them. Retain custom additions privately. |
| `Assets/Sound Hub/` | Mostly ignored extracted sounds and dimension music. Ordinary Minecraft files can be extracted again. `opening/`, `ui/selected/`, `ui/workshop/` and custom recordings require the private originals; extraction does not recreate them. |
| `Sounds/`, `Assets/Private Sources/Opening/` | Ignored original selected audio and source recordings. Preserve originals, attribution and private license records. The tracked audio manifests and preparation scripts describe derivatives but are not copies of the source recordings. |
| `Assets/Skyboxes/Black Mesa/` | Ignored Ewan Howell skybox pack. Runtime reads the original cube atlases under `assets/minecraft/optifine/sky/`. Restore the pack from its original source or the private archive, with the applicable license. Generated `panoramas/` are disposable. |
| `Assets/World Map/WorldBuilder/` | Ignored map UI, textures and audio extracted from the retained WorldBuilder source collection. Restore from the private backup, including the source archives and extraction records. The runtime paths must stay intact. |
| `Assets/Fonts/Zekton/` | Ignored licensed fallback font. Restore `Zekton-Regular.otf` and its private purchase/license records. Release builds require it. Production IBM Plex Sans faces and their OFL license are tracked under `Code/ui/fonts/IBMPlexSans/`. Windows Segoe UI is resolved from the OS, not distributed. |
| `Assets/Icons/`, `References/` | Many application icons, the swamp painting and historical images are tracked. Other owner-supplied files can be ignored individually. Verify with `git ls-files -- <path>` and `git check-ignore -v -- <path>`; retain originals and licenses privately. |
| `Assets/Opening/`, `Assets/Extensive Library/`, `Assets/Extras/structures_NBT (original)/` | Private local inputs. The build still requires the existing optional opening rig and `Assets/Extensive Library/textures/entity/enderdragon/dragon.png`. Extracted source resources were removed from current tracking during 3.1, with verified private recovery. Restore from the matching original client/source archive; never assume a fresh clone is a release installation. |
| `Code/ui/audio/` | Metadata and derivation scripts remain tracked. Private recorded-audio derivatives are local inputs preserved in the 3.1 media archive. Restore exact files/digests before building; the opening and selected feedback are unchanged. |
| `Game Reference/`, `WorldBuilder Reference/`, `Redstone Reference/` | Ignored development/reference collections, optional for ordinary play. Original archives and preservation records may be irreplaceable. Some preparation tools depend on their current paths. Keep them where they are; consider a documented consolidation and tool-path migration in a separate change. |
| Root archives and other private source folders | Original fonts, skyboxes, audio and reference packages may live in ignored ZIPs or private folders. A filename list cannot restore them. Keep a private inventory and verified independent copies. |
| `Code/saves/`, root `saves/`, `screenshots/` | Source play uses `Code/saves/`; the root executable uses root `saves/`; an installed executable uses `saves/` beside itself. `Code/saves/` also contains tracked built-in structures. Preserve user builds, `_autosave.json.gz`, `_backups/`, custom music and screenshots separately. Do not assume every user filename is ignored; review staging explicitly. |
| `.app_config.json`, `.tutorial_config.json`, `.opening_config.json`, `config.json` | Per-location settings live beside the source/application base. Preserve the source, root and installed copies. The installer keeps an existing `config.json`. Preserve local preferences rather than replacing them with defaults. |
| `Code/biome_captures/`, `Code/worlds/`, `Code/world_map_regions/` | Tracked scene records and imagery. Restore from the matching Git revision. The two Library subsets carry source hashes and are reproducible with `Code/tools/prepare_library_previews.py`; canonical captures remain unchanged. |
| `Code/tutorial_prepared/`, build folders, virtual environments | Ignored generated data. Recreate dependencies and use `Code/tools/pack_scene_captures.py`, `Code/tools/bake_tutorial.py`, then the build script. Prepared lessons require matching source and assets. |
| `.qa/`, caches and logs | Normally disposable test output, but rollback EXEs, original-audio recovery ZIPs and private recovery inventories stored here are preservation exceptions. Copy those out before cleanup. The world cache in the user's local application-data folder is regenerable. |

Run a quick, read-only presence check from the repository root:

```powershell
python Code/tools/check_local_assets.py
```

This lists missing required paths and reports optional reference folders. It does not prove licensing, complete media integrity or backup availability. The release builder additionally validates selected audio hashes, scene packages and prepared lesson fingerprints.

For a machine reset, copy original/private media, license records, personal saves/settings, source archives and a known-good installer to independent storage. Hash both copies and test restoration into a separate directory. A second folder on the same disk, including a synced checkout whose remote contents have not been verified, is not a verified independent backup. The local 3.0 inventory and rollback records are retained privately under `.qa/release-3/`.

## Validated Java recovery in 3.1

Install and launch **Java 1.21.1** once. Point setup at that launcher's installation
if it is not the default location:

```powershell
python Code/setup_assets.py --minecraft-dir <minecraft-directory> --output-dir .qa/java-assets-review
```

Setup verifies the version's declared asset-index SHA-1/size, then reads sounds
from `assets/objects/<first-two-hash-characters>/<hash>`. Sounds are not assumed
to be in the client JAR. PNGs and animation metadata come from the JAR, retaining
native pixels and nested paths. Every selected object must be present and valid;
snapshots, modded identifiers, unvalidated versions and destination collisions
fail closed. Existing identical files are idempotent; differing files are never
replaced. Stage and inspect a fresh output before integrating recovered files.
Synthetic fixtures verify this protocol; a complete fresh Java installation was
not downloaded or recreated during 3.1. Private media cannot be reconstructed by
this command. The former unrestricted "1.21.1+" recovery claim was unverified.

## Native acceleration and source-only checks

`python Code/build_native.py` uses Cargo's locked, offline dependency-free build.
Its adjacent JSON receipt records Rust/build-source hashes, binary SHA-256 and
machine/bitness. Without Cargo, only a matching verified DLL is reused. Missing,
stale or damaged receipts/binaries select Python fallback; a failed optional
Cargo build is explicitly reported. `--required` fails instead. Source loading
checks the sources too; the packaged loader checks the bundled receipt/binary.
Receipts detect stale local artifacts, not authenticity of downloaded code.

`pytest -m core` and the source-contract CI use synthetic/redistributable fixtures
without private assets, reference libraries or prepared lessons. That pass does
not assert that a fresh clone can run the complete accepted presentation. The
builder deliberately rejects missing private inputs. See the current
[preservation record](engineering/PRESERVATION_3_1.md) before cleaning QA folders.
