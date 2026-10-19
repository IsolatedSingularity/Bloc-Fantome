from pathlib import Path
p=Path('Code/ui/opening_scene.py')
s=p.read_text()
s=s.replace('TARGET = (0, 2, 2)','TARGET = (0, 3, 2)')
s=s.replace("        self.error = ''","        self.pointer = (-1, -1)\n        self.last_turn = (-1.0, 0)\n        self.demonstrated = False",1)
a=s.index('                rim =');b=s.index('        self.resize(size)',a)
s=s[:a]+'''                self.floor.append((x,y,-1,B.POLISHED_ANDESITE,'base'))
                material = B.SMOOTH_QUARTZ if (x+y)%2 else B.SMOOTH_STONE
                self.floor.append((x,y,0,material,'light' if (x+y)%2 else 'dark'))
        # A processional stair leads to an open lantern shrine. The two split
        # porticoes settle onto their plinths to frame the light over the landing.
        self.pedestals = [(x,y,z,B.QUARTZ_BRICKS,'stone')
                          for x in (-2,2) for y in (-2,-1) for z in (1,2)]
        self.pedestals += [(x,y,z,B.SMOOTH_QUARTZ,'stone')
                           for y,height in ((2,1),(1,2),(0,3),(-1,3),(-2,3))
                           for x in (-1,0,1) for z in range(1,height+1)]
        self.pedestals += [(0,3,1,B.CHISELED_QUARTZ,'stone')]
        left = [(x,y,z,B.QUARTZ_PILLAR,'stone')
                for x in (-3,) for y in (-2,-1) for z in range(2,5)]
        left += [(x,y,5,B.SMOOTH_QUARTZ,'stone') for x in (-3,-2,-1) for y in (-2,-1)]
        right = [(x,y,z,B.QUARTZ_PILLAR,'stone')
                 for x in (3,) for y in (-2,-1) for z in range(2,5)]
        right += [(x,y,5,B.SMOOTH_QUARTZ,'stone') for x in (2,3) for y in (-2,-1)]
        self.sections = (tuple(left), tuple(right))
        self.vein = [(0,-1,11,B.GLOWSTONE,'glow'), (0,-1,12,B.GLOWSTONE,'glow'),
                     (-1,-1,13,B.GLOWSTONE,'glow'), (0,-1,13,B.GLOWSTONE,'glow'),
                     (0,-2,13,B.GLOWSTONE,'glow'), (1,-2,14,B.GLOWSTONE,'glow'),
                     (0,-2,14,B.GLOWSTONE,'glow'), (-1,-2,14,B.GLOWSTONE,'glow')]
''' + s[b:]
s=s.replace('(0,0,3,B.GLOWSTONE', '(0,-2,4,B.GLOWSTONE')
s=s.replace('self.close_rect = pygame.Rect(w-122,20,100,30)\n        self.skip_rect = pygame.Rect(24,h-38,180,22)\n        self.replay_rect = pygame.Rect(w-122,h-42,100,28)', 'self.close_rect = pygame.Rect(w-56,20,36,36)\n        self.turn_rects = (pygame.Rect(w//2-58,h-72,44,40),\n                           pygame.Rect(w//2+14,h-72,44,40))')
s=s.replace('        self.elapsed += max(0.0, seconds)', '''        self.elapsed += max(0.0, seconds)
        # One quiet demonstration pairs the depressed E key with its actual turn.
        if self.complete and not self.demonstrated and self.elapsed-self.placed_at>=6.2:
            self.turn(1)

    def turn(self, direction):
        self.renderer.rotateView(direction)
        self.last_turn = (self.elapsed, direction)
        self.demonstrated = True

    def ghost_hit(self, pos):
        if not self.ready:
            return False
        sprite=self._sprite(B.CHISELED_QUARTZ,'stone')
        x,y=self.renderer.worldToScreen(*self.TARGET)
        local=(int(pos[0]-(x-sprite.get_width()//2)),int(pos[1]-y))
        return (0<=local[0]<sprite.get_width() and 0<=local[1]<sprite.get_height()
                and sprite.get_at(local).a>32)''')
