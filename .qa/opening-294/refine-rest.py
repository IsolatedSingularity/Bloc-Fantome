from pathlib import Path
p=Path('Code/blocFantome.py');s=p.read_text(encoding='utf-8');s=s.replace('            if self.openingScene is not None:',"            if getattr(self, 'openingScene', None) is not None:",1)
s=s.replace('width, height = 460, 572','width, height = 460, 608')
s=s.replace('            self._openOpeningScene()\n\n    def _settingsMenuRect', '''            self._openOpeningScene()
        elif pygame.Rect(sliderX,y+36,sliderWidth,30).collidepoint(mouseX,mouseY):
            from ui.opening_scene import save_skip, skip_on_launch
            try:
                save_skip(not skip_on_launch())
                self.assetManager.playClickSound()
            except OSError as exc:
                self.tooltipText = f"Could not save opening preference: {exc}"
                self.tooltipTimer = 4000

    def _settingsMenuRect''')
s=s.replace("            self.smallFont,openingRect.collidepoint(mousePos),False)\n", """            self.smallFont,openingRect.collidepoint(mousePos),False)
        from ui.opening_scene import skip_on_launch
        skip=skip_on_launch()
        skipRect=pygame.Rect(sliderX,y+36,sliderWidth,30)
        self.assetManager.drawButton(self.screen,skipRect,
            f"Skip opening on launch: {'ON' if skip else 'OFF'}",
            self.smallFont,skipRect.collidepoint(mousePos),skip)
""")
p.write_text(s,encoding='utf-8')
p=Path('tests/test_opening_scene.py');s=p.read_text(encoding='utf-8').replace('assert pygame.Rect((0,0),size).contains(scene.skip_rect)','assert all(pygame.Rect((0,0),size).contains(rect) for rect in scene.turn_rects)')
s=s.replace('        scene=OpeningScene((1200,800),app.assetManager)\n        scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=scene.skip_rect.center))','        app.settingsMenuOpen=True\n        panel=app._settingsMenuRect()\n        app._handleSettingsClick(panel.centerx,panel.y+242+8*36+15)\n        app.settingsMenuOpen=False')
s+='''\n\ndef test_rotation_hint_runs_once_and_hover_uses_visible_ghost(app):
    scene=OpeningScene((1200,800),app.assetManager)
    scene.update(scene.READY_AT)
    x,y=scene.renderer.worldToScreen(*scene.TARGET)
    scene.handle_event(pygame.event.Event(pygame.MOUSEMOTION,pos=(x,y+20)))
    assert scene.ghost_hit(scene.pointer)
    assert not scene.ghost_hit((x-32,y))
    scene.place()
    scene.update(6.3)
    assert scene.renderer.viewRotation==1
    scene.update(10)
    assert scene.renderer.viewRotation==1
    scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=scene.turn_rects[0].center))
    assert scene.renderer.viewRotation==0
'''
p.write_text(s,encoding='utf-8')

