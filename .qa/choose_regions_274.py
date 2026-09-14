import json
d=json.load(open('.qa/biomes-274.json'))
for dim,b,n in [('',44,6),('DIM-1',173,8)]:
    rows={(r['x'],r['z']):r for r in d if r['dim']==dim}
    best=[]
    for x,z in rows:
        cells=[rows.get((x+i*16,z+j*16)) for i in range(n) for j in range(n)]
        if all(cells): best.append((sum(r['biomes'].get(str(b),0) for r in cells)/(n*n*16),x,z,n*16))
    print(b, sorted(best,reverse=True)[:3])
