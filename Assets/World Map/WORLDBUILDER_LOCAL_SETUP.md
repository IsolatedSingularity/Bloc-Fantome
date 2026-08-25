# WorldBuilder local asset setup

Bloc Fantôme's World Map has a complete generated fallback, but release builds use a small recovered presentation set from the repository owner's licensed local `WorldBuilder.zip` archive.

Expected local path:

```text
Assets/World Map/WorldBuilder/
  ui/
    question_mark.png
    question_mark_blink.png
    question_mark_shadow.png
    flag1.png ... flag6.png
    bonus_flag1.png ... bonus_flag6.png
    next_world_arrow.png
    prev_world_arrow.png
    worldbuilder_title.png
  audio/
    m_game_*.mp3
    m_intro_*.mp3
    s_button_click_2.mp3
    s_goal_mission_4.mp3
    s_rollover_1.mp3
```

The local archive was inspected with ProjectorRays and its Director cast assets were exported without bundling the old Shockwave runtime or obsolete game logic. Keep the archive and extracted binary assets out of Git. `Code/build_exe.py` validates the required release subset before packaging, while a source checkout without the private set renders native fallback markers and uses the ordinary Bloc Fantôme audio route.
