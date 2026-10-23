"""Opt-in native finishing evidence with isolated preferences and save paths."""
from contextlib import ExitStack
from concurrent.futures import ThreadPoolExecutor
import ctypes
import json
import os
from pathlib import Path
from time import perf_counter
import pygame
from tools.verify_review_audio import temporary_attribute


def run(output,module):
    import runtime_paths
    from ui import opening_scene,feedback
    from ui.fonts import set_text_scale
    from ui.workshop_actions import WORLD
    out=Path(output).resolve();out.mkdir(parents=True,exist_ok=True)
    records=[];frames=[];cues=[];modes=[];phase='startup';start=perf_counter();last=-1
    writer=ThreadPoolExecutor(max_workers=1,thread_name_prefix='evidence')
    pending=[]
    for name in ('startup','world','goodbye'):(out/name).mkdir(exist_ok=True)
    original_flip=pygame.display.flip;original_mode=pygame.display.set_mode;original_play=feedback.play
    original_sound=pygame.mixer.Sound;sound_loads=[]
    def sound(*a,**k):
        t=perf_counter()-start
        result=original_sound(*a,**k)
        sound_loads.append({'t':t,'duration':perf_counter()-start-t,'path':str(a[0]) if a else 'buffer'})
        return result
    def flip():
        nonlocal last
        original_flip();now=perf_counter()-start
        records.append({'t':now,'phase':phase})
        if phase in ('startup','world','goodbye') and now-last>=1/20 and os.environ.get('BLOC_QA_NO_FRAMES')!='1':
            if len(pending)>=4:pending.pop(0).result()
            filename=f'{len(frames):04}.jpg'
            pending.append(writer.submit(pygame.image.save,pygame.display.get_surface().copy(),str(out/phase/filename)))
            frames.append((now,phase,filename));last=now
    def mode(size,*a,**k):
        modes.append({'t':perf_counter()-start,'size':size,'args':a});return original_mode(size,*a,**k)
    def play(assets,name):
        result=original_play(assets,name)
        if result is not None:cues.append({'t':perf_counter()-start,'name':name,'busy':result.get_busy()})
        return result
    with ExitStack() as stack:
        for owner,key,value in ((pygame.display,'flip',flip),(pygame.display,'set_mode',mode),(feedback,'play',play),(pygame.mixer,'Sound',sound),
             (module,'APP_CONFIG_FILE',str(out/'preferences.json')),(module,'SAVES_DIR',str(out/'saves')),
             (runtime_paths,'SAVES_DIR',str(out/'saves')),(runtime_paths,'BASE_DIR',str(out)),
             (opening_scene,'CONFIG_PATH',str(out/'opening.json'))):
            stack.enter_context(temporary_attribute(owner,key,value))
        app=module.BlocFantome();app.autoSaveEnabled=False;app.tutorialScreen.visible=False
        app.effectsMuted=False;app.musicMuted=False;app.ambientMuted=True
        app.effectsVolume=.65;app.musicVolume=.22;app.musicController.set_volume(.22)
        original_events=app._handleEvents;ready=None;step=-1;checks={}
        interactive=__import__('os').environ.get('BLOC_QA_INTERACTIVE')=='1'
        startup_only=__import__('os').environ.get('BLOC_QA_STARTUP_ONLY')=='1'
        def tick():
            nonlocal phase,ready,step
            original_events();now=perf_counter()
            if ready is None:
                ready=now;checks['ready_seconds']=now-start
                checks['startup_modes']=list(modes)
                checks['native_title']=getattr(getattr(app,'windowChrome',None),'enabled',False)
                checks['os_dpi']=ctypes.windll.user32.GetDpiForWindow(pygame.display.get_wm_info()['window'])
                app.workshop.visibility.pinned=True
                (out/'ready.json').write_text(json.dumps(checks,indent=2))
            age=now-ready
            if interactive:
                phase='interactive'
                if age>900:app.running=False
                return
            if startup_only:
                if age>5:phase='goodbye';app.running=False
                return
            if age<.7:return
            if age<20.5:
                phase='world';app.workshop.page='world'
                if step==-1:app._applyWindowSize(1200,900)
                current=int((age-.7)/1.2)
                toggles=[r for r in WORLD if r[4]]
                if current!=step and current<len(toggles)*2:
                    action,_,_,_,field=toggles[current//2]
                    app.workshop.act(action,app);step=current
                    checks[f'{action}-{current%2}']=bool(getattr(app,field))
                return
            if age<21.5:
                if step!=100:
                    app._render();pygame.image.save(app.screen,str(out/'world.png'))
                    app.workshop.page='';phase='settings';app.settingsMenuOpen=True;step=100
                    for size in ((960,640),(1200,800),(1920,1080)):
                        for scale in (1.,1.25,1.5):
                            set_text_scale(scale);app.workshop.text_scale=scale;app._applyWindowSize(*size)
                            app._render();pygame.image.save(app.screen,str(out/f'settings-{size[0]}-{round(scale*100)}.png'))
                            box,sliders,controls=app._settingsLayout()
                            assert app.screen.get_rect().contains(box),(size,scale,box)
                            assert all(box.contains(r) for _,_,r in controls)
                    set_text_scale(1);app.workshop.text_scale=1;app._applyWindowSize(1200,800)
                    app.settingsMenuOpen=False
                    from pygame._sdl2 import Window
                    app._displayWindow=window=Window.from_display_module();position=window.position;size=app.screen.get_size()
                    app._toggleFullscreen();app._render()
                    checks['fullscreen_size']=app.screen.get_size()
                    pygame.image.save(app.screen,str(out/'fullscreen.png'))
                    app._toggleFullscreen();app._render()
                    app._displayWindow=Window.from_display_module()
                    checks['restored_geometry']=app.screen.get_size()==size and app._displayWindow.position==position
                    assert checks['restored_geometry']
                    app._openWorldMap();app._render()
                    pygame.image.save(app.screen,str(out/'map.png'))
                    assert app.worldMapView.back_rect.top>=28
                    app._exitWorldMap()
                return
            phase='goodbye';app.running=False
        app._handleEvents=tick
        try:app.run()
        finally:
            writer.shutdown(wait=True)
            for future in pending:future.result()
            for name in ('startup','world','goodbye'):
                rows=[f for f in frames if f[1]==name]
                lines=[]
                folder=out/name;folder.mkdir(exist_ok=True)
                for i,(t,_,filename) in enumerate(rows):
                    duration=rows[i+1][0]-t if i+1<len(rows) else .05
                    lines.extend((f"file '{filename}'",f'duration {duration:.6f}'))
                if rows:lines.append(f"file '{rows[-1][2]}'")
                (folder/'frames.ffconcat').write_text('\n'.join(lines),encoding='utf-8')
            checks.update(sound_loads=sound_loads,version=module.APP_VERSION,records=records,cues=cues,modes=modes,interactive_mode=interactive,
                          audio_driver=__import__('os').environ.get('SDL_AUDIODRIVER','default'),startup=getattr(app,'_startupMetrics',{}))
            (out/'probe.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
