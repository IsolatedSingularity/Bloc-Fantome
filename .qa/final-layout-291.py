from pathlib import Path
import json,gzip
p=Path('Code/biome_captures/tutorial_end_city.json.gz');d=json.loads(gzip.decompress(p.read_bytes()))
shift=53-d['origin'][2];d['origin'][2]=53;d['size'][2]-=shift
d['blocks']=[[x,y,z-shift,p] for x,y,z,p in d['blocks'] if z>=shift]
p.write_bytes(gzip.compress(json.dumps(d,separators=(',',':')).encode(),mtime=0))
print(len(d['blocks']))
p=Path('tests/test_public_contract.py');s=p.read_text().replace("sum(bool(step['is_horror']) for step in TOUR) == 1","sum(bool(step['is_horror']) for step in TOUR) == 0");p.write_text(s)
# Measure the detail area before allocating preview and description space.
p=Path('Code/ui/library.py');s=p.read_text();a=s.index('        if entry:\n            yy=wrapped');b=s.index('        else:wrapped',a)
s=s[:a]+'''        if entry:
            yy=wrapped(screen,entry['name'],app.font,detail)
            warning_height=58 if entry['kind'] in ('biome','world') else 0
            preview_height=max(90,min(240,detail.height-175))
            preview=app.previewImages.get(app,entry,(detail.width,preview_height))
            if preview:
                screen.blit(preview,(detail.x,yy+10));yy+=preview_height+16
            description_bottom=detail.bottom-warning_height-8
            wrapped(screen,entry['detail'],self.small,(detail.x,yy+8,detail.width,max(0,description_bottom-yy-8)),MUTED)
            if warning_height:
                wrapped(screen,'Opening replaces the canvas. Save your current build first.',self.small,(detail.x,detail.bottom-warning_height,detail.width,warning_height),ACCENT)
'''+s[b:];p.write_text(s)
