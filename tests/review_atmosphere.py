"""Isolated actual editor frames and end-to-end weather timing, not artistic acceptance."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import random
import subprocess
import sys
import time
import math
import statistics
from unittest.mock import patch


def distribution(samples):
    ordered=sorted(samples)
    return dict(median_ms=statistics.median(ordered),p95_ms=ordered[math.ceil(.95*len(ordered))-1],
                max_ms=ordered[-1],count=len(ordered))


def resources():
    if os.name!='nt':return {}
    import ctypes
    from ctypes import wintypes
    class Counters(ctypes.Structure):
        _fields_=[('cb',wintypes.DWORD),('faults',wintypes.DWORD)]+[
            (name,ctypes.c_size_t) for name in ('peak_rss','rss','peak_paged','paged','peak_nonpaged','nonpaged','pagefile','peak_pagefile')]
    kernel=ctypes.WinDLL('kernel32');psapi=ctypes.WinDLL('psapi')
    kernel.GetCurrentProcess.restype=wintypes.HANDLE
    psapi.GetProcessMemoryInfo.argtypes=[wintypes.HANDLE,ctypes.POINTER(Counters),wintypes.DWORD]
    info=Counters();info.cb=ctypes.sizeof(info)
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(),ctypes.byref(info),info.cb):raise ctypes.WinError()
    return dict(rss_bytes=info.rss,peak_rss_bytes=info.peak_rss)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--viewport', default='1200x800')
    parser.add_argument('--scenes', nargs='+', default=['small'])
    parser.add_argument('--frames', type=int, default=90)
    parser.add_argument('--motion', action='store_true')
    parser.add_argument('--rotations',action='store_true')
    parser.add_argument('--fallback',action='store_true')
    parser.add_argument('--night',action='store_true')
    parser.add_argument('--interactions',action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    out = args.output.resolve(); out.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault('SDL_VIDEODRIVER', 'windows')
    os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
    if args.fallback:os.environ['BLOC_FANTOME_DISABLE_NATIVE']='1'
    sys.path[:0] = [str(root/'Code'), str(root/'tests')]
    import pygame
    import blocFantome as b
    import runtime_paths
    from engine.world_catalog import WORLD_ENTRIES
    from engine.native_acceleration import backend_name
    random.seed(330)
    report = dict(complete=False, physical_input=False, audio_driver=os.environ['SDL_AUDIODRIVER'],
                  backend=backend_name(),source_sha256=hashlib.sha256((root/'Code/blocFantome.py').read_bytes()).hexdigest(), cases=[])
    report['source_hashes']={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in
        ('Code/blocFantome.py','Code/engine/atmosphere.py','Code/engine/renderer.py','Code/engine/audio.py','Code/engine/audio_decode.py')}
    report['harness_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    mode = pygame.display.set_mode
    with patch.object(b, 'APP_CONFIG_FILE', str(out/'preferences.json')), \
         patch.object(b, 'SAVES_DIR', str(out/'saves')), \
         patch.object(b, 'DERIVED_WORLD_CACHE_DIR', str(out/'cache')), \
         patch.object(runtime_paths, 'BASE_DIR', str(out)), \
         patch.object(b.TutorialScreen, '_saveConfig'), \
         patch.object(pygame.display, 'set_mode', lambda size, flags=0, *a, **kw: mode(size,flags|pygame.HIDDEN,*a,**kw)):
        app = b.BlocFantome()
        try:
            assert app.assetManager.loadAllAssets()
            app.autoSaveEnabled = False; app.tutorialScreen.visible = False
            app.musicMuted = True; app.musicController.stop(); app.workshop.visibility.reduced_motion = False
            app._applyWindowSize(*map(int,args.viewport.split('x')))
            app.worldCenteredRotation = True
            app.skyboxRenderer.set_selection('overworld',2 if args.night else 0,crossfade=False)
            if args.night:app.celestialEnabled=True;app.dayBrightness=.18
            def complete():
                deadline = time.monotonic()+120
                while time.monotonic()<deadline:
                    app._pollWorldLoad(); app._render(); pygame.event.pump()
                    if app.pendingWorldLoad is None and app._worldSurfaceBuild is None:
                        app._render(); return
                    time.sleep(.001)
                raise RuntimeError('World frame incomplete after 120 seconds')
            for scene in args.scenes:
                app.rainEnabled=False; app._stopRain(); app.snowEnabled=False; app._stopSnow()
                if scene=='small':
                    app._switchDimension('overworld')
                    app.world.resize(14,14,16,min_y=0,preserve=False)
                    app.sceneMetadata={}; app.sceneStructurePositions=set(); app.sceneTerrainMode='all'
                    for x,y,z,kind in b.STRUCTURE_RAIN_COURTYARD['blocks']:
                        app.world.setBlock(x,y,z,kind)
                    app._invalidateViewCaches()
                else:
                    entry=next(e for e in WORLD_ENTRIES if e.scene_id==scene)
                    app._handleWorldLibraryAction(('open',entry))
                complete(); app._fitWorldToViewport(notify=False); complete()
                for label, rain, fog, sky in [('clear',False,False,True),('rain',True,False,True),
                                               ('fog',False,True,True),('combined',True,True,True),
                                               ('fog-no-sky',False,True,False)]:
                    app.rainEnabled=rain; app.lightingEnabled=fog; app.lightingDirty=fog
                    app.skyboxesEnabled=sky
                    if rain:app._startRain()
                    else:app._stopRain()
                    app.nextThunderTime=999999; app.nextThunderAmbientTime=999999
                    app._invalidateViewCaches(); app._biomeViewSurfaces.clear()
                    cold_start=time.perf_counter();complete();cold_ms=(time.perf_counter()-cold_start)*1000
                    for _ in range(90):app._updateRain(1000/60);app._render()
                    timings=[]
                    movie=None
                    if args.motion:
                        w,h=app.screen.get_size()
                        movie=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pixel_format','rgb24',
                            '-video_size',f'{w}x{h}','-framerate','60','-i','-','-an','-c:v','libx264','-preset','fast',
                            '-crf','24','-pix_fmt','yuv420p',str(out/f'{scene}-{label}.mp4')],stdin=subprocess.PIPE)
                    for frame in range(args.frames):
                        start=time.perf_counter()
                        if args.motion and label=='combined':
                            app.renderer.offsetX+=math.sin(frame/60)*.7
                        app._updateRain(1000/60)
                        app._render()
                        timings.append((time.perf_counter()-start)*1000)
                        if movie:movie.stdin.write(pygame.image.tobytes(app.screen,'RGB'))
                    if movie:
                        movie.stdin.close();assert movie.wait()==0
                    pygame.image.save(app.screen,str(out/f'{scene}-{label}.png'))
                    row=dict(scene=scene,mode=label,viewport=app.screen.get_size(),
                             skybox=app.skyboxRenderer.active_name(app.currentDimension),
                             blocks=len(app.world.blocks),cold_complete_frame_ms=cold_ms,
                             timing=distribution(timings),resources=resources())
                    if hasattr(app,'atmosphere'):row['atmosphere']=app.atmosphere.metrics()
                    report['cases'].append(row)
                    (out/'results.json').write_text(json.dumps(report,indent=2))
                if args.motion:
                    app.rainEnabled=True;app._startRain();app.lightingEnabled=False;app.skyboxesEnabled=True
                    for label,intensity in (('light-rain',.6),('heavy-rain',1.4)):
                        app.atmosphere.intensity=app.atmosphere.target=intensity
                        app.atmosphere.next_change=app.atmosphere.elapsed+120
                        for _ in range(120):app._updateRain(1000/60);app._render()
                        w,h=app.screen.get_size()
                        movie=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pixel_format','rgb24',
                            '-video_size',f'{w}x{h}','-framerate','60','-i','-','-an','-c:v','libx264','-preset','fast',
                            '-crf','24','-pix_fmt','yuv420p',str(out/f'{scene}-{label}.mp4')],stdin=subprocess.PIPE)
                        for _ in range(360):
                            app._updateRain(1000/60);app._render()
                            movie.stdin.write(pygame.image.tobytes(app.screen,'RGB'))
                        movie.stdin.close();assert movie.wait()==0
                        pygame.image.save(app.screen,str(out/f'{scene}-{label}.png'))
                    report['intensity_demo']='Controlled .6 and 1.4 intensity poses, 6 seconds each; production renderer with scripted 60 Hz weather time.'
                if args.interactions:
                    app.rainEnabled=True;app._startRain();app.lightingEnabled=True
                    complete();events=[]
                    def send(items,mods=0):
                        pygame.event.clear()
                        for event in items:pygame.event.post(event)
                        with patch.object(pygame.key,'get_mods',return_value=mods):app._handleEvents()
                    for label,button in (('placement',1),('removal',3)):
                        before=dict(app.world.blocks);app.selectedBlock=b.BlockType.DIAMOND_BLOCK
                        point=None
                        w,h=app.screen.get_size()
                        for y in range(h//3,2*h//3,12):
                            for x in range(w//3,2*w//3,12):
                                app._updateHoveredCell(x,y)
                                cell=app.hoveredCell if button==1 else app.hoveredSourceBlock
                                if cell and app.world.isInBounds(*cell) and (button==3 or app.world.getBlock(*cell)!=b.BlockType.DIAMOND_BLOCK):
                                    point=(x,y);break
                            if point:break
                        assert point,'No editable visible pixel'
                        start=time.perf_counter()
                        with patch.object(pygame.mouse,'get_pos',return_value=point):
                            send([pygame.event.Event(pygame.MOUSEMOTION,pos=point,rel=(0,0),buttons=(0,0,0)),
                                  pygame.event.Event(pygame.MOUSEBUTTONDOWN,pos=point,button=button),
                                  pygame.event.Event(pygame.MOUSEBUTTONUP,pos=point,button=button)])
                        app._update();complete()
                        assert app.world.blocks!=before,'Input did not edit the world'
                        events.append(dict(action=label,ms=(time.perf_counter()-start)*1000))
                        send([pygame.event.Event(pygame.KEYDOWN,key=pygame.K_z,mod=pygame.KMOD_CTRL)],pygame.KMOD_CTRL)
                        complete();assert app.world.blocks==before,'Undo failed'
                    before=dict(app.world.blocks);path=out/(scene+'-saved.json.gz')
                    assert app._saveBuilding(filepath=str(path),silent=True)
                    assert app._loadBuildingFromPath(str(path),silent=True)
                    complete();assert app.world.blocks==before
                    report.setdefault('interactions',[]).append(dict(scene=scene,events=events,undo_exact=True,save_reload_exact=True))
                if args.rotations:
                    app.rainEnabled=True;app._startRain();app.lightingEnabled=True;app.skyboxesEnabled=True
                    for rotation in range(4):
                        app.renderer.setViewRotation(rotation);app._fitWorldToViewport(notify=False)
                        app._invalidateViewCaches();complete()
                        for _ in range(90):app._updateRain(1000/60);app._render()
                        pygame.image.save(app.screen,str(out/f'{scene}-rotation-{rotation}.png'))
                    app.workshop.visibility.reduced_motion=True
                    for _ in range(60):app._updateRain(1000/60);app._render()
                    pygame.image.save(app.screen,str(out/f'{scene}-reduced.png'))
                    app.workshop.visibility.reduced_motion=False
            report['complete']=True
        finally:
            app._stopRain(); app._stopHorrorRain()
            app.worldLoadExecutor.shutdown(wait=True,cancel_futures=True)
            if getattr(app,'_saveExecutor',None):app._saveExecutor.shutdown(wait=True,cancel_futures=True)
            pygame.quit()
            (out/'results.json').write_text(json.dumps(report,indent=2))


if __name__=='__main__':main()
