"""The opening cannot edit the builder; motion and picking share one projection."""
import os
import sys
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Code'))

import pygame
import pytest
from blocFantome import BlocFantome, BlockType
from ui.opening_scene import OpeningScene, skip_on_launch


@pytest.fixture(scope='module')
def app():
    app=BlocFantome()
    assert app.assetManager.loadAllAssets()
    yield app
    if app.openingScene:app._closeOpeningScene()
    app.worldLoadExecutor.shutdown(wait=True)
    pygame.display.quit()


def test_opening_isolated_from_world_undo_and_editor_input(app):
    app.world.setBlock(2,3,1,BlockType.DIAMOND_BLOCK)
    app._placeBlockWithUndo(3,3,1,BlockType.QUARTZ_BLOCK)
    original=dict(app.world.blocks)
    revision=app.world.revision
    camera=(app.zoomLevel,app.renderer.offsetX,app.renderer.offsetY,app.renderer.viewRotation)
    path=app.currentBuildPath
    app._openOpeningScene()
    try:
        scene=app.openingScene
        pygame.event.clear()
        for key in (pygame.K_c,pygame.K_q,pygame.K_e,pygame.K_s):
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=key,mod=0))
        app._handleEvents();app._update()
        assert scene.target_angle==135
        scene.elapsed=scene.READY_AT
        assert scene.place()
        scene.update(scene.REVEAL_DURATION)
        app._render()
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_e,mod=0))
        app._handleEvents()
        scene.update(.5)
        assert scene.target_angle==pytest.approx(154)
        scene.handle_event(pygame.event.Event(pygame.KEYUP,key=pygame.K_e))
        assert app.world.revision==revision
        assert app.world.blocks==original
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_ESCAPE,mod=0))
        app._handleEvents()
        assert app.openingScene is None
        assert (app.zoomLevel,app.renderer.offsetX,app.renderer.offsetY,app.renderer.viewRotation)==camera
        assert app.currentBuildPath==path
        assert app.undoManager.undo() is not None
        assert app.world.getBlock(3,3,1)==BlockType.AIR
        assert app.world.getBlock(2,3,1)==BlockType.DIAMOND_BLOCK
    finally:
        if app.openingScene:app._closeOpeningScene()


def test_native_close_remains_available_during_encounter(app):
    running=app.running
    app._openOpeningScene()
    try:
        scene=app.openingScene
        scene.update(5);scene.place();scene.update(5)
        scene.activate('door');scene.update(scene.RISE_DURATION);scene.activate('heart')
        assert scene.phase=='encounter'
        pygame.event.clear();pygame.event.post(pygame.event.Event(pygame.QUIT))
        app._handleEvents()
        assert app.openingScene is None and app.running
        assert app._exitDialog is not None
        app._exitAction('stay')
        from ui.opening_audio import OPENING_CHANNELS
        assert not any(pygame.mixer.Channel(i).get_busy() for i in (*OPENING_CHANNELS.values(),30))
    finally:
        if app.openingScene:app._closeOpeningScene()
        app.running=running
        app._exitDialog=None


def test_rigid_sections_frame_rate_independent_and_exact_final_pose(app):
    first=OpeningScene((1200,800),app.assetManager)
    second=OpeningScene((1200,800),app.assetManager)
    for scene in (first,second):
        scene.update(scene.READY_AT)
        assert scene.place()
        assert not scene.place()
    for _ in range(120):first.update(1/60)
    for _ in range(60):second.update(1/30)
    for a,b in zip(first.section_offsets(),second.section_offsets()):
        assert a==pytest.approx(b)
    for frame in range(60):
        first.update(.1)
        cells=first.cells()
        for section,offset in zip(first.sections,first.section_offsets()):
            transformed={(x+offset[0],y+offset[1],z+offset[2]) for x,y,z,_,_ in section}
            assert transformed.issubset({c[:3] for c in cells})
    assert first.section_offsets()==((1,0,1),(-1,0,1))
    assert first.complete
    cells=first.cells()
    assert len(cells)==len({c[:3] for c in cells})
    assert all(float(v).is_integer() for c in cells for v in c[:3])


