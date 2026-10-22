import os,sys,json,time,cProfile,pstats
from pathlib import Path
os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy'
sys.path.insert(0,str(Path.cwd()/'Code'))
import blocFantome as m
from engine.save_job import capture_save,write_timed
from engine.world_snapshot import WorldSnapshot
out=Path('.qa/pass-b-finalization/save-profile');out.mkdir(parents=True,exist_ok=True)
app=m.BlocFantome();n=160
app.world.replace(WorldSnapshot(n,n,8,blocks={(x,y,z):m.BlockType.STONE for x in range(n) for y in range(n) for z in range(4)}))
t=time.perf_counter();snapshot=capture_save(app.world,'overworld',{},set());capture=(time.perf_counter()-t)*1000
pr=cProfile.Profile();pr.runcall(write_timed,out/'save.gz',snapshot,m.BLOCK_DEFINITIONS,(out/'backups',3))
pr.dump_stats(str(out/'writer.prof'))
rows=[]
for (file,line,name),(primitive,total,own,cumulative,callers) in pstats.Stats(pr).stats.items():
 rows.append(dict(file=file,line=line,function=name,calls=total,self_ms=own*1000,cumulative_ms=cumulative*1000))
(out/'report.json').write_text(json.dumps(dict(blocks=len(snapshot.blocks),capture_ms=capture,includes_one_backup=True,dialog_ms=0,dialog_note='Direct save path; native Save As human dwell excluded',profile_overhead=True,functions=sorted(rows,key=lambda r:-r['cumulative_ms'])),indent=2))
app.worldLoadExecutor.shutdown(wait=True)
