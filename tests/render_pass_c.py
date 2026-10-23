"""Native-size font comparisons and timestamped reciprocal atlas recordings."""
import json
import os
from pathlib import Path
import sys
import time
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Code'))
os.environ['SDL_VIDEODRIVER']='windows';os.environ['SDL_AUDIODRIVER']='dummy'
import pygame
import blocFantome as b
import runtime_paths
from ui.fonts import set_text_scale
from ui.lifecycle import GoodbyeScreen


def render(output):
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    original=pygame.display.set_mode
    rows=[]
    with patch.object(pygame.display,'set_mode',lambda size,flags=0,*a,**k:original(size,flags|pygame.HIDDEN,*a,**k)),patch.object(b,'APP_CONFIG_FILE',str(out/'config.json')),patch.object(runtime_paths,'BASE_DIR',str(out)),patch.object(b.BlocFantome,'_saveAppConfig'):
        for family in ('segoe','plex','plex-light'):
            os.environ['BLOC_FONT_EXPERIMENT']=family
            app=b.BlocFantome();app.autoSaveEnabled=False;app.effectsMuted=app.musicMuted=app.ambientMuted=True
            try:
                assert app.assetManager.loadAllAssets();app._createInitialFloor()
                app.workshop.visibility.pinned=True;app.tutorialScreen.visible=False
                for size in ((960,640),(1200,800)):
                    for scale in (1,1.5):
                        set_text_scale(scale);app.workshop.text_scale=scale;app._applyWindowSize(*size)
                        app.skyboxesEnabled=False;app._fitWorldToViewport(notify=False)
                        for page in ('menu','settings','library','hud'):
                            app.workshop.page='menu' if page=='menu' else ''
                            app.settingsMenuOpen=page=='settings'
                            app.library.visible=False
                            if page=='library':app.library.open(app,'Worlds')
                            start=time.perf_counter()
                            while time.perf_counter()-start<.3:
                                app._update();app._render();pygame.event.pump();app.clock.tick(60)
                            name=f'{family}-{page}-{size[0]}-{round(scale*100)}.png'
                            pygame.image.save(app.screen,str(out/name))
                            import ctypes
                            rows.append(dict(name=name,size=size,scale=scale,driver=pygame.display.get_driver(),os_dpi=ctypes.windll.user32.GetDpiForWindow(pygame.display.get_wm_info()['window'])))
                if family=='segoe':
                    set_text_scale(1);app.workshop.text_scale=1;app._applyWindowSize(1200,800)
                    app.library.visible=False;app.settingsMenuOpen=False;app.workshop.page='';app._render()
                    frames=[];flips=[];phase='open';start=time.perf_counter();last=-1
                    original_flip=pygame.display.flip
                    def flip():
                        nonlocal last
                        original_flip();now=time.perf_counter()-start;flips.append(dict(seconds=now,phase=phase))
                        if now-last>=1/30:frames.append((now,phase,app.screen.copy()));last=now
                    def settle():
                        deadline=time.perf_counter()+20
                        while app._mapTransition is not None:
                            app._handleEvents();app._update();app._render();app.clock.tick(60)
                            if time.perf_counter()>deadline:raise TimeoutError('Map')
                    before=dict(app.world.blocks)
                    with patch.object(pygame.display,'flip',flip):
                        for visit in range(3):
                            phase=f'open-{visit}';app._requestWorldMap();settle()
                            pygame.image.save(app.screen,str(out/'map.png'))
                            phase=f'close-{visit}'
                            if visit%2:app._handleWorldMapAction('exit')
                            else:
                                pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_ESCAPE));app._handleEvents()
                            assert app._mapTransition and app._mapTransition.closing
                            settle();assert not app.worldMapActive and dict(app.world.blocks)==before
                        for _ in range(5):
                            phase='rapid-cancel';app._requestWorldMap();app._render()
                            pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_ESCAPE));app._handleEvents()
                            assert app._mapTransition is None and not app.worldMapActive
                        app.workshop.visibility.reduced_motion=True
                        phase='reduced-open';app._requestWorldMap();settle()
                        phase='reduced-close';app._requestExitWorldMap();settle()
                        assert dict(app.world.blocks)==before
                    lines=[]
                    for i,(timestamp,_,surface) in enumerate(frames):
                        name=f'atlas-{i:04}.png';pygame.image.save(surface,str(out/name))
                        duration=frames[i+1][0]-timestamp if i+1<len(frames) else 1/30
                        lines.extend([f"file '{name}'",f'duration {duration:.6f}'])
                    lines.append(f"file 'atlas-{len(frames)-1:04}.png'")
                    (out/'atlas.ffconcat').write_text('\n'.join(lines))
                    (out/'atlas-timing.json').write_text(json.dumps(dict(flips=flips,checks={'three_back_escape_cycles':True,'five_immediate_cancellations':True,'reduced_motion':True,'world_preserved':True},physical_input=False,audio_muted=True),indent=2))
                    from ui.map_transition import MapTransition
                    view=MapTransition(app.screen);pygame.image.save(view.paper,str(out/'atlas-cover.png'))
                    for size in ((960,640),(1200,800),(1920,1080)):
                        for scale in (1,1.5):
                            set_text_scale(scale);app._applyWindowSize(*size)
                            GoodbyeScreen(app.screen,phrase='The fireflies have it from here.').render(1000)
                            pygame.image.save(app.screen,str(out/f'goodbye-{size[0]}-{round(scale*100)}.png'))
            finally:
                app.worldLoadExecutor.shutdown(wait=True,cancel_futures=True)
                if hasattr(app,'_mapExecutor'):app._mapExecutor.shutdown(wait=True,cancel_futures=True)
                set_text_scale(1)
        (out/'matrix.json').write_text(json.dumps(rows,indent=2))
    pygame.quit()


if __name__=='__main__':render(ROOT/'.qa/pass-c/visual')