s=s.replace('        if event.type==pygame.KEYDOWN:', '''        if hasattr(event,'pos'):
            self.pointer=event.pos
        if event.type==pygame.KEYDOWN:''')
s=s.replace('self.renderer.rotateView(-1 if event.key==pygame.K_q else 1)','self.turn(-1 if event.key==pygame.K_q else 1)')
a=s.index('        elif self.skip_rect');b=s.index('    def _sprite',a)
s=s[:a]+'''        elif self.complete:
            for rect,direction in zip(self.turn_rects,(-1,1)):
                if rect.collidepoint(event.pos):
                    self.turn(direction)
                    break
        elif self.ghost_hit(event.pos):
            self.place()

'''+s[b:]
s=s.replace("'rim':(126,143,154),",'')
s=s.replace('worldToScreen(0,-1,8.5)','worldToScreen(0,-1,11.5)')
s=s.replace('sprite.set_alpha(round(80+35*math.sin(self.elapsed*2)))','sprite.set_alpha(210 if self.ghost_hit(self.pointer) else round(80+35*math.sin(self.elapsed*2)))')
s=s.replace('pygame.draw.lines(self.geometry,(199,219,214),True,points,1)', 'pygame.draw.lines(self.geometry,(247,239,194) if self.ghost_hit(self.pointer) else (199,219,214),\n                                      True,points,2 if self.ghost_hit(self.pointer) else 1)')
s=s.replace('worldToScreen(0,0,3)','worldToScreen(0,-2,4)')
a=s.index('        if self.ready:\n            caption=')
s=s[:a]+'''        # Only tactile controls remain in the scene. Preferences live in Settings.
        hovered=self.close_rect.collidepoint(self.pointer)
        color=(237,236,220) if hovered else (123,145,155)
        cx,cy=self.close_rect.center
        pygame.draw.line(screen,color,(cx-5,cy-5),(cx+5,cy+5),2)
        pygame.draw.line(screen,color,(cx+5,cy-5),(cx-5,cy+5),2)
        if self.complete:
            since=self.elapsed-self.placed_at
            for rect,label,direction in zip(self.turn_rects,('Q','E'),(-1,1)):
                pressed=(self.last_turn[1]==direction and self.elapsed-self.last_turn[0]<.3)
                if direction==1 and not self.demonstrated and 5.95<=since<6.2:
                    pressed=True
                face=rect.move(0,3 if pressed else 0)
                hover=rect.collidepoint(self.pointer)
                pygame.draw.rect(screen,(26,38,48),rect.move(0,4),border_radius=5)
                pygame.draw.rect(screen,(77,94,101) if hover or pressed else (47,63,73),face,border_radius=5)
                pygame.draw.rect(screen,(142,161,164) if hover else (91,113,124),face,1,border_radius=5)
                text=self.font.render(label,True,(230,234,225))
                screen.blit(text,text.get_rect(center=face.center))
                # Small curved arrow above each key conveys direction without prose.
                arrow=pygame.Rect(rect.centerx-10,rect.y-20,20,13)
                pygame.draw.arc(screen,(142,161,164),arrow,.15,math.pi-.15,1)
                tip=(arrow.left,arrow.centery) if direction<0 else (arrow.right-1,arrow.centery)
                pygame.draw.polygon(screen,(142,161,164),[tip,(tip[0]-3,tip[1]-4),(tip[0]+3,tip[1]-4)])
'''
p.write_text(s)
p=Path('Code/blocFantome.py');s=p.read_text();s=s.replace('            if self.openingScene is not None:',"            if getattr(self, 'openingScene', None) is not None:",1)
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
p.write_text(s)
p=Path('tests/test_opening_scene.py');s=p.read_text().replace('assert pygame.Rect((0,0),size).contains(scene.skip_rect)','assert all(pygame.Rect((0,0),size).contains(rect) for rect in scene.turn_rects)')
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
p.write_text(s)
