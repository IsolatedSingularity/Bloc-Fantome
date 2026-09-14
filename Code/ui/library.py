"""One content library with explicit scene-opening and structure-placement actions."""
import pygame
from ui.chrome import panel, wrapped, TEXT, MUTED, ACCENT
from ui.fonts import load_ui_font


class Library:
    TABS = ('Worlds', 'Biomes', 'Structures', 'Saved Builds')

    def __init__(self):
        self.visible = False
        self.tab = 'Worlds'
        self.dimension = 'overworld'
        self.scroll = 0
        self.pending = None
        self.rows = []
        self.tab_rects = {}
        self.dimension_rects = {}
        self.rect = self.list_rect = self.close_rect = self.open_rect = self.browse_rect = pygame.Rect(0, 0, 0, 0)
        self.font = load_ui_font(18)
        self.small = load_ui_font(15)
        self.entries = []
        self.max_scroll = 0

    def open(self, app, tab='Worlds'):
        self.visible = True
        self.tab = tab
        self.dimension = app.currentDimension
        self.refresh(app)

    def refresh(self, app):
        from engine.world_catalog import world_catalog
        from engine.build_catalog import build_catalog
        from runtime_paths import WORLDS_DIR, SAVES_DIR, BUILTIN_STRUCTURES_DIR
        self.scroll = 0
        self.pending = None
        if self.tab == 'Biomes':
            self.entries = [dict(key=e['id'], name=e['id'].replace('_', ' ').title(),
                detail='A captured Minecraft landscape. Open it to explore, rotate and build.',
                kind='biome', value=e) for e in app.biomePanel.entries(self.dimension)]
        elif self.tab == 'Worlds':
            self.entries = [dict(key=e.key if hasattr(e, 'key') else e.filename, name=e.name,
                detail=e.subtitle+'\n'+e.description, kind='world', value=e)
                for e in world_catalog(WORLDS_DIR)
                if e.category == {'overworld':'Overworld','nether':'Nether','end':'The End'}[self.dimension]]
        else:
            builds = build_catalog(SAVES_DIR, BUILTIN_STRUCTURES_DIR, app.tutorialScreen.TUTORIAL_STEPS)
            self.entries = [dict(key=e.key, name=e.label, detail=e.category,
                kind='build', value=e) for e in builds if self.tab == 'Saved Builds' and e.kind == 'file']
            if self.tab == 'Structures':
                self.entries = [dict(key=k, name=v['name'], detail='Place this structure in your current build.',
                    kind='structure', value=k) for k,v in app.structureDefinitions.items()] + self.entries

    def activate(self, app):
        entry = self.pending
        if entry is None: return
        self.visible = False
        kind, value = entry['kind'], entry['value']
        if kind == 'biome': app._queueBiomeScene(value['id'])
        elif kind == 'world': app._handleWorldLibraryAction(('open', value))
        elif kind == 'structure':
            app.structurePlacementMode = True
            app.selectedStructure = value
            app.tooltipText = entry['name']+' | Click to place; Esc cancels'
            app.tooltipTimer = 4000
        else: app._handleBuildLibraryAction(('open', value))

    def handle_event(self, event, app):
        if not self.visible: return False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE: self.visible = False
            elif event.key == pygame.K_RETURN and self.pending:
                app.assetManager.playClickSound(); self.activate(app)
            elif event.key in (pygame.K_UP, pygame.K_DOWN) and self.entries:
                index = self.entries.index(self.pending) if self.pending in self.entries else -1
                index = max(0, min(len(self.entries)-1, index+(-1 if event.key==pygame.K_UP else 1)))
                self.pending = self.entries[index]
                self.scroll = max(0, min(self.scroll, index*92))
                self.scroll = max(self.scroll, (index+1)*92-self.list_rect.height+8)
            return True
        if event.type == pygame.MOUSEWHEEL:
            self.scroll = max(0, min(self.max_scroll, self.scroll-event.y*92))
            return True
        if event.type != pygame.MOUSEBUTTONDOWN: return event.type in (pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION)
        if event.button != 1: return True
        acted = True
        if self.close_rect.collidepoint(event.pos): self.visible = False
        elif self.open_rect.collidepoint(event.pos) and self.pending: self.activate(app)
        elif self.browse_rect.collidepoint(event.pos):
            self.visible = False
            if self.tab == 'Worlds': app._openJavaWorldDialog()
            else: app._openNativeLoadDialog()
        else:
            acted = False
            for tab, rect in self.tab_rects.items():
                if rect.collidepoint(event.pos):
                    self.tab = tab; self.refresh(app); acted = True; break
            for dim, rect in self.dimension_rects.items():
                if rect.collidepoint(event.pos):
                    self.dimension = dim; self.refresh(app); acted = True; break
            if self.list_rect.collidepoint(event.pos):
                for rect, entry in self.rows:
                    if rect.collidepoint(event.pos): self.pending = entry; acted = True; break
        if acted: app.assetManager.playClickSound()
        return True

    def render(self, app):
        if not self.visible: return
        screen, assets = app.screen, app.assetManager
        mouse = pygame.mouse.get_pos()
        shade = pygame.Surface(screen.get_size(), pygame.SRCALPHA); shade.fill((0,0,0,175)); screen.blit(shade,(0,0))
        self.rect = pygame.Rect(0,0,min(900,screen.get_width()-40),min(680,screen.get_height()-40))
        self.rect.center = screen.get_rect().center
        panel(screen,self.rect,assets)
        x,y,w,h = self.rect
        from ui.chrome import heading
        heading(screen,(x+14,y+12,w-76,34),'Library',assets,app.sectionFont)
        self.close_rect=pygame.Rect(self.rect.right-48,y+14,30,30)
        assets.drawButton(screen,self.close_rect,'X',self.small,self.close_rect.collidepoint(mouse))
        self.tab_rects={}
        tw=(w-44)//4
        for i,tab in enumerate(self.TABS):
            rect=pygame.Rect(x+22+i*tw,y+58,tw-5,34);self.tab_rects[tab]=rect
            assets.drawButton(screen,rect,tab,self.font,rect.collidepoint(mouse),self.tab==tab)
        self.dimension_rects={}
        if self.tab in ('Worlds','Biomes'):
            for i,(dim,label) in enumerate((('overworld','Overworld'),('nether','Nether'),('end','The End'))):
                rect=pygame.Rect(x+22+i*140,y+102,134,30);self.dimension_rects[dim]=rect
                assets.drawButton(screen,rect,label,self.small,rect.collidepoint(mouse),dim==self.dimension)
        else:
            screen.blit(self.small.render('Choose an item, then use the action below.',True,MUTED),(x+22,y+109))
        self.list_rect=pygame.Rect(x+22,y+144,(w-60)//2,h-216)
        pygame.draw.rect(screen,(22,22,22),self.list_rect)
        pygame.draw.rect(screen,(100,100,100),self.list_rect,2)
        self.max_scroll=max(0,len(self.entries)*92-self.list_rect.height+12)
        self.scroll=min(self.scroll,self.max_scroll)
        old_clip=screen.get_clip();screen.set_clip(self.list_rect.inflate(-6,-6))
        self.rows=[]
        for i,entry in enumerate(self.entries):
            rect=pygame.Rect(self.list_rect.x+8,self.list_rect.y+8+i*92-self.scroll,self.list_rect.width-16,86)
            if not rect.colliderect(screen.get_clip()):continue
            self.rows.append((rect.clip(screen.get_clip()),entry))
            assets.drawButton(screen,rect,'',self.small,rect.collidepoint(mouse),entry==self.pending)
            preview=app.previewImages.get(app,entry,(100,70))
            if preview:screen.blit(preview,(rect.x+5,rect.y+7))
            wrapped(screen,entry['name'],self.small,(rect.x+114,rect.y+12,rect.width-124,rect.height-20))
        screen.set_clip(old_clip)
        if not self.entries:wrapped(screen,'No items here yet. Save a build or browse files.',self.font,self.list_rect.inflate(-24,-24),MUTED)
        if self.max_scroll:
            track=self.list_rect.inflate(-2,-4);thumb=max(22,int(track.height*self.list_rect.height/(len(self.entries)*92+12)))
            pygame.draw.rect(screen,(175,175,175),(track.right-4,track.y+int((track.height-thumb)*self.scroll/self.max_scroll),3,thumb))
        detail=pygame.Rect(self.list_rect.right+20,self.list_rect.y,w-self.list_rect.width-64,self.list_rect.height)
        entry=self.pending
        if entry:
            yy=wrapped(screen,entry['name'],app.font,detail)
            warning_height=58 if entry['kind'] in ('biome','world') else 0
            preview_height=max(90,min(240,detail.height-175))
            preview=app.previewImages.get(app,entry,(detail.width,preview_height))
            if preview:
                screen.blit(preview,(detail.x,yy+10));yy+=preview_height+16
            description_bottom=detail.bottom-warning_height-8
            wrapped(screen,entry['detail'],self.small,(detail.x,yy+8,detail.width,max(0,description_bottom-yy-8)),MUTED)
            if warning_height:
                wrapped(screen,'Opening replaces the canvas. Save your current build first.',self.small,(detail.x,detail.bottom-warning_height,detail.width,warning_height),ACCENT)
        else:wrapped(screen,'Select an item to see its details.',self.font,detail,MUTED)
        self.browse_rect=pygame.Rect(x+22,self.rect.bottom-54,210,32) if self.tab in ('Worlds','Saved Builds') else pygame.Rect(0,0,0,0)
        if self.browse_rect.width:assets.drawButton(screen,self.browse_rect,'Import Java World...' if self.tab=='Worlds' else 'Browse Files...',self.small,self.browse_rect.collidepoint(mouse))
        self.open_rect=pygame.Rect(self.rect.right-252,self.rect.bottom-54,230,32)
        label='Select an item'
        if entry:label='Place structure' if entry['kind']=='structure' else 'Open scene' if entry['kind'] in ('world','biome') else 'Start lesson' if entry['value'].kind=='tutorial' else 'Open build'
        assets.drawButton(screen,self.open_rect,label,self.font,bool(entry) and self.open_rect.collidepoint(mouse),bool(entry))
