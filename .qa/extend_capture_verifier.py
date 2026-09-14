from pathlib import Path
p=Path('Code/tools/verify_world_map_regions.py');s=p.read_text().replace('def verify(world, directory):','def verify(world, directory, source_worlds=None):').replace("            region=world/dimension/'region'/", "            region=(source_worlds or {}).get(data['key'],world)/dimension/'region'/")
p.write_text(s)
