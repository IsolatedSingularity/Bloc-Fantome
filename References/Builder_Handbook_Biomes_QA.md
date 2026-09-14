# Builder Handbook and Biomes release 2.8.0

Implemented dimension-aware six-face skies with bounded polygon scenery layers,
smooth rotation, native projection, and a Python fallback. Skyboxes remain optional.

Biomes contains all 79 registered Java 1.16.1 biomes: 69 Overworld, five Nether,
and five End. Large block-rendered cards open editable scenes after confirmation.
The roster and settings come from the local mapped Java sources. Scenes are
representative dioramas, not reproductions of Java seed generation.

Getting Started has seven connected practice lessons. The Builder's Handbook has
20 selectable lessons covering building tools, terrain, biomes, dimensions,
atmosphere, liquids, lighting, redstone, saving, and an unsettling room that changes
when viewed from another direction. Lessons have observed objectives, hints,
retry, skip, and saved completion. Leaving restores the original build and tools.

Implementation is concentrated in `Code/ui/tutorial.py`,
`Code/engine/tutorial_runtime.py`, `Code/engine/tutorial_lessons.py`,
`Code/ui/biomes.py`, `Code/engine/biome_catalog.py`,
`Code/engine/biome_scenes.py`, `Code/engine/skybox.py`,
`Code/engine/sky_layers.py`, the native renderer, and application integration.
The splash and README were not changed for this feature request.

Validation:

- Full suite: 301 passed (`.qa/pytest-release-280.log`).
- After final handbook navigation and hotbar highlight fixes: all 128 application
  integration tests passed, including a new navigation regression
  (`.qa/pytest-final-nav.log`).
- Compile checks and `git diff --check` passed.
- All 79 previews and lesson layouts rendered at 960x640, 1200x800, and
  1920x1080; evidence is in `.qa/guided-release-visual`.
- Native and NumPy cubemap output parity is regression tested.
- 1080p sky rendering p95: settled 6.2–7.5 ms; paced rotation 12.2–13.8 ms.
  Cold maximum frames were 23.7–26.4 ms. These are measured rendering times on
  the development machine, not a guarantee for every build or machine.
- Final executable archive includes all new modules, native DLL, Tk dialogs,
  and existing packaged map assets (`.qa/archive-280.log`).
- Live packaged UI verified placement credit and restoration on leaving practice.

Release installation and shortcut evidence:
`.qa/guided-280-install-verification.json` and `.qa/guided-280-install.log`.
