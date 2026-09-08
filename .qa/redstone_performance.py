import os, sys, json, time, statistics
from pathlib import Path
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'Code'))
import pygame
import blocFantome as m
from engine.redstone_lab import LAB_CIRCUITS
app = m.BlocFantome()
app.autoSaveEnabled = app.autoBackupEnabled = False
app._saveAppConfig = lambda: None
assert app.assetManager.loadAllAssets()
app._toggleRedstoneLab()
m.WINDOW_WIDTH, m.WINDOW_HEIGHT = 1920, 1080
app.screen = pygame.display.set_mode((1920,1080))
results = {}
for key in ('piston_door','clock','counter'):
    app._loadRedstoneLabCircuit(key)
    if key == 'clock': app._interactBlock(*LAB_CIRCUITS[key].controls[0][1])
    samples=[]
    for frame in range(360):
        start=time.perf_counter()
        if key == 'counter' and app.redstoneLabPulseStart is None:
            app._redstoneLabAction('pulse')
        if key == 'piston_door' and frame % 60 == 0:
            app._interactBlock(*LAB_CIRCUITS[key].controls[0][1])
        app._advanceLabRedstone(17)
        app._updateHoveredCell(650,480)
        app._render()
        pygame.display.flip()
        if frame >= 60: samples.append((time.perf_counter()-start)*1000)
    results[key]={'median_ms':round(statistics.median(samples),2),
                  'p95_ms':round(sorted(samples)[int(.95*len(samples))-1],2),
                  'max_ms':round(max(samples),2),'frames':len(samples)}
print(json.dumps(results,indent=2))
(root/'.qa/redstone-final/performance.json').write_text(json.dumps(results,indent=2))
pygame.quit()
