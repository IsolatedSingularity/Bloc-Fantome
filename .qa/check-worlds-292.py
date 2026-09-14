import os, sys, time, json
from pathlib import Path
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
sys.path.insert(0,'Code')
import pygame
import blocFantome as module
from engine.world_catalog import WORLD_ENTRIES
out=Path('.qa/revision-292-worlds');out.mkdir(exist_ok=True)
module.DERIVED_WORLD_CACHE_DIR=str(out/'scene-cache')
app=module.BlocFantome();assert app.assetManager.loadAllAssets()
app._preloadTutorialMusic();app.tutorialScreen.visible=False
app.autoSaveEnabled=False;app._applyWindowSize(1920,1080)
app.worldCenteredRotation=True
results=[]
selected=set(sys.argv[1:])
def settle():
    frames=[];deadline=time.perf_counter()+150
    while time.perf_counter()<deadline:
        start=time.perf_counter();app._update();app._render()
        frames.append((time.perf_counter()-start)*1000)
        if app.pendingWorldLoad is None and app._worldSurfaceBuild is None:break
        time.sleep(.002)
    assert app.pendingWorldLoad is None and app._worldSurfaceBuild is None
    assert not app.tooltipText.startswith('Could not open'),app.tooltipText
    return frames
for entry in WORLD_ENTRIES:
    if selected and entry.scene_id not in selected:continue
    start=time.perf_counter();app._handleWorldLibraryAction(('open',entry))
    dispatch=(time.perf_counter()-start)*1000
    frames=settle();ready=(time.perf_counter()-start)*1000
    row=dict(scene=entry.scene_id,cells=len(app.world.blocks),bounds=[app.world.width,app.world.depth,app.world.height],dispatch_ms=round(dispatch,2),ready_ms=round(ready,2),loading_frame_max_ms=round(max(frames),2),views=[])
    for rotation in range(4):
        if rotation:app._rotateViewAndRecenter(1);settle()
        assert app.renderStats['drawn']>0
        for _ in range(6):app._update();app._render()
        samples=[]
        for _ in range(90):
            t=time.perf_counter();app._update();app._render();samples.append((time.perf_counter()-t)*1000)
        row['views'].append(dict(rotation=app.renderer.viewRotation,drawn=app.renderStats['drawn'],frame_p95_ms=round(sorted(samples)[85],2)))
        if rotation==0:pygame.image.save(app.screen,str(out/(entry.scene_id+'.png')))
    print(json.dumps(row),flush=True);results.append(row)
    report_path=out/'performance.json'
    previous=json.loads(report_path.read_text()) if selected and report_path.exists() else []
    updated={r['scene']:r for r in previous}
    updated.update({r['scene']:r for r in results})
    report_path.write_text(json.dumps(list(updated.values()),indent=2))
app.worldLoadExecutor.shutdown(wait=True);pygame.quit()
