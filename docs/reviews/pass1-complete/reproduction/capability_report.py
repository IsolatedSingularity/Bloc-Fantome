from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'Code'))
from ui.workshop_actions import TOOLS,WORLD,MENU
shortcuts={'fill':'F on non-half blocks','half':'F on stairs/slabs','selection':'Ctrl+B','copy':'Ctrl+C','paste':'Ctrl+V','fill_selection':'Ctrl+A','hollow':'Ctrl+H with a confirmed selection','history':'Ctrl+H without a confirmed selection','blueprint':'Ctrl+Shift+B','mirror_x':'Ctrl+M','mirror_y':'Shift+M','measure':'M','replace':'Ctrl+R','center':'Shift+Home','undo':'Ctrl+Z','redo':'Ctrl+Y','save':'Ctrl+S'}
verified={'copy':'Production test copies selected blocks; Ctrl+C no longer clears the world.','radial':'Production test cycles 4, 8, off; Ctrl+T no longer opens structures.','fill':'Production test enables existing fill tool.','mirror_x':'Production test enables X mirror.','mirror_y':'Production test enables Y mirror.','half':'Production test flips the original half property.','undo':'Native mouse placement/Undo restores blocks; production undo/redo test.','redo':'Production test restores the undone block.','clear_world':'Production confirmation test consumes keys and Escape preserves the build.','fullscreen':'Three native scripted fullscreen round trips preserve exact zoom and world anchor.','save':'Native scripted compressed save/reopen preserves all 147 test blocks.','history':'Native render at 150% text; original jump handler retained.','map':'Native renders at 100/150% text; original campaign/traveler tests.','lab':'Native renders and scroll at 100/150% text; original simulator tests.','settings':'Native render at 3 text sizes; slider/mute displayed-hitbox tests.','help':'Native render at 3 text sizes.','tutorial':'Native tutorial/minimized captures; prepared lesson and restoration tests.','advanced_tutorial':'Original advanced=True route retained; prepared lesson suite.','clean':'Native clean capture; unchanged build/camera state by presentation-only flag.','text_scale':'Native renders and hitbox checks at 100/125/150% text.'}
rows=['# Capability destinations and evidence','',
'The callable routes below are the production inventory, not placeholder study buttons. `command` uses `_executeInputCommand`; `key` uses the existing `_handleKeyDown` with explicit modifiers; `method` calls the named original app method. Retained does not mean every operation received native OS-input acceptance. The current suite and native evidence are linked from REVIEW.md.','',
'| Old control / shortcut | New location | Callable route | Actual verification / limit |','|---|---|---|---|']
for group,actions in [('Tools',TOOLS),('World',WORLD),('Menu',MENU)]:
 for id,label,route,args,field in actions:
  old=shortcuts.get(id,(' + '.join(args) if route=='key' else label))
  target=route+': '+', '.join(getattr(x,'name',str(x)) for x in args)
  outcome=verified.get(id,'Route exists in production; destination/field inventory checked. Individual OS-input acceptance pending.')
  rows.append(f'| {old} | {group} > {label} | `{target}` | {outcome} |')
rows += ['', '## Content, gestures and specialized controls','',
'| Previous capability | Current location and route | Evidence |','|---|---|---|',
'| Full block palette, categories, search | Build drawer, dynamic `world.catalog.definitions`, `_selectBlockForPlacement` | 464 non-air identities plus AIR retained; full-catalog/filter tests; native Oxidized Copper selection |',
'| Favorites/recent | Build category menu; right-click material; Favorite | Production filtering tests; original preference persistence retained |',
'| Hotbar slots, assignment, drag | Bottom hotbar; keys 1–9, right-click assignment, material or slot drag | Native material drag to slot 5, select/place/Undo; production release-capture test |',
'| Door, stair, slab and redstone properties | Lower-left contextual Half/Turn/Build-Interact; Tools for all routes | Original model/source/interaction tests, native stair context; not every model manually clicked |',
'| Q/E, pan, wheel, Fit | Bottom-right Q/Fit/E; existing mouse and shortcuts | Resize/zoom/rotation exactness tests; native fullscreen round trips |',
'| World/Biome/Structure/Build galleries and side previews | Library four tabs, real asynchronous previews; explicit Open or Place | All four native captures; native preview selection did not place; cancellation/ownership tests |',
'| Java import and saved build browse | Library Worlds > Browse Java world; other tabs > Browse file | Original native dialog methods retained; OS file dialog flow not recorded |',
'| World Map dimension/region/level/traveler controls | World > World Map; shared matte controls with original artwork and campaign | Native hub and source/catalog/travel tests; full campaign not manually replayed |',
'| Tutorial drag, minimize, startup checkbox, previous/next/leave | Menu > Tutorial / Advanced tutorial; same movable panel | Native regular/minimized captures; prepared scenes, session restoration and panel drag tests |',
'| Lab circuits/components/simulation/build/test/cutaway/return | Menu > Redstone Lab; scrollable native text panel | Native normal/scrolled captures, simulator and session restoration tests |',
'| Settings/audio/mute/preferences | Menu > Settings/audio; shared measured hitboxes | Native scale matrix; mute and slider tests |',
'| Recover hidden controls | Bottom 16 px hot zone, Controls, F1, Ctrl+Tab; Menu pin/always-visible | Hidden controls have no hits; native quiet/clean captures; keyboard handler tests, OS injection incomplete |',
'| Legacy fallback | Menu > Legacy fallback; Ctrl+Tab returns | Retained until owner acceptance; modern default never reserves old sidebar width |',
'', 'Save errors persist in the modern workshop; failed loads preserve the live scene. Success and undo acknowledgements expire after three seconds. Clear-world buttons require confirmation; Escape and Cancel preserve the build. Library selection only previews; Open/Place is separate. Native keyboard delivery and a complete uninterrupted owner workflow remain acceptance gaps, rather than inferred passes.']
(ROOT/'docs/reviews/pass1-complete/CAPABILITIES.md').write_text('\n'.join(rows)+'\n',encoding='utf-8')
print('Wrote capability inventory')
