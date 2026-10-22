# Bloc Fantôme laptop-reset recovery

GitHub source and the downloadable release are not a backup of this working folder. Copy the items below to your chosen backup destination before resetting Windows. No recovery archive was created, at the owner's request.

## Irreplaceable or owner-managed inputs

Paths below are relative to the project folder unless stated otherwise. Copy complete directories, including hidden files. Check that OneDrive files are downloaded and that the destination copy opens before resetting.

| Copy | Why GitHub alone is insufficient |
| --- | --- |
| `Assets/` in full | Extracted Texture Hub and Sound Hub, Zekton font, skyboxes, WorldBuilder media, opening media, private licensing records and future local assets are partly ignored. Keep original source bytes. |
| Root asset archives and original media | `zekton.zip`, `*.skybox.zip`, `Black Mesa Skyboxes.zip`, `WorldBuilder.zip`, and any locally supplied archives may be ignored. Retain originals even when extracted assets exist. |
| `Code/saves/` and root `saves/` | User builds, autosaves, rolling backups and custom music are not all tracked. Keep both locations. |
| Installed app's `saves/`, `screenshots/`, `.app_config.json`, `.tutorial_config.json`, `.opening_config.json` | The installed app writes beside its executable, separately from this checkout. Current installation is `C:\Users\hunkb\AppData\Local\Programs\Bloc Fantôme`. Include hidden files. |
| Project and `Code/` hidden configuration files | `.app_config.json`, `.tutorial_config.json` and any local configuration retain settings and tutorial progress. Review packages have separate configurations too. |
| `.qa/` rollback packages and preservation evidence | Review executables, old prepared bundles and archived evidence are ignored. Preserve at least `owner-pass-ar`, `owner-pass-ar-icons`, `owner-pass-ar-ui`, `release-299`, and `repository-archive-20261020`. Copy their saves too. |
| `References/`, `Game Reference/`, `WorldBuilder Reference/`, `Redstone Reference/`, `NEW; PONDER PACKAGE/` | Source captures, reference media and authoring inputs are partly ignored or local-only. Copy in full rather than guessing which derived-looking files are original. |
| `abyssalAnchor/`, `Jenova/`, `OPEN_INACCURACIES.md`, `OPEN_PROBLEMS.md`, `REFACTOR_IMPLEMENTATION_PLAN.md`, `NEXT.txt`, `nextIdeas.txt` | Private planning/reference material may exist outside the tracked source tree. Preserve when present. |
| `AGENTS.md`, `.codex/`, `.agents/`, `.kilo/`, `.vscode/` and local agent instructions | Local workflow settings are intentionally excluded from Git. Preserve privately. |
| Any `.env*`, `secrets/`, `credentials/`, `*.key`, `*.pem` | If present, copy privately through your own secure backup process; do not upload them with the public release. |
| Root EXEs and `Code/build/installer/` installers | Keep known-good rollback binaries and the corresponding external Assets directory. A review EXE with an Assets junction is not a portable package by itself. |

Do not rely on copying a junction: copy the actual target assets. Saves chosen through Save As may live anywhere outside these directories; copy those locations too.

## Reproducible data

These can be regenerated from preserved source and assets: `.venv/`, Python `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, PyInstaller work files, Rust build intermediates, and installed `%LOCALAPPDATA%\BlocFantome\Cache\worlds`. `Code/tutorial_prepared/` is reproducible with `Code/tools/bake_tutorial.py` but useful to retain for exact rollback builds. Original captures and opening media must be retained before recreating their derived files.

## Restore check

1. Restore the repository and the private inputs above. Use the published 2.9.9 tag for matching source; keep accepted main separately.
2. Install the complete 2.9.9 installer. It includes runtime assets; the separate EXE alone does not replace an installer.
3. Restore user saves/settings to the intended installed location. Do not overwrite newer saves with example builds.
4. Launch through Start Menu, check version 2.9.9, open a copied build and save a new copy. Verify audio, opening, tutorial, Dimensions and World Map.
5. For development, rebuild the Python 3.12 environment from the pinned requirement files and run the documented tests. Keep old binaries until this restoration is verified.

The exact ignore rules remain in `.gitignore`. The local release checkpoint also contains `recovery-inventory.json`, listing ignored files present at inspection time with sizes and recovery categories. It is intentionally local because it can reveal private filenames. Git history does not contain files that were never added.
