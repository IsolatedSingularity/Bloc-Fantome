from pathlib import Path
p=Path('Code/blocFantome.py');s=p.read_text(encoding='utf-8');a=s.index('    def _renderPanel(');b=s.index('    def ',a+10)
part=s[a:b].replace('availableHeight = WINDOW_HEIGHT - headerHeight','availableHeight = WINDOW_HEIGHT - headerHeight - 126')
part=part.replace('totalHeight += numRows * (slotSize + 4) + 5','totalHeight += numRows * (slotSize + 4) + 32')
s=s[:a]+part+s[b:]
a=s.index('    def _handlePanelClick(');b=s.index('        panelX = mouseX',a)
s=s[:b]+'''        # The fixed tome/settings stack owns the lower strip. Off-screen
        # scroll controls must not keep clickable rectangles there.
        if mouseY >= WINDOW_HEIGHT - 126:
            return

'''+s[b:]
p.write_text(s,encoding='utf-8')
p=Path('Code/tools/bake_biome_atlases.py');s=p.read_text();s=s.replace("name=next(k for k,v in json.loads((root/'manifest.json').read_text()).items() if v['file']==path.name)","name='_tutorial_end_city' if path.name=='tutorial_end_city.json.gz' else next(k for k,v in json.loads((root/'manifest.json').read_text()).items() if v['file']==path.name)");p.write_text(s)
