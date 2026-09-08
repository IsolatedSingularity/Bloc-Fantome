from collections import Counter
from types import SimpleNamespace

from domain.blocks import BlockType
from domain.world_catalog import WorldCatalog
from engine.world import World
from engine.world_map import build_hub
from engine.world_map_regions import REGIONS, build_region_hub, load_region


def _world() -> World:
    definitions = {
        block: SimpleNamespace(isDoor=False, isStair=False, isSlab=False, modelKind=None)
        for block in BlockType
    }
    catalog = WorldCatalog(
        BlockType,
        BlockType.AIR,
        BlockType.WATER,
        BlockType.LAVA,
        BlockType.OBSIDIAN,
        BlockType.COBBLESTONE,
        BlockType.STONE,
        definitions,
    )
    return World(1, 1, 1, catalog=catalog)


def test_nether_regions_preserve_full_vanilla_assemblies_and_all_five_biomes():
    world = _world()
    scene = build_hub(world, "nether")
    assert (world.width, world.depth, world.height) == (240,240,256)
    assert scene.region_key == "bastion"
    biomes=set()
    for key,_label in REGIONS['nether']:
        data=load_region('nether',key)
        assert data['seed']==1 and data['data_version']==2567
        assert len(data['chunks'])==225
        biomes.update(map(int,data['biomes']))
    assert {8,170,171,172,173} <= biomes
    bastion=load_region('nether','bastion')['structures']['bastion_remnant:-50,-9']
    assert len(bastion['Children'])==112
    assert 'hoglin_stable' in bastion['Children'][0]['pool_element']['location']
    fortress=load_region('nether','fortress')['structures']['fortress:21,-8']
    assert len(fortress['Children'])==147
    assert fortress['BB']==[237,48,-184,454,83,-13]


def test_end_capture_contains_central_island_and_complete_natural_city_ship():
    world = _world()
    scene = build_hub(world, "end")
    assert scene.region_key=='central'
    data=load_region('end','central')
    assert len([e for e in data['entities'] if e['id']=='minecraft:end_crystal'])==10
    assert {'minecraft:iron_bars','minecraft:wall_torch','minecraft:bedrock','minecraft:obsidian'} <= {p['Name'] for p in data['palette']}
    scene=build_region_hub(world,'end','city')
    assert scene.route_indices==(0,1)
    data=load_region('end','city')
    city=data['structures']['endcity:-73,-15']
    assert len(city['Children'])==57
    assert sum(c.get('Template')=='ship' for c in city['Children'])==1
    ox,oz=data['origin']
    for child in city['Children']:
        x0,y0,z0,x1,y1,z1=child['BB']
        assert 0 <= x0-ox <= x1-ox < world.width
        assert 0 <= z0-oz <= z1-oz < world.depth
        assert 0 <= y0 <= y1 < world.height


def test_captured_palette_states_are_retained_without_material_aliases():
    data=load_region('nether','fortress')
    names={p['Name'] for p in data['palette']}
    assert {'minecraft:nether_brick_fence','minecraft:nether_brick_stairs','minecraft:spawner'} <= names
    fences=[p for p in data['palette'] if p['Name']=='minecraft:nether_brick_fence']
    assert len(fences)>1
    assert all({'north','east','south','west'} <= set(p['Properties']) for p in fences)
    assert all(0<=x<240 and 0<=z<240 and 0<=y<256 and 0<index<len(data['palette']) for x,z,y,index in data['blocks'])


def test_ocean_hub_has_full_58_block_monument_without_decorative_water_blocks():
    world = _world()
    scene = build_hub(world, "ocean")
    data = load_region('ocean','monument')
    counts = Counter(data['palette'][pid]['Name'] for x,z,y,pid in data['blocks'])
    assert data['structures']['monument:-55,-53']['BB'] == [-909,39,-877,-852,61,-820]
    assert counts['minecraft:prismarine'] > 1000
    assert counts['minecraft:sea_lantern'] >= 15
    assert counts['minecraft:kelp'] > 0 and counts['minecraft:seagrass'] > 0
    assert counts['minecraft:water'] == 0
    assert scene.runtime_dimension == 'overworld'
    assert scene.route_indices == (0,)
    ship = load_region('ocean','shipwreck')
    assert ship['structures']['shipwreck:-18,11']['BB'] == [-292,50,187,-269,58,195]
    assert not world.blocks


def test_overworld_has_requested_biomes_and_complete_taiga_village():
    taiga = load_region('overworld','taiga')
    mushroom = load_region('overworld','mushroom')
    assert '5' in taiga['biomes'] and '14' in mushroom['biomes']
    assert any(p['Name']=='minecraft:spruce_log' for p in taiga['palette'])
    assert {'minecraft:mycelium','minecraft:red_mushroom_block','minecraft:brown_mushroom_block'} <= {p['Name'] for p in mushroom['palette']}
    ox,oz=taiga['origin']
    for piece in taiga['structures']['village:-11,-18']['Children']:
        x0,y0,z0,x1,y1,z1=piece['BB']
        assert ox<=x0<=x1<ox+taiga['size'][0]
        assert oz<=z0<=z1<oz+taiga['size'][1]


def test_outer_islands_have_no_end_stone_at_capture_boundaries():
    data=load_region('end','city')
    width,depth=data['size'][:2]
    assert width>=512 and depth>=512
    assert all(x not in (0,width-1) and z not in (0,depth-1)
               for x,z,y,pid in data['blocks'] if data['palette'][pid]['Name']=='minecraft:end_stone')
