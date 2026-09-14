"""A compact, ungated journey through building, dimensions and living systems."""
def page(key,title,text,hint,focus='canvas',capture=None,world=None):
    return dict(id=key,title=title,content=[text],hint=hint,goals=[],icons='oak_planks oak_log glass oak_stairs cobblestone poppy water lantern grass'.split(),scene=key,dimension='overworld',focus=focus,is_horror=key=='horror',capture=capture,world=world)

TOUR=(
 page('welcome','Before the night','Someone left a light burning. No footprints lead away from the door. You have until sunset to decide what that means.','Drag or minimize this panel. Back and Next move freely. Leave restores your own build.'),
 page('blocks','What the sand kept','The well is older than the houses. Nobody remembers digging it. Every morning, the rope comes back wet.','Choose Blocks or a hotbar slot (1-9). Left-click places; right-click removes. R turns stairs. F flips a stair or slab.','blocks',capture='_scene_tour_well'),
 page('camera','The watch is over','The banner still hangs. The sentry does not. From the road, you would never see the open door.','Q / E rotates; wheel zooms. Middle-drag or WASD pans. Home fits the scene. F11 opens fullscreen.',capture='_scene_tour_outpost'),
 page('history','Across the fire','They built a road across the fire, then barred the far gate. Whatever crossed first never came back.','Change a stretch of the bridge. Ctrl+Z undoes; Ctrl+Y redoes. F fills between two corners; B cycles brush size.',capture='_scene_tour_fortress'),
 page('structures','The bells still ring','A bell at dawn. Another at dusk. The village beyond the hill answers neither.','Structures places a chosen building on your canvas. Ctrl+B selects an area; Ctrl+C / V copies and pastes.','structures',world='village_plains_1161'),
 page('terrain','The earth remembers','The rain took the names. The wind took the roads. Something beneath this ground has outlasted both.','Terrain Slice creates a building landscape. Canvas + / - expands or contracts its bounds; the terrain tool shapes local ground.','terrain',capture='eroded_badlands'),
 page('biomes','Roots without sunlight','Nothing here has seen the sun. Still the forest grows toward something. Listen before you cut.','Biomes holds larger captured landscapes. Select a dimension and preview, then Open scene.','biomes',capture='warped_forest'),
 page('dimensions','No road home','There are doors at the tops of these towers. No stairs beneath them. Whoever lived here expected to arrive another way.','Worlds opens complete scenes. The Overworld, Nether and End have separate terrain, skies and weather. Q / E reveals the city.','worlds',world='end_city_1161'),
 page('skies','The long turning','The stars have moved since the last watch. One has stayed above the same hill. Do not use it to find north.','This sky turns slowly on its own. Rotate or pan the build to see the difference. World Controls selects other sky presets.','toggles'),
 page('rain','Water at the threshold','By morning the path will be gone. The reeds already lean toward the door. Keep the lantern above the waterline.','Rain is running now. World Controls switches rain, snow, clouds and the sky independently.','toggles',capture='swamp'),
 page('snow','A quieter warning','The first tracks led into the trees. Snow covered them before you found the second set. Those led out.','Snow is running now. Try the weather controls in other dimensions; their effects change with the world.','toggles',capture='snowy_taiga'),
 page('liquids','Beneath the tide','The sea rose. The lamps stayed lit. Far below the boats, something is still keeping watch.','The water is cut away to reveal the real monument; every source water cell remains editable. Place a liquid; L toggles flow.',world='ocean_monument_1161'),
 page('lighting','The price of gold','The vault is open. The floor around it is clean. Even the ash has learned to keep its distance.','Lighting is enabled. Place a lantern or glowstone and watch the nearby surfaces. World Controls switches illumination.','toggles',capture='_scene_tour_bastion'),
 page('redstone','A machine that waits','Four lamps. Sixteen answers. Whoever built this left no name, only a way to count the hours.','This is the full 4-bit counter. Open Redstone Lab above Settings and choose 4-bit Counter; Pulse +1 drives its real register.','canvas'),
 page('worldmap','Beyond this shore','The map ends where the ink ran out. The world did not. There are lights beyond the last crossing.','Explore the live World Map. Return to Build comes back to this page; Next then continues the tour.'),
 page('saving','Leave a light','Build something that will survive your absence. A shelter. A crossing. One small light for whoever comes next.','Ctrl+S saves; Ctrl+O opens saved builds. Leave returns to your canvas. The ? beside Settings always reopens the tour.','settings',capture='mushroom_fields'),
)
OPTIONAL_HORROR=page('horror','The last service','The seats face an empty wall. Beneath the floor, something knocks three times. Nobody taught you the answer.','Look around freely. Back returns to the last page; Leave restores your original canvas.')

def tour_scene(step):
    from engine.tutorial_scenes import scene_snapshot
    return dict(scene_snapshot(step['id']).blocks)
def practice_scene(kind):
    from engine.tutorial_scenes import scene_snapshot
    return dict(scene_snapshot('welcome' if kind=='cottage' else kind).blocks)
