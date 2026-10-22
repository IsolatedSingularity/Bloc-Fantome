"""Matched scalar/batch full-world repaint timings and exact RGBA equality."""
import os,sys,json,time,cProfile,pstats
from pathlib import Path
from unittest.mock import patch
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Code'))
os.environ['SDL_VIDEODRIVER']='windows';os.environ['SDL_AUDIODRIVER']='dummy'
import pygame
import blocFantome as b


def main():
    out=ROOT/'.qa/pass-b/projection';out.mkdir(parents=True,exist_ok=True)
    b.DERIVED_WORLD_CACHE_DIR=str(out/'cache')
    original=pygame.display.set_mode
    pygame.display.set_mode=lambda size,flags=0,*a,**k:original(size,flags|pygame.HIDDEN,*a,**k)
    with patch.object(b,'APP_CONFIG_FILE',str(out/'config.json')),patch.object(b.BlocFantome,'_saveAppConfig'),patch.object(b.TutorialScreen,'_saveConfig'):
        app=b.BlocFantome();app.autoSaveEnabled=False;app.tutorialScreen.visible=False
        app.assetManager.loadAllAssets();app._applyWindowSize(1200,800)
        report=[]
        try:
            for name in ('ocean_monument_1161','trial_chamber_121'):
                assert app._loadBuildingFromPath(str(ROOT/'Code/worlds'/f'{name}.json.gz'),silent=True)
                app._fitWorldToViewport(notify=False)
                app._worldTransitionKind=None
                batch=app.renderer.worldToScreenBatch
                scalar=lambda points:[list(app.renderer.worldToScreen(*p)) for p in points]
                cases=[]
                for rotation in range(4):
                    app.renderer.setViewRotation(rotation)
                    app._fitWorldToViewport(notify=False)
                    for zoom_delta in (0,.025):
                        app._handleZoom(zoom_delta,600,400)
                        times={'scalar':[],'batch':[]};pixels={};counts=[]
                        for repeat in range(8):
                            for mode in (('scalar','batch') if repeat%2==0 else ('batch','scalar')):
                                used=[]
                                def project(points):
                                    used.append(len(points))
                                    return (scalar if mode=='scalar' else batch)(points)
                                app.renderer.worldToScreenBatch=project
                                app._invalidateViewCaches();app._worldTransitionKind=None
                                app._biomeViewSurfaces.clear()
                                # Measure world composition only; sky/UI/mouse animation cannot
                                # contaminate equality or claim an end-to-end latency result.
                                app.screen.fill((0,0,0))
                                start=time.perf_counter();app._renderWorld()
                                times[mode].append((time.perf_counter()-start)*1000)
                                assert used, (name,rotation,mode,'projection path not exercised')
                                counts.append(used[0])
                                pixels[mode]=pygame.image.tobytes(app.screen,'RGBA')
                            assert pixels['scalar']==pixels['batch'],(name,rotation,zoom_delta)
                        cases.append(dict(rotation=rotation,zoom=app.zoomLevel,pixel_equal=True,
                            projected_points=counts,scalar_ms=times['scalar'],batch_ms=times['batch']))
                report.append(dict(scene=name,cases=cases))
                app.renderer.worldToScreenBatch=batch
                (out/'matched.json').write_text(json.dumps(report,indent=2))
                print(name,'exact pixels',flush=True)
        finally:app.worldLoadExecutor.shutdown(wait=True,cancel_futures=True);pygame.quit()


if __name__=='__main__':main()
