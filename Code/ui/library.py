"""One content library with explicit scene-opening and structure-placement actions."""
import pygame
from ui.chrome import panel, wrapped, button, TEXT, MUTED, ACCENT
from ui.fonts import load_ui_font
from ui.scroll import SmoothScroll


class Library:
    TABS = ('Worlds', 'Biomes', 'Structures', 'Saved Builds')

    def __init__(self):
        self.visible = False
        self.tab = 'Worlds'
        self.dimension = 'overworld'
        self.scroll = 0
        self.scroller = SmoothScroll()
        self.pending = None
        self.rows = []
        self.tab_rects = {}
        self.dimension_rects = {}
        self.rect = self.list_rect = self.close_rect = self.open_rect = self.browse_rect = pygame.Rect(0, 0, 0, 0)
        self.font = load_ui_font(18)
        self.small = load_ui_font(15)
        self.entries = []
        self.max_scroll = 0
        self.row_height = 64

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
        self.scroller.reset()
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
                self.scroll = max(0, min(self.scroll, (index//getattr(self,'columns',2))*self.row_height))
                self.scroll = max(self.scroll, (index//getattr(self,'columns',2)+1)*self.row_height-self.list_rect.height+8)
                self.scroller.reset(self.scroll)
            return True
        if event.type == pygame.MOUSEWHEEL:
            if self.list_rect.collidepoint(pygame.mouse.get_pos()):self.scroller.wheel(event,self.max_scroll,100)
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
        if not self.visible:return
        screen=app.screen;mouse=pygame.mouse.get_pos()
        scale=getattr(getattr(app,'workshop',None),'text_scale',1)
        self.row_height=max(64,self.small.get_linesize()*2+16)
        shade=pygame.Surface(screen.get_size(),pygame.SRCALPHA);shade.fill((0,0,0,125));screen.blit(shade,(0,0))
        self.rect=pygame.Rect(0,0,min(round(960*scale),screen.get_width()-48),min(round(820*scale),screen.get_height()-48))
        self.rect.center=screen.get_rect().center;panel(screen,self.rect)
        x,y,w,h=self.rect;left=x+22;top=y+18
        screen.blit(app.sectionFont.render('Library',True,TEXT),(left,top))
        self.close_rect=pygame.Rect(self.rect.right-110,top,88,max(34,self.small.get_height()+6))
        button(screen,self.close_rect,'Close',self.small,self.close_rect.collidepoint(mouse),quiet=True)
        tab_height=max(34,self.font.get_height()+8);tw=(w-44)//4
        self.tab_rects={}
        for i,tab in enumerate(self.TABS):
            rect=pygame.Rect(left+i*tw,top+44,tw-4,tab_height);self.tab_rects[tab]=rect
            button(screen,rect,tab,self.font,rect.collidepoint(mouse),self.tab==tab,quiet=True)
        self.dimension_rects={};row_top=top+44+tab_height+16
        if self.tab in ('Worlds','Biomes'):
            for i,(dim,label) in enumerate((('overworld','Overworld'),('nether','Nether'),('end','The End'))):
                rect=pygame.Rect(left+i*round(140*scale),row_top,round(134*scale),max(30,self.small.get_height()+6));self.dimension_rects[dim]=rect
                button(screen,rect,label,self.small,rect.collidepoint(mouse),dim==self.dimension,quiet=True)
            row_top+=max(30,self.small.get_height()+6)+12
        self.list_rect=pygame.Rect(left,row_top,round((w-62)*.60),self.rect.bottom-66-row_top)
        detail=pygame.Rect(self.list_rect.right+24,row_top,self.rect.right-22-(self.list_rect.right+24),self.list_rect.height)
        entry=self.pending
        # The selected full preview gets the worker before decorative row thumbnails.
        if entry:
            title_height=max(30,self.font.get_height()+4)
            wrapped(screen,entry['name'],self.font,(detail.x,detail.y,detail.width,title_height),ACCENT)
            foot_height=max(42,self.small.get_linesize()*2+8)
            preview_height=max(40,detail.height-title_height-foot_height-8)
            preview=app.previewImages.get(app,entry,(detail.width,preview_height))
            if preview:screen.blit(preview,(detail.x,detail.y+title_height+4))
            else:wrapped(screen,'Preparing preview…',self.small,(detail.x,detail.y+title_height+24,detail.width,40),MUTED)
            message=('Place in your current build. Esc cancels.' if entry['kind']=='structure' else
                     'Opening replaces the canvas. Save your build first.')
            wrapped(screen,message,self.small,(detail.x,detail.bottom-foot_height,detail.width,foot_height),MUTED)
        else:wrapped(screen,'Select an item to preview it.',self.font,detail,MUTED)
        self.columns=max(2,self.list_rect.width//250)
        tile_width=self.list_rect.width//self.columns
        self.row_height=max(108,self.list_rect.height//4,self.small.get_linesize()*2+66)
        self.max_scroll=max(0,((len(self.entries)+self.columns-1)//self.columns)*self.row_height-self.list_rect.height)
        self.scroll=self.scroller.update(self.max_scroll,getattr(app.workshop.visibility,'reduced_motion',False))
        old=screen.get_clip();screen.set_clip(self.list_rect);self.rows=[]
        for i,item in enumerate(self.entries):
            rect=pygame.Rect(left+(i%self.columns)*tile_width,row_top+(i//self.columns)*self.row_height-self.scroll,tile_width-8,self.row_height-8)
            if not rect.colliderect(self.list_rect):continue
            self.rows.append((rect.clip(self.list_rect),item))
            button(screen,rect,'',self.small,rect.collidepoint(mouse),item==entry,quiet=True)
            image_height=rect.height-self.small.get_linesize()*2-12
            preview=app.previewImages.get(app,item,(rect.width-12,image_height))
            if preview:screen.blit(preview,(rect.x+6,rect.y+4))
            else:wrapped(screen,'Preparing preview…',self.small,(rect.x+8,rect.y+12,rect.width-16,image_height),MUTED)
            wrapped(screen,item['name'],self.small,(rect.x+8,rect.y+image_height+4,rect.width-16,self.small.get_linesize()+2))
            supporting={'structure':'Place in canvas','biome':'Captured landscape','world':'Editable world','build':'Saved build'}[item['kind']]
            wrapped(screen,supporting,self.small,(rect.x+8,rect.bottom-self.small.get_linesize()-3,rect.width-16,self.small.get_linesize()+2),MUTED)
        screen.set_clip(old)
        if not self.entries:wrapped(screen,'No items here yet. Save a build or browse files.',self.font,self.list_rect,MUTED)
        if self.max_scroll:
            thumb=max(20,round(self.list_rect.height**2/(self.list_rect.height+self.max_scroll)))
            pygame.draw.rect(screen,MUTED,(self.list_rect.right+6,self.list_rect.y+round((self.list_rect.height-thumb)*self.scroll/self.max_scroll),3,thumb),border_radius=1)
        bottom=self.rect.bottom-48;button_height=max(32,self.small.get_height()+6)
        self.browse_rect=pygame.Rect(left,bottom,self.list_rect.width,button_height) if self.tab in ('Worlds','Saved Builds') else pygame.Rect(0,0,0,0)
        if self.browse_rect.width:button(screen,self.browse_rect,'Import Java World…' if self.tab=='Worlds' else 'Browse files…',self.small,self.browse_rect.collidepoint(mouse),quiet=True)
        self.open_rect=pygame.Rect(detail.x,bottom,min(detail.width,round(230*scale)),button_height)
        label='Select an item'
        if entry:label='Place structure' if entry['kind']=='structure' else 'Open world' if entry['kind']=='world' else 'Open biome' if entry['kind']=='biome' else 'Start lesson' if entry['value'].kind=='tutorial' else 'Open build'
        button(screen,self.open_rect,label,self.small,self.open_rect.collidepoint(mouse),bool(entry),enabled=bool(entry))