@pytest.mark.parametrize('size',[(960,640),(1200,800),(1920,1080)])
def test_visible_ghost_is_clickable_at_every_supported_size(app,size):
    scene=OpeningScene(size,app.assetManager)
    scene.update(scene.READY_AT)
    scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=(10,100)))
    assert scene.placed_at is None
    x,y=scene.renderer.worldToScreen(*scene.TARGET)
    scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,
        pos=(x,y)))
    assert scene.placed_at is not None
    assert all(pygame.Rect((0,0),size).contains(rect) for rect in scene.turn_rects)
    assert pygame.Rect((0,0),size).contains(scene.close_rect)


def test_skip_preference_persists_and_corrupt_config_is_safe(app,tmp_path):
    target=tmp_path/'opening.json'
    with patch('ui.opening_scene.CONFIG_PATH',str(target)):
        assert skip_on_launch()
        app.settingsMenuOpen=True
        app._renderSettingsMenu()
        control=next(rect for _,action,rect in app._settingsLayout()[2] if action=='skip')
        app._handleSettingsClick(*control.center)
        app.settingsMenuOpen=False
        assert not skip_on_launch()
        target.write_text('[]')
        assert skip_on_launch()


def test_settings_opening_button_matches_rendered_row(app):
    app.settingsMenuOpen=True
    app._renderSettingsMenu()
    panel=app._settingsMenuRect()
    button=next(rect for _,action,rect in app._settingsLayout()[2] if action=='opening')
    assert panel.contains(button)
    app._handleSettingsClick(*button.center)
    try:
        assert app.openingScene is not None
        assert not app.settingsMenuOpen
    finally:app._closeOpeningScene()


def test_idle_hint_does_not_move_camera_and_held_keys_orbit_continuously(app):
    scene=OpeningScene((1200,800),app.assetManager)
    scene.update(scene.READY_AT);scene.place();scene.update(10)
    assert scene.renderer.angle==135
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_e))
    scene.update(.5)
    assert scene.target_angle==pytest.approx(154)
    scene.handle_event(pygame.event.Event(pygame.KEYUP,key=pygame.K_e))
    scene.update(.5)
    assert scene.target_angle==pytest.approx(154)
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_q))
    scene.handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST))
    scene.update(.5)
    assert scene.target_angle==pytest.approx(154)
    scene.close()


@pytest.mark.parametrize('size',[(960,640),(1200,800),(1920,1080)])
def test_two_scene_visible_click_path_and_return(app,size):
    scene=OpeningScene(size,app.assetManager)
    def click(point):
        scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=point))
    scene.update(4.5);click(scene.renderer.worldToScreen(*scene.TARGET))
    scene.update(4.8)
    door=scene.renderer.project((.5,-1,4.7))[:2]
    assert scene.target_at(door)=='door'
    click(door);assert scene.phase=='approach'
    scene.update(2.7)
    assert not scene.targets() and not scene.orbit_enabled
    assert 12.4<scene.renderer.half<35.5
    scene.update(scene.RISE_DURATION-2.7)
    assert scene.phase=='sanctuary'
    assert scene.renderer.half==pytest.approx(41)
    heart=scene.project_sanctuary((1,-25,35))[:2]
    assert scene.target_at(heart)=='heart'
    click(heart);assert scene.awakened_at is not None
    assert scene.phase=='encounter'
    locked=(scene.renderer.angle,scene.target_zoom)
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_q))
    scene.handle_event(pygame.event.Event(pygame.MOUSEWHEEL,y=2))
    scene.update(1.3);click(scene.return_rect.center)
    assert not scene.closed and not scene.targets() and not scene.orbit_enabled
    scene.handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST))
    scene.update(43)
    assert scene.closed
    scene.close()


