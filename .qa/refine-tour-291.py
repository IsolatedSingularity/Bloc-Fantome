from pathlib import Path
p=Path('Code/engine/tutorial_runtime.py');s=p.read_text()
s=s.replace('    def _applyTourScene(self,snapshot,step):\n', '''    def _applyTourScene(self,snapshot,step):
        from dataclasses import replace
        snapshot=replace(snapshot,blocks=dict(snapshot.blocks),
            properties={p:v.copy() for p,v in snapshot.properties.items()},
            surface_positions=frozenset(snapshot.surface_positions),
            structure_positions=frozenset(snapshot.structure_positions),
            structure_surfaces_by_view={r:frozenset(v) for r,v in snapshot.structure_surfaces_by_view.items()},
            view_surface_positions_by_view={r:frozenset(v) for r,v in snapshot.view_surface_positions_by_view.items()})
''')
p.write_text(s)
p=Path('Code/ui/preview_browser.py');s=p.read_text().replace('120+(370','120+(370')
# Use a fixed base image for every requested size; never regenerate user previews just to enlarge them.
s=s.replace("        elif kind=='world':\n            path", "        elif kind=='world':\n            path")
p.write_text(s)
p=Path('Code/ui/chrome.py');s=p.read_text();s+='''\n\ndef heading(screen,rect,text,assets,font):
    """Use the editor's raised section artwork and native heading font everywhere."""
    assets.drawButton(screen,pygame.Rect(rect),text,font,False,False,letterSpacing=1)
''';p.write_text(s)
p=Path('Code/ui/library.py');s=p.read_text().replace("        screen.blit(app.font.render('Library',True,TEXT),(x+22,y+18))", "        from ui.chrome import heading\n        heading(screen,(x+14,y+12,w-76,34),'Library',assets,app.sectionFont)")
s=s.replace('yy+=260','yy+=260')
p.write_text(s)
p=Path('Code/ui/help.py');s=p.read_text().replace("    screen.blit(app.font.render('Help / Shortcuts',True,TEXT),(box.x+20,box.y+18))", "    from ui.chrome import heading\n    heading(screen,(box.x+14,box.y+12,box.width-76,34),'Help / Shortcuts',app.assetManager,app.sectionFont)")
p.write_text(s)
p=Path('Code/blocFantome.py');s=p.read_text(encoding='utf-8');a=s.index('        # Title\n',s.index('    def _renderSettingsMenu'));b=s.index('        mousePos =',a)
s=s[:a]+'''        from ui.chrome import heading
        heading(self.screen,(menuX+14,menuY+12,menuWidth-68,34),'Settings',self.assetManager,self.sectionFont)

'''+s[b:];p.write_text(s,encoding='utf-8')
p=Path('Code/ui/redstone_lab.py');s=p.read_text();a=s.index('def header(app):');b=s.index('def cursor(app):',a)
s=s[:a]+'''def header(app):
    # Keep the existing workbench in one panel while its behavior is deferred.
    return


'''+s[b:]
s=s.replace("    label(app,'REDSTONE LAB',(x+14,16),TEXT,app.smallFont)","    from ui.chrome import heading\n    heading(app.screen,(x+8,8,w-16,32),'Redstone Lab',app.assetManager,app.sectionFont)")
p.write_text(s)
