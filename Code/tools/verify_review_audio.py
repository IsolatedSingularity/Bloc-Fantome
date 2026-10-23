"""Opt-in silent packaged-runtime probe; never runs during normal startup."""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from contextlib import contextmanager
import pygame
from engine.audio import AudioRouter
from runtime_paths import SOUNDS_DIR
from ui import feedback
from ui.opening_audio import OpeningAudio, MIXER_CHANNEL_COUNT, RESERVED_CHANNEL_COUNT


@contextmanager
def temporary_attribute(owner,name,value):
    """Isolate the opt-in probe without packaging the unittest framework."""
    previous=getattr(owner,name)
    setattr(owner,name,value)
    try:yield
    finally:setattr(owner,name,previous)


def run(output):
    pygame.display.set_mode((1200,800),pygame.HIDDEN)
    pygame.mixer.set_num_channels(MIXER_CHANNEL_COUNT)
    pygame.mixer.set_reserved(RESERVED_CHANNEL_COUNT)
    assets=SimpleNamespace(audioRouter=AudioRouter(pygame.mixer))
    feedback.set_volume(assets,0)
    rows=[]
    for name,(filename,*_rest) in feedback.CUES.items():
        pygame.mixer.stop()
        path=feedback.sound_path(filename)
        channel=feedback.play(assets,name)
        if channel is None or channel.get_sound() is not assets._selected_cues[name]:
            raise RuntimeError(f'Selected cue did not decode/play: {name}')
        pygame.time.wait(25)
        rows.append(dict(role=name,path=str(path.resolve()),bytes=path.stat().st_size,
            sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            decoded_seconds=assets._selected_cues[name].get_length(),playing=channel.get_busy()))
    opening=OpeningAudio(0)
    try:
        assert opening.spatial.ready
        derived={name:sound.get_length() for name,sound in opening.spatial.sounds.items()}
    finally:opening.close()
    result=dict(display_driver=pygame.display.get_driver(),mixer=pygame.mixer.get_init(),
                mixer_version=pygame.mixer.get_sdl_mixer_version(),selected=rows,derived=derived,
                silent=True,physical_input=False,human_listening=False)
    Path(output).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    pygame.quit()


