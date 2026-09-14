from pathlib import Path
p=Path('Code/ui/tutorial.py')
s=p.read_text(encoding='utf-8').replace('from engine.tutorial_lessons import GETTING_STARTED, HANDBOOK','from engine.tutorial_lessons import TOUR')
s=s.replace('TUTORIAL_STEPS = HANDBOOK','TUTORIAL_STEPS = TOUR').replace('self.TUTORIAL_STEPS=HANDBOOK if advanced else GETTING_STARTED','self.TUTORIAL_STEPS=TOUR')
s=s.replace('self.smallFont=load_ui_font(15)','self.smallFont=load_ui_font(18)').replace('self.panelWidth=368','self.panelWidth=380')
s=s.replace('self.menuOpen=self.advanced','self.menuOpen=False')
a=s.index('    def observe(self,app):');b=s.index('    def _updateHighlight',a)
s=s[:a]+'''    def observe(self,app):
        if not self.visible:return
        rotation=app.renderer.viewRotation
        if self.baseline is not None and rotation!=self.baseline and self.lesson.get('is_horror') and not self.anomalyShown:
            app._revealGuidedAnomaly()
            self.anomalyShown=True
        self.baseline=rotation
        self._updateHighlight(app)

'''+s[b:]
s=s.replace("        elif focus=='hotbar':", "        elif focus=='settings':\n            self.highlightRect=pygame.Rect(self.screenWidth-40,self.screenHeight-42,36,36)\n        elif focus=='hotbar':")
s=s.replace("            if self.menuOpen and not getattr(self,'lessonStarted',False): self.selectLesson(self.currentStep)\n            else: self.menuOpen=not self.menuOpen", "            self.selectLesson(0)")
s=s.replace("        elif self.advanced: self.menuOpen=True\n        else: self.hide()", "        else: self.hide()")
a=s.index('    def _button(');b=s.index('    def render(',a)
s=s[:a]+'''    def _button(self,screen,rect,label,active=False):
        hover=rect.collidepoint(pygame.mouse.get_pos())
        if self.assetManager:
            self.assetManager.drawButton(screen,rect,label,self.smallFont,hover,active)
        else:
            pygame.draw.rect(screen,(58,57,63) if not hover else (83,80,90),rect)
            pygame.draw.rect(screen,(164,145,111),rect,1)
            text=self.smallFont.render(label,True,(236,226,204))
            screen.blit(text,text.get_rect(center=rect.center))

'''+s[b:]
s=s.replace("        pygame.draw.rect(screen,(19,21,20) if not horror else (22,14,27),panel,border_radius=6)\n        pygame.draw.rect(screen,(112,133,106) if not horror else (112,64,101),panel,2,border_radius=6)","""        pygame.draw.rect(screen,(24,23,29) if not horror else (24,13,30),panel,border_radius=3)
        # Engraved frame and corner fittings match the game's stone controls.
        pygame.draw.rect(screen,(147,126,93) if not horror else (134,80,123),panel,2,border_radius=3)
        pygame.draw.rect(screen,(67,59,53),panel.inflate(-10,-10),1)
        for px,py,sx,sy in ((x,y,1,1),(panel.right,y,-1,1),(x,panel.bottom,1,-1),(panel.right,panel.bottom,-1,-1)):
            pygame.draw.lines(screen,(202,174,119),False,[(px+sx*4,py+sy*22),(px+sx*4,py+sy*4),(px+sx*22,py+sy*4)],3)
        for i in range(1,5):
            pygame.draw.line(screen,(31,28,34),(x+10,y+46+i*70),(panel.right-10,y+46+i*70))""")
s=s.replace("label='BUILDER’S HANDBOOK' if self.advanced else 'GETTING STARTED'","label=f'FIELD GUIDE   /   {self.currentStep+1:02d} — {len(self.TUTORIAL_STEPS):02d}'")
a=s.index('            cy+=14\n            for key,amount,label');b=s.index('            if self.hintVisible:',a)
s=s[:a]+'''            cy+=20
            cy=self._text(screen,'AT YOUR OWN PACE',cx,cy,content_width,(201,175,124),self.smallFont)+8
'''+s[b:]
a=s.index('            if self.complete():');b=s.index('            if horror:',a)
s=s[:a]+s[b:]
s=s.replace("            if self.counts['rotate']:","            if self.anomalyShown:")
s=s.replace("'Lessons' if not self.menuOpen else 'Return'","'Restart'").replace("'Retry')","'Reset view')")
a=s.index("        next_label='Next page'");b=s.index("        self._button(screen,self.skipButtonRect",a)
s=s[:a]+'''        next_label='Finish' if self.currentStep==len(self.TUTORIAL_STEPS)-1 else 'Next'
        self._button(screen,self.nextButtonRect,next_label,True)
'''+s[b:]
s=s.replace('Show Getting Started on launch','Show tour on launch')
p.write_text(s,encoding='utf-8')
p=Path('Code/engine/tutorial_runtime.py');s=p.read_text();s=s.replace("continuing=(not tutorial.advanced and self.sceneMetadata.get('guided_course')=='starter')","continuing=False  # Every tour page replaces its example, including Back and direct jumps.")
s=s.replace("self.skyboxesEnabled=self.cloudsEnabled=self.celestialEnabled=False","self.skyboxesEnabled=step['id'] in ('welcome','skies','dimensions','farewell')\n            self.cloudsEnabled=self.celestialEnabled=False")
s=s.replace("        tutorial.observe(self)","""        self.blocksExpanded=step.get('focus')=='blocks'
        self.experimentalExpanded=step.get('focus')=='toggles'
        self.structuresExpanded=step.get('focus')=='structures'
        self.biomePanel.expanded=step.get('focus')=='biomes'
        self.panelScrollOffset=0
        tutorial.observe(self)""")
p.write_text(s)
p=Path('Code/engine/tutorial_lessons.py');s=p.read_text().replace("is_horror=key=='uninvited'","is_horror=scene=='uninvited'");p.write_text(s)
