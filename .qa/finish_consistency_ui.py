from pathlib import Path
p=Path('Code/blocFantome.py');s=p.read_text(encoding='utf-8')
def r(a,b):
    global s
    assert a in s,a[:90];s=s.replace(a,b)
def sec(a,b,new):
    global s
    start=s.index(a);end=s.index(b,start);s=s[:start]+new+s[end:]
sec('    def _renderShortcutsPanel(self) -> None:', '    def _toggleCelestial(self):', '''    def _renderShortcutsPanel(self) -> None:
        from ui.help import render
        render(self)

''')
r('            # Let tutorial handle events first if visible','''            if self.showShortcutsPanel:
                if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_SLASH):
                    self.showShortcutsPanel = False
                elif event.type == pygame.MOUSEBUTTONDOWN and getattr(self,'helpCloseRect',pygame.Rect(0,0,0,0)).collidepoint(event.pos):
                    self.showShortcutsPanel = False
                    self.assetManager.playClickSound()
                if event.type in (pygame.KEYDOWN,pygame.MOUSEBUTTONDOWN,pygame.MOUSEBUTTONUP,pygame.MOUSEWHEEL):continue
            if self.settingsMenuOpen:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE or (event.key == pygame.K_COMMA and pygame.key.get_mods() & pygame.KMOD_CTRL):self.settingsMenuOpen = False
                    continue
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:self._handleSettingsClick(*event.pos)
                    continue
                if event.type == pygame.MOUSEWHEEL:continue
            # Let tutorial handle events first if visible''')
r('        self.library.render(self)','        self._renderShortcutsPanel()\n        self.library.render(self)')
r('        self.screen, experimentalRect, "World Controls", self.font,','        self.screen, experimentalRect, "World Controls", self.smallFont,')
sec('        # Volume sliders - match render layout','        # Full-width Minecraft buttons', '''        for volumeType, control in self.volumeControlRects.items():
            if control['mute'].collidepoint(mouseX, mouseY):
                setattr(self,volumeType+'Muted',not getattr(self,volumeType+'Muted'))
                self._setVolume(volumeType,getattr(self,volumeType+'Volume'))
                self.assetManager.playClickSound()
                return
            if control['track'].inflate(0,12).collidepoint(mouseX,mouseY):
                self.draggingSlider=volumeType
                self._setVolume(volumeType,(mouseX-control['track'].left)/control['track'].width)
                return
        sliderX = menuX + 28
        sliderWidth = menuWidth - 56

''')
r('        valueText = self.smallFont.render(f"{int(value * 100)}%", True, (220, 220, 220))\n        self.screen.blit(valueText, valueText.get_rect(topright=(x + width, y)))','''        volumeType = label.split()[0].lower()
        muted = getattr(self,volumeType+'Muted',False)
        mute = pygame.Rect(x+width-30,y,30,26)
        self.assetManager.drawButton(self.screen,mute,'M' if muted else '♪',self.smallFont,mute.collidepoint(pygame.mouse.get_pos()),muted)
        valueText = self.smallFont.render('Muted' if muted else f"{int(value * 100)}%", True, (220, 220, 220))
        self.screen.blit(valueText, valueText.get_rect(topright=(mute.left-10, y)))
        width -= 42''')
r('        track = pygame.Rect(x, y + 22, width, 12)','        track = pygame.Rect(x, y + 22, width, 12)\n        self.volumeControlRects[volumeType] = {"track":track,"mute":mute}')
r('        handleX = track.x + int(track.width * value)','        handleX = track.x + 5 + round((track.width-10) * value)')
r('            self.effectsVolume = value\n','            self.effectsVolume = value\n        self.assetManager.audioRouter.set_group_volume("ui",0 if self.effectsMuted else self.effectsVolume)\n        self.assetManager.audioRouter.set_group_volume("effects",0 if self.effectsMuted else 1.0)\n        for group in ("ambient","weather","portal"):\n            self.assetManager.audioRouter.set_group_volume(group,0 if self.ambientMuted else 1.0)\n')
r('        self.assetManager.audioRouter.set_group_volume("ui", 0 if self.effectsMuted else self.effectsVolume)','        self.assetManager.audioRouter.set_group_volume("ui", 0 if self.effectsMuted else self.effectsVolume)\n        self.assetManager.audioRouter.set_group_volume("effects",0 if self.effectsMuted else 1.0)')
# Click sound belongs to an action, never a blank sidebar hit.
r('                self._handlePanelClick(mouseX, mouseY)\n                self.assetManager.playClickSound()','                self._handlePanelClick(mouseX, mouseY)')
r('            self.blocksExpanded = not self.blocksExpanded\n            return','            self.blocksExpanded = not self.blocksExpanded\n            self.assetManager.playClickSound()\n            return')
r('            self.settingsMenuOpen = not self.settingsMenuOpen\n            return','            self.settingsMenuOpen = not self.settingsMenuOpen\n            self.assetManager.playClickSound()\n            return')
p.write_text(s,encoding='utf-8')
# Correct tutorial copy and routes to the unified library.
p=Path('Code/engine/tutorial_runtime.py');s=p.read_text(encoding='utf-8').replace("self.biomePanel.expanded=step.get('focus')=='biomes'","self.biomePanel.expanded=False")
p.write_text(s,encoding='utf-8')
p=Path('Code/engine/tutorial_lessons.py');s=p.read_text(encoding='utf-8').replace('Toggles','World Controls').replace('toggles menu','World Controls menu').replace('Use the sliders on the right.','Open Settings with the gear for volume sliders.').replace('Open Biomes','Open Library, then Biomes').replace('Open Worlds','Open Library, then Worlds');p.write_text(s,encoding='utf-8')
