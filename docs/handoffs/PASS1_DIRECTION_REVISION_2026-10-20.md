# Pass 1 direction revision: contextual workshop and architectural weight

Owner feedback supersedes the first checkpoint's stone-frame recommendation and permanent-sidebar retention. Retain the atmospheric workshop direction and Minecraft hotbar, but use modern minimal controls elsewhere. Remove nested frames and the permanent right panel. Keep every editing capability and real side previews. Creature work remains deferred. This is another review slice before broad migration, as requested, not completed Pass 1 acceptance.

## Proposed direction

Recommend **Anchored workshop**: a small persistent top navigation strip, one lower-left material/context surface, existing hotbar, and camera controls. Build, Tools and World open temporary drawers; Library opens a larger list-and-preview surface. An active operation stays visible until completed or cancelled. Ordinary material options should fade when idle, with pin/always-visible preferences. Only one drawer owns input at once; close returns to the same camera. No outer frame around already grouped controls.

The second candidate, **Command desk**, opens a broad temporary work surface near the bottom. It provides more room for complex choices but obscures much more of the build, especially at 960x640. Prefer its space allocation for Library, not routine material changes. Both studies retain final-size Zekton and original block art. Production styling has not been migrated.

- [Quiet native canvas](../../.qa/pass1-revision2/anchored-quiet-1200.png)
- [Anchored Build drawer](../../.qa/pass1-revision2/anchored-build-1200.png)
- [Command desk alternative](../../.qa/pass1-revision2/desk-build-1200.png)
- [Library with real side preview](../../.qa/pass1-revision2/anchored-library-1200.png)
- [Active fill context](../../.qa/pass1-revision2/anchored-fill-1200.png)
- [125% text study at 960](../../.qa/pass1-revision2/anchored-text125.png)

The prototype renders the real editor world, block sprites, existing hotbar and existing Library preview provider. It temporarily supplies a full-width viewport inside its isolated process. It does not patch production camera/input geometry. Material selection, half/facing, camera rotation/fit, drawer switching and Library preview selection are wired. Other commands deliberately report that they remain with the existing editor; the subset grid is not the complete inventory. Search, full inventory scrolling, production command dispatch, accessibility/focus traversal, idle fading, pinning and full migration are pending. Do not mistake the native design study for a feature-complete editor.

## Capability destinations for migration

| Existing capability | Proposed home |
| --- | --- |
| All blocks, categories, favorites, search, pick block, hotbar assignment | Build drawer; existing hotbar and shortcuts remain |
| Build/interact, stair/slab half, facing, relevant block properties | Lower-left material context |
| Brush size, fill, flood fill, replace, wand | Tools; only the active tool's options appear in context |
| Selection, copy/paste, clipboard rotation, fill/hollow/delete selection, stamp, blueprint | Tools > Selection; contextual actions after selection |
| Mirror X/Y, radial symmetry | Tools > Symmetry; active-state indicator stays visible |
| Measure, layers, grid, X-ray, minimap | Tools > View/Measure; contextual layer controls |
| Worlds, Biomes, Structures, Saved Builds, native/Java browse | Library tabs with actual previews and explicit Open/Place action |
| Dimension, terrain slice, grow/shrink canvas, local noise, terrain visibility | World > Terrain; preserve existing deterministic/undoable owners |
| Rain, snow, sun/moon, clouds, lighting/AO/fog, skybox and preset arrows | World > Atmosphere |
| Liquid flow/clear, simulation controls, clear world | World > Simulation; retain existing destructive-action handling |
| World Map | World > World Map |
| Save, Save As, Open, undo, redo, history | Persistent Save/Undo plus Menu > File/History and existing shortcuts |
| Pan, zoom, rotate, fit, center selection | Existing canvas gestures/shortcuts; compact camera controls |
| Tutorial, help, Redstone Lab | Menu with named entries; tutorial behavior preserved |
| Settings, volume buses, hotkeys, display/fullscreen | Menu > Settings; retain existing state owners |
| Pin, always-visible, reduced motion | Menu > Interface; keyboard-accessible reveal control |

This is a destination plan, not proof that every callback has migrated. Before replacing the production right panel, inventory each existing callback and regression-check its reachability, modal precedence, press/drag/release capture, errors, undo and camera continuity.

## Sound direction and research

