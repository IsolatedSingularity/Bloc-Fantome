from pathlib import Path
p=Path('Code/blocFantome.py');s=p.read_text(encoding='utf-8')
def replace(a,b):
    global s
    assert a in s,a[:100]
    s=s.replace(a,b)
def section(a,b,new):
    global s
    start=s.rindex(a) if a.startswith('        # ===== VIEW INDICATOR') else s.index(a)
    end=s.index(b,start);s=s[:start]+new+s[end:]
replace('APP_VERSION = "2.8.1"','APP_VERSION = "2.9.0"')
replace('scaledBtn = pygame.transform.scale(texture, (rect.width, rect.height))','from ui.chrome import button_surface\n                scaledBtn = button_surface(texture, rect.size)')
replace('        self.biomePanel = BiomePanel()','        self.biomePanel = BiomePanel()\n        from ui.library import Library\n        self.library = Library()\n        self.pendingBiomeLoad = None\n        self.helpButtonRect = pygame.Rect(0,0,0,0)')
replace('            if self.worldLibrary.visible:','            if self.library.handle_event(event, self):\n                continue\n            if self.pendingBiomeLoad is not None and event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEWHEEL):\n                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:\n                    self.pendingBiomeLoad[0].cancel()\n                    self.pendingBiomeLoad = None\n                continue\n            if self.worldLibrary.visible:')
replace('        self._pollWorldLoad()','        self._pollWorldLoad()\n        self._pollBiomeLoad()\n        self.assetManager.audioRouter.set_group_volume("ui", 0 if self.effectsMuted else self.effectsVolume)')
replace('        self.buildLibrary.open(entries)','        self.library.open(self, "Saved Builds")')
replace('        self.worldLibrary.open(world_catalog(WORLDS_DIR))','        self.library.open(self, "Worlds")')
replace('        self.worldLibrary.render(self.screen)','        self.worldLibrary.render(self.screen)\n        self.library.render(self)')
replace('            self.assetManager.playClickSound()\n            self.assetManager.playClickSound()','            self.assetManager.playClickSound()')
replace('"Advanced Tutorial", True','"Tutorial", True')
# Merge the three content launchers and their duplicated click layout.
section('        # ===== CHECK WORLDS MAIN BUTTON =====','        # ===== CHECK BUILD FILE BUTTONS', '''        if currentY <= panelY <= currentY + mainButtonHeight and ICON_MARGIN <= panelX <= PANEL_WIDTH - ICON_MARGIN:
            self._openWorldLibrary()
            self.assetManager.playClickSound()
            return
        if self.helpButtonRect.collidepoint(mouseX, mouseY):
            self.showShortcutsPanel = True
            self.assetManager.playClickSound()
            return
        if self.rotLeftBtnRect and self.rotLeftBtnRect.collidepoint(mouseX, mouseY):
            self._rotateViewAndRecenter(-1)
            return
        if self.rotRightBtnRect and self.rotRightBtnRect.collidepoint(mouseX, mouseY):
            self._rotateViewAndRecenter(1)
            return

''')
section('        # ===== WORLDS MAIN BUTTON =====','        # ===== SEPARATOR LINE =====', '''        libraryRect = pygame.Rect(panelX + ICON_MARGIN, currentY, PANEL_WIDTH - 2 * ICON_MARGIN, mainButtonHeight)
        for focus in ('worlds', 'structures', 'biomes'):
            self.lessonControlRects[focus] = libraryRect
        self.biomePanel.header = libraryRect
        self.assetManager.drawButton(self.screen, libraryRect, "Library", self.font,
            libraryRect.collidepoint(mouseX, mouseY), self.library.visible, letterSpacing=1)
        currentY += mainButtonHeight + 5

''')
section('        # Worlds opens a modal and has no inline content.','        # Available height for scrollable area', '''        # One Library entry and compact save/camera/help controls.
        totalHeight += mainButtonHeight + 180

''')
section('        # ===== VIEW INDICATOR (no buttons - use Q/E hotkeys) =====','        # Reset clipping', '''        self.rotLeftBtnRect = pygame.Rect(panelX+18,currentY,42,30)
        self.rotRightBtnRect = pygame.Rect(panelX+PANEL_WIDTH-60,currentY,42,30)
        for rect,label in ((self.rotLeftBtnRect,'Q'),(self.rotRightBtnRect,'E')):
            self.assetManager.drawButton(self.screen,rect,label,self.smallFont,rect.collidepoint((mouseX,mouseY)))
        label = self.smallFont.render('Rotate view',True,(210,210,200))
        self.screen.blit(label,label.get_rect(center=(panelX+PANEL_WIDTH//2,currentY+15)))
        currentY += 42
        self.helpButtonRect = pygame.Rect(panelX+18,currentY,PANEL_WIDTH-36,30)
        self.assetManager.drawButton(self.screen,self.helpButtonRect,'Help / Shortcuts',self.smallFont,self.helpButtonRect.collidepoint((mouseX,mouseY)))
        self.volumeControlRects.clear()
        self.hotkeysExpandBtnRect = None

''')
replace('self.screen, experimentalRect, "Toggles"','self.screen, experimentalRect, "World Controls"') if 'self.screen, experimentalRect, "Toggles"' in s else None
# Capture preparation is pure data work; apply it atomically on the main thread.
replace('    def _openBiomeScene(self, biome_id):\n        """Open the exact previewed diorama as ordinary editable blocks."""','    def _stageBiomeScene(self, biome_id):\n        """Prepare captured cells without touching the live editor or SDL."""')
replace("        self._applyStagedBuild(data['dimension'],(width,depth,height,0),metadata,snapshot,None,silent=True)",'''        return snapshot, metadata

    def _queueBiomeScene(self, biome_id):
        if self.pendingBiomeLoad is not None or self.pendingWorldLoad is not None:
            return
        self.pendingBiomeLoad = (self.worldLoadExecutor.submit(self._stageBiomeScene, biome_id), biome_id)

    def _pollBiomeLoad(self):
        if self.pendingBiomeLoad is None or not self.pendingBiomeLoad[0].done():
            return
        future, name = self.pendingBiomeLoad
        self.pendingBiomeLoad = None
        try:
            self._applyBiomeScene(*future.result())
        except Exception as error:
            self.tooltipText = f"Could not open biome: {error}"
            self.tooltipTimer = 5000

    def _openBiomeScene(self, biome_id):
        self._applyBiomeScene(*self._stageBiomeScene(biome_id))

    def _applyBiomeScene(self, snapshot, metadata):
        self.searchActive = False
        self.searchQuery = ''
        self.searchResults = []
        self.biomePanel.expanded = False
        self.buildLibrary.close()
        self.worldLibrary.close()
        self.library.visible = False
        self._applyStagedBuild(snapshot.dimension,(snapshot.width,snapshot.depth,snapshot.height,0),metadata,snapshot,None,silent=True)''')
