"""Generate auditable biome samples with the local, unmodified Java 1.16.1 server.

Only writes its dedicated QA world. Commands and vanilla responses are retained.
Run from the repository root; no game installation or network download needed.
"""
from pathlib import Path
import json
import queue
import re
import subprocess
import sys
import threading
import time
import gzip
import struct

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from engine.biome_catalog import BIOMES
from engine.anvil import _NBTReader

ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT/'.qa/biome-capture-281'

def main():
    global WORK
    void='--void' in sys.argv
    if void:WORK=ROOT/'.qa/void-capture-281'
    WORK.mkdir(parents=True,exist_ok=True)
    special='--special' in sys.argv
    existing=json.loads((WORK/'locations.json').read_text()) if special else []
    if special:
        # 1.16.1 stores custom dimension definitions in WorldGenSettings in
        # level.dat. Preserve every existing NBT byte and append only our registry entries.
        level=WORK/'world/level.dat';raw=gzip.decompress(level.read_bytes())
        marker=b'\x0a\x00\x0adimensions';start=raw.index(marker)+len(marker)
        reader=_NBTReader(raw);reader.stream.seek(start);registered=reader.payload(10)
        end=reader.stream.tell()-1;additional=b''
        def string(value):
            data=value.encode();return struct.pack('>H',len(data))+data
        def named(name,value):
            if isinstance(value,dict):return b'\x0a'+string(name)+b''.join(named(k,v) for k,v in value.items())+b'\x00'
            if isinstance(value,int):return b'\x04'+string(name)+struct.pack('>q',value)
            return b'\x08'+string(name)+string(value)
        for row in existing:
            if row['location']:continue
            key='bloc_capture:'+row['id']
            if key in registered:continue
            additional+=named(key,{'type':'minecraft:overworld','generator':{
                'type':'minecraft:noise','seed':1,'settings':'minecraft:overworld',
                'biome_source':{'type':'minecraft:fixed','biome':'minecraft:'+row['id']}}})
        if additional:
            (WORK/'level-before-special.dat').write_bytes(level.read_bytes())
            level.write_bytes(gzip.compress(raw[:end]+additional+raw[end:]))
    (WORK/'eula.txt').write_text('eula=true\n')
    (WORK/'server.properties').write_text('server-ip=127.0.0.1\nserver-port=25589\nonline-mode=false\nlevel-name=world\nlevel-seed=1\nview-distance=2\nmax-tick-time=-1\nsync-chunk-writes=true\n')
    if void:
        settings={'structures':{'structures':{}},'layers':[{'height':1,'block':'minecraft:air'}],
                  'biome':'minecraft:the_void','features':True,'lakes':False}
        with (WORK/'server.properties').open('a') as stream:
            stream.write('level-type=flat\ngenerator-settings='+json.dumps(settings)+'\n')
    jar=ROOT/'Game Reference/01_upstream/minecraft-1.16.1-server.jar'
    process=subprocess.Popen(['java','-Xmx2G','-jar',str(jar),'nogui'],cwd=WORK,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
    messages=queue.Queue()
    log=(WORK/'capture.log').open('a',encoding='utf-8')
    def reader():
        for line in process.stdout:
            log.write(line); log.flush(); messages.put(line)
    threading.Thread(target=reader,daemon=True).start()
    def wait(pattern,timeout=180):
        end=time.monotonic()+timeout; lines=[]
        while time.monotonic()<end:
            try: line=messages.get(timeout=1)
            except queue.Empty: continue
            lines.append(line)
            if re.search(pattern,line): return ''.join(lines)
        raise TimeoutError(pattern)
    def command(text):
        process.stdin.write(text+'\n');process.stdin.flush()
    result=[r for r in existing if r['location']] if special else []
    try:
        wait(r'Done \(')
        command('gamerule randomTickSpeed 0')
        command('gamerule doMobSpawning false')
        for entry in BIOMES:
            if void and entry['id']!='the_void':continue
            name,dimension=entry['id'],entry['dimension']
            if special and any(r['id']==name for r in result):continue
            dim={'overworld':'overworld','nether':'the_nether','end':'the_end'}[dimension]
            dim='bloc_capture:'+name if special else 'minecraft:'+dim
            response=''; location=None
            for x,z in (() if special else ((0,0),(12000,12000),(-12000,-12000))):
                command(f'execute in {dim} positioned {x} 64 {z} run locatebiome minecraft:{name}')
                response=wait(r'(nearest minecraft:|Could not find|No biome)')
                match=re.search(r'\[(-?\d+),[^,]+, (-?\d+)\]',response)
                if match: location=[int(match[1]),int(match[2])];break
                if name in ('the_void','deep_warm_ocean','mountain_edge'):break
            if special:location=[0,0];response='Explicit single-biome dimension using vanilla noise generator and biome features.'
            row=dict(id=name,dimension=dimension,raw_id=entry['raw_id'],location=location,response=response.strip())
            if special:
                row['capture_kind']='single_biome'
                row['source_world']='world/dimensions/bloc_capture/'+name
            if location:
                ox,oz=(v//16*16-16 for v in location)
                command(f'execute in {dim} run forceload add {ox} {oz} {ox+47} {oz+47}')
                wait(r'(Marked|already marked)')
                time.sleep(4)
                command('save-all flush');wait(r'Saved the game')
                command(f'execute in {dim} run forceload remove all')
                row['origin']=[ox,oz]
            result.append(row)
            (WORK/'locations.json').write_text(json.dumps(result,indent=2))
            print(name,location,flush=True)
    finally:
        command('stop');process.wait(timeout=120);log.close()

if __name__=='__main__':main()
