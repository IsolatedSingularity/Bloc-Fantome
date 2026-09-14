import os, sys, time, json
from pathlib import Path
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Code'))
import pygame
from blocFantome import BlocFantome
app=BlocFantome()
app.assetManager.loadAllAssets()
app.tutorialScreen.visible=False
out=Path(__file__).parent/'consistency-baseline'
out.mkdir(exist_ok=True)
results=[]
for name in ('plains','warped_forest','end_highlands'):
    t=time.perf_counter(); app._openBiomeScene(name)
    row={'biome':name,'load_ms':(time.perf_counter()-t)*1000,'cells':len(app.world.blocks),'zoom':app.zoomLevel,'frames':[]}
    for turn in range(2):
        if turn:app._rotateViewAndRecenter(1)
        for frame in range(8):
            t=time.perf_counter();app._update();app._render()
            row['frames'].append({'turn':turn,'ms':round((time.perf_counter()-t)*1000,2),'build_index':app._worldSurfaceBuildIndex,'cached':app._worldSurfaceCache is not None})
        pygame.image.save(app.screen,str(out/f'{name}_{turn}.png'))
    print(json.dumps(row),flush=True);results.append(row)
(out/'results.json').write_text(json.dumps(results,indent=2))
app.worldLoadExecutor.shutdown(wait=True)
pygame.quit()
