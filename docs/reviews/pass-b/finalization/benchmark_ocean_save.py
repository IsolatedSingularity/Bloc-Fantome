import os,sys,json,time
from pathlib import Path
os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy'
sys.path.insert(0,str(Path.cwd()/'Code'))
import pygame
import blocFantome as m
out=Path('.qa/pass-b-finalization/ocean-save');out.mkdir(parents=True,exist_ok=True)
app=m.BlocFantome();app.autoSaveEnabled=False;app.tutorialScreen.visible=False
snapshot=app._readBuildFile(str(Path('Code/worlds/ocean_monument_1161.json.gz').resolve()))[3]
app.world.replace(snapshot);app.sceneMetadata=dict(snapshot.scene_metadata);app.sceneStructurePositions=set(snapshot.structure_positions)
all_flips=[];original_flip=pygame.display.flip
def flip():
 original_flip();all_flips.append(time.perf_counter())
pygame.display.flip=flip
t=time.perf_counter();app._saveBuilding(filepath=str((out/'ocean.json.gz').resolve()));submission=(time.perf_counter()-t)*1000
capture_flips=len(all_flips);frames=[]
while app._pendingSave:
 app._pollSave();pygame.event.pump();pygame.display.flip();frames.append(time.perf_counter());time.sleep(.005)
result=dict(blocks=len(app.world.blocks),properties=len(app.world.blockProperties),submission_ms=submission,
 save=app._lastSaveMetrics,capture_presented_frames=capture_flips,all_max_frame_gap_ms=max((b-a for a,b in zip(all_flips,all_flips[1:])),default=0)*1000,presented_frames=len(frames),max_frame_gap_ms=max((b-a for a,b in zip(frames,frames[1:])),default=0)*1000)
(out/'report.json').write_text(json.dumps(result,indent=2));print(result)
import gzip
with gzip.open(out/'ocean.json.gz','rt') as f:loaded=json.load(f)
assert len(loaded['blocks'])==len(app.world.blocks)
result['round_trip_block_count']=True
(out/'report.json').write_text(json.dumps(result,indent=2))
app._saveExecutor.shutdown(wait=True);app.worldLoadExecutor.shutdown(wait=True)