replace('if self.sceneMetadata.get("kind") == "world":','if self.sceneMetadata.get("kind") in ("world", "biome"):')
# A settled vanilla capture must not spend every frame simulating thousands of water sources.
replace('        if self.pendingWorldLoad is None:\n            return\n        _future, entry, _path = self.pendingWorldLoad','''        if self.pendingBiomeLoad is not None:
            from ui.chrome import panel as draw_panel
            box = pygame.Rect(0,0,400,100)
            box.center = self.screen.get_rect().center
            draw_panel(self.screen,box,self.assetManager)
            text = self.smallFont.render('Preparing '+self.pendingBiomeLoad[1].replace('_',' ')+'...',True,(238,238,230))
            self.screen.blit(text,text.get_rect(center=(box.centerx,box.centery-12)))
            text = self.smallFont.render('Esc cancels; your build stays intact.',True,(190,190,180))
            self.screen.blit(text,text.get_rect(center=(box.centerx,box.centery+18)))
            return
        if self.pendingWorldLoad is None:
            return
        _future, entry, _path = self.pendingWorldLoad''')
# Shared Settings panel. Keep its tested geometry and native text.
section('        # Tiled dirt/stone menu background','        # Title\n', '''        from ui.chrome import panel as draw_panel
        draw_panel(self.screen, menuRect, self.assetManager)

''')
p.write_text(s,encoding='utf-8')
p=Path('Code/ui/library.py');s=p.read_text();s=s.replace('from domain.structures import PREMADE_STRUCTURES','from blocFantome import PREMADE_STRUCTURES');p.write_text(s)
p=Path('Code/installer.iss');s=p.read_text(encoding='utf-8').replace('MyAppVersion "2.8.1"','MyAppVersion "2.9.0"');p.write_text(s,encoding='utf-8')
