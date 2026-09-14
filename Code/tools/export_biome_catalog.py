"""Rebuild the small runtime biome table from the owner's Java 1.16.1 corpus."""
from pathlib import Path
import pprint
import re


def export():
    root = Path(__file__).resolve().parents[2]
    sources = root / 'Game Reference/05_mapped_sources/net/minecraft/world/biome'
    registry = (sources / 'Biomes.java').read_text(encoding='utf-8')
    rows = []
    for raw_id, name, cls in re.findall(r'register\((\d+), "([^"]+)", new (\w+)\(\)\)', registry):
        source = (sources / f'{cls}.java').read_text(encoding='utf-8')
        def value(pattern, default):
            match = re.search(pattern, source)
            return match.group(1) if match else default
        category = value(r'category\(Biome.Category.(\w+)\)', 'NONE')
        rows.append(dict(id=name, raw_id=int(raw_id), category=category,
                         dimension='nether' if category == 'NETHER' else 'end' if category == 'THEEND' else 'overworld',
                         depth=float(value(r'\.depth\(([-\d.]+)F\)', '0')),
                         scale=float(value(r'\.scale\(([-\d.]+)F\)', '0')),
                         temperature=float(value(r'\.temperature\(([-\d.]+)F\)', '0.5')),
                         surface=value(r'configureSurfaceBuilder\(SurfaceBuilder.\w+, SurfaceBuilder.(\w+)\)', 'GRASS_CONFIG'),
                         features=re.findall(r'DefaultBiomeFeatures\.(add\w+)\(this\)', source),
                         source=f'Game Reference/05_mapped_sources/net/minecraft/world/biome/{cls}.java'))
    target = root / 'Code/engine/biome_catalog.py'
    target.write_text('"""Generated Java 1.16.1 registry and biome settings. See tools/export_biome_catalog.py."""\nBIOMES = ' + pprint.pformat(tuple(rows), width=110) + '\nBY_ID = {entry["id"]: entry for entry in BIOMES}\n', encoding='utf-8')
    print(f'Exported {len(rows)} Java 1.16.1 biome definitions')


if __name__ == '__main__':
    export()
