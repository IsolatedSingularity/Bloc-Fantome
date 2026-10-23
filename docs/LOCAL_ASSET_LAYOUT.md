# Local assets and recovery

Git restores the program and its tracked resources. It does not restore the complete local installation, personal builds, licensed media or reference collections. Keep those in a separate private backup. Paths below are relative to the checkout unless described otherwise.

| Location | Purpose and recovery |
| --- | --- |
| `Assets/Texture Hub/` | Mostly ignored Minecraft block, entity, item, GUI and colormap textures. Extract again from an owned Java installation with `Code/setup_assets.py`. Selected special textures are tracked exceptions. Retain the original game version and any custom additions in a private backup. |
| `Assets/Sound Hub/` | Mostly ignored extracted sounds and dimension music. Ordinary Minecraft files can be extracted again. `opening/`, `ui/selected/`, `ui/workshop/` and custom recordings require the private originals; extraction does not recreate them. |
| `Sounds/`, `Assets/Private Sources/Opening/` | Ignored original selected audio and source recordings. Preserve originals, attribution and private license records. The tracked audio manifests and preparation scripts describe derivatives but are not copies of the source recordings. |
| `Assets/Skyboxes/Black Mesa/` | Ignored Ewan Howell skybox pack. Runtime reads the original cube atlases under `assets/minecraft/optifine/sky/`. Restore the pack from its original source or the private archive, with the applicable license. Generated `panoramas/` are disposable. |
| `Assets/World Map/WorldBuilder/` | Ignored map UI, textures and audio extracted from the retained WorldBuilder source collection. Restore from the private backup, including the source archives and extraction records. The runtime paths must stay intact. |
| `Assets/Fonts/Zekton/` | Ignored licensed fallback font. Restore `Zekton-Regular.otf` and its private purchase/license records. Release builds require it. Production IBM Plex Sans faces and their OFL license are tracked under `Code/ui/fonts/IBMPlexSans/`. Windows Segoe UI is resolved from the OS, not distributed. |
| `Assets/Icons/`, `References/` | Many application icons, the swamp painting and historical images are tracked. Other owner-supplied files can be ignored individually. Verify with `git ls-files -- <path>` and `git check-ignore -v -- <path>`; retain originals and licenses privately. |
| `Assets/Opening/`, `Assets/Extensive Library/` | Opening rig images/arrays are ignored private inputs; the build still requires them for the optional existing presentation. The dragon texture used by the build comes from `Assets/Extensive Library/textures/entity/enderdragon/dragon.png`. Neither folder should be assumed recoverable from Git alone. |
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
