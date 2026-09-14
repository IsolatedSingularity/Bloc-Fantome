from pathlib import Path
for name in ('Code/blocFantome.py','Code/build_exe.py','Code/installer.iss'):
 p=Path(name);s=p.read_text(encoding='utf-8').replace('2.9.0','2.9.1');p.write_text(s,encoding='utf-8')
p=Path('Code/build_exe.py');s=p.read_text(encoding='utf-8');needle="    cmd.append(f\"--add-data={os.path.join(SCRIPT_DIR, 'biome_captures')}{os.pathsep}biome_captures\")"
s=s.replace(needle,needle+"\n    cmd.append(f\"--add-data={os.path.join(SCRIPT_DIR, 'world_previews')}{os.pathsep}world_previews\")")
p.write_text(s,encoding='utf-8')
p=Path('Code/engine/tutorial_lessons.py');s=p.read_text();s=s.replace('The build follows your cursor until placed.','Then click the canvas to place the build.');p.write_text(s)
p=Path('AGENTS.md');s=p.read_text();s+='\n- UI consistency is a release requirement across every panel and dialog: use the established Minecraft textures, raised grey controls, shared Zekton typography at native size, and measured layouts. Worlds, Biomes and Structures must remain discoverable in the right panel with real content previews. Avoid text-only replacement galleries and low-resolution scaled UI.\n';p.write_text(s)
