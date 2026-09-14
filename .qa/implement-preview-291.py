from pathlib import Path
p=Path('Code/blocFantome.py');s=p.read_text(encoding='utf-8')
s=s.replace('        self.library = Library()','        self.library = Library()\n        from ui.preview_browser import PreviewBrowser, PreviewImages\n        self.previewBrowser = PreviewBrowser()\n        self.previewImages = PreviewImages()')
s=s.replace('        totalHeight += mainButtonHeight + 180','        totalHeight += self.previewBrowser.height() + 180')
a=s.index('        libraryRect = pygame.Rect(',s.index('    def _renderPanel('));b=s.index('        # ===== SEPARATOR LINE',a)
s=s[:a]+'''        currentY = self.previewBrowser.render(self, panelX, currentY, PANEL_WIDTH)
        self.biomePanel.header = pygame.Rect(0, 0, 0, 0)

'''+s[b:]
a=s.index('        if currentY <= panelY <= currentY + mainButtonHeight',s.index('    def _handlePanelClick('));b=s.index('        if self.helpButtonRect',a)
s=s[:a]+'''        if self.previewBrowser.click(self, (mouseX, mouseY)):
            return
'''+s[b:]
s=s.replace('        self._renderStructureTooltip()','        self._renderStructureTooltip()\n        self.previewBrowser.render_hover(self)')
# Pending tutorial imports keep navigation visible, including during main-thread render preparation.
s=s.replace('        self._renderPanelBlockTooltip()','        self._renderPanelBlockTooltip()\n        if getattr(self, "_pendingTourLoad", None):\n            from ui.chrome import panel as chrome_panel\n            rect = pygame.Rect(self._worldViewportRight()//2-140, 50, 280, 36)\n            chrome_panel(self.screen, rect, self.assetManager)\n            self.screen.blit(self.smallFont.render("Preparing scene...", True, (238,238,230)), rect.move(14,8))')
p.write_text(s,encoding='utf-8')
p=Path('Code/ui/library.py');s=p.read_text()
s=s.replace("if self.tab == 'Saved Builds' or e.kind == 'tutorial'", "if self.tab == 'Saved Builds' and e.kind == 'file'")
s=s.replace('*58','*92').replace('* 58','* 92').replace(',52)',',86)')
s=s.replace("            wrapped(screen,entry['name'],self.font,rect.inflate(-16,-12))", "            preview=app.previewImages.get(app,entry,(100,70))\n            if preview:screen.blit(preview,(rect.x+5,rect.y+7))\n            wrapped(screen,entry['name'],self.small,(rect.x+114,rect.y+12,rect.width-124,rect.height-20))")
s=s.replace("            preview=None\n            if entry['kind']=='biome':preview=app.biomePanel.preview(entry['value'],assets,(detail.width,190))\n            elif entry['kind']=='structure':preview=app.structurePreviews.get(entry['value'])", "            preview=app.previewImages.get(app,entry,(detail.width,240))")
s=s.replace('190/preview.get_height()','240/preview.get_height()').replace('yy+=210','yy+=260')
p.write_text(s)
p=Path('Code/ui/preview_browser.py');s=p.read_text();s=s.replace("        source=None", "        source=self.images.get((entry['key'],(600,400)))")
s=s.replace("        if kind=='biome':", "        if source is not None:pass\n        elif kind=='biome':",1)
p.write_text(s)
