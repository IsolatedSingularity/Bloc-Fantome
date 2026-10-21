# Capability destinations and evidence

The callable routes below are the production inventory, not placeholder study buttons. `command` uses `_executeInputCommand`; `key` uses the existing `_handleKeyDown` with explicit modifiers; `method` calls the named original app method. Retained does not mean every operation received native OS-input acceptance. The current suite and native evidence are linked from REVIEW.md.

| Old control / shortcut | New location | Callable route | Actual verification / limit |
|---|---|---|---|
| F on non-half blocks | Tools > Fill corners | `command: TOGGLE_FILL` | Production test enables existing fill tool. |
| b | Tools > Brush size | `key: b` | Route exists in production; destination/field inventory checked. Individual OS-input acceptance pending. |
| Ctrl+B | Tools > Select / confirm corners | `command: START_OR_CONFIRM_SELECTION` | Route exists in production; destination/field inventory checked. Individual OS-input acceptance pending. |
| Ctrl+C | Tools > Copy selection | `key: c, ctrl` | Production test copies selected blocks; Ctrl+C no longer clears the world. |
| Ctrl+V | Tools > Paste clipboard | `key: v, ctrl` | Route exists in production; destination/field inventory checked. Individual OS-input acceptance pending. |
| [ | Tools > Rotate clipboard left | `key: [` | Route exists in production; destination/field inventory checked. Individual OS-input acceptance pending. |
| ] | Tools > Rotate clipboard right | `key: ]` | Route exists in production; destination/field inventory checked. Individual OS-input acceptance pending. |
| Ctrl+A | Tools > Fill selection | `key: a, ctrl` | Route exists in production; destination/field inventory checked. Individual OS-input acceptance pending. |
| Ctrl+H with a confirmed selection | Tools > Hollow selection | `command: HOLLOW_SELECTION` | Route exists in production; destination/field inventory checked. Individual OS-input acceptance pending. |
| delete | Tools > Delete selection | `key: delete` | Route exists in production; destination/field inventory checked. Individual OS-input acceptance pending. |
| f + ctrl + shift | Tools > Flood fill | `key: f, ctrl, shift` | Route exists in production; destination/field inventory checked. Individual OS-input acceptance pending. |
| Ctrl+R | Tools > Replace material | `command: TOGGLE_REPLACE` | Route exists in production; destination/field inventory checked. Individual OS-input acceptance pending. |
| w + ctrl + shift | Tools > Connected selection / wand | `key: w, ctrl, shift` | Route exists in production; destination/field inventory checked. Individual OS-input acceptance pending. |
| p | Tools > Stamp clipboard | `key: p` | Route exists in production; destination/field inventory checked. Individual OS-input acceptance pending. |
| Ctrl+Shift+B | Tools > Blueprint / apply | `command: TOGGLE_BLUEPRINT` | Route exists in production; destination/field inventory checked. Individual OS-input acceptance pending. |
| Ctrl+M | Tools > Mirror X | `command: TOGGLE_X_MIRROR` | Production test enables X mirror. |
| Shift+M | Tools > Mirror Y | `command: TOGGLE_Y_MIRROR` | Production test enables Y mirror. |
| t + ctrl | Tools > Radial symmetry | `key: t, ctrl` | Production test cycles 4, 8, off; Ctrl+T no longer opens structures. |
| M | Tools > Measure | `command: TOGGLE_MEASUREMENT` | Route exists in production; destination/field inventory checked. Individual OS-input acceptance pending. |
| / | Tools > Layer view | `key: /` | Route exists in production; destination/field inventory checked. Individual OS-input acceptance pending. |
| . | Tools > Layer up | `key: .` | Route exists in production; destination/field inventory checked. Individual OS-input acceptance pending. |
| , | Tools > Layer down | `key: ,` | Route exists in production; destination/field inventory checked. Individual OS-input acceptance pending. |
| g | Tools > Grid | `key: g` | Route exists in production; destination/field inventory checked. Individual OS-input acceptance pending. |
| x | Tools > X-ray | `key: x` | Route exists in production; destination/field inventory checked. Individual OS-input acceptance pending. |
| tab | Tools > Minimap | `key: tab` | Route exists in production; destination/field inventory checked. Individual OS-input acceptance pending. |
| Shift+Home | Tools > Center selection / cursor | `command: CENTER_CONTEXT` | Route exists in production; destination/field inventory checked. Individual OS-input acceptance pending. |
| i | Tools > Build / interact | `key: i` | Route exists in production; destination/field inventory checked. Individual OS-input acceptance pending. |
| r | Tools > Rotate placement | `key: r` | Route exists in production; destination/field inventory checked. Individual OS-input acceptance pending. |
| r + shift | Tools > Rotate placed block | `key: r, shift` | Route exists in production; destination/field inventory checked. Individual OS-input acceptance pending. |
| F on stairs/slabs | Tools > Flip half | `command: FLIP_PREVIEW_HALF` | Production test flips the original half property. |
| Overworld | World > Overworld | `method: _switchDimension, overworld` | Route exists in production; destination/field inventory checked. Individual OS-input acceptance pending. |
| Nether | World > Nether | `method: _switchDimension, nether` | Route exists in production; destination/field inventory checked. Individual OS-input acceptance pending. |
| The End | World > The End | `method: _switchDimension, end` | Route exists in production; destination/field inventory checked. Individual OS-input acceptance pending. |
| Generate terrain slice | World > Generate terrain slice | `method: _generateTerrainSlice` | Route exists in production; destination/field inventory checked. Individual OS-input acceptance pending. |
| Grow canvas | World > Grow canvas | `method: _resizeCanvas, 16` | Route exists in production; destination/field inventory checked. Individual OS-input acceptance pending. |
| Shrink canvas | World > Shrink canvas | `method: _resizeCanvas, -16` | Route exists in production; destination/field inventory checked. Individual OS-input acceptance pending. |
| Local terrain noise | World > Local terrain noise | `method: _applyLocalTerrainNoise` | Route exists in production; destination/field inventory checked. Individual OS-input acceptance pending. |
| Terrain visibility | World > Terrain visibility | `terrain_view: ` | Route exists in production; destination/field inventory checked. Individual OS-input acceptance pending. |
| Rain | World > Rain | `method: _toggleRain` | Route exists in production; destination/field inventory checked. Individual OS-input acceptance pending. |
| Snow | World > Snow | `method: _toggleSnow` | Route exists in production; destination/field inventory checked. Individual OS-input acceptance pending. |
| Sun / moon | World > Sun / moon | `method: _toggleCelestial` | Route exists in production; destination/field inventory checked. Individual OS-input acceptance pending. |
| Clouds | World > Clouds | `method: _toggleClouds` | Route exists in production; destination/field inventory checked. Individual OS-input acceptance pending. |
| Lighting / AO | World > Lighting / AO | `method: _toggleLighting` | Route exists in production; destination/field inventory checked. Individual OS-input acceptance pending. |
| Skybox | World > Skybox | `method: _toggleSkyboxes` | Route exists in production; destination/field inventory checked. Individual OS-input acceptance pending. |
| Previous sky | World > Previous sky | `method: _cycleSkybox, -1` | Route exists in production; destination/field inventory checked. Individual OS-input acceptance pending. |
| Next sky | World > Next sky | `method: _cycleSkybox, 1` | Route exists in production; destination/field inventory checked. Individual OS-input acceptance pending. |
| Horror rain | World > Horror rain | `method: _toggleHorrorRain` | Route exists in production; destination/field inventory checked. Individual OS-input acceptance pending. |
| l | World > Liquid simulation | `key: l` | Route exists in production; destination/field inventory checked. Individual OS-input acceptance pending. |
| Clear liquids | World > Clear liquids | `method: _clearAllLiquids` | Route exists in production; destination/field inventory checked. Individual OS-input acceptance pending. |
| World Map | World > World Map | `method: _openWorldMap` | Native renders at 100/150% text; original campaign/traveler tests. |
| c | World > Clear world | `key: c` | Production confirmation test consumes keys and Escape preserves the build. |
| Ctrl+S | Menu > Save | `save: ` | Native scripted compressed save/reopen preserves all 147 test blocks. |
| Save As | Menu > Save As | `method: _openSaveAsDialog` | Route exists in production; destination/field inventory checked. Individual OS-input acceptance pending. |
| Open Library | Menu > Open Library | `library: Saved Builds` | Route exists in production; destination/field inventory checked. Individual OS-input acceptance pending. |
| Ctrl+Z | Menu > Undo | `undo: ` | Native mouse placement/Undo restores blocks; production undo/redo test. |
| Ctrl+Y | Menu > Redo | `redo: ` | Production test restores the undone block. |
| Ctrl+H without a confirmed selection | Menu > History | `command: TOGGLE_HISTORY` | Native render at 150% text; original jump handler retained. |
| Settings / audio | Menu > Settings / audio | `settings: ` | Native render at 3 text sizes; slider/mute displayed-hitbox tests. |
| Controls / shortcuts | Menu > Controls / shortcuts | `help: ` | Native render at 3 text sizes. |
| Tutorial | Menu > Tutorial | `method: _beginTutorial` | Native tutorial/minimized captures; prepared lesson and restoration tests. |
| Advanced tutorial | Menu > Advanced tutorial | `method: _beginTutorial, True` | Original advanced=True route retained; prepared lesson suite. |
| Redstone Lab | Menu > Redstone Lab | `method: _toggleRedstoneLab` | Native renders and scroll at 100/150% text; original simulator tests. |
| Screenshot | Menu > Screenshot | `method: _takeScreenshot` | Route exists in production; destination/field inventory checked. Individual OS-input acceptance pending. |
| Fullscreen / windowed | Menu > Fullscreen / windowed | `method: _toggleFullscreen` | Three native scripted fullscreen round trips preserve exact zoom and world anchor. |
| Pin working controls | Menu > Pin working controls | `preference: pinned` | Route exists in production; destination/field inventory checked. Individual OS-input acceptance pending. |
| Always show controls | Menu > Always show controls | `preference: always` | Route exists in production; destination/field inventory checked. Individual OS-input acceptance pending. |
| Reduced motion | Menu > Reduced motion | `preference: reduced_motion` | Route exists in production; destination/field inventory checked. Individual OS-input acceptance pending. |
| Text size | Menu > Text size | `text_scale: ` | Native renders and hitbox checks at 100/125/150% text. |
| Clean Canvas | Menu > Clean Canvas | `clean: ` | Native clean capture; unchanged build/camera state by presentation-only flag. |
| Legacy fallback | Menu > Legacy fallback | `legacy: ` | Route exists in production; destination/field inventory checked. Individual OS-input acceptance pending. |
| Quick save 1 | Menu > Quick save 1 | `method: _quickSave, 1` | Route exists in production; destination/field inventory checked. Individual OS-input acceptance pending. |
| Quick save 2 | Menu > Quick save 2 | `method: _quickSave, 2` | Route exists in production; destination/field inventory checked. Individual OS-input acceptance pending. |
| Quick save 3 | Menu > Quick save 3 | `method: _quickSave, 3` | Route exists in production; destination/field inventory checked. Individual OS-input acceptance pending. |
| Quick save 4 | Menu > Quick save 4 | `method: _quickSave, 4` | Route exists in production; destination/field inventory checked. Individual OS-input acceptance pending. |
| Quick load 1 | Menu > Quick load 1 | `method: _quickLoad, 1` | Route exists in production; destination/field inventory checked. Individual OS-input acceptance pending. |
| Quick load 2 | Menu > Quick load 2 | `method: _quickLoad, 2` | Route exists in production; destination/field inventory checked. Individual OS-input acceptance pending. |
| Quick load 3 | Menu > Quick load 3 | `method: _quickLoad, 3` | Route exists in production; destination/field inventory checked. Individual OS-input acceptance pending. |
| Quick load 4 | Menu > Quick load 4 | `method: _quickLoad, 4` | Route exists in production; destination/field inventory checked. Individual OS-input acceptance pending. |

