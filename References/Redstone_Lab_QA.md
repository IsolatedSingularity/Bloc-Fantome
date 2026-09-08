# Redstone Lab QA

Final verification: 2026-09-07. The closeout added no features and changed no runtime behavior; it removed one trailing-whitespace error in `Code/engine/model_renderer.py`.

## Results

| Check | Result |
| --- | --- |
| Full regression suite on the final source state | **277 passed in 49.58 s** |
| `git diff --check` | Passed |
| Screenshot generation | **41 PNGs**, successful exit |
| Display sizes | 960×640, 1200×800, 1920×1080 |
| Functional coverage | Door/staircase repeated cycles; clock stop/restart; feed-tape block conservation; four-bit counter overflow in four orientations; vertical pistons; comparator timing and persistence |
| Interaction coverage | Direct clicks, isolated Interact mode, editor-state restoration, pause/step/reset, timed counter pulses, autosave exclusion |
| Rendering coverage | Six piston facings, source-model equality, camera rotation, cached/full-render pixel equality after signal changes and edits |

Representative final screenshots were visually inspected for native-size text, palette/library spacing, control overlap, stage framing, door states, dust/torch appearance, piston orientation and cutaway visibility. No new functional or layout regression was found. Rotate the view or use Cutaway to inspect wiring obscured by the physical build.

Reproduction commands, using Python 3.12 from the repository root:

```powershell
python -m pytest -q -p no:cacheprovider --basetemp=.qa/redstone-closeout-exact
python tests/render_visual_checks.py .qa/redstone-closeout --redstone
git diff --check
```

Logs: `.qa/redstone-closeout-exact.log` and `.qa/redstone-closeout-render.log`. Images: `.qa/redstone-closeout/`. Final source hashes: `.qa/redstone-closeout-final-sha256.json`.

## Source fidelity and boundaries

The counter preserves all 1,989 records from `Redstone Reference/05_NORMALIZED/counter4-64863392d381.blocks.jsonl`; colored concrete maps to matching wool. Its clock follows the producer's 30-tick HIGH / 110-tick LOW contract in `03_VERIFIED/nucleation-redstone-eda/seq_counter.py`. Other exhibits are authored adaptations of ordinary mechanisms, not exact copies of creator schematics.

Piston, comparator and wall-torch model elements match the local Java 1.16.1 asset JSON. Simulation reference: `Game Reference/05_mapped_sources/net/minecraft/block/`. This is not a claim of complete vanilla parity. Quasi-connectivity remains disabled in the Lab as agreed; comparator container/item-frame inputs remain unsupported.

The earlier 1080p benchmark measured p95 frame times of 5.57 ms (door), 7.27 ms (clock), and 17.06 ms (counter), with occasional higher spikes. These were 300 warmed headless frames per exhibit, not a guarantee of uninterrupted 60 FPS.

## Handoff

Implementation centers on `Code/engine/redstone.py`, `redstone_lab.py`, `model_renderer.py`, `piston_models.py`, `lab_render_cache.py`, `Code/ui/redstone_lab.py`, and `Code/blocFantome.py`; supporting changes cover block state, persistence, counter data, packaging data inclusion and tests. README and World Map were not edited. Changes remain unstaged, uncommitted and unpushed. No executable was rebuilt.

An earlier live QA run exposed the old Lab autosave leak and wrote `Code/saves/_autosave.json.gz`; its prior contents were not recovered. The separate root `Saves` folder was unchanged. Lab autosaving is now blocked and regression-tested; subsequent QA launches disabled persistence. The temporary live QA process has exited.

Next step: owner review of the source app and screenshots. No further feature work is included in this closeout.
