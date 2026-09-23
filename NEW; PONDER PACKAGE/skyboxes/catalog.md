# Skybox candidates and conversion notes

A curated set of eight entries spanning **seven source collections/assets**; the cloudy pack appears twice because the two projections are alternative acquisition routes, not different skies. All are author/publisher-labelled CC0. The exact page-specific notices remain authoritative. No binary sky assets are inside this kit.

| Candidate | Creator | Intended audition direction | Acquisition |
|---|---|---|---|
| [Cloudy Skyboxes · cubemaps](../SOURCES.md#sky-cloud-cube) | Screaming Brain Studios | cloud masses; dusk; night | Selective fetch |
| [Cloudy Skyboxes · panoramas](../SOURCES.md#sky-cloud-pano) | Screaming Brain Studios | same sky collection in another projection | Selective fetch |
| [Space Skyboxes](../SOURCES.md#sky-space) | StumpyStrust | surreal/cosmic; optional comparison | Official page |
| [Skybox Pack](../SOURCES.md#sky-kenney) | Kenney | stylized baseline for comparison | Official page |
| [Qwantani Dusk 2 (Pure Sky)](../SOURCES.md#sky-qwantani) | Greg Zaal (photography), Jarod Guest (processing) | quiet dusk; soft warm horizon | Official page |
| [Kloppenheim 06 (Pure Sky)](../SOURCES.md#sky-kloppenheim06) | Greg Zaal (original), Jarod Guest (sky edits) | soft low-contrast light; cool ambient sky | Official page |
| [Satara Night](../SOURCES.md#sky-satara) | Greg Zaal | stars and Milky Way; wide night field | Selective fetch |
| [Moonlit Golf](../SOURCES.md#sky-moonlit) | Greg Zaal | cool moonlit night; faint stars | Selective fetch |

The two cloudy archives use their publisher's actual filenames. The download helper resolves the corresponding link from the official page instead of fabricating a static URL. The page has inconsistent prose about files per pack; the helper's ZIP inventory will establish actual contents after retrieval. Space Skyboxes is a different author's much larger pack and is kept page-only. [Clouds](../SOURCES.md#sky-cloud-cube), [space](../SOURCES.md#sky-space).

The soft dusk Qwantani preview is my strongest initial visual direction for quiet wonder, but that is an artistic suggestion rather than a tested in-engine result. Satara offers a richer star field while its visible lamps/buildings make it unsuitable as an untouched void backdrop. Moonlit Golf has the same terrestrial-horizon distinction. The pure-sky entries remove that integration burden. [Qwantani](../SOURCES.md#sky-qwantani), [Satara](../SOURCES.md#sky-satara), [Moonlit](../SOURCES.md#sky-moonlit).

## Existing target format

Bloc's current `SkyboxRenderer.FACE_COORDS` expects this **3-column, 2-row atlas**:

```text
+--------+--------+--------+
| bottom | top    | east   |
+--------+--------+--------+
| south  | west   | north  |
+--------+--------+--------+
```

It is neither a horizontal cross nor an equirectangular panorama. The renderer uses independent sky drift, cached projected orientations and a 420 ms crossfade. Keep that machinery. [Source](../SOURCES.md#b-sky).

## Proposed offline conversion workflow

Keep the original file and its creator/license record. For an HDR/EXR source, first choose exposure and tone-map to an ordinary RGB image. Do not assume Pygame can load a high-dynamic-range EXR as a display-ready sky. Select a practical face size based on actual viewport needs, not the maximum downloadable resolution.

Convert panorama → six faces, or split an existing cross → six faces. Then map the faces into the existing 3×2 positions. **Face ordering alone is insufficient:** verify each face's orientation, rotations and flips against the actual ray-to-UV code in the rest of `skybox.py` and the native path. Those per-face conventions were not fully audited in this run. Do not ship a converter with guessed orientations.

Inspect every shared edge, the ceiling, floor and a complete drift cycle. Avoid a bright foreground horizon line behind an intentionally isolated platform. Use a diagnostic labelled cube before a visually complex sky, then test both the Python fallback and native projection. Do not rotate or resize the user's game camera to hide a bad cubemap conversion.

## “Composite sky” ideas, not generated assets

An authored cloud bank, distant stars and a restrained horizon gradient can be separate source layers if their perspective, exposure and projection agree. A pasted flat star texture on one face will expose seams when the sky turns. A bright moon baked into a panorama also should not be duplicated by an existing celestial overlay. Keep the composite as an offline derivative with clear attribution and parent filenames, not a reason to replace the skybox renderer.

Example selective commands from the kit root:

```powershell
python scripts/fetch_references.py --manifest skyboxes/manifest.json --id sky-satara --execute
python scripts/fetch_references.py --manifest skyboxes/manifest.json --id sky-cloud-cube --max-total-mib 40 --execute
```

No `--execute` means no network calls. The manifest includes acquisition status and format, so an agent can see which entries are not yet ready-to-load assets.
