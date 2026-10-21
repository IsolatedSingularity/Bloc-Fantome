"""Owner Pass A: exact edit ordering, input ownership, weather and pixels."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import random
from unittest.mock import patch
import pygame
import pytest
from engine.draw_order import DrawOrder, painter_key
from engine.world_snapshot import WorldSnapshot, prepare_snapshot
from test_workshop_production import app, reset
import blocFantome as b
from ui.scroll import SmoothScroll


def test_paged_order_random_edits_preserve_snapshot_and_exact_sort():
    rng=random.Random(23)
    original=tuple(sorted(((x%73,x,2,3,'stone') for x in range(5000)),key=painter_key))
    order=DrawOrder(original);reference={painter_key(v):v for v in original}
    for _ in range(100):
        value=(rng.randrange(100),rng.randrange(6000),2,3,'glass')
        remove=rng.choice(original)
        order=order.patched((painter_key(remove),),(value,))
        reference.pop(painter_key(remove),None);reference[painter_key(value)]=value
    assert tuple(order)==tuple(sorted(reference.values(),key=painter_key))
    assert tuple(DrawOrder(original))==original
    assert order[255:800]==tuple(order)[255:800]
    assert order[-1]==tuple(order)[-1]


def test_prepared_edit_matches_fresh_all_modes_and_views(app):
    from engine.build_io import _draw_orders
    rng=random.Random(123)
    blocks={(x,y,z):b.BlockType.STONE for x in range(9) for y in range(9) for z in range(3)}
    structures=frozenset(p for p in blocks if p[0]<4)
    app.world.replace(prepare_snapshot(WorldSnapshot(32,32,32,blocks=blocks,structure_positions=structures),app.world.catalog))
    old=app.world.drawOrdersByMode['all'][0];saved=tuple(old)
    for _ in range(25):
        pos=(rng.randrange(9),rng.randrange(9),rng.randrange(5))
        app.world.setBlock(*pos,rng.choice((b.BlockType.AIR,b.BlockType.STONE,b.BlockType.GLASS)))
        expected=_draw_orders(app.world.blocks,app.world.sceneStructurePositions,
                              app.world.sceneStructureSurfacesByView,app.world.viewSurfacePositionsByView)
        for mode,views in expected.items():
            for rotation,rows in views.items():assert tuple(app.world.drawOrdersByMode[mode][rotation])==rows
    assert tuple(old)==saved


def test_precise_scroll_decelerates_without_overshoot():
    scroll=SmoothScroll()
    scroll.wheel(pygame.event.Event(pygame.MOUSEWHEEL,y=-1,precise_y=-.25),500)
    assert scroll.target==15
    positions=[scroll.advance(500,1/60) for _ in range(90)]
    assert positions==sorted(positions) and positions[-1]==15
    scroll.wheel(pygame.event.Event(pygame.MOUSEWHEEL,y=20),500)
    assert scroll.advance(500,1/60,True)==0


def test_navigation_fades_and_motion_reveals_without_hidden_hits(app):
    shell=app.workshop;shell.visibility.last_activity=-100;shell.last_time=-100
    with patch('pygame.mouse.get_pos',return_value=(500,400)),patch('pygame.mouse.get_pressed',return_value=(False,False,False)):
        shell.render(app)
        assert not any(a.startswith('nav:') or a=='save' for _,a,_ in shell.hits)
        shell.handle_event(pygame.event.Event(pygame.MOUSEMOTION,pos=(501,400),rel=(1,0),buttons=(0,0,0)),app)
        shell.render(app)
    actions={a for _,a,_ in shell.hits}
    assert {'nav:build','nav:library','nav:world','nav:map','nav:tools','nav:menu','save'}<=actions
    assert not {'reveal','undo','left','fit','right'}&actions


def test_tools_regions_scroll_independently(app):
    shell=app.workshop;shell.page='tools';shell.render(app)
    event=pygame.event.Event(pygame.MOUSEWHEEL,y=-1,precise_y=-.5)
    with patch('pygame.mouse.get_pos',return_value=shell.shortcuts_rect.center):
        assert shell.handle_event(event,app)
    assert shell.shortcut_scroller.target==30 and shell.scroller.target==0
    with patch('pygame.mouse.get_pos',return_value=shell.list_rect.center):shell.handle_event(event,app)
    assert shell.scroller.target==30 and shell.shortcut_scroller.target==30


def test_library_tile_selection_never_activates(app):
    app._generateStructurePreviews();app.library.open(app,'Structures');app.library.render(app)
    rect,entry=app.library.rows[0]
    before=dict(app.world.blocks)
    app.library.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=rect.center),app)
    assert app.library.pending==entry and app.library.visible
    assert app.world.blocks==before and not app.structurePlacementMode


def test_snow_lands_on_current_roof_without_accumulation(app):
    app.world.setBlock(4,5,9,b.BlockType.STONE)
    app.snowEnabled=True;app._startSnow()
    app.snowFlakes=[dict(surface=(4,5,9),altitude=20,speed=2,driftSpeed=.02,driftPhase=0,rotation=0)]
    app._updateSnow(16)
    flake=app.snowFlakes[0];sx,sy=app.renderer.worldToScreen(4,5,9)
    assert flake['y']==pytest.approx(sy+b.TILE_HEIGHT*app.zoomLevel/2-flake['altitude'])
    for _ in range(110):app._updateSnow(16)
    assert not app.snowLayers and len(app.world.blocks)==1
    app._stopSnow();app.snowEnabled=False


@pytest.mark.parametrize('rotation',range(4))
def test_local_patch_pixels_match_full_repaint_with_transparency(app,rotation):
    app.world.resize(64,64,48,preserve=False)
    blocks={(x,y,0):b.BlockType.STONE for x in range(40) for y in range(40)}
    blocks.update({(x,18,z):b.BlockType.GLASS for x in range(16,22) for z in range(1,5)})
    app.world.replace(prepare_snapshot(WorldSnapshot(64,64,48,blocks=blocks),app.world.catalog))
    app.renderer.viewRotation=rotation;app.lightingEnabled=False;app.sceneTerrainMode='all'
    app._fitWorldToViewport(notify=False);app._renderWorld()
    for material in (b.BlockType.STONE,b.BlockType.AIR,b.BlockType.GLASS):
        app._placeBlockWithUndo(18,18,3,material);app._afterWorldEdit(((18,18,3),))
        assert app._localWorldPatch is not None
        app._renderWorld();partial=pygame.image.tostring(app._worldSurfaceCache,'RGBA')
        app._biomeViewSurfaces.clear();app._invalidateViewCaches();app._renderWorld()
        assert pygame.image.tostring(app._worldSurfaceCache,'RGBA')==partial
