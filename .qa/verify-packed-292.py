import sys,json,gzip
from pathlib import Path
sys.path.insert(0,'Code')
from engine.capture_records import CaptureRecords,load_capture_file
root=Path('Code/biome_captures');total=0;files=0
for path in sorted(root.glob('*.json.gz')):
    original=json.loads(gzip.decompress(path.read_bytes()))
    runtime=load_capture_file(path)
    assert isinstance(runtime['blocks'],CaptureRecords),path
    expected=original.pop('blocks');actual=runtime.pop('blocks')
    assert runtime==original,path
    assert len(actual)==len(expected),path
    assert all(tuple(a)==b for a,b in zip(expected,actual,strict=True)),path
    total+=len(actual);files+=1
Path('.qa/revision-292-packed-verification.json').write_text(json.dumps(dict(files=files,cells=total,metadata_equal=True,records_equal=True),indent=2))
print('Verified exact packed round trip:',files,'captures;',total,'cells',flush=True)
