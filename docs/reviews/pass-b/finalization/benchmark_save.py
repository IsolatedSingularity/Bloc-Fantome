import os,sys,json,time,gzip
from pathlib import Path
os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy'
sys.path.insert(0,str(Path.cwd()/'Code'))
import pygame
import blocFantome as m
from engine.save_job import capture_save
from engine.build_io import write_build
from engine.world_snapshot import WorldSnapshot
out=Path('.qa/pass-b-finalization/save-benchmark');out.mkdir(parents=True,exist_ok=True)
m.SAVES_DIR=str(out);app=m.BlocFantome();app.autoSaveEnabled=False;app.tutorialScreen.visible=False
results=[]
for n in (12,160):
 cells={(x,y,z):m.BlockType.STONE for x in range(n) for y in range(n) for z in range(4)}
 app.world.replace(WorldSnapshot(n,n,8,blocks=cells));app.sceneMetadata={};app.sceneStructurePositions=set()
 t=time.perf_counter();snap=capture_save(app.world,'overworld',{},set());capture=(time.perf_counter()-t)*1000
 path=out/f'sync-{n}.gz';t=time.perf_counter();write_build(path,snap,m.BLOCK_DEFINITIONS);sync=(time.perf_counter()-t)*1000
 path=out/f'async-{n}.gz';t=time.perf_counter();app._saveBuilding(filepath=str(path));submission=(time.perf_counter()-t)*1000
 frames=[]
 while app._pendingSave:
  app._pollSave();pygame.event.pump();pygame.display.flip();frames.append(time.perf_counter());time.sleep(.005)
 with gzip.open(path,'rt') as f:loaded=json.load(f)
 assert len(loaded['blocks'])==len(cells)
 results.append(dict(blocks=len(cells),capture_ms=capture,synchronous_write_ms=sync,submission_ms=submission,
  asynchronous=app._lastSaveMetrics,presented_frames=len(frames),max_frame_gap_ms=max((b-a for a,b in zip(frames,frames[1:])),default=0)*1000,
  path=str(path.resolve()),round_trip=True))
app._saveExecutor.shutdown(wait=True);app.worldLoadExecutor.shutdown(wait=True)
(out/'report.json').write_text(json.dumps(results,indent=2))
print(json.dumps(results,indent=2))