@pytest.mark.parametrize('phase', ['shrine','approach','sanctuary','encounter'])
@pytest.mark.parametrize('method', ['mouse','escape'])
def test_skip_entire_intro_in_every_phase_preserves_editor(app, phase, method):
    original=dict(app.world.blocks)
    camera=(app.zoomLevel,app.renderer.offsetX,app.renderer.offsetY,app.renderer.viewRotation)
    history=list(app.undoManager.undo_stack);path=app.currentBuildPath
    app._openOpeningScene()
    scene=app.openingScene;scene.phase=phase
    if phase=='encounter':scene.awakened_at=scene.elapsed;scene.audio.start_encounter()
    pygame.event.clear()
    event=(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_ESCAPE,mod=0) if method=='escape'
           else pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=scene.close_rect.center))
    pygame.event.post(event);app._handleEvents()
    try:
        assert app.openingScene is None
        assert app.world.blocks==original and app.undoManager.undo_stack==history
        assert camera==(app.zoomLevel,app.renderer.offsetX,app.renderer.offsetY,app.renderer.viewRotation)
        assert app.currentBuildPath==path and app.running
        from ui.opening_audio import OPENING_CHANNELS
        assert not any(pygame.mixer.Channel(i).get_busy() for i in (*OPENING_CHANNELS.values(),30))
    finally:
        if app.openingScene:app._closeOpeningScene()


def test_camera_projection_ray_round_trip_and_opaque_occlusion(app):
    from ui.presentation_renderer import Camera
    for angle in (0,31,90,135,225,359):
        camera=Camera((1920,1080));camera.angle=angle
        point=(2.5,3.5,4.5)
        assert camera.hit(camera.project(point)[:2],(2,3,4),(3,4,5)) is not None
        assert camera.hit((-1000,-1000),(2,3,4),(3,4,5)) is None
    scene=OpeningScene((1200,800),app.assetManager)
    scene.update(4.5);scene.place();scene.update(4.8);scene.activate('door');scene.update(scene.RISE_DURATION)
    # The altar is genuinely hidden by an opaque foreground pier from this angle.
    scene.renderer.angle=90
    pos=scene.project_sanctuary((1,-20,12))[:2]
    assert scene.target_at(pos) is None


def test_orbit_frame_rate_independent_and_hover_sound_sparse(app):
    scenes=[OpeningScene((1200,800),app.assetManager) for _ in range(2)]
    for scene in scenes:
        scene.update(4.5);scene.place();scene.update(4.8);scene.turn(1)
    for _ in range(60):scenes[0].update(1/60)
    for _ in range(30):scenes[1].update(1/30)
    assert scenes[0].renderer.angle==pytest.approx(scenes[1].renderer.angle)
    scene=scenes[0]
    scene.pointer=scene.renderer.project((.5,-1,4.7))[:2]
    with patch.object(scene.audio,'play') as play:
        scene.renderer.angle=scene.target_angle=135
        scene.pointer=scene.renderer.project((.5,-1,4.7))[:2]
        scene.update(0)
        for _ in range(20):scene.update(0)
        assert sum(c.args[0]=='hover' for c in play.call_args_list)==1


def test_precise_wheel_zoom_is_smooth_bounded_and_pickable(app):
    scene=OpeningScene((1200,800),app.assetManager)
    scene.update(4.5)
    before=scene.renderer.half
    scene.handle_event(pygame.event.Event(pygame.MOUSEWHEEL,y=1,precise_y=.5))
    assert scene.renderer.half==before
    scene.update(.02)
    assert before*scene.target_zoom<scene.renderer.half<before
    for delta,bound in ((100,.55),(-100,1.5)):
        scene.handle_event(pygame.event.Event(pygame.MOUSEWHEEL,y=delta))
        scene.update(2)
        assert scene.target_zoom==bound
        assert scene.ghost_hit(scene.renderer.worldToScreen(*scene.TARGET))
    scene.place();scene.update(5);scene.activate('door')
    scene.handle_event(pygame.event.Event(pygame.MOUSEWHEEL,y=10))
    assert scene.target_zoom==1
    scene.close()


