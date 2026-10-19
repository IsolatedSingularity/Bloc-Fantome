from pathlib import Path
p=Path('.qa/maintenance/verify-performance.py');s=p.read_text();s=s.replace("'nether_fortress_biomes_1161.json.gz'","'ocean_monument_1161.json.gz'").replace('fortress-view-','ocean-view-').replace('isolated-performance.json','ocean-performance.json');Path('.qa/maintenance/verify-ocean.py').write_text(s)
