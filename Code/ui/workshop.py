"""Anchored editor presentation; world, commands and persistence stay in the app."""
from dataclasses import dataclass
import pygame
from ui import chrome
from ui.fonts import load_ui_font, set_text_scale
from ui.workshop_actions import ACTIONS, TOOLS, WORLD, MENU
from engine.input_commands import Command
from ui.scroll import SmoothScroll
from ui.tool_icons import draw as draw_icon
from ui.help import SHORTCUTS


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
        self.tile_levels={};self.frame_dt=0

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

    def close_drawer(self, app):
        self.page=''; self.menu=False; self.category_menu=False
        app.searchActive=False; self.focus=None

    def open_drawer(self, page, app):
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
        context_height=max(107,self.small.get_linesize()+self.font.get_linesize()+max(30,self.small.get_height()+8)+38)
        self.context=pygame.Rect(24,h-80-context_height,min(w-48,round(320*self.text_scale)),context_height)
        dirty=(self.saved_revision!=app.world.revision if self.saved_revision is not None else app.undoManager.can_undo())
        occupied=bool(self.page or self.focus or self.captured or operation or self.error or app.panning
                      or app.draggingSlider or app.library.visible or app.settingsMenuOpen
                      or app.tutorialScreen.visible or self.confirm or app.showShortcutsPanel or app.historyPanelOpen
                      or any(pygame.mouse.get_pressed()))
        if 0<=mouse[0]<w and h-16<=mouse[1]<h and not self.clean:self.reveal()
        if self.context.collidepoint(mouse) and self.visibility.alpha>0:occupied=True
        if self.hotbar_bounds.collidepoint(mouse) and self.visibility.alpha>0:occupied=True
        alpha=self.visibility.update(now,dt,occupied)
        if not self.clean:
            if alpha>0:
                navigation=pygame.Surface(screen.get_size(),pygame.SRCALPHA)
                self._panel(navigation,(24,20,370,46),225)
                for i,label in enumerate(('Build','Library','World','Map')):
                    self._button(navigation,(28+i*91,26,89,34),label,'nav:'+label.lower(),self.page==label.lower(),quiet=True)
                self._panel(navigation,(w-301,20,277,46),225)
                for i,(label,action) in enumerate((('Tools','nav:tools'),('Save','save'),('Menu','nav:menu'))):
                    self._button(navigation,(w-297+i*91,26,89,34),label,action,self.page==label.lower(),quiet=True)
                navigation.set_alpha(round(alpha*255));screen.blit(navigation,(0,0))
            for i,(label,action) in enumerate((('+','grow'),('−','shrink'),('Noise','noise'))):
                rect=pygame.Rect(w-208+i*62,h-64,58,44)
                self._button(screen,rect,'',action,quiet=False)
                draw_icon(screen,action,rect.inflate(-14,-8),chrome.ACCENT)
                if rect.collidepoint(mouse):
                    text={'grow':'Grow canvas (+)','shrink':'Shrink canvas (−)','noise':'Local terrain noise'}[action]
                    tip=pygame.Rect(w-230,h-98,206,28);chrome.panel(screen,tip)
                    chrome.wrapped(screen,text,self.small,tip.inflate(-10,-4))
            if alpha>0:
                layer=pygame.Surface(screen.get_size(),pygame.SRCALPHA)
                self._hotbar(layer,app)
                if not self.page and not app.tutorialScreen.visible:
                    chrome.panel(layer,self.context,alpha=226)
                    sprite=app.assetManager.getBlockSprite(app.selectedBlock)
                    if sprite:layer.blit(sprite,(35,self.context.y+13))
                    definition=app.world.catalog.definitions[app.selectedBlock]
                    layer.blit(self.small.render(('INTERACT' if app.interactionMode else 'BUILD')+(' · Unsaved' if dirty else ''),True,chrome.MUTED),(110,self.context.y+13))
                    chrome.wrapped(layer,definition.name,self.font,(110,self.context.y+19+self.small.get_linesize(),self.context.width-100,self.font.get_height()+4))
                    button_height=max(30,self.small.get_height()+8);button_y=self.context.bottom-button_height-8
                    button_width=(self.context.width-30)//2
                    if definition.isStair or definition.isSlab:
                        self._button(layer,(34,button_y,button_width,button_height),'Half: '+app.previewSlabPosition.name.title(),'half',quiet=True)
                        self._button(layer,(44+button_width,button_y,button_width,button_height),'Turn: '+app.previewFacing.name.title(),'turn',quiet=True)
                    elif definition.isDoor or definition.modelKind in ('lever','button','repeater','comparator','piston','piston_head','torch','redstone_torch'):
                        self._button(layer,(34,button_y,button_width,button_height),'Turn: '+app.previewFacing.name.title(),'turn',quiet=True)
                        self._button(layer,(44+button_width,button_y,button_width,button_height),'Build / Interact','interact',quiet=True)
                    else:
                        self._button(layer,(34,button_y,button_width,button_height),'Fill corners','fill',app.fillToolActive,quiet=True)
                        self._button(layer,(44+button_width,button_y,button_width,button_height),'More tools','nav:tools',quiet=True)
                    self.panels.append(self.context)
                layer.set_alpha(round(alpha*255));screen.blit(layer,(0,0))
            else:self.hotbar_bounds=pygame.Rect(0,0,0,0)
            if not self.page and not app.tutorialScreen.visible and alpha<=0:
                identity=pygame.Rect(24,h-115,320,35);self._panel(screen,identity,220)
                chrome.wrapped(screen,app.world.catalog.definitions[app.selectedBlock].name+(' · Unsaved' if dirty else ''),self.small,identity.inflate(-20,-4))
            if self.page:self._drawer(app)
        if operation:
            rect=self.operation_rect
            self._panel(screen,rect)
            chrome.wrapped(screen,operation+' · Esc cancels',self.small,rect.inflate(-24,-14),chrome.ACCENT)
        if self.status and now-self._status_at>3:self.status=''
        if self.error or self.status:
            height=max(44,self.small.get_linesize()*(2 if self.error else 1)+20)
            width=min(w-48,620 if self.error else self.small.size(self.status)[0]+28)
            box=pygame.Rect(24,self.context.top-16-height,width,height);self._panel(screen,box)
            chrome.wrapped(screen,self.error or self.status,self.small,box.inflate(-24,-12),chrome.ERROR if self.error else chrome.TEXT)
        if self.confirm:
            box=pygame.Rect(0,0,min(w-48,460),170);box.center=screen.get_rect().center
            self._panel(screen,box)
            message = ('Shrink canvas? Blocks outside the new bounds will be removed.' if self.confirm=='shrink' else 'Clear this world? Unsaved changes will be removed.')
            chrome.wrapped(screen,message,self.font,box.inflate(-40,-38))
            self._button(screen,(box.x+20,box.bottom-50,190,34),'Cancel','confirm:cancel')
            self._button(screen,(box.right-210,box.bottom-50,190,34),'Shrink canvas' if self.confirm=='shrink' else 'Clear world','confirm:clear')
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
            if i==app.hotbarSelectedSlot:pygame.draw.rect(screen,chrome.ACCENT,rect,2,border_radius=3)
            sprite=app.assetManager.getIconSprite(block)
            if sprite:
                scale=min(44/sprite.get_width(),44/sprite.get_height())
                sprite=pygame.transform.scale(sprite,(max(1,round(sprite.get_width()*scale)),max(1,round(sprite.get_height()*scale))))
                screen.blit(sprite,sprite.get_rect(center=rect.center))
            screen.blit(self.small.render(str(i+1),True,chrome.TEXT),(rect.x+3,rect.y+1))
            self.hits.append((rect,'slot:'+str(i),True))
        self.panels.append(self.hotbar_bounds)

    def _drawer(self,app):
        screen=app.screen;w,h=screen.get_size()
        width=min(w-48,max(356,round(356*self.text_scale)))
        y=self.operation_rect.bottom+10 if self.operation_rect.height else 82
        box=pygame.Rect(w-width-24 if self.page in ('tools','world','menu') else 24,y,width,h-y-84);self._panel(screen,box)
        self.shortcuts_rect=pygame.Rect(0,0,0,0)
        x=box.x+22;y=box.y+18
        screen.blit(self.title.render(self.page.title(),True,chrome.TEXT),(x,y))
        self._button(screen,(box.right-108,y,88,max(32,self.small.get_height()+6)),'Close','close')
        row_h=max(37,self.small.get_height()+18)
        if self.page=='build':
            search=pygame.Rect(x,y+48,width-44,row_h)
            self._button(screen,search,self.query or 'Search all materials…','search',app.searchActive)
            names=['All','Favorites',*self.categories]
            # Two measured icon-and-text tabs plus paging retain all categories
            # even at 150% text and 960px without a dropdown.
            tab_width=(width-78)//2
            count=max(1,(len(names)+1)//2);self.category_page%=count
            for i,label in enumerate(names[self.category_page*2:self.category_page*2+2]):
                rect=pygame.Rect(x+i*tab_width,search.bottom+8,tab_width-4,row_h)
                self._button(screen,rect,'', 'category:'+label,self.category==label)
                blocks=self.categories.get(label,app.favoriteBlocks if label=='Favorites' else app.hotbar)
                if blocks:
                    sprite=app.assetManager.getIconSprite(blocks[0])
                    if sprite:screen.blit(pygame.transform.smoothscale(sprite,(24,24)),(rect.x+5,rect.centery-12))
                chrome.wrapped(screen,label,self.small,(rect.x+33,rect.y+8,rect.width-38,row_h-10))
            self._button(screen,(box.right-52,search.bottom+8,30,row_h),'›','category_next')
            footer_button=max(24,self.small.get_height()+8)
            self.list_rect=pygame.Rect(x,search.bottom+row_h+24,width-44,max(30,box.bottom-(search.bottom+row_h+24)-footer_button-14))
            blocks=self.filtered_blocks(app);cols=max(3,(width-44)//74);cell=(width-44)//cols
            self.max_scroll=max(0,((len(blocks)+cols-1)//cols)*cell-self.list_rect.height)
            self.scroll=self.scroller.update(self.max_scroll,self.visibility.reduced_motion)
            old=screen.get_clip();screen.set_clip(self.list_rect)
            for i,block in enumerate(blocks):
                rect=pygame.Rect(x+(i%cols)*cell,self.list_rect.y+(i//cols)*cell-self.scroll,cell-5,cell-5)
                if not rect.colliderect(self.list_rect):continue
                chrome.button(screen,rect,'',self.small,rect.collidepoint(pygame.mouse.get_pos()),block==app.selectedBlock,focused=self.focus=='block:'+block.name)
                sprite=app.assetManager.getIconSprite(block)
                if sprite:
                    scale=min((cell-12)/sprite.get_width(),(cell-12)/sprite.get_height(),1)
                    if scale<1:sprite=pygame.transform.smoothscale(sprite,(round(sprite.get_width()*scale),round(sprite.get_height()*scale)))
                    screen.blit(sprite,sprite.get_rect(center=rect.center))
                if block in app.favoriteBlocks:screen.blit(self.small.render('★',True,chrome.ACCENT),(rect.x+4,rect.y+2))
                self.hits.append((rect.clip(self.list_rect),'block:'+block.name,True))
            screen.set_clip(old)
            self._button(screen,(x,box.bottom-footer_button-5,width-44,footer_button),f'{len(blocks)} materials · Favorite / Ctrl+D','favorite',quiet=True)
        else:
            rows={'tools':TOOLS,'world':WORLD,'menu':MENU}[self.page]
            self.list_rect=pygame.Rect(x,y+54,width-44,max(36,box.height-88))
            if self.page=='tools':
                full_height=self.list_rect.height
                self.list_rect.height=max(40,round(full_height*.52))
                divider=self.list_rect.bottom+10
                pygame.draw.line(screen,chrome.MUTED,(x,divider),(box.right-22,divider))
                screen.blit(self.small.render('Controls · Ctrl+Z Undo',True,chrome.ACCENT),(x,divider+8))
                self.shortcuts_rect=pygame.Rect(x,divider+12+self.small.get_linesize(),width-44,max(20,box.bottom-14-(divider+12+self.small.get_linesize())))
                stride=self.small.get_linesize()*2+12
                shortcuts=(('Home / Shift+Home','Fit world / center selection'),('F1 / Ctrl+Tab','Reveal / focus controls'))+SHORTCUTS
                self.shortcut_max=max(0,len(shortcuts)*stride-self.shortcuts_rect.height)
                offset=self.shortcut_scroller.update(self.shortcut_max,self.visibility.reduced_motion)
                old=screen.get_clip();screen.set_clip(self.shortcuts_rect)
                for i,(keys,label) in enumerate(shortcuts):
                    sy=self.shortcuts_rect.y+i*stride-offset
                    screen.blit(self.small.render(keys,True,chrome.ACCENT),(x,sy))
                    chrome.wrapped(screen,label,self.small,(x,sy+self.small.get_linesize(),width-44,self.small.get_linesize()+2))
                screen.set_clip(old)
            if self.page=='world':
                toggles=[r for r in rows if r[4]]
                actions=[r for r in rows if not r[4] and r[0] not in ('grow','shrink','noise','map')]
                tile_h=max(82,self.small.get_linesize()*2+42);tile_w=(width-52)//2
                toggle_height=((len(toggles)+1)//2)*(tile_h+8)
                self.max_scroll=max(0,toggle_height+34+len(actions)*(row_h+6)-self.list_rect.height)
                self.scroll=self.scroller.update(self.max_scroll,self.visibility.reduced_motion)
                old=screen.get_clip();screen.set_clip(self.list_rect)
                colors={'rain':(121,177,213),'snow':(190,222,234),'sun':(225,189,107),'lighting':(225,189,107),'clouds':(173,185,195),'sky':(150,170,211),'flow':(113,188,180),'horror_rain':(191,110,114)}
                for i,(action,label,route,args,field) in enumerate(toggles):
                    value=bool(getattr(app,field));rect=pygame.Rect(x+(i%2)*(tile_w+8),self.list_rect.y+(i//2)*(tile_h+8)-self.scroll,tile_w,tile_h)
                    self._button(screen,rect,'',action,value)
                    previous=self.tile_levels.get(action,float(value))
                    amount=1 if self.visibility.reduced_motion else min(1,self.frame_dt/.16)
                    level=previous+(float(value)-previous)*amount;self.tile_levels[action]=level
                    background=tuple(round(a+(b-a)*level) for a,b in zip(chrome.CONTROL,chrome.HOVER))
                    pygame.draw.rect(screen,background,rect,border_radius=12)
                    if self.focus==action:pygame.draw.rect(screen,chrome.FOCUS,rect,2,border_radius=12)
                    color=colors.get(action,chrome.ACCENT) if value else chrome.MUTED
                    draw_icon(screen,action,pygame.Rect(rect.x+10,rect.y+8,30,30),color)
                    chrome.wrapped(screen,label,self.small,(rect.x+10,rect.y+40,rect.width-20,self.small.get_linesize()+2),color)
                    screen.blit(self.small.render('On' if value else 'Off',True,color),(rect.right-38,rect.y+12))
                sy=self.list_rect.y+toggle_height-self.scroll
                screen.blit(self.small.render('World actions',True,chrome.MUTED),(x,sy+4))
                for i,(action,label,*_) in enumerate(actions):
                    self._button(screen,(x,sy+34+i*(row_h+6),width-44,row_h),label,action)
                screen.set_clip(old)
            else:
                self.max_scroll=max(0,len(rows)*(row_h+6)-self.list_rect.height)
                self.scroll=self.scroller.update(self.max_scroll,self.visibility.reduced_motion)
                old=screen.get_clip();screen.set_clip(self.list_rect)
                for i,(action,label,route,args,field) in enumerate(rows):
                    value=getattr(app,field,False) if field else False
                    if field:label+=': '+('On' if value is True else 'Off' if value is False else str(value))
                    if route=='preference':
                        value=getattr(self.visibility,args[0]);label+=': '+('On' if value else 'Off')
                    if action=='text_scale':label+=f': {self.text_scale:.0%}'
                    rect=pygame.Rect(x,self.list_rect.y+i*(row_h+6)-self.scroll,width-44,row_h)
                    self._button(screen,rect,label,action,bool(value))
                    if self.page=='tools':
                        pygame.draw.polygon(screen,chrome.HOVER,[(rect.x,rect.y),(rect.x+30,rect.y),(rect.x,rect.y+30)])
                        draw_icon(screen,action,pygame.Rect(rect.x+1,rect.y+1,22,22),chrome.MUTED)
                screen.set_clip(old)
        if self.max_scroll:
            thumb=max(20,round(self.list_rect.height**2/(self.list_rect.height+self.max_scroll)))
            pygame.draw.rect(screen,chrome.MUTED,(box.right-10,self.list_rect.y+round((self.list_rect.height-thumb)*self.scroll/self.max_scroll),3,thumb),border_radius=1)

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
            if event.key==pygame.K_TAB and (ctrl_tab or self.focus):
                actions=[a for _,a,e in self.hits if e]
                if actions:
                    step=-1 if mods&pygame.KMOD_SHIFT else 1
                    self.focus=actions[(actions.index(self.focus)+step)%len(actions)] if self.focus in actions else actions[0]
                    app.searchActive=self.focus=='search'
                self.reveal();return True
            if event.key==pygame.K_ESCAPE:
                if self.confirm:self.confirm=None;return True
                if self.page or self.focus:self.close_drawer(app);return True
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
                if self.shortcuts_rect.collidepoint(pygame.mouse.get_pos()):self.shortcut_scroller.wheel(event,self.shortcut_max)
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

    def act(self,action,app):
        self.reveal()
        if action.startswith('slot:'):
            app.hotbarSelectedSlot=int(action[5:])
            self.select(app.hotbar[app.hotbarSelectedSlot],app,close=False);return
        if action.startswith('block:'):
            self.select(type(app.selectedBlock)[action[6:]],app,close=False);return
        if action.startswith('nav:'):
            page=action[4:]
            if page=='map':self.close_drawer(app);app._openWorldMap();return
            if page=='library':self.close_drawer(app);app.library.open(app,'Structures')
            else:self.open_drawer(page,app)
            return
        if action in ('build','menu'):self.open_drawer(action,app);return
        if action=='library':self.close_drawer(app);app.library.open(app,'Structures');return
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
            if action=='shrink':app._resizeCanvas(-16);return
        elif action=='shrink' and app._canvasResizeImpact(-16)[1]:self.confirm=action;self.focus='confirm:cancel';return
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
                if app._saveBuilding():
                    self.status='Saved';self.error='';self.saved_revision=app.world.revision;self.cue(app,'success')
                else:
                    self.error='Save failed. Your build is still open. Retry Save.';self.cue(app,'failure')
            elif route in ('undo','redo'):
                result=getattr(app.undoManager,route)()
                if result:self.status=route.title()+': '+result.get_description();self.cue(app,'cancel' if route=='undo' else 'select')
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
            if route not in ('preference','text_scale') and action not in ('rain','snow','sun','clouds','lighting','sky','sky_previous','sky_next','flow'):
                self.close_drawer(app)
        except (OSError,ValueError,pygame.error) as error:
            self.error=f'{label} failed: {error}'
