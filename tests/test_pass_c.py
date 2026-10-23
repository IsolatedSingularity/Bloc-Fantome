"""Pass C persistence, reciprocal transitions and exact raster contracts."""
import json
from pathlib import Path
from unittest.mock import patch
import pygame
import pytest
from test_workshop_production import app, reset
from ui.map_transition import MapTransition
from ui.fonts import load_ui_font, font_source
from engine.raster import model_face


def test_repaint_batch_preserves_alpha_painter_order_clip_and_releases_surfaces():
    from engine.repaint_batch import RepaintBatch
    expected=pygame.Surface((40,30),pygame.SRCALPHA)
    actual=expected.copy()
    expected.set_clip((3,2,30,24));actual.set_clip(expected.get_clip())
    commands=[]
    for i in range(13):
        sprite=pygame.Surface((14,12),pygame.SRCALPHA)
        sprite.fill((i*19,255-i*17,i*7,90+i*8))
        commands.append((sprite,(i*2-4,i-2)))
    expected.blits(commands,doreturn=False)
    pool=RepaintBatch(capacity=4).begin(actual)
    for command in commands:pool.append(command)
    pool.finish()
    assert pygame.image.tobytes(actual,'RGBA')==pygame.image.tobytes(expected,'RGBA')
    assert pool.target is None and pool.count==0
    assert all(command[0] is None for command in pool.commands)


def test_tutorial_unread_survives_restart_and_preserves_preferences(app,tmp_path):
    import runtime_paths
    path=tmp_path/'.tutorial_config.json'
    path.write_text(json.dumps({'showOnStartup':True,'other':'keep'}))
    tutorial=app.tutorialScreen
    with patch.object(runtime_paths,'BASE_DIR',str(tmp_path)):
        tutorial._loadConfig()
        assert not tutorial.openedOnce and not tutorial.shouldShowOnStartup()
        # Fixture suppresses writes; exercise the real persistence method here.
        from ui.tutorial import GuidedTutorialMixin
        with patch.object(tutorial,'_saveConfig',lambda:GuidedTutorialMixin._saveConfig(tutorial)),patch.object(tutorial,'onStepChange',None):
            tutorial.show()
        tutorial._loadConfig()
    assert tutorial.openedOnce and json.loads(path.read_text())['other']=='keep'
    tutorial.visible=False


def test_map_close_back_and_escape_restore_world(app):
    app.world.setBlock(3,4,2,__import__('blocFantome').BlockType.STONE)
    before=dict(app.world.blocks);app._openWorldMap()
    app._handleWorldMapAction('exit')
    assert app.worldMapActive and app._mapTransition.closing
    app._mapTransition.started-=321;app._update()
    assert not app.worldMapActive and app._mapTransition.ready
    assert dict(app.world.blocks)==before
    app._mapTransition.started-=221;app._render()
    assert app._mapTransition is None
    app._openWorldMap();app._requestExitWorldMap()
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_ESCAPE))
    app._handleEvents()
    assert not app.worldMapActive and app._mapTransition is None
    assert dict(app.world.blocks)==before


@pytest.mark.parametrize('closing',[False,True])
def test_map_transition_resize_and_reduced_motion(closing):
    screen=pygame.Surface((960,640))
    transition=MapTransition(screen,True,closing=closing)
    assert transition.covered
    transition.render(pygame.Surface((1200,800)))
    assert transition.paper.get_size()==(1200,800)
    transition.reveal();assert transition.finished


def test_typography_production_default_and_branding_exception(monkeypatch):
    monkeypatch.delenv('BLOC_FONT_EXPERIMENT',raising=False)
    baseline=font_source()
    assert baseline.endswith('IBMPlexSans-Regular.ttf')
    monkeypatch.setenv('BLOC_FONT_EXPERIMENT','plex-light')
    assert load_ui_font(14).path.endswith('IBMPlexSans-Regular.ttf')
    assert load_ui_font(25,bold=True).path.endswith('IBMPlexSans-Light.ttf')
    assert load_ui_font(25,experiment=False).path!=baseline


def test_full_startup_sprite_pixels_match_accepted(app):
    import hashlib
    expected=json.loads((Path(__file__).parents[1]/'docs/reviews/pass-c/raster-equivalence.json').read_text())['baseline']
    actual={str(k):hashlib.sha256(pygame.image.tobytes(v,'RGBA')).hexdigest() for k,v in app.assetManager.blockSprites.items()}
    assert actual==expected


@pytest.mark.parametrize('clip',[None,(7,9,13,11),(0,0,0,0)])
def test_model_sampling_matches_scalar_with_alpha_clipping_and_wrapped_uv(clip):
    import random
    rng=random.Random(28)
    texture=pygame.Surface((16,16),pygame.SRCALPHA)
    for x in range(16):
        for y in range(16):texture.set_at((x,y),tuple(rng.randrange(256) for _ in range(4)))
    for origin in ((0,0),(-.7,.4),(1.2,-1.4)):
        points=((-3.5,4.25),(22.3,9.5),(31.8,35.5),(6,30.25))
        a=pygame.Surface((32,32),pygame.SRCALPHA);a.fill((11,22,33,44));b=a.copy()
        a.set_clip(clip);b.set_clip(clip)
        model_face(a,points,texture,.7,origin,(.8,.1),(-.2,1.3))
        p0,p1,_,p3=points;ux,uy=p1[0]-p0[0],p1[1]-p0[1];vx,vy=p3[0]-p0[0],p3[1]-p0[1]
        determinant=ux*vy-uy*vx
        for y in range(4,32):
            for x in range(32):
                dx,dy=x+.5-p0[0],y+.5-p0[1]
                u=(dx*vy-dy*vx)/determinant;v=(ux*dy-uy*dx)/determinant
                if -.001<=u<=1.001 and -.001<=v<=1.001:
                    color=texture.get_at((int((origin[0]+u*.8-v*.2)*16)%16,int((origin[1]+u*.1+v*1.3)*16)%16))
                    if color.a:b.set_at((x,y),(int(color.r*.7),int(color.g*.7),int(color.b*.7),color.a))
        assert pygame.image.tobytes(a,'RGBA')==pygame.image.tobytes(b,'RGBA')