Stafford Bawler describes the isometric-scale trap directly: the structures are enormous, despite their distant presentation. Monument Valley moved from literal marble scraping toward musical and harmonious abstraction. The useful principle is a composed architectural event rather than a louder scrape. [Primary interview](https://mcvuk.com/development-news/heard-about-the-sounds-of-monument-valley/). The [Develop talk page](https://www.asoundeffect.com/video-the-sound-of-monument-valley-explored-with-sound-designer-stafford-bawler/) was located; no claim of hearing the talk or game playback is made.

Inspected [Territory's Horizon UI concepts](https://territorystudio.com/project/horizon-zero-dawn/) and its [object-focused concept image](https://territorystudio.com/wp-content/uploads/2018/09/TerritoryStudio_Games_Horizon_L_001.jpg). These are contributor concepts, not evidence of the shipped HUD's exact behavior. Apply their visual restraint and contextual association, not a literal hologram skin.

Original B's stone passage begins at source 32 s, where the next few seconds are comparatively weak. A sparse peak governs its master gain: crest factor 35.81 dB; 30-180 Hz energy is 5.17% of mono spectral energy. The revision uses sustained stone passages at 24 s and 48 s, slower recorded mechanism strain, low air displacement and irregular settling. The first revised render still had sparse extreme peaks, so it was retained under `audio/iteration1/` and revised using lookahead peak control before mastering.

- **B2 Foundation:** sustained physical load, softer surface grit, irregular foundation releases and a settling finish. [Audio](../../.qa/pass1-revision2/audio/B2-foundation.mp3), [in the native opening](../../.qa/pass1-revision2/audio/B2-foundation-in-scene.mp4).
- **B3 Resonant:** longer architectural resonance using filtered recorded excitation, with more low-frequency emphasis. [Audio](../../.qa/pass1-revision2/audio/B3-resonant.mp3), [in scene](../../.qa/pass1-revision2/audio/B3-resonant-in-scene.mp4).
- [Level-matched original B reference](../../.qa/pass1-revision2/audio/B-level-matched-reference.mp3). This reference is explicitly peak-controlled and gain-adjusted; the original B master is untouched.

All three comparison clips have RMS 0.075, not a perceptual-loudness guarantee. New candidate crest factors are 17.30/15.08 dB and low-band fractions 35.59%/46.08%. These measurements substantiate a different envelope and frequency balance, not subjective quality. B2 is the proposed physical direction; owner listening must decide whether it achieves the requested scale without becoming machinery or a cinematic rumble. No vocal or creature sources were used.

Existing decoded preview recordings are reused. Source hashes, original creator/license records, cue sheets, SuperCollider scripts and unmastered renders are retained in `.qa/pass1-revision2/audio/`. No new lossless master or Sonniss acquisition is claimed. The earlier Sonniss access limitation remains. Piano, runtime audio assets and scene geometry are unchanged. Videos are offline mixes over the unchanged 1080p native capture, with the rise starting at 13 s, not loopback recordings. Assistant subjective audition is unavailable; owner listening remains the artistic gate.

## Separate evidence and preservation

**Source/test:** [reproducible native study](../../.qa/pass1-revision2/ui_study.py), [sound authoring script](../../.qa/pass1-revision2/audio_study.py), [review exporter](../../.qa/pass1-revision2/prepare_review.py). The full application suite was not rerun for this isolated study. Prior production test evidence remains in the [first checkpoint](PASS1_OWNER_CHECKPOINT_2026-10-20.md). Final production source hashes match that checkpoint. Git diff whitespace check passed, with the existing CRLF warning only.

**Native visual:** 24 state/size renders across 960x640, 1200x800 and 1920x1080, two enlarged-text renders and one active-fill render. Hit rectangles stay within the screen; a captured press-drag-release leaves world revision/camera unchanged. [Scripted results](../../.qa/pass1-revision2/visual-checks.json). OS pointer input additionally opened Library, selected Oak Tree and closed the drawer: [native selection capture](../../.qa/pass1-revision2/native-library-selection.jpg). These checks cover the study's limited interaction scope, not production integration. Iteration removed the obsolete Fit toast and camera controls under open drawers.

**Audio:** [signal analysis](../../.qa/pass1-revision2/audio/analysis.json), [comparison method](../../.qa/pass1-revision2/audio/comparison.json), [licenses/provenance](../../.qa/pass1-revision2/audio/provenance.json), [decoded scene-mix checks](../../.qa/pass1-revision2/verification.json). Both scene mixes decode without clipped samples. An initial reference export used an unsupported limiter threshold of 0.06; corrected to 0.07 and export completed.

**Performance:** No new production performance claim. Prior preview measurements remain valid for unchanged source, but the inherited cached-load and camera gates remain on HOLD. This study does not relax them or establish final migration performance.

**Preservation:** All 56 earlier preservation targets remain byte-identical, including original media, saves/settings and root/installed executables. [Verification](../../.qa/pass1-revision2/preservation.json). No installed build, creature, production source, main branch, staging, commit or push was changed by this revision. The isolated QA window was closed after inspection.

Owner checkpoint: approve or revise compact drawers plus the larger Library, and choose B2/B3 or describe the remaining sound deficiency. Broad UI migration awaits this requested direction decision. Independent engineering from the first checkpoint remains preserved.
