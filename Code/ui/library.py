"""One content library with explicit scene-opening and structure-placement actions."""
import pygame
import math
from ui.chrome import panel, wrapped, button, TEXT, MUTED, ACCENT
from ui.tool_icons import draw as icon
from ui.fonts import load_ui_font
from ui.scroll import SmoothScroll
from ui.feedback import action as feedback_action, play as cue


class Library:
    TABS = ('Worlds', 'Biomes', 'Structures', 'Saved Builds')

    def __init__(self):
        self.visible = False
        self.home = True;self.home_focus=None
        self.back_rect=pygame.Rect(0,0,0,0)
        self._morph_from=None;self._morph_at=0
        self._art_hover={};self._art_at=pygame.time.get_ticks()
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
        self._saved_future = None
        self._saved_entries = []
        self.max_scroll = 0
        self.row_height = 64

    def open(self, app, tab=None):
        app.workshop.close_drawer(app)
        self.visible = True
        self.home = tab is None
        self.tab = tab or 'Worlds'
        self._morph_from=None
        self.dimension = app.currentDimension
        if self.home:self.entries=[];self.pending=None
        else:self.refresh(app)
        cue(app.assetManager,'close')

    def change_view(self,app,tab=None):
        self._morph_from=self.rect.copy();self._morph_at=pygame.time.get_ticks()
        self.home=tab is None;self.pending=None;self.rows=[]
        self.tab_rects={};self.dimension_rects={}
        self.open_rect=self.browse_rect=self.list_rect=self.back_rect=pygame.Rect(0,0,0,0)
        if tab:self.tab=tab;self.refresh(app)
        cue(app.assetManager,'button' if tab else 'close')

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
        elif self.tab == 'Structures':
            self.entries = [dict(key=k, name=v['name'], detail='Place this structure in your current build.',
                kind='structure', value=k) for k,v in app.structureDefinitions.items()]
        else:
            if self._saved_future is None or self._saved_future.done():
                self._saved_future = app.worldLoadExecutor.submit(build_catalog, SAVES_DIR,
                    BUILTIN_STRUCTURES_DIR, tuple(app.tutorialScreen.TUTORIAL_STEPS))
            self.entries = list(self._saved_entries)

    def _poll_entries(self, app):
        future = self._saved_future
        if self.tab != 'Saved Builds' or future is None or not future.done():return
        self._saved_future = None
        try:
            self.entries = [dict(key=e.key, name=e.label, detail=e.category, kind='build', value=e)
                            for e in future.result() if e.kind == 'file']
            self._saved_entries = list(self.entries)
        except OSError as error:
            app.workshop.error = f'Could not read saved builds: {error}'


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

    @feedback_action
    def handle_event(self, event, app):
        if not self.visible: return False
        self._poll_entries(app)
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:self.visible=False;cue(app.assetManager,'close')
            elif self.home:
                if self.home_focus is None:self.home_focus=0
                if event.key in (pygame.K_RIGHT,pygame.K_DOWN,pygame.K_TAB):self.home_focus=(self.home_focus+1)%4
                elif event.key in (pygame.K_LEFT,pygame.K_UP):self.home_focus=(self.home_focus-1)%4
                elif event.key==pygame.K_RETURN:self.change_view(app,self.TABS[self.home_focus])
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
        if any(action=='nav:library' and enabled and rect.collidepoint(event.pos)
               for rect,action,enabled in app.workshop.hits):
            self.visible=False;app.workshop.reveal();cue(app.assetManager,'close');return True
        if not self.rect.collidepoint(event.pos):return True
        acted = True
        if self.close_rect.collidepoint(event.pos): self.visible = False;cue(app.assetManager,'close')
        elif not self.home and self.back_rect.collidepoint(event.pos):self.change_view(app)
        elif self.open_rect.collidepoint(event.pos) and self.pending: self.activate(app)
        elif self.browse_rect.collidepoint(event.pos):
            self.visible = False
            if self.tab == 'Worlds': app._openJavaWorldDialog()
            else: app._openNativeLoadDialog()
        else:
            acted = False
            for tab, rect in self.tab_rects.items():
                if rect.collidepoint(event.pos):
                    self.change_view(app,tab); acted = True; break
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
        self._poll_entries(app)
        screen=app.screen;mouse=pygame.mouse.get_pos();sw,sh=screen.get_size()
        scale=app.workshop.text_scale;compact=sw<1100 or scale>1.25
        target=pygame.Rect(0,0,min(sw-48,round((460 if compact else 720)*min(scale,1.25))),
                           min(sh-100,round((332 if compact else 202)*min(scale,1.25)))) if self.home else pygame.Rect(0,0,min(sw-48,880),min(sh-160,580))
        target.center=(sw//2,sh//2)
        progress=min(1,(pygame.time.get_ticks()-self._morph_at)/180)
        if app.workshop.visibility.reduced_motion:progress=1
        self._transition_progress=progress
        if self._morph_from is not None and progress<1:
            ease=1-(1-progress)**3
            self.rect=pygame.Rect(*(round(a+(b-a)*ease) for a,b in zip(self._morph_from,target)))
        else:self.rect=target;self._morph_from=None
        panel(screen,self.rect,alpha=240)
        panel_clip=screen.get_clip();screen.set_clip(self.rect.clip(panel_clip))
        x,y,w,h=self.rect;left=x+16;top=y+12
        from ui.chrome import close_size
        close_width=close_size(self.small)
        self.close_rect=pygame.Rect(self.rect.right-close_width-12,y+8,close_width,close_width)
        if self.home:button(screen,self.close_rect,'Close',self.small,self.close_rect.collidepoint(mouse),quiet=True)
        else:self.close_rect=pygame.Rect(0,0,0,0)
        self.tab_rects={};self.dimension_rects={};self.rows=[]
        self.open_rect=self.browse_rect=self.list_rect=self.back_rect=pygame.Rect(0,0,0,0)
        if self.home:
            now=pygame.time.get_ticks();dt=min(.05,(now-self._art_at)/1000);self._art_at=now
            cols=2 if compact else 4;gap=10;rows=4//cols
            tile_top=self.close_rect.bottom+8
            tile_w=(w-32-gap*(cols-1))//cols;tile_h=max(50,(self.rect.bottom-12-tile_top-gap*(rows-1))//rows)
            for i,(tab,label,art) in enumerate(zip(self.TABS,('Dimensions','Biomes','Structures','Saved'),('worlds','biomes','structures','saved'))):
                r=pygame.Rect(left+i%cols*(tile_w+gap),tile_top+i//cols*(tile_h+gap),tile_w,tile_h)
                self.tab_rects[tab]=r
                button(screen,r,'',self.small,r.collidepoint(mouse),focused=i==self.home_focus,quiet=True)
                art_size=max(24,min(tile_w-12,tile_h-self.font.get_linesize()-8))
                focused=r.collidepoint(mouse) or i==self.home_focus
                level=self._art_hover.get(tab,0)
                level+=(float(focused)-level)*(1 if app.workshop.visibility.reduced_motion else 1-math.exp(-dt/ .09))
                self._art_hover[tab]=level
                lift=0 if app.workshop.visibility.reduced_motion else round(3*level)
                icon(screen,'library_'+art,pygame.Rect(r.centerx-art_size//2,r.y-lift,art_size,art_size),(255,255,255))
                text=self.font.render(label,True,TEXT);screen.blit(text,text.get_rect(center=(r.centerx,r.bottom-self.font.get_linesize()//2-4)))
            screen.set_clip(panel_clip)
            return
        self.back_rect=pygame.Rect(left,top,36,max(32,self.small.get_height()+8))
        button(screen,self.back_rect,'',self.small,self.back_rect.collidepoint(mouse),quiet=True)
        # Native-size arrow: the single child-page navigation affordance.
        cx,cy=self.back_rect.center
        pygame.draw.lines(screen,TEXT,False,[(cx+3,cy-7),(cx-4,cy),(cx+3,cy+7)],3)
        row_top=self.back_rect.bottom+12
        bottom=self.rect.bottom-max(44,self.small.get_linesize()+20)
        gallery_left=left
        if self.tab in ('Worlds','Biomes'):
            rail_width=min(round(142*scale),w//4)
            tile_h=max(60,(bottom-row_top-26)//3)
            for i,(dim,label) in enumerate((('overworld','Overworld'),('nether','Nether'),('end','The End'))):
                r=pygame.Rect(left,row_top+i*(tile_h+8),rail_width,tile_h)
                self.dimension_rects[dim]=r.clip(self.rect)
                button(screen,r,'',self.small,r.collidepoint(mouse),dim==self.dimension,quiet=True)
                size=max(24,min(rail_width-24,tile_h-self.small.get_linesize()-12))
                icon(screen,'dimension_'+dim,pygame.Rect(r.centerx-size//2,r.y+4,size,size),TEXT)
                label_surface=self.small.render(label,True,ACCENT if dim==self.dimension else TEXT)
                screen.blit(label_surface,label_surface.get_rect(midbottom=(r.centerx,r.bottom-6)))
            gallery_left+=rail_width+16
        entry=self.pending
        self.list_rect=pygame.Rect(gallery_left,row_top,self.rect.right-16-gallery_left,max(40,bottom-row_top-10))
        self.columns=2;tw=self.list_rect.width//2
        self.row_height=max(148,self.list_rect.height//2,self.small.get_linesize()+116)
        self.max_scroll=max(0,((len(self.entries)+self.columns-1)//self.columns)*self.row_height-self.list_rect.height)
        self.scroll=self.scroller.update(self.max_scroll,app.workshop.visibility.reduced_motion)
        old=screen.get_clip();screen.set_clip(self.list_rect.clip(old))
        for i,item in enumerate(self.entries):
            r=pygame.Rect(gallery_left+i%self.columns*tw,row_top+i//self.columns*self.row_height-self.scroll,tw-8,self.row_height-8)
            if not r.colliderect(self.list_rect):continue
            self.rows.append((r.clip(screen.get_clip()),item));button(screen,r,'',self.small,r.collidepoint(mouse),item==entry,quiet=True)
            ih=r.height-self.small.get_linesize()-10
            preview=app.previewImages.get(app,item,(r.width-10,ih))
            if preview:screen.blit(preview,(r.x+5,r.y+2))
            else:wrapped(screen,'Preparing…',self.small,(r.x+8,r.y+12,r.width-16,ih),MUTED)
            wrapped(screen,item['name'],self.small,(r.x+8,r.bottom-self.small.get_linesize()-3,r.width-16,self.small.get_linesize()+2))
        if not self.entries:wrapped(screen,'Preparing saved builds…' if self._saved_future is not None and self.tab=='Saved Builds' else 'No saved builds yet. Browse files to open one.',self.font,self.list_rect,MUTED)
        screen.set_clip(old)
        if self.max_scroll:
            thumb=max(20,round(self.list_rect.height**2/(self.list_rect.height+self.max_scroll)))
            pygame.draw.rect(screen,MUTED,(self.list_rect.right+2,self.list_rect.y+round((self.list_rect.height-thumb)*self.scroll/self.max_scroll),2,thumb))
        bh=max(32,self.small.get_height()+8)
        if self.tab in ('Worlds','Saved Builds'):
            self.browse_rect=pygame.Rect(left,bottom,min(w//2-20,round(235*scale)),bh)
            button(screen,self.browse_rect,'Import Java World…' if self.tab=='Worlds' else 'Browse files…',self.small,self.browse_rect.collidepoint(mouse),quiet=True)
        if entry:
            self.open_rect=pygame.Rect(self.rect.right-176,bottom,160,bh)
            button(screen,self.open_rect,'Place' if entry['kind']=='structure' else 'Open',self.font,self.open_rect.collidepoint(mouse),True)
        screen.set_clip(panel_clip)