def test_controls_fade_and_return_on_bottom_hover_and_completion(app):
    scene=OpeningScene((1200,800),app.assetManager)
    scene.update(4.5);assert scene.controls_alpha==255
    scene.update(3.5);assert scene.controls_alpha==0
    scene.handle_event(pygame.event.Event(pygame.MOUSEMOTION,pos=scene.slider_rect.center))
    assert scene.controls_alpha==255
    scene.pointer=(-1,-1)
    scene.place();scene.update(4.8)
    assert scene.controls_alpha==255
    scene.activate('door');scene.update(scene.RISE_DURATION)
    scene.update(3.5);assert scene.controls_alpha==0
    scene.activate('heart');scene.update(1.3)
    assert scene.controls_alpha==255
    scene.update(3.5);assert scene.controls_alpha==0
    scene.close()


def test_orbit_audio_uses_one_loop_until_motion_stops():
    from unittest.mock import Mock
    from ui.opening_audio import OpeningAudio
    audio=OpeningAudio();audio.sounds={'orbit':object()}
    channel=Mock();channel.get_busy.return_value=False
    with patch('ui.opening_audio.pygame.mixer.Channel',return_value=channel):
        audio.update_orbit(90,1/60)
        channel.get_busy.return_value=True
        for _ in range(120):audio.update_orbit(90,1/60)
        assert channel.play.call_count==1
        assert channel.play.call_args.kwargs['loops']==-1
        for _ in range(120):audio.update_orbit(0,1/60)
        assert channel.stop.called
        audio.close()


def test_camera_handoffs_preserve_orbit_zoom_and_ease_without_a_cut(app):
    import numpy as np
    scene=OpeningScene((1200,800),app.assetManager,effects_volume=0)
    try:
        scene.update(5);scene.place();scene.update(5)
        scene.renderer.angle=scene.target_angle=215
        scene.zoom=scene.target_zoom=.72;scene.update(0)
        before=(scene.renderer.center.copy(),scene.renderer.half,scene.renderer.angle)
        scene.activate('door');scene.update(0)
        assert np.allclose(scene.renderer.center,before[0])
        assert scene.renderer.half==pytest.approx(before[1])
        assert scene.renderer.angle==pytest.approx(before[2])
        scene.update(scene.RISE_DURATION)
        scene.renderer.angle=scene.target_angle=310
        scene.zoom=scene.target_zoom=.8;scene.update(0)
        before=(scene.renderer.center.copy(),scene.renderer.half,scene.renderer.angle)
        scene.activate('heart');scene.update(0)
        assert np.allclose(scene.renderer.center,before[0])
        assert scene.renderer.half==pytest.approx(before[1])
        assert scene.renderer.angle==pytest.approx(before[2])
        scene.update(.01)
        assert np.linalg.norm(scene.renderer.center-before[0])<.01
        assert abs(scene.renderer.angle-before[2])<.01
        scene.update(2.79)
        assert scene.renderer.half==pytest.approx(55)
        assert scene.renderer.angle%360==pytest.approx(scene.ARRIVAL_ANGLE)
    finally:scene.close()


def test_vault_ribs_connect_bay_corners_and_keep_terminal_cross():
    from ui.opening_geometry import sanctuary
    cells=sanctuary()
    for cy in (-8,8):
        assert cells[0,cy,50][0]==BlockType.CHISELED_QUARTZ
        for sx in (-1,1):
            for sy in (-1,1):
                assert (round(.5+sx*10),round(cy+.5+sy*8),38) in cells
    for x,z in ((0,18),(-1,17),(0,17),(1,17),(0,16)):
        assert cells[2*x,-26,2*z][0]==BlockType.YELLOW_STAINED_GLASS
