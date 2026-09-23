# Retrieval helpers

Python 3.10 or newer, standard library only. No pip installation, mod installation, Java runtime or account token is needed by these helpers. Public hosts may rate-limit requests; the helper stops on failure and writes a receipt rather than silently skipping missing material.

## Targeted source set

Run from the extracted kit root:

```powershell
python scripts/fetch_references.py --group ponder --group create --group create-scenes
python scripts/fetch_references.py --group ponder --group create --group create-scenes --execute
python scripts/index_scene_methods.py downloads/create-scenes/Create > downloads/create_scene_methods.json
```

The first command is a plan only. The second downloads selected Ponder core classes, Create's facade/registry and all 47 scene source files, along with applicable license files. These are reading references, not a buildable assembled mod. By default they go under this kit's `downloads/`, not into Bloc Fantôme.

```powershell
python scripts/fetch_references.py --group shaders --execute
python scripts/fetch_references.py --group bloc-baseline --execute
```

Shader files retain their GPL/LGPL notices. Bloc's application file is included as a retrieval target even though the connector could not return its large body during research. A normal direct download may work in your environment; no success is claimed in advance.

## Optional full Ponder package source

The targeted core is sufficient to follow these notes. To collect the rest of the Ponder package for an agent:

```powershell
python scripts/expand_ponder_manifest.py
python scripts/expand_ponder_manifest.py --execute
python scripts/fetch_references.py --manifest downloads/ponder_full_manifest.json --group ponder-full --execute
```

The expansion step reads the pinned GitHub tree, refuses a truncated response, and includes Java files under `common/src/main/java/net/createmod/ponder/` plus LICENSE. It does not include assets, Minecraft classes, external Catnip dependencies or repository history. Tree-discovered files are explicitly marked as not read in this research pass. The generated manifest can then be searched and fetched independently.

## Selective assets

```powershell
python scripts/fetch_references.py --manifest audio/manifest.json --id ui-chimes --execute
python scripts/fetch_references.py --manifest audio/manifest.json --id ui-kenney --execute
python scripts/fetch_references.py --manifest audio/manifest.json --id ui-impact --max-total-mib 40 --execute
python scripts/fetch_references.py --manifest skyboxes/manifest.json --id sky-satara --execute
python scripts/fetch_references.py --manifest skyboxes/manifest.json --id sky-cloud-cube --max-total-mib 40 --execute
```

A `page_link` resolver reads the official page and matches one exact published archive basename. It does not scrape an entire site, guess CDN directories, use a search-result download mirror, or execute JavaScript. A changed page produces a visible failure and source-page link. A direct URL is used only where a concrete asset URL was surfaced. No music recordings or paid packs are in the automatic-fetch set.

The normal 16 MiB **transfer** budget includes fetched resolver pages and payload bytes. A large archive may require an explicit larger budget. Per-file caps still apply. ZIPs are validated and inventoried, never automatically extracted. The JSON receipt preserves actual member names and sizes; those were not invented in the catalogue.

## PowerShell convenience wrappers

```powershell
.\scripts\fetch_ponder_reference.ps1
.\scripts\fetch_ponder_reference.ps1 -Execute
.\scripts\fetch_visual_references.ps1 -Execute
.\scripts\fetch_cc0_assets.ps1 -Execute
```

The last wrapper intentionally selects only the small Wind Chimes Ogg archive, not every asset. Use the Python CLI for other IDs. Wrappers accept `-Destination`, `-MaxTotalMiB` and a Python executable path through `-Python`. Run them using your normal trusted-script policy; the kit does not change PowerShell security settings. PowerShell was not installed in the research environment, so these wrappers received static review, not execution.

## Failure and integrity behavior

Only HTTPS is accepted for normal downloads, including redirects. Existing files are not overwritten or called “verified”; choose a new destination for a fresh fetch. A payload is written into a temporary file, checked, then published without replacing an existing destination. That final step uses same-directory hard links, supported by ordinary NTFS/Linux filesystems; unsupported filesystems produce an explicit error rather than an overwrite fallback.

Source text must be nonempty UTF-8 and not an HTML error page. ZIPs receive a bounded uncompressed inventory and CRC pass, with no extraction. JPEGs receive a signature check only; a successful fetch does not establish image decoding, cubemap seams or visual suitability. No file checksums are used as a substitute for these checks.

## Run the bundled tests

```powershell
python -m unittest discover -s scripts/tests -v
python scripts/verify_kit.py
```

Downloader tests use a temporary **localhost** server. The HTTP exception is a test-only function parameter, not a CLI mode. They test successful transfer, resolver behavior, redirects, HTML/empty rejection, byte caps, path containment, ZIP inventory, no-overwrite behavior, dry runs, manifests and method/tree indexing. They do not prove availability of external servers or compatibility with a game runtime.
