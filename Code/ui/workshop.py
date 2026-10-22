"""Anchored editor presentation; world, commands and persistence stay in the app."""
from dataclasses import dataclass
import random
import pygame
from ui import chrome
from ui.fonts import load_ui_font, set_text_scale
from ui.workshop_actions import ACTIONS, TOOLS, WORLD, MENU
from engine.input_commands import Command
from ui.scroll import SmoothScroll
from ui.tool_icons import draw as draw_icon
from ui.help import SHORTCUTS
from ui.feedback import action as feedback_action


@dataclass
class Visibility:
    last_activity: float = 0
    alpha: float = 1
    pinned: bool = False
    always: bool = False
    reduced_motion: bool = False

    def update(self, now, dt, occupied=False):
        if occupied: self.last_activity=now
        target=1.0 if occupied or self.pinned or self.always or now-self.last_activity<4 else 0.0
        step=max(0,dt)/.18
        self.alpha=target if self.reduced_motion else min(target,self.alpha+step) if target>self.alpha else max(target,self.alpha-step)
        return self.alpha


class Workshop:
    @property
    def status(self):return getattr(self,'_status','')

    @status.setter
    def status(self,value):
        self._status=value;self._status_at=pygame.time.get_ticks()/1000

    def __init__(self, variant='anchored', text_scale=1, categories=None):
        self.variant=variant; self.categories=categories or {}
        self.font=load_ui_font(17); self.small=load_ui_font(14); self.title=load_ui_font(25,bold=True)
        self.visibility=Visibility(last_activity=pygame.time.get_ticks()/1000)
        self.last_time=pygame.time.get_ticks()/1000
        self.hits=[]; self.panels=[]; self.context=pygame.Rect(0,0,0,0)
        self.captured=set(); self.focus=None; self.menu=False; self.legacy=False
        self.page=''; self.query=''; self.category='All'; self.scroll=0; self.max_scroll=0
        self.error=''; self.status=''; self.saved_revision=None; self.clean=False
        self.text_scale=text_scale; self.drag_block=None; self.drag_origin=None; self.dragging=False
        self.hotbar_rects=[]; self.hotbar_bounds=pygame.Rect(0,0,0,0)
        self.list_rect=pygame.Rect(0,0,0,0); self.category_menu=False
        self.confirm=None; self._filter_key=None; self._filtered=[]
        self.scroller=SmoothScroll(); self.shortcut_scroller=SmoothScroll()
        self.shortcuts_rect=pygame.Rect(0,0,0,0); self.shortcut_max=0
        self.category_page=0
        self.category_scroller=SmoothScroll();self.category_rect=pygame.Rect(0,0,0,0);self.category_max=0
        self.italic=load_ui_font(14,italic=True)
        self.tile_levels={};self.frame_dt=0
        self.menu_group="File";self.menu_slots=False;self.menu_hits=[]
        self._layers={}
        from ui.motion import Opacity
        self._drawer_opacity=Opacity()
        self._drawer_layer=None;self._drawer_bounds=None

    def _layer(self, name, size):
        layer=self._layers.get(name)
        if layer is None or layer.get_size()!=size:
            layer=self._layers[name]=pygame.Surface(size,pygame.SRCALPHA)
        layer.set_alpha(255);layer.fill((0,0,0,0))
        return layer

    @staticmethod
    def active(app):
        return not (getattr(getattr(app,'workshop',None),'legacy',False) or
                    getattr(app,'openingScene',None) or getattr(app,'worldMapActive',False)
                    or getattr(app,'redstoneLabActive',False))

    @staticmethod
    def operation(app):
        states=[label for field,label in (
            ('fillToolActive','Fill: choose two corners'),('selectionActive','Selection'),
            ('replaceMode','Replace: choose source'),('stampMode','Stamp'),
            ('blueprintMode','Blueprint'),('measurementMode','Measure'),
            ('structurePlacementMode','Place structure'),('mirrorModeX','Mirror X'),
            ('mirrorModeY','Mirror Y'),('magicWandMode','Wand')) if getattr(app,field,False)]
        if getattr(app,'brushSize',1)!=1:states.append(f'Brush {app.brushSize} x {app.brushSize}')
        if getattr(app,'radialSymmetry',0):states.append(f'Radial {app.radialSymmetry}')
        if getattr(app,'layerViewEnabled',False):states.append(f'Layer {app.currentViewLayer}')
        return ' · '.join(states)

    def preferences(self):
        return dict(always=self.visibility.always,pinned=self.visibility.pinned,
                    reduced_motion=self.visibility.reduced_motion,text_scale=self.text_scale)

    def restore_preferences(self, values):
        for key in ('always','pinned','reduced_motion'):
            setattr(self.visibility,key,bool(values.get(key,False)))
        self.text_scale=max(1,min(2,float(values.get('text_scale',1))))
        set_text_scale(self.text_scale)

    def reveal(self):
        self.visibility.last_activity=pygame.time.get_ticks()/1000
        self.visibility.alpha=1

    @staticmethod
    def cue(app,name):
        assets=getattr(app,'assetManager',None)
        if assets is not None and hasattr(assets,'audioRouter'):
            from ui.feedback import play
            play(assets,name)

    def close_drawer(self, app, *, audible=False):
        if audible and (self.page or self.menu):self.cue(app,'close')
        self.page=''; self.menu=False; self.category_menu=False
        app.searchActive=False; self.focus=None
        self._clear_drawer_hits()

    def _clear_drawer_hits(self):
        # Multiple queued input events may arrive before another render.
        # A dismissed/replaced drawer must not retain the old action regions.
        self.hits=self.hits[:getattr(self,'_drawer_hit_start',len(self.hits))]
        self.menu_hits=[]

    def open_drawer(self, page, app):
        self._clear_drawer_hits()
        self.page='' if self.page==page else page
        self.menu=self.page=='menu'; self.scroll=0; self.scroller.reset(); self.shortcut_scroller.reset(); self.category_menu=False
        app.searchActive=False; self.focus=None; self.reveal()
        self.cue(app,'open' if self.page else 'cancel')

    def filtered_blocks(self, app):
        definitions=app.world.catalog.definitions
        key=(self.query.casefold(),self.category,tuple(app.favoriteBlocks),tuple(app.recentBlocks),len(definitions))
        if key!=self._filter_key:
            allowed=(app.favoriteBlocks if self.category=='Favorites' else app.recentBlocks
                     if self.category=='Recent' else self.categories.get(self.category))
            self._filtered=[b for b,d in definitions.items() if b.name!='AIR'
                and (allowed is None or b in allowed)
                and all(word in (d.name+' '+b.name.replace('_',' ')).casefold() for word in self.query.casefold().split())]
            self._filter_key=key
        return self._filtered

    def _button(self,screen,rect,label,action,selected=False,enabled=True,quiet=False):
        rect=pygame.Rect(rect)
        chrome.button(screen,rect,label,self.small,rect.collidepoint(pygame.mouse.get_pos()),
                      selected,enabled,self.focus==action,quiet)
        if rect.colliderect(screen.get_clip()):self.hits.append((rect.clip(screen.get_clip()),action,enabled))

    def _panel(self,screen,rect,alpha=246):
        rect=pygame.Rect(rect);chrome.panel(screen,rect,alpha=alpha);self.panels.append(rect)

    @staticmethod
    def canvas_controls(size):
        w,h=size
        return [(pygame.Rect(w-210+i*64,h-64,58,44),action)
                for i,action in enumerate(('grow','shrink','noise'))]

    def _canvas_preview(self,app,controls,mouse):
        modal=(self.clean or self.confirm or app.library.visible or app.settingsMenuOpen
               or app.tutorialScreen.visible or app.showShortcutsPanel or app.historyPanelOpen
               or getattr(app,'_pendingTourLoad',None))
        action=next((a for rect,a in controls if rect.collidepoint(mouse)),None) if not modal else None
        if action!='noise':app._clearTerrainNoisePreview()
        if action is None:
            self._preview_key=None
            return
        key=(action,app.world.revision,app.screen.get_size(),app.renderer.offsetX,
             app.renderer.offsetY,app.renderer.viewRotation,app.zoomLevel)
        if action=='noise':
            if app._terrainNoisePreviewSeed is None:
                app._terrainNoisePreviewSeed=random.randint(0,0x7fffffff)
            plan=app._terrainNoisePlanForSeed(app._terrainNoisePreviewSeed)
            key+=(app._terrainNoisePreviewPlanKey,)
            surface=app._terrainNoisePreviewSurface
        else:surface=app._canvasResizePreviewSurface
        if key==getattr(self,'_preview_key',None) and surface is not None:
            app.screen.blit(surface,(0,0))
        elif action=='noise':app._renderTerrainNoisePreview(plan)
        else:
            delta=16 if action=='grow' else -16
            app._renderCanvasResizePreview(delta,app._canvasResizeDimensions(delta))
        self._preview_key=key

    def _held_block(self,screen,app):
        definition=app.world.catalog.definitions[app.selectedBlock]
        details=['Interact'] if app.interactionMode else []
        if definition.isSlab or definition.isStair:
            details.append(app.previewSlabPosition.name.title()+' half')
        if definition.isStair or definition.isDoor or definition.textureFront:
            details.append(app.previewFacing.name.title())
        detail=' · '.join(details)
        name=definition.name
        width=min(screen.get_width()-48,max(190,self.font.size(name)[0]+78,self.small.size(detail)[0]+78))
        width=min(width,self.hotbar_bounds.left-40)
        compact=width<240;text_left=72 if compact else 88
        name_font=self.small if compact else self.font
        available=width-text_left-12
        name_height=chrome.wrapped_height(name,name_font,available)
        detail_height=chrome.wrapped_height(detail,self.small,available) if detail else 0
        height=max(78,name_height+detail_height+16)
        self.context=pygame.Rect(24,screen.get_height()-10-height,width,height)
        app.tutorialScreen.selectedPreviewRect = self.context.copy()
        app.tutorialScreen.hotbarBounds = self.hotbar_bounds.copy()
        self._panel(screen,self.context,225)
        sprite=app.assetManager.getIconSprite(app.selectedBlock)
        if sprite:
            icon_size=60 if compact else 72
            scale=min(icon_size/sprite.get_width(),icon_size/sprite.get_height())
            sprite=pygame.transform.scale(sprite,(max(1,round(sprite.get_width()*scale)),max(1,round(sprite.get_height()*scale))))
            screen.blit(sprite,sprite.get_rect(center=(self.context.x+text_left//2,self.context.centery)))
        top=self.context.centery-(name_height+detail_height)//2
        chrome.wrapped(screen,name,name_font,(self.context.x+text_left,top,available,name_height),chrome.TEXT)
        if detail:chrome.wrapped(screen,detail,self.small,(self.context.x+text_left,top+name_height,available,detail_height),chrome.MUTED)

    def render(self,app):
        screen=app.screen;w,h=screen.get_size();mouse=pygame.mouse.get_pos()
        now=pygame.time.get_ticks()/1000;dt=now-self.last_time;self.last_time=now
        self.frame_dt=max(0,min(.1,dt))
        self.hits=[];self.panels=[];self.hotbar_rects=[]
        operation=self.operation(app)
        if getattr(app,'_pendingTourLoad',None):operation='Preparing lesson…'
        self.operation_rect=pygame.Rect(24,78,min(w-48,800),0)
        if operation:
            lines=1;line=''
            for word in (operation+' · Esc cancels').split():
                trial=(line+' '+word).strip()
                if line and self.small.size(trial)[0]>self.operation_rect.width-24:
                    lines+=1;line=word
                else:line=trial
            self.operation_rect.height=max(42,lines*(self.small.get_linesize()+3)+14)
        self.context=pygame.Rect(24,h-80,0,0)
        occupied=bool(self.page or self.focus or self.captured or operation or self.error or app.panning
                      or app.draggingSlider or app.library.visible or app.settingsMenuOpen
                      or app.tutorialScreen.visible or self.confirm or app.showShortcutsPanel or app.historyPanelOpen
                      or any(pygame.mouse.get_pressed()))
        if 0<=mouse[0]<w and h-16<=mouse[1]<h and not self.clean:self.reveal()
        if self.hotbar_bounds.collidepoint(mouse) and self.visibility.alpha>0:occupied=True
        alpha=self.visibility.update(now,dt,occupied)
        controls=self.canvas_controls(screen.get_size())
        self._canvas_preview(app,controls,mouse)
        if not self.clean:
            if alpha>0:
                navigation=self._layer('navigation',screen.get_size())
                for right,items in ((False,tuple((label,'nav:'+label.lower()) for label in ('Build','Library','World','Map'))),
                                    (True,(('Tools','nav:tools'),('Save','save'),('Menu','nav:menu')))):
                    widths=[max(86,self.small.size(label)[0]+24) for label,_ in items]
                    group_width=sum(widths)+4*(len(items)-1)+12
                    x=w-24-group_width if right else 24
                    self._panel(navigation,(x,20,group_width,46),225)
                    x+=6
                    for (label,action),width in zip(items,widths):
                        self._button(navigation,(x,26,width,34),label,action,self.page==label.lower(),quiet=True)
                        x+=width+4
                navigation.set_alpha(round(alpha*255));screen.blit(navigation,(0,0))
            for rect,action in controls:
                self._button(screen,rect,'',action,quiet=False)
                draw_icon(screen,action,rect.inflate(-4,-2),chrome.ACCENT)
                if rect.collidepoint(mouse):
                    text={'grow':'Grow canvas','shrink':'Shrink canvas','noise':'Terrain noise'}[action]
                    label=self.small.render(text,True,chrome.TEXT)
                    tip=label.get_rect().inflate(20,12);tip.bottomright=(w-24,rect.top-8)
                    chrome.panel(screen,tip);screen.blit(label,label.get_rect(center=tip.center))
            if alpha>0:
                layer=self._layer('hud',screen.get_size())
                self._hotbar(layer,app)
                if self.page!='build':self._held_block(layer,app)
                if not app.tutorialScreen.visible and self.page!='build':
                    rect=app.tutorialScreen._restoreTileRect()
                    chrome.icon_button(layer,rect,'?',app.tutorialScreen.dockFont,rect.collidepoint(mouse),self.focus=='tutorial')
                    self.hits.append((rect,'tutorial',True))
                    if rect.collidepoint(mouse):
                        label=self.small.render('Tutorial',True,chrome.TEXT)
                        tip=label.get_rect(midbottom=(rect.centerx,rect.top-8)).inflate(16,8)
                        chrome.panel(layer,tip);layer.blit(label,label.get_rect(center=tip.center))
                layer.set_alpha(round(alpha*255));screen.blit(layer,(0,0))
            else:self.hotbar_bounds=pygame.Rect(0,0,0,0)
            self._animated_drawer(app)
        if operation:
            rect=self.operation_rect
            self._panel(screen,rect)
            chrome.wrapped(screen,operation+' · Esc cancels',self.small,rect.inflate(-24,-14),chrome.ACCENT)
        if self.status and now-self._status_at>3:self.status=''
        if self.error or self.status:
            width=min(w-48,620 if self.error else self.small.size(self.status)[0]+28)
            height=chrome.wrapped_height(self.error or self.status,self.small,width-24)+12
            box=pygame.Rect(24,self.context.top-8-height,width,height);self._panel(screen,box)
            chrome.wrapped(screen,self.error or self.status,self.small,box.inflate(-24,-12),chrome.ERROR if self.error else chrome.TEXT)
        if self.confirm:
            box=pygame.Rect(0,0,min(w-48,460),170);box.center=screen.get_rect().center
            self._panel(screen,box)
            message = 'Clear this world? Unsaved changes will be removed.'
            chrome.wrapped(screen,message,self.font,box.inflate(-40,-38))
            self._button(screen,(box.x+20,box.bottom-50,190,34),'Cancel','confirm:cancel')
            self._button(screen,(box.right-210,box.bottom-50,190,34),'Clear world','confirm:clear')
        if self.dragging and self.drag_block is not None:
            sprite=app.assetManager.getIconSprite(self.drag_block)
            if sprite:screen.blit(sprite,sprite.get_rect(center=mouse))

    def _hotbar(self,screen,app):
        w,h=screen.get_size();slot=50;padding=4;step=slot+padding
        width=len(app.hotbar)*step+padding
        self.hotbar_bounds=pygame.Rect((w-width)//2,h-68,width,58)
        chrome.panel(screen,self.hotbar_bounds,alpha=225)
        for i,block in enumerate(app.hotbar):
            rect=pygame.Rect(self.hotbar_bounds.x+padding+i*step,h-64,slot,slot)
            self.hotbar_rects.append(rect)
            pygame.draw.rect(screen,chrome.SELECTED if i==app.hotbarSelectedSlot else chrome.CONTROL,rect,border_radius=3)
            if i==app.hotbarSelectedSlot:chrome.outline(screen,chrome.ACCENT,rect,3,2)
            sprite=app.assetManager.getIconSprite(block)
            if sprite:
                scale=min(44/sprite.get_width(),44/sprite.get_height())
                sprite=pygame.transform.scale(sprite,(max(1,round(sprite.get_width()*scale)),max(1,round(sprite.get_height()*scale))))
                screen.blit(sprite,sprite.get_rect(center=rect.center))
            screen.blit(self.small.render(str(i+1),True,chrome.TEXT),(rect.x+3,rect.y+1))
            self.hits.append((rect,'slot:'+str(i),True))
        self.panels.append(self.hotbar_bounds)

    def _drawer(self,app):
        from ui.workshop_views import draw_drawer
        draw_drawer(self,app)

    def _animated_drawer(self,app):
        screen=app.screen
        alpha=self._drawer_opacity.update(bool(self.page),pygame.time.get_ticks()/1000,
                                          self.visibility.reduced_motion)
        if self._drawer_layer is None or self._drawer_layer.get_size()!=screen.get_size():
            self._drawer_layer=pygame.Surface(screen.get_size(),pygame.SRCALPHA)
            self._drawer_bounds=None
        if self.page:
            # Reuse one transparent viewport buffer, clearing/blitting only the
            # drawer bounds. Text is rasterized at its native final coordinates.
            if self._drawer_bounds:self._drawer_layer.fill((0,0,0,0),self._drawer_bounds)
            start=len(self.panels)
            self._drawer_hit_start=len(self.hits)
            app.screen=self._drawer_layer
            try:self._drawer(app)
            finally:app.screen=screen
            self._drawer_bounds=self.panels[start].clip(screen.get_rect())
        if alpha and self._drawer_bounds:
            self._drawer_layer.set_alpha(round(255*alpha))
            screen.blit(self._drawer_layer,self._drawer_bounds,self._drawer_bounds)
        # A fading closed panel owns no commands, but still blocks click-through
        # while visible. Reopening reverses opacity from the current value.
        if not self.page and alpha and self._drawer_bounds:self.panels.append(self._drawer_bounds)

    def handle_event(self,event,app):
        ctrl_tab=(event.type==pygame.KEYDOWN and event.key==pygame.K_TAB and getattr(event,'mod',0)&pygame.KMOD_CTRL)
        if self.legacy and ctrl_tab:
            self.legacy=False;self.reveal();return True
        if not self.active(app):return False
        if event.type==pygame.TEXTINPUT and self.page=='build' and app.searchActive:
            self.query+=''.join(char for char in event.text if char.isprintable())
            self.scroll=0;self.scroller.reset();self.reveal();return True
        if event.type in (pygame.WINDOWFOCUSLOST,pygame.WINDOWFOCUSGAINED):
            self.captured.clear();self.drag_block=None;self.dragging=False;self.focus=None
            app.panning=False;app.draggingSlider=None;self.reveal();return False
        if event.type==pygame.KEYDOWN:
            mods=getattr(event,'mod',0)
            if self.confirm:
                if event.key==pygame.K_ESCAPE:self.confirm=None;self.focus=None
                elif event.key==pygame.K_TAB:self.focus='confirm:clear' if self.focus=='confirm:cancel' else 'confirm:cancel'
                elif event.key==pygame.K_RETURN and self.focus in ('confirm:cancel','confirm:clear'):self.act(self.focus,app)
                return True
            if getattr(app,'searchActive',False) and self.page!='build':
                self.focus=None
                return False
            if self.page=='menu' and event.key in (pygame.K_UP,pygame.K_DOWN,pygame.K_TAB):
                actions=[a for _,a,e in self.menu_hits if e]
                if actions:
                    step=-1 if event.key==pygame.K_UP or mods&pygame.KMOD_SHIFT else 1
                    self.focus=actions[(actions.index(self.focus)+step)%len(actions)] if self.focus in actions else actions[0]
                self.reveal();return True
            if self.page=='menu' and event.key in (pygame.K_LEFT,pygame.K_RIGHT):
                from ui.command_palette import GROUPS
                groups=list(GROUPS);step=-1 if event.key==pygame.K_LEFT else 1
                self.act('menu_group:'+groups[(groups.index(self.menu_group)+step)%len(groups)],app);return True
            if event.key==pygame.K_TAB and (ctrl_tab or self.focus):
                actions=[a for _,a,e in self.hits if e]
                if actions:
                    step=-1 if mods&pygame.KMOD_SHIFT else 1
                    self.focus=actions[(actions.index(self.focus)+step)%len(actions)] if self.focus in actions else actions[0]
                    app.searchActive=self.focus=='search'
                self.reveal();return True
            if event.key==pygame.K_ESCAPE:
                if self.confirm:self.confirm=None;return True
                if self.page=="menu" and self.menu_slots:self.menu_slots=False;self.scroller.reset();return True
                if self.page or self.focus:self.close_drawer(app,audible=True);return True
                if self.clean:self.clean=False;self.reveal();return True
            if event.key==pygame.K_F1:
                self.clean=False;self.reveal();return True
            if event.key==pygame.K_f and mods&pygame.KMOD_CTRL and not mods&pygame.KMOD_SHIFT:
                self.page='build';self.category='All';app.searchActive=True;self.focus='search';self.reveal();return True
            if self.page=='build' and app.searchActive:
                if event.key==pygame.K_BACKSPACE:self.query=self.query[:-1];self.scroll=0;self.scroller.reset()
                elif event.key==pygame.K_RETURN:
                    blocks=self.filtered_blocks(app)
                    if blocks:self.select(blocks[0],app)
                # SDL TEXTINPUT owns printable text, including Unicode input
                # and IME commits. KEYDOWN owns only editing/navigation keys.
                return True
            if event.key==pygame.K_RETURN and self.focus:self.act(self.focus,app);return True
            if self.page and event.key in (pygame.K_UP,pygame.K_DOWN,pygame.K_PAGEUP,pygame.K_PAGEDOWN):
                self.scroll=max(0,min(self.max_scroll,self.scroll+(-1 if event.key in (pygame.K_UP,pygame.K_PAGEUP) else 1)*(self.list_rect.height if event.key in (pygame.K_PAGEUP,pygame.K_PAGEDOWN) else 50)))
                self.scroller.reset(self.scroll)
                return True
            self.reveal()
        if event.type==pygame.MOUSEWHEEL and self.page:
            if any(r.collidepoint(pygame.mouse.get_pos()) for r in self.panels):
                if self.category_rect.collidepoint(pygame.mouse.get_pos()):self.category_scroller.wheel(event,self.category_max)
                elif self.shortcuts_rect.collidepoint(pygame.mouse.get_pos()):self.shortcut_scroller.wheel(event,self.shortcut_max)
                elif self.list_rect.collidepoint(pygame.mouse.get_pos()):self.scroller.wheel(event,self.max_scroll)
                return True
        if event.type==pygame.MOUSEBUTTONUP and event.button in self.captured:
            if self.dragging and self.drag_block is not None:
                for i,rect in enumerate(self.hotbar_rects):
                    if rect.collidepoint(event.pos):app._updateHotbarSlot(i,self.drag_block);self.status=f'Assigned slot {i+1}';break
            self.captured.discard(event.button);self.dragging=False;self.drag_block=None;return True
        if event.type==pygame.MOUSEMOTION:
            if getattr(event,'rel',(0,0)) != (0,0):self.reveal()
            if self.captured:
                if self.drag_block is not None and self.drag_origin:
                    self.dragging=self.dragging or pygame.Vector2(event.pos).distance_to(self.drag_origin)>8
                return True
            if not app.panning and any(r.collidepoint(event.pos) for r in self.panels):
                app.panelHovered=True;app.hoveredCell=None;app.hoveredSourceBlock=None;return True
        if event.type==pygame.MOUSEBUTTONDOWN:
            if event.button in (4,5):return any(r.collidepoint(event.pos) for r in self.panels)
            self.reveal()
            hits=self.hits[-2:] if self.confirm else self.hits
            for rect,action,enabled in reversed(hits):
                if rect.collidepoint(event.pos):
                    self.captured.add(event.button)
                    if enabled and event.button in (1,3):
                        if action.startswith('slot:'):
                            i=int(action[5:])
                            if event.button==3:app._updateHotbarSlot(i,app.selectedBlock)
                            else:
                                app.hotbarSelectedSlot=i;self.select(app.hotbar[i],app,close=False)
                                self.drag_block=app.hotbar[i];self.drag_origin=event.pos
                        elif action.startswith('block:'):
                            block=type(app.selectedBlock)[action[6:]]
                            if event.button==3:app._toggleFavorite(block)
                            else:
                                self.select(block,app,close=False);self.drag_block=block;self.drag_origin=event.pos
                        elif event.button==1:self.act(action,app)
                    return True
            if self.confirm or any(r.collidepoint(event.pos) for r in self.panels):
                self.captured.add(event.button);return True
            self.focus=None
        return False

    def select(self,block,app,close=True):
        changed=block!=app.selectedBlock
        app._selectBlockForPlacement(block);app._addToRecentBlocks(block)
        if close:self.close_drawer(app)
        if changed:self.cue(app,'select')
        self.reveal()

    @feedback_action
    def act(self,action,app):
        self.reveal()
        if action not in ('save','save_as') and not action.startswith('quick_save_'):
            self.cue(app,'button')
        if action.startswith('menu_group:'):
            self.menu_group=action.split(':',1)[1];self.scroller.reset();self.focus=action;return
        if action=='menu_slots':
            self.menu_slots=not self.menu_slots;self.scroller.reset();return
        if action.startswith('slot:'):
            app.hotbarSelectedSlot=int(action[5:])
            self.select(app.hotbar[app.hotbarSelectedSlot],app,close=False);return
        if action.startswith('block:'):
            self.select(type(app.selectedBlock)[action[6:]],app,close=False);return
        if action.startswith('nav:'):
            page=action[4:]
            if page=='map':self.close_drawer(app);app._requestWorldMap();return
            if page=='library':
                if app.library.visible:app.library.visible=False;self.cue(app,'close')
                else:self.close_drawer(app);app.library.open(app)
            else:self.open_drawer(page,app)
            return
        if action in ('build','menu'):self.open_drawer(action,app);return
        if action=='library':self.close_drawer(app);app.library.open(app);return
        if action=='close':self.close_drawer(app);self.cue(app,'cancel');return
        if action=='reveal':self.clean=False;return
        if action=='search':app.searchActive=True;self.focus='search';return
        if action=='category_next':self.category_page+=1;return
        if action=='categories':self.category_menu=not self.category_menu;self.scroll=0;app.searchActive=False;return
        if action.startswith('category:'):
            self.category=action[9:];self.category_menu=False;self.scroll=0;self.scroller.reset();app.searchActive=False;return
        if action=='favorite':app._toggleFavorite(app.selectedBlock);return
        if action=='confirm:cancel':self.confirm=None;self.focus=None;return
        if action=='confirm:clear':
            action=self.confirm;self.confirm=None;self.focus=None
        elif action=='clear_world':self.confirm=action;self.focus='confirm:cancel';return
        if action=='fit':app._executeInputCommand(Command.FIT_WORLD);return
        if action in ('left','right'):app._rotateViewAndRecenter(-1 if action=='left' else 1);return
        row=ACTIONS.get(action)
        if not row:return
        _,label,route,args,field=row
        try:
            if route=='command':app._executeInputCommand(args[0])
            elif route=='key':
                mods=(pygame.KMOD_CTRL if 'ctrl' in args else 0)|(pygame.KMOD_SHIFT if 'shift' in args else 0)
                app._handleKeyDown(pygame.event.Event(pygame.KEYDOWN,key=pygame.key.key_code(args[0]),mod=mods,unicode=''))
            elif route=='method':
                if args[0]=='_beginTutorial':app._beginTutorial(advanced=args[1] if len(args)>1 else False)
                else:getattr(app,args[0])(*args[1:])
            elif route=='save':
                result=app._saveBuilding() if app.currentBuildPath else app._openSaveAsDialog()
                if result:
                    from pathlib import Path
                    self.status='Saved: '+Path(app.currentBuildPath).name;self.error='';self.saved_revision=app.world.revision
                elif result is False:
                    self.error='Save failed. Your build is still open. Retry Save.'
            elif route in ('undo','redo'):
                result=getattr(app.undoManager,route)()
                if result:self.status=route.title()+': '+result.get_description();self.cue(app,'button')
            elif route=='library':app.library.open(app,args[0])
            elif route=='settings':app.settingsMenuOpen=True
            elif route=='help':app.showShortcutsPanel=True
            elif route=='preference':
                setattr(self.visibility,args[0],not getattr(self.visibility,args[0]));app._saveAppConfig()
            elif route=='text_scale':
                self.text_scale={1:1.25,1.25:1.5,1.5:1}.get(self.text_scale,1)
                set_text_scale(self.text_scale);app.assetManager.uiTextCache.clear();app._saveAppConfig()
            elif route=='clean':self.clean=True
            elif route=='legacy':self.legacy=True
            elif route=='terrain_view':
                modes=('all','transparent','hidden');app.sceneTerrainMode=modes[(modes.index(app.sceneTerrainMode)+1)%3];app._invalidateViewCaches()
            if route not in ('preference','text_scale') and action not in ('rain','snow','sun','clouds','lighting','sky','sky_previous','sky_next','flow','horror_rain','overworld','nether','end'):
                self.close_drawer(app)
        except (OSError,ValueError,pygame.error) as error:
            self.error=f'{label} failed: {error}'
            self.cue(app,'error')
