"""Matched accepted/candidate world repaint, including every incremental frame.

Run with the repository Python. Uses the accepted source from Git, isolated data,
native hidden SDL, real placement, picking and final RGBA comparison.
"""
import ast
import cProfile
import gc
import json
import os
from pathlib import Path
import pstats
import subprocess
import sys
import time
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Code'))
os.environ['SDL_VIDEODRIVER']='windows'
os.environ['SDL_AUDIODRIVER']='dummy'
import pygame
import blocFantome as b


def main():
    out=ROOT/'docs/reviews/final-3/performance';out.mkdir(parents=True,exist_ok=True)
    original=pygame.display.set_mode
    source=subprocess.check_output(['git','show','c3591022:Code/blocFantome.py'],cwd=ROOT).decode('utf-8')
    cls=next(n for n in ast.parse(source).body if isinstance(n,ast.ClassDef) and n.name=='BlocFantome')
    fn=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='_renderWorld')
    ns=dict(b.__dict__);exec(compile(ast.Module(body=[fn],type_ignores=[]),'accepted-renderer','exec'),ns)
    accepted=ns['_renderWorld'];candidate=b.BlocFantome._renderWorld
    cull=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='_visibleScreenRenderPlan')
    exec(compile(ast.Module(body=[cull],type_ignores=[]),'baseline-culling','exec'),ns)
    baseline_cull=ns['_visibleScreenRenderPlan'];candidate_cull=b.BlocFantome._visibleScreenRenderPlan
    report=[];gc_events=[];gc_start={}
    def gc_trace(phase,info):
        if phase=='start':gc_start[info['generation']]=time.perf_counter()
        else:gc_events.append(dict(generation=info['generation'],ms=(time.perf_counter()-gc_start[info['generation']])*1000))
    gc.callbacks.append(gc_trace)
    with patch.object(pygame.display,'set_mode',lambda size,flags=0,*a,**k:original(size,flags|pygame.HIDDEN,*a,**k)),patch.object(b,'APP_CONFIG_FILE',str(ROOT/'.qa/final-3/perf-config.json')),patch.object(b.BlocFantome,'_saveAppConfig'),patch.object(b.TutorialScreen,'_saveConfig'),patch.object(b,'DERIVED_WORLD_CACHE_DIR',str(ROOT/'.qa/final-3/cache')):
        app=b.BlocFantome();app.autoSaveEnabled=False;app.tutorialScreen.visible=False
        assert app.assetManager.loadAllAssets();app._applyWindowSize(1200,800)
        def settle():
            samples=[]
            while True:
                app.screen.fill((24,35,34));start=time.perf_counter();app._renderWorld()
                samples.append((time.perf_counter()-start)*1000);pygame.event.pump()
                if app._worldSurfaceBuild is None:return samples
                if len(samples)>1000:raise RuntimeError('Unfinished repaint')
        try:
            for name in ('ancient_city_121','trial_chamber_121','village_plains_1161','ocean_monument_1161'):
                assert app._loadBuildingFromPath(str(ROOT/'Code/worlds'/f'{name}.json.gz'),silent=True)
                app._fitWorldToViewport(notify=False);app._worldTransitionKind=None
                app._renderWorld=candidate.__get__(app);settle()
                row={'scene':name,'blocks':len(app.world.blocks),'operations':[]}
                for operation in ('pan','zoom','rotate','edit'):
                    if operation=='pan':app.renderer.offsetX+=35
                    elif operation=='zoom':app._handleZoom(.025,600,400)
                    elif operation=='rotate':app._rotateViewAndRecenter(1)
                    else:
                        x,y=app.world.width//2,app.world.depth//2
                        z=min(app.world.max_y_exclusive-1,app.world.getHighestBlock(x,y)+1)
                        start=time.perf_counter();app._placeBlockWithUndo(x,y,z,b.BlockType.STONE);app._afterWorldEdit(((x,y,z),))
                        row['edit_handler_ms']=(time.perf_counter()-start)*1000
                    kind=app._worldTransitionKind;fallback=app._worldZoomFallback;results={'accepted':[],'candidate':[]};runs={'accepted':[],'candidate':[]};pixels={}
                    # Warm both paths, then alternate order to avoid assigning all
                    # first-use sprite/cache work to the accepted painter.
                    for repeat in range(5):
                        pairs=(('accepted',accepted),('candidate',candidate))
                        if repeat%2:pairs=pairs[::-1]
                        for label,render in pairs:
                            app._renderWorld=render.__get__(app);app._visibleScreenRenderPlan=(baseline_cull if label=='accepted' else candidate_cull).__get__(app);app._invalidateViewCaches();app._biomeViewSurfaces.clear();app._worldTransitionKind=kind
                            app._worldZoomFallback=fallback
                            samples=settle();pixels[label]=pygame.image.tobytes(app.screen,'RGBA')
                            if repeat:results[label].extend(samples);runs[label].append(samples)
                        assert pixels['accepted']==pixels['candidate'],(name,operation,repeat)
                    gc_summary={generation:dict(count=len(events),total_ms=sum(e['ms'] for e in events),max_ms=max((e['ms'] for e in events),default=0))
                                for generation in (0,1,2) if (events:=[e for e in gc_events if e['generation']==generation])}
                    row['operations'].append(dict(action=operation,frames_ms=results,runs_ms=runs,pixel_equal=True,gc_summary=gc_summary))
                    gc_events.clear()
                start=time.perf_counter()
                for i in range(20):app._updateHoveredCell(400+i*4,350)
                row['picking_20_ms']=(time.perf_counter()-start)*1000
                app._invalidateViewCaches();app._biomeViewSurfaces.clear();app._worldTransitionKind='zoom'
                profile=cProfile.Profile();profile.enable();settle();profile.disable()
                with (out/(name+'-profile.txt')).open('w') as f:pstats.Stats(profile,stream=f).strip_dirs().sort_stats('cumulative').print_stats(25)
                pygame.image.save(app.screen,str(out/(name+'.png')))
                report.append(row);(out/'matched.json').write_text(json.dumps(report,indent=2))
                print(name,'pixel equal',flush=True)
        finally:gc.callbacks.remove(gc_trace);app.worldLoadExecutor.shutdown(wait=True,cancel_futures=True);pygame.quit()


if __name__=='__main__':main()
