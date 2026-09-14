from pathlib import Path
p=Path('Code/ui/biomes.py');s=p.read_text();a=s.index('        surface = pygame.Surface(size,pygame.SRCALPHA)\n        cells =');b=s.index('\n    def render(self,',a);s=s[:a]+"        raise FileNotFoundError(f'Missing source biome preview: {path}')\n"+s[b:];s=s.replace('from engine.biome_scenes import biome_scene\n','');p.write_text(s)
for name in ('Code/blocFantome.py','Code/build_exe.py','Code/installer.iss'):
 p=Path(name);s=p.read_text(encoding='utf-8').replace('2.8.0','2.8.1');p.write_text(s,encoding='utf-8')