def run_handoff(output, app_module):
    """Hidden native integration probe with isolated saves/settings and real calls."""
    import time
    import runtime_paths
    import engine.build_io as build_io
    from ui.opening_audio import OPENING_CHANNELS
    out=Path(output).resolve();out.parent.mkdir(parents=True,exist_ok=True)
    original_mode=pygame.display.set_mode
    def hidden(size,flags=0,*args,**kwargs):
        return original_mode(size,flags|pygame.HIDDEN,*args,**kwargs)
    with temporary_attribute(pygame.display,'set_mode',hidden), \
         temporary_attribute(app_module,'APP_CONFIG_FILE',str(out.parent/'isolated-config.json')), \
         temporary_attribute(app_module,'SAVES_DIR',str(out.parent/'saves')), \
         temporary_attribute(runtime_paths,'SAVES_DIR',str(out.parent/'saves')), \
         temporary_attribute(app_module,'DERIVED_WORLD_CACHE_DIR',str(out.parent/'cache')), \
         temporary_attribute(app_module.TutorialScreen,'_saveConfig',lambda *_:None):
        app=app_module.BlocFantome();app.autoSaveEnabled=False;app.tutorialScreen.visible=False
        app.musicMuted=True;app.effectsMuted=True;app.effectsVolume=0
        result=dict(hidden=True,physical_input=False,human_listening=False,checks=[])
        def ready():
            pygame.mixer.stop();app.assetManager._feedback_last={};feedback.set_volume(app.assetManager,0)
        def cue(name):
            assert any(pygame.mixer.Channel(i).get_sound() is app.assetManager._selected_cues[name]
                       for i in (0,1,27,28,29)),name
            result['checks'].append(name)
        try:
            assert app.assetManager.loadAllAssets()
            app._createInitialFloor();app._render()
            ready();app._playLifecycleCue('boot');cue('boot')
            ready();app._saveBuilding(filepath=str(out.parent/'saved.json.gz'))
            app._pendingSave.future.result(timeout=15);app._pollSave();cue('save')
            saved_blocks=dict(app.world.blocks)
            saved_bounds=(app.world.width,app.world.depth,app.world.height,app.world.min_y)
            app._placeBlockWithUndo(1,1,2,app_module.BlockType.STONE)
            assert app.world.blocks!=saved_blocks
            assert app._loadBuildingFromPath(str(out.parent/'saved.json.gz'),silent=True)
            assert app.world.blocks==saved_blocks
            assert (app.world.width,app.world.depth,app.world.height,app.world.min_y)==saved_bounds
            result['checks'].append('saved world reload restores exact blocks and bounds')
            ready();app.currentBuildPath=None
            with temporary_attribute(app,'_openSaveAsDialog',lambda:None):app.workshop.act('save',app)
            assert not any(pygame.mixer.Channel(i).get_busy() for i in (0,1,27,28))
            result['checks'].append('cancel silent')
            ready()
            def failed_write(*args,**kwargs):raise OSError('isolated review failure')
            with temporary_attribute(build_io,'write_build',failed_write):
                app._saveBuilding(filepath=str(out.parent/'failed.json.gz'))
                while not app._pendingSave.future.done():pygame.event.pump();pygame.time.wait(1)
                app._pollSave()
                assert app.workshop.error
            cue('error');app.workshop.error=''
            ready();app.workshop.page='build'
            pygame.event.clear();pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_ESCAPE,mod=0))
            app._handleEvents();cue('close');assert not app.workshop.page
            ready();app._requestWorldMap();cue('world_map')
            transition=app._mapTransition
            started=time.perf_counter()
            while not app.worldMapActive and time.perf_counter()-started<15:
                app._update();app._render();app.clock.tick(60)
            pygame.image.save(app.screen,out.parent/'map-cover.png')
            result['map_activation_ms']=(time.perf_counter()-started)*1000
            assert app.worldMapActive
            app._render();app._mapTransition=None;app._exitWorldMap()
            original=dict(app.world.blocks);history=list(app.undoManager.undo_stack)
            camera=(app.zoomLevel,app.renderer.offsetX,app.renderer.offsetY,app.renderer.viewRotation)
            path=app.currentBuildPath
            app._openOpeningScene();scene=app.openingScene
            scene.update(5);scene.place();scene.update(5);scene.activate('door')
            scene.update(scene.RISE_DURATION);scene.activate('heart');scene.update(12)
            # Read the rendered back buffer before swapping it. A post-flip
            # read can return a cleared buffer even though presentation worked.
            scene.render(app.screen)
            assert scene.phase=='encounter' and scene.gpu is not None
            result['opengl_renderer']=scene.gpu.gl.glGetString(0x1F01).decode()
            capture=scene.gpu.capture(scene.size)
            assert pygame.surfarray.array3d(capture).max()>0
            result['gl_error']=scene.gpu.gl.glGetError();assert result['gl_error']==0
            pygame.image.save(capture,out.parent/'encounter.png')
            pygame.display.flip()
            pygame.event.clear();pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_ESCAPE,mod=0))
            app._handleEvents()
            assert app.openingScene is None and app.world.blocks==original
            assert app.undoManager.undo_stack==history and app.currentBuildPath==path
            assert camera==(app.zoomLevel,app.renderer.offsetX,app.renderer.offsetY,app.renderer.viewRotation)
            assert not any(pygame.mixer.Channel(i).get_busy() for i in (*OPENING_CHANNELS.values(),30))
            app._render();pygame.image.save(app.screen,out.parent/'restored-editor.png')
            result['checks'].append('encounter Escape restores editor and releases WGL/audio')
            ready();app._playLifecycleCue('shutdown');cue('shutdown')
            started=time.perf_counter();app._shutdown()
            result['shutdown_ms']=(time.perf_counter()-started)*1000
            out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
        except Exception:
            import traceback
            out.with_suffix('.error.txt').write_text(traceback.format_exc(),encoding='utf-8')
            raise SystemExit(1)
        finally:
            if app.openingScene is not None:app._closeOpeningScene()
            app.worldLoadExecutor.shutdown(wait=True,cancel_futures=True)
            pygame.quit()
