import os,sys,time,json
from pathlib import Path
os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy';sys.path.insert(0,'Code')
import pygame
import blocFantome as module
out=Path('.qa/revision-292-biomes');out.mkdir(exist_ok=True)
module.DERIVED_WORLD_CACHE_DIR=str(out/'scene-cache')
app=module.BlocFantome();assert app.assetManager.loadAllAssets()
app._preloadTutorialMusic();app.tutorialScreen.visible=False;app.autoSaveEnabled=False
app._applyWindowSize(1920,1080);app.worldCenteredRotation=True
rows=[]
for name in ('the_end','deep_ocean'):
    start=time.perf_counter();app._queueBiomeScene(name);frames=[]
    deadline=start+120
    while time.perf_counter()<deadline:
        t=time.perf_counter();app._update();app._render();frames.append((time.perf_counter()-t)*1000)
        if app.pendingBiomeLoad is None and app._worldSurfaceBuild is None:break
        time.sleep(.002)
    assert app.pendingBiomeLoad is None
    assert not app.tooltipText.startswith('Could not open'),app.tooltipText
    row=dict(biome=name,blocks=len(app.world.blocks),ready_ms=round((time.perf_counter()-start)*1000,2),loading_frame_max_ms=round(max(frames),2),views=[])
    for rotation in range(4):
        if rotation:app._rotateViewAndRecenter(1)
        for _ in range(180):
            app._update();app._render()
            if app._worldSurfaceBuild is None:break
        assert app._worldSurfaceBuild is None and app.renderStats['drawn']>0
        pygame.image.save(app.screen,str(out/f'{name}_{rotation}.png'))
        times=[]
        for _ in range(90):
            t=time.perf_counter();app._update();app._render();times.append((time.perf_counter()-t)*1000)
        row['views'].append(dict(rotation=app.renderer.viewRotation,drawn=app.renderStats['drawn'],frame_p95_ms=round(sorted(times)[85],2)))
    print(row,flush=True);rows.append(row)
(out/'performance.json').write_text(json.dumps(rows,indent=2))
app.worldLoadExecutor.shutdown(wait=True);pygame.quit()
