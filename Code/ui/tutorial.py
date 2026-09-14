"""Movable Minecraft tutorial panel with three navigation buttons."""
from collections import Counter
import json
import os
import pygame
from engine.tutorial_lessons import TOUR, OPTIONAL_HORROR
from ui.fonts import load_ui_font
from ui.chrome import panel, wrapped, TEXT, MUTED

class GuidedTutorialMixin:
    guided=True
    TUTORIAL_STEPS=TOUR
    def __init__(self,*args,**kwargs):
        self.completed=set();self.counts=Counter();self.menuOpen=False;self.menuPage=0
        self.hintVisible=True;self.retryRequested=False;self.optionsOpen=False
        self.extraRects={};self.menuRects=[];self.highlightRect=None;self.baseline=None
        self.optional=False;self.anomalyShown=False
        super().__init__(*args,**kwargs)
        self.titleFont=load_ui_font(21,bold=True)
        self.contentFont=load_ui_font(17)
        self.smallFont=load_ui_font(15)
        self.setAdvanced(False)
    def _loadConfig(self):
        from runtime_paths import BASE_DIR
        self.configPath=os.path.join(BASE_DIR,'.tutorial_config.json')
        try:
            with open(self.configPath,encoding='utf-8') as f:data=json.load(f)
            self.showOnStartup=bool(data.get('showOnStartup',True))
        except (OSError,ValueError,TypeError):self.showOnStartup=True
    def _saveConfig(self):
        try:
            with open(self.configPath+'.tmp','w',encoding='utf-8') as f:
                json.dump({'showOnStartup':self.showOnStartup,'guidedVersion':2},f)
            os.replace(self.configPath+'.tmp',self.configPath)
        except OSError:pass
    def setAdvanced(self,advanced):
        self.advanced=bool(advanced);self.TUTORIAL_STEPS=TOUR
        self.currentStep=min(getattr(self,'currentStep',0),len(TOUR)-1)
        self.panelWidth=336;self.panelHeight=366
        self.panelX=14;self.panelY=64
        self._layoutPanelControls()
    def resize(self,width,height):
        self.screenWidth,self.screenHeight=width,height
        self.panelX=max(8,min(width-self.panelWidth-8,self.panelX))
        self.panelY=max(8,min(height-self.panelHeight-8,self.panelY))
        self._layoutPanelControls()
    def _layoutPanelControls(self):
        super()._layoutPanelControls()
        x=self.panelX+14;y=self.panelY+self.panelHeight-70
        self.backButtonRect=pygame.Rect(x,y,96,30)
        self.nextButtonRect=pygame.Rect(x+106,y,96,30)
        self.skipButtonRect=pygame.Rect(x+212,y,96,30)
        self.checkboxRect=pygame.Rect(x,y+44,14,14)
        self.optionalRect=pygame.Rect(x,y-26,308,21)
    def advancedHotbarNames(self,index):return tuple(TOUR[index]['icons'])
    def show(self):
        self.visible=True;self.minimized=False;self.dragging=False;self.menuOpen=False
        self.selectLesson(0)
    def selectLesson(self,index,retry=False):
        self.optional=False;self.currentStep=max(0,min(index,len(TOUR)-1))
        self.menuOpen=False;self.lessonStarted=True;self.retryRequested=retry
        self.counts.clear();self.baseline=None;self.highlightRect=None
        if self.onStepChange:self.onStepChange(self.currentStep)
        self.retryRequested=False
    @property
    def lesson(self):return OPTIONAL_HORROR if self.optional else TOUR[self.currentStep]
    def record(self,action,amount=1):
        if self.visible:self.counts[action]+=amount
    def complete(self):return True
    def _onNextClick(self):
        if self.optional or self.currentStep==len(TOUR)-1:self.hide()
        else:self.selectLesson(self.currentStep+1)
    def _onBackClick(self):
        if self.optional:self.selectLesson(len(TOUR)-1)
        elif self.currentStep:self.selectLesson(self.currentStep-1)
    def observe(self,app):
        focus=self.lesson.get('focus');self.highlightRect=None
        if focus in ('blocks','toggles','structures','worlds','biomes','terrain'):
            self.highlightRect=getattr(app,'lessonControlRects',{}).get(focus)
        elif focus=='settings':self.highlightRect=getattr(app,'settingsGearRect',None)
    def _playClickSound(self):
        if self.assetManager:self.assetManager.playClickSound()
    def handleEvent(self,event):
        if not self.visible:return False
        if self.minimized:
            if event.type==pygame.MOUSEBUTTONDOWN and event.button==1 and self._restoreTileRect().collidepoint(event.pos):
                self.minimized=False;return True
            return False
        if event.type==pygame.MOUSEBUTTONUP and event.button==1 and self.dragging:
            self.dragging=False;return True
        if event.type==pygame.MOUSEMOTION and self.dragging:self._movePanel(*event.pos);return True
        rect=pygame.Rect(self.panelX,self.panelY,self.panelWidth,self.panelHeight)
        if event.type==pygame.MOUSEWHEEL and rect.collidepoint(pygame.mouse.get_pos()):return True
        if event.type!=pygame.MOUSEBUTTONDOWN or not rect.collidepoint(event.pos):return False
        if event.button!=1:return True
        if self.minimizeButtonRect.collidepoint(event.pos):self.minimized=True
        elif self.titleBarRect.collidepoint(event.pos):
            self.dragging=True;self.dragOffset=(event.pos[0]-self.panelX,event.pos[1]-self.panelY)
        elif self.checkboxRect.collidepoint(event.pos):self.showOnStartup=not self.showOnStartup;self._saveConfig()
        elif self.backButtonRect.collidepoint(event.pos):self._onBackClick()
        elif self.nextButtonRect.collidepoint(event.pos):self._onNextClick()
        elif self.skipButtonRect.collidepoint(event.pos):self.hide()
        elif self.currentStep==len(TOUR)-1 and not self.optional and self.optionalRect.collidepoint(event.pos):
            self.optional=True
            if self.onStepChange:self.onStepChange(self.currentStep)
        else:return True
        self._playClickSound();return True
    def _button(self,screen,rect,label,active=False):
        if self.assetManager:self.assetManager.drawButton(screen,rect,label,self.smallFont,rect.collidepoint(pygame.mouse.get_pos()),active)
        else:
            pygame.draw.rect(screen,(95,95,95),rect)
            screen.blit(self.smallFont.render(label,True,TEXT),rect.move(8,5))
    def render(self,screen):
        if not self.visible:return
        if self.minimized:return
        if self.highlightRect:
            pygame.draw.rect(screen,(215,202,145),self.highlightRect.clip(screen.get_rect()).inflate(4,4),2)
        x,y=self.panelX,self.panelY;w=self.panelWidth
        panel(screen,(x,y,w,self.panelHeight),self.assetManager)
        label='OPTIONAL DETOUR' if self.optional else f'TUTORIAL  {self.currentStep+1} / {len(TOUR)}'
        self._button(screen,pygame.Rect(x+8,y+8,w-46,30),label)
        self._button(screen,self.minimizeButtonRect,'-')
        area=pygame.Rect(x+16,y+52,w-32,self.backButtonRect.top-y-63)
        old=screen.get_clip();screen.set_clip(area)
        yy=wrapped(screen,self.lesson['title'],self.titleFont,area)
        yy=wrapped(screen,self.lesson['content'][0],self.contentFont,(area.x,yy+12,area.width,100))
        pygame.draw.line(screen,(95,86,72),(area.x,yy+8),(area.right,yy+8))
        yy=wrapped(screen,self.lesson['hint'],self.smallFont,(area.x,yy+19,area.width,area.bottom-yy-19),MUTED)
        screen.set_clip(old)
        if self.currentStep==len(TOUR)-1 and not self.optional:
            screen.blit(self.smallFont.render('Optional: visit the abandoned chapel >',True,(202,185,145)),self.optionalRect)
        self._button(screen,self.backButtonRect,'Back')
        self._button(screen,self.nextButtonRect,'Finish' if self.currentStep==len(TOUR)-1 else 'Next',True)
        self._button(screen,self.skipButtonRect,'Leave')
        pygame.draw.rect(screen,(115,115,115),self.checkboxRect,2)
        if self.showOnStartup:pygame.draw.rect(screen,(220,210,166),self.checkboxRect.inflate(-6,-6))
        screen.blit(self.smallFont.render('Show on launch',True,MUTED),(self.checkboxRect.right+8,self.checkboxRect.y-1))
