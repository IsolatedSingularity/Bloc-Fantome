import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import pygame
import pytest
from engine.atmosphere import Atmosphere, DepthStencil, rain_material
from engine.renderer import IsometricRenderer


def test_motion_is_time_based_and_bounded():
    a,b=Atmosphere(42),Atmosphere(42)
    a.start_rain((1200,800)); b.start_rain((1200,800))
    for _ in range(60):a.update(1000/60, True, False)
    for _ in range(120):b.update(1000/120, True, False)
    assert a.elapsed==pytest.approx(b.elapsed)
    assert a.intensity==pytest.approx(b.intensity,abs=.002)
    assert len(a.drops)==len(b.drops)
    assert {p['depth'] for p in a.drops}=={0,1,2}
    for _ in range(10000):a.update(16,True,False)
    assert .55<=a.intensity<=1.45
    assert len(a.drops)<=Atmosphere.MAX_DROPS
    a.stop_rain()
    assert not a.drops and a.rain_layer is None


def test_depth_preserves_cutouts_and_transparency_in_painter_order():
    pygame.init()
    r=IsometricRenderer(0,0)
    d=DepthStencil((64,64),r,(0,20))
    far=pygame.Surface((32,32),pygame.SRCALPHA);far.fill((255,255,255,255))
    near=far.copy();near.fill((0,0,0,0),(8,8,8,8))
    d.add(far,(0,0),0);d.add(near,(0,0),20);d.flush()
    assert d.surface.get_at((1,1)).r<10
    assert d.surface.get_at((3,3)).r>240
    glass=far.copy();glass.set_alpha(80)
    d.add(glass,(0,0),0);d.flush()
    assert 20<d.surface.get_at((1,1)).r<150


def test_fog_changes_without_world_repaint_and_keeps_foreground_clear():
    pygame.init()
    a=Atmosphere(330);screen=pygame.Surface((320,240),pygame.SRCALPHA)
    r=IsometricRenderer(0,0)
    source=pygame.Surface((320,240),pygame.SRCALPHA)
    d=a.begin_depth(source,r,(0,20))
    block=pygame.Surface((160,240),pygame.SRCALPHA);block.fill('white')
    d.add(block,(160,0),20);d.flush()
    a.update(16,False,False)
    a.render_fog(screen,source,(0,0),(140,170,190),1)
    first=pygame.image.tobytes(screen,'RGBA')
    assert screen.get_at((250,120)).a<8
    for _ in range(600):a.update(1000/60,False,False)
    screen.fill((0,0,0,0));a.render_fog(screen,source,(0,0),(140,170,190),1)
    assert pygame.image.tobytes(screen,'RGBA')!=first
    assert a.depth_for(source) is d
    a.release()
    assert a.metrics()['surface_bytes']==0


def test_material_responses_use_visible_material_names():
    assert rain_material('OAK_PLANKS')=='wood'
    assert rain_material('OAK_LEAVES')=='foliage'
    assert rain_material('STONE_BRICKS')=='masonry'
    assert rain_material('STONE')=='stone'
    assert rain_material('GLASS')=='glass_metal'
    assert rain_material('WATER')=='water'


def test_elevated_contacts_follow_real_top_faces_at_every_rotation_and_zoom():
    r=IsometricRenderer(400,300)
    a=Atmosphere()
    a.add_contact((3,4,8),'stone',(.5,.5))
    contact=a.contacts[0]
    for rotation in range(4):
        r.setViewRotation(rotation)
        for zoom in (.25,1.,2.):
            r.setZoom(zoom)
            polygon=r.getBlockFacePolygons(3,4,8)['top']
            px,py=a.project_contact(contact,r)
            assert r._pointInConvexPolygon((px,py),polygon)
            floor_y=a.project_contact(dict(contact,position=(3,4,0)),r)[1]
            assert floor_y-py==pytest.approx(8*r._blockH,abs=1)
    for _ in range(120):a.update(16,True)
    assert contact['age']>=0


def test_occluded_roof_contact_does_not_draw_through_front_tower():
    pygame.init();r=IsometricRenderer(0,0);a=Atmosphere()
    source=pygame.Surface((64,64),pygame.SRCALPHA)
    d=a.begin_depth(source,r,(0,20))
    near=pygame.Surface((64,64),pygame.SRCALPHA);near.fill('white')
    d.add(near,(0,0),20);d.flush();a.visibility_depth=d
    contact=dict(position=(0,0,0),uv=(.5,.5))
    assert not a.contact_visible(contact,r,16,16)


def test_incoming_streak_head_stops_at_elevated_surface():
    pygame.init();r=IsometricRenderer(200,300);a=Atmosphere()
    a.size=(500,500);a.rain_level=1
    a.drops=[dict(x=-100,y=-100,depth=0,angle=.1,length=9)]
    a.add_contact((0,0,4),'stone')
    contact=a.contacts[0];contact['age']=-.001
    screen=pygame.Surface((500,500),pygame.SRCALPHA)
    a.render_rain(screen,r)
    _,top=a.project_contact(contact,r)
    bounds=screen.get_bounding_rect()
    assert bounds.height>5
    assert bounds.bottom<=round(top)+1


def test_recorded_rain_assets_have_headroom_and_verified_hashes():
    import hashlib,json
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    manifest=root/'Assets/Sound Hub/ambient/weather/atmosphere/manifest.json'
    if not manifest.exists():pytest.skip('Private prepared rain assets absent')
    data=json.loads(manifest.read_text())
    assert len(data['outputs'])==19
    assert sum(row['decoded_bytes'] for row in data['outputs'].values())<24*1024**2
    for path,row in data['outputs'].items():
        assert hashlib.sha256((root/path).read_bytes()).hexdigest()==row['sha256']
        assert row['peak']<.92 and row['clipped_samples']==0
    assert data['outputs']['Assets/Sound Hub/ambient/weather/atmosphere/rain-bed.ogg']['boundary_step']<.01


def test_bounded_original_preserves_exact_horror_rain_input():
    from pathlib import Path
    import numpy as np
    from engine.audio_decode import load_sound
    path=Path(__file__).resolve().parents[1]/'Assets/Sound Hub/ambient/weather/relaxingrain.mp3'
    if not path.exists():pytest.skip('Private original recording absent')
    pygame.mixer.init(44100,-16,2)
    original=load_sound(path)
    bounded=load_sound(path,max_seconds=30.25)
    frames=30*pygame.mixer.get_init()[0]
    assert np.array_equal(pygame.sndarray.samples(original)[:frames],pygame.sndarray.samples(bounded)[:frames])
    assert bounded.get_length()<31
