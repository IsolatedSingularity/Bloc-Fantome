"""Opt-in native workshop study. Editing and modal owners stay in the app.

Enable with BLOC_WORKSHOP_PREVIEW=stone or glass. This review slice deliberately
retains the complete right-hand palette until the owner accepts the shell.
"""
from dataclasses import dataclass
import pygame
from ui.chrome import panel, wrapped, TEXT, MUTED
from ui.fonts import load_ui_font
from engine.input_commands import Command


@dataclass
class Visibility:
    last_activity: float = 0
    alpha: float = 1
    pinned: bool = False
    always: bool = False
    reduced_motion: bool = False

    def update(self, now, dt, occupied=False):
        if occupied:self.last_activity=now
        target=1.0 if occupied or self.pinned or self.always or now-self.last_activity<4 else 0.0
        step=max(0,dt)/.18
        self.alpha=target if self.reduced_motion else min(target,self.alpha+step) if target>self.alpha else max(target,self.alpha-step)
        return self.alpha


class Workshop:
    def __init__(self, variant='stone', text_scale=1):
        self.variant=variant
        self.font=load_ui_font(round(17*text_scale))
        self.small=load_ui_font(round(14*text_scale))
        self.title=load_ui_font(round(22*text_scale))
        self.visibility=Visibility(last_activity=pygame.time.get_ticks()/1000)
        self.hits=[];self.panels=[];self.context=pygame.Rect(0,0,0,0)
        self.captured=set();self.focus=None;self.menu=False
        self.last_time=pygame.time.get_ticks()/1000
        self.legacy=False
        self.error='';self.status='';self.saved_revision=None

    @staticmethod
    def active(app):
        return not (getattr(getattr(app,'workshop',None),'legacy',False) or app.openingScene or app.worldMapActive or app.redstoneLabActive or app.tutorialScreen.visible)

    @staticmethod
    def operation(app):
        states=[label for field,label in (
            ('fillToolActive','Fill: choose two corners'),('selectionActive','Selection'),
            ('replaceMode','Replace'),('stampMode','Stamp'),('blueprintMode','Blueprint'),
            ('measurementMode','Measure'),('structurePlacementMode','Place structure'),
            ('mirrorModeX','Mirror X'),('mirrorModeY','Mirror Y'),('magicWandMode','Wand'))
            if getattr(app,field,False)]
        if app.brushSize!=1:states.append(f'Brush {app.brushSize} x {app.brushSize}')
        if app.radialSymmetry:states.append(f'Radial {app.radialSymmetry}')
        if app.layerViewEnabled:states.append(f'Layer {app.currentViewLayer}')
        return ' | '.join(states)

    def _surface(self,screen,rect,assets):
        if self.variant=='stone':
            panel(screen,rect,assets,accent=(182,174,151))
        else:
            glass=pygame.Surface(rect.size,pygame.SRCALPHA)
            glass.fill((18,34,42,236));screen.blit(glass,rect)
            pygame.draw.rect(screen,(109,146,153),rect,1)
            pygame.draw.line(screen,(177,197,190),rect.topleft,(rect.right-1,rect.top))

    def render(self,app):
        screen=app.screen;w,h=screen.get_size();right=app._worldViewportRight()
        now=pygame.time.get_ticks()/1000;dt=now-self.last_time;self.last_time=now
        mouse=pygame.mouse.get_pos();self.hits=[];self.panels=[]
        # One measured rectangle is the drawing, focus and input owner.
        def button(rect,label,action,selected=False,enabled=True,target=None):
            target=target or screen
            app.assetManager.drawButton(target,rect,label,self.small,enabled and rect.collidepoint(mouse),selected)
            if not enabled:
                veil=pygame.Surface(rect.size,pygame.SRCALPHA);veil.fill((15,18,20,115));target.blit(veil,rect)
            self.hits.append((rect,action,enabled))
            if self.focus==action:pygame.draw.rect(target,(236,218,161),rect.inflate(4,4),2)
        topbar=pygame.Rect(12,12,right-24,53)
        self._surface(screen,topbar,app.assetManager);self.panels.append(topbar)
        x=22
        for label,action,width in [('Build','build',70),('Library','library',85),('Menu','menu',70),('Show controls','reveal',134)]:
            button(pygame.Rect(x,22,width,32),label,action);x+=width+7
        button(pygame.Rect(right-105,22,80,32),'Save','save')
        # Camera controls are permanent, far from the work and context fade.
        for i,(label,action) in enumerate((('Q','left'),('Fit','fit'),('E','right'))):
            button(pygame.Rect(right-158+i*48,h-112,44,30),label,action)
        name=app.world.catalog.definitions[app.selectedBlock].name
        mode='Interact' if app.interactionMode else 'Build'
        identity=pygame.Rect(12,h-119,min(310,right-190),43)
        self._surface(screen,identity,app.assetManager);self.panels.append(identity)
        wrapped(screen,f'{mode} / {name}',self.font,(24,h-109,min(286,right-214),29))
        # Glass composes the options beside the material dock; stone groups
        # the workflow vertically near the persistent anchors.
        ch=182 if self.small.get_height()<22 else 220
        self.context=pygame.Rect(12,78,306,ch) if self.variant=='stone' else pygame.Rect(12,h-132-ch,306,ch)
        operation=self.operation(app)
        occupied=(self.context.collidepoint(mouse) or self.focus is not None or bool(self.captured)
                  or bool(operation) or bool(self.error) or self.menu or app.panning or bool(app.draggingSlider))
        alpha=self.visibility.update(now,dt,occupied)
        if alpha>0:
            # Render at final text size, then change opacity only.
            layer=pygame.Surface(screen.get_size(),pygame.SRCALPHA)
            self._surface(layer,self.context,app.assetManager)
            x,y=self.context.x+14,self.context.y+14
            sprite=app.assetManager.getBlockSprite(app.selectedBlock)
            if sprite:layer.blit(sprite,(x,y))
            wrapped(layer,name,self.font,(x+76,y+8,198,48));y+=70
            definition=app.world.catalog.definitions[app.selectedBlock]
            if definition.isStair or definition.isSlab:
                label='Half: '+app.previewSlabPosition.name.title()
                button(pygame.Rect(x,y,132,30),label,'half',target=layer)
                button(pygame.Rect(x+140,y,132,30),'Turn '+app.previewFacing.name.title(),'turn',target=layer)
            else:
                button(pygame.Rect(x,y,132,30),'Fill corners','fill',app.fillToolActive,target=layer)
                button(pygame.Rect(x+140,y,132,30),'Mirror X','mirror',app.mirrorModeX,target=layer)
            y+=39
            button(pygame.Rect(x,y,132,30),'Undo','undo',enabled=app.undoManager.can_undo(),target=layer)
            button(pygame.Rect(x+140,y,132,30),'Redo','redo',enabled=app.undoManager.can_redo(),target=layer)
            layer.set_alpha(round(alpha*255));screen.blit(layer,(0,0))
        if operation:
            rect=pygame.Rect(12,self.context.bottom+10 if self.variant=='stone' else 78,max(306,right-24),47)
            self._surface(screen,rect,app.assetManager);wrapped(screen,operation+' | Esc cancels',self.small,rect.inflate(-20,-12))
            self.panels.append(rect)
        if self.menu:
            box=pygame.Rect(12,78,306,381);self._surface(screen,box,app.assetManager)
            self.panels.append(box)
            actions=[('Pin controls','pin'),('Always visible','always'),('Reduced motion','motion'),
                     ('Settings','settings'),('Controls / shortcuts','help'),('World Map','map'),
                     ('Tutorial','tutorial'),('Redstone Lab','lab'),('Original HUD / Ctrl+Tab','legacy')]
            for i,(label,action) in enumerate(actions):
                selected={'pin':self.visibility.pinned,'always':self.visibility.always,'motion':self.visibility.reduced_motion}.get(action,False)
                button(pygame.Rect(26,91+i*39,278,31),label,action,selected)
        message=self.error or self.status
        if message:
            rect=pygame.Rect(12,h-166,max(306,right-190),38)
            self._surface(screen,rect,app.assetManager)
            self.panels.append(rect)
            wrapped(screen,message,self.small,rect.inflate(-20,-10),(255,201,166) if self.error else TEXT)

    def handle_event(self,event,app):
        ctrl_tab=(event.type==pygame.KEYDOWN and event.key==pygame.K_TAB and getattr(event,'mod',0)&pygame.KMOD_CTRL)
        if self.legacy and ctrl_tab:
            self.legacy=False;self.visibility.last_activity=pygame.time.get_ticks()/1000
            return True
        if not self.active(app):return False
        if getattr(app,'searchActive',False) or getattr(app,'historyPanelOpen',False):
            self.focus=None
            return False
        if event.type==pygame.WINDOWFOCUSLOST:
            self.captured.clear();self.focus=None;app.panning=False;app.draggingSlider=None
            self.visibility.last_activity=pygame.time.get_ticks()/1000
            return False
        # Plain Tab retains the editor's minimap shortcut until UI focus has
        # explicitly been entered with Ctrl+Tab. Escape releases that focus.
        if event.type==pygame.KEYDOWN and event.key==pygame.K_TAB and (ctrl_tab or self.focus):
            actions=[a for _,a,enabled in self.hits if enabled]
            if actions:
                step=-1 if getattr(event,'mod',0)&pygame.KMOD_SHIFT else 1
                self.focus=actions[(actions.index(self.focus)+step)%len(actions)] if self.focus in actions else actions[0]
            return True
        if event.type==pygame.KEYDOWN and event.key==pygame.K_RETURN and self.focus:
            self.act(self.focus,app);return True
        if event.type==pygame.KEYDOWN and event.key==pygame.K_ESCAPE and (self.menu or self.focus):
            self.menu=False;self.focus=None;return True
        if event.type==pygame.MOUSEBUTTONUP and event.button in self.captured:
            self.captured.discard(event.button);return True
        if event.type==pygame.MOUSEMOTION and self.captured:return True
        if event.type==pygame.MOUSEBUTTONDOWN:
            # The last drawn frame owns the entire gesture, including a fade.
            for rect,action,enabled in reversed(self.hits):
                if rect.collidepoint(event.pos):
                    self.captured.add(event.button)
                    self.visibility.last_activity=pygame.time.get_ticks()/1000
                    if event.button==1 and enabled:self.act(action,app)
                    return True
            if (any(rect.collidepoint(event.pos) for rect in self.panels) or
                    (self.visibility.alpha>0 and self.context.collidepoint(event.pos)) or
                    (self.menu and pygame.Rect(12,78,306,381).collidepoint(event.pos))):
                self.captured.add(event.button);return True
            self.focus=None
        return False

    def act(self,action,app):
        self.visibility.last_activity=pygame.time.get_ticks()/1000
        if action=='build':app.blocksExpanded=True;app.inventoryScroll=app.inventoryScrollTarget=0
        elif action=='library':app.library.open(app,'Structures')
        elif action=='menu':self.menu=not self.menu
        elif action=='legacy':self.legacy=True;self.menu=False;self.focus=None
        elif action=='reveal':self.visibility.alpha=1
        elif action in ('pin','always','motion'):
            field={'pin':'pinned','always':'always','motion':'reduced_motion'}[action]
            setattr(self.visibility,field,not getattr(self.visibility,field))
        elif action=='settings':app.settingsMenuOpen=True;self.menu=False
        elif action=='help':app.showShortcutsPanel=True;self.menu=False
        elif action=='map':app._openWorldMap();self.menu=False
        elif action=='tutorial':app._beginTutorial(advanced=False);self.menu=False
        elif action=='lab':app._toggleRedstoneLab();self.menu=False
        elif action in ('half','fill','mirror','fit'):
            app._executeInputCommand({'half':Command.FLIP_PREVIEW_HALF,'fill':Command.TOGGLE_FILL,
                'mirror':Command.TOGGLE_X_MIRROR,'fit':Command.FIT_WORLD}[action])
        elif action=='turn':app.previewFacing=type(app.previewFacing)((app.previewFacing.value+1)%4)
        elif action in ('left','right'):app._rotateViewAndRecenter(-1 if action=='left' else 1)
        elif action in ('undo','redo'):
            result=getattr(app.undoManager,action)()
            if result:self.status=action.title()+': '+result.get_description()
        elif action=='save':
            if app._saveBuilding():self.status='Saved';self.error='';self.saved_revision=app.world.revision
            else:self.error='Save failed. Your build is still open. Retry Save.'
