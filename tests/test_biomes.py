import re
from pathlib import Path

from domain.blocks import BlockType
from engine.biome_catalog import BIOMES, BY_ID
from engine.biome_scenes import biome_scene
from engine.biome_capture import capture


def test_catalog_matches_local_1161_registry_exactly():
    source=Path(__file__).resolve().parents[1]/'Game Reference/05_mapped_sources/net/minecraft/world/biome/Biomes.java'
    if source.exists():
        expected=set(re.findall(r'register\(\d+, "([^"]+)"',source.read_text()))
        assert set(BY_ID)==expected
    assert len(BIOMES)==79
    assert sum(e['dimension']=='nether' for e in BIOMES)==5
    assert sum(e['dimension']=='end' for e in BIOMES)==5


def test_every_biome_is_bounded_unique_and_uses_editable_blocks():
    signatures=set()
    for entry in BIOMES:
        cells=biome_scene(entry['id'])
        width,depth=capture(entry['id'])['size'][:2]
        assert cells
        positions=set()
        for x,y,z,name in cells:
            assert 0<=x<width and 0<=y<depth and 0<=z<256
            assert name in BlockType.__members__,name
            assert (x,y,z) not in positions
            positions.add((x,y,z))
        signatures.add(hash(cells))
    assert len(signatures)==79
    assert biome_scene.cache_info().currsize<=6


def test_rebuilding_evicted_biome_is_deterministic():
    before=biome_scene('warped_forest')
    biome_scene.cache_clear()
    assert biome_scene('warped_forest')==before


def test_capture_manifest_complete_and_all_render_angles_packaged():
    from engine.biome_capture import manifest,capture,ROOT
    from engine.capture_materials import MATERIALS
    rows=manifest()
    assert set(rows)==set(BY_ID)
    assert sum(row['kind']=='natural' for row in rows.values())==74
    assert rows['the_void']['kind']=='void_preset'
    for name,row in rows.items():
        data=capture(name)
        assert data['data_version']==2567
        assert data['chunks']
        assert len(data['palette'])==len(data['editable_palette'])
        for view in range(4):assert (ROOT/'atlases'/f'{name}_{view}.png').is_file()
    for name in MATERIALS:assert (ROOT/'materials'/f'{name.lower()}.png').is_file()


def test_biome_familiarity_order_and_void_special_case():
    from ui.biomes import BiomePanel
    panel=BiomePanel()
    assert panel.entries('overworld')[0]['id']=='plains'
    assert panel.entries('nether')[0]['id']=='nether_wastes'
    assert panel.entries('end')[0]['id']=='the_end'
    assert {b[3] for b in biome_scene('the_void')}=={'STONE','COBBLESTONE'}


def test_distinctive_materials_match_biome_families():
    for biome,required in [('birch_forest','BIRCH_LOG'),('crimson_forest','CRIMSON_STEM'),
                           ('mushroom_fields','MYCELIUM'),('badlands','RED_SAND'),
                           ('bamboo_jungle','BAMBOO'),('warm_ocean','BRAIN_CORAL_BLOCK'),
                           ('end_highlands','CHORUS_PLANT'),('ice_spikes','PACKED_ICE')]:
        assert required in {c[3] for c in biome_scene(biome)}