## Content, gestures and specialized controls

| Previous capability | Current location and route | Evidence |
|---|---|---|
| Full block palette, categories, search | Build drawer, dynamic `world.catalog.definitions`, `_selectBlockForPlacement` | 464 non-air identities plus AIR retained; full-catalog/filter tests; native Oxidized Copper selection |
| Favorites/recent | Build category menu; right-click material; Favorite | Production filtering tests; original preference persistence retained |
| Hotbar slots, assignment, drag | Bottom hotbar; keys 1–9, right-click assignment, material or slot drag | Native material drag to slot 5, select/place/Undo; production release-capture test |
| Door, stair, slab and redstone properties | Lower-left contextual Half/Turn/Build-Interact; Tools for all routes | Original model/source/interaction tests, native stair context; not every model manually clicked |
| Q/E, pan, wheel, Fit | Bottom-right Q/Fit/E; existing mouse and shortcuts | Resize/zoom/rotation exactness tests; native fullscreen round trips |
| World/Biome/Structure/Build galleries and side previews | Library four tabs, real asynchronous previews; explicit Open or Place | All four native captures; native preview selection did not place; cancellation/ownership tests |
| Java import and saved build browse | Library Worlds > Browse Java world; other tabs > Browse file | Original native dialog methods retained; OS file dialog flow not recorded |
| World Map dimension/region/level/traveler controls | World > World Map; shared matte controls with original artwork and campaign | Native hub and source/catalog/travel tests; full campaign not manually replayed |
| Tutorial drag, minimize, startup checkbox, previous/next/leave | Menu > Tutorial / Advanced tutorial; same movable panel | Native regular/minimized captures; prepared scenes, session restoration and panel drag tests |
| Lab circuits/components/simulation/build/test/cutaway/return | Menu > Redstone Lab; scrollable native text panel | Native normal/scrolled captures, simulator and session restoration tests |
| Settings/audio/mute/preferences | Menu > Settings/audio; shared measured hitboxes | Native scale matrix; mute and slider tests |
| Recover hidden controls | Bottom 16 px hot zone, Controls, F1, Ctrl+Tab; Menu pin/always-visible | Hidden controls have no hits; native quiet/clean captures; keyboard handler tests, OS injection incomplete |
| Legacy fallback | Menu > Legacy fallback; Ctrl+Tab returns | Retained until owner acceptance; modern default never reserves old sidebar width |

Save errors persist in the modern workshop; failed loads preserve the live scene. Success and undo acknowledgements expire after three seconds. Clear-world buttons require confirmation; Escape and Cancel preserve the build. Library selection only previews; Open/Place is separate. Native keyboard delivery and a complete uninterrupted owner workflow remain acceptance gaps, rather than inferred passes.
