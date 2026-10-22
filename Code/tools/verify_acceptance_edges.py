"""Native source/frozen fast-skip, preference and SDL-worker teardown evidence."""
import json
from pathlib import Path
from time import perf_counter, sleep
import pygame
from tools.verify_review_audio import temporary_attribute


def run(output,module):
    import runtime_paths
    out=Path(output).resolve();out.parent.mkdir(parents=True,exist_ok=True)
    root=out.parent
    config=root/'saved-off.json'
    config.write_text(json.dumps({'skyboxesEnabled':False}),encoding='utf-8')
    old=root/'.tutorial_config.json'
    old.write_text(json.dumps({'showOnStartup':True,'guidedVersion':2}),encoding='utf-8')
    original_mode=pygame.display.set_mode
    rows=[]
    with temporary_attribute(pygame.display,'set_mode',lambda size,flags=0,*a,**kw:original_mode(size,flags|pygame.HIDDEN,*a,**kw)), \
         temporary_attribute(module,'APP_CONFIG_FILE',str(config)), \
         temporary_attribute(runtime_paths,'BASE_DIR',str(root)), \
         temporary_attribute(module.BlocFantome,'_saveAppConfig',lambda self:None):
        for name,event in (
            ('escape',pygame.event.Event(pygame.KEYDOWN,key=pygame.K_ESCAPE)),
            ('letter',pygame.event.Event(pygame.KEYDOWN,key=pygame.K_a)),
            ('mouse',pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=(5,5))),
            ('window-close',pygame.event.Event(pygame.QUIT)),
            ('worker-skip',pygame.event.Event(pygame.KEYDOWN,key=pygame.K_ESCAPE)),
            ('reduced-motion',None)):
            from ui.opening_audio import MIXER_CHANNEL_COUNT, RESERVED_CHANNEL_COUNT
            pygame.init()
            pygame.mixer.set_num_channels(MIXER_CHANNEL_COUNT)
            pygame.mixer.set_reserved(RESERVED_CHANNEL_COUNT)
            app=module.BlocFantome();app.effectsMuted=True;app.musicMuted=True;app.autoSaveEnabled=False
            assert not app.skyboxesEnabled
            assert not app.tutorialScreen.shouldShowOnStartup()
            driver=pygame.display.get_driver()
            worker_observations=[]
            if name=='worker-skip':
                def worker():
                    sleep(.3)
                    assert pygame.display.get_init()
                    surface=pygame.Surface((8,8));surface.fill((1,2,3))
                    worker_observations.append('SDL alive until worker finished')
                app.worldLoadExecutor.submit(worker)
            app.workshop.visibility.reduced_motion=name=='reduced-motion'
            pygame.event.clear()
            if event is not None:pygame.event.post(event)
            times=[];first=[None];first_surface=[None]
            original_flip=pygame.display.flip
            def flip():
                original_flip();times.append(perf_counter())
                if name=='reduced-motion':
                    data=pygame.image.tobytes(app.screen,'RGB')
                    if first[0] is None:first[0]=data
                    assert data==first[0]
                if len(times)==1:
                    first_surface[0]=app.screen.copy()
            start=perf_counter()
            with temporary_attribute(pygame.display,'flip',flip):app._shutdown()
            elapsed=(perf_counter()-start)*1000
            assert pygame.mixer.get_init() is None and not pygame.display.get_init()
            if event is not None:assert elapsed<650,(name,elapsed)
            else:assert 2700<elapsed<3400,(name,elapsed,(times[-1]-times[0])*1000)
            if first_surface[0] is not None:
                pygame.image.save(first_surface[0],str(root/(name+'.png')))
            if name=='worker-skip':assert worker_observations
            rows.append(dict(case=name,driver=driver,elapsed_ms=elapsed,frames=len(times),
                saved_skybox_off_preserved=True,old_tutorial_auto_launch_ignored=True,
                sdl_closed=True,worker=worker_observations))
    assert json.loads(old.read_text())['showOnStartup'] is True
    out.write_text(json.dumps({'physical_input':False,'audio_muted':True,'cases':rows},indent=2),encoding='utf-8')
