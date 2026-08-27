# World Builder local reference and release assets

Bloc Fantôme's World Map has a complete generated fallback, but release builds use a small recovered presentation set from the repository owner's licensed local `WorldBuilder.zip` archive.

Expected local path:

```text
Assets/World Map/WorldBuilder/
  ui/
    question_mark.png
    question_mark_blink.png
    question_mark_shadow.png
    question_mark_rollover_blink.png
    flag1.png ... flag6.png
    bonus_flag1.png ... bonus_flag6.png
    next_world_arrow.png
    prev_world_arrow.png
    worldbuilder_title.png
    font_extended.png
  audio/
    m_game_*.mp3
    m_intro_*.mp3
    s_button_click_2.mp3
    s_goal_mission_4.mp3
    s_rollover_1.mp3
```

The complete local corpus lives at `WorldBuilder Reference/` and is intentionally
Git-ignored. Agents must start at:

```text
WorldBuilder Reference/08_AGENT_REFERENCE/START_HERE.md
```

It preserves both original archives, byte-identical DCR movies, ProjectorRays
source and bytecode output, raw chunks, a second shockwave-extractor bitmap and
audio export, SHA-256 inventories, searchable cast/Lingo indexes, and reviewed
behavior notes. Rebuild its derived indexes with:

```powershell
python "WorldBuilder Reference/99_TOOLS/build_agent_reference.py"
```

Re-export the palette-correct mission casts from their Director CASt, BITD, and
CLUT chunks with:

```powershell
python "WorldBuilder Reference/99_TOOLS/export_worldbuilder_markers.py"
```

The marker exporter preserves the original low-bit-depth palettes and Director
registration points. Do not substitute the generic shockwave-extractor PNGs:
those flatten the custom palettes and were the source of the previously correct
outline but incorrect in-app rendering.

Keep the corpus, tool binaries, private archives, and extracted assets out of
Git. `Code/build_exe.py` validates the required release subset before packaging,
while a source checkout without the private set renders native fallbacks and
uses the ordinary Bloc Fantôme audio route.
