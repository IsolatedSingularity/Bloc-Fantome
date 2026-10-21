"""Native composition studies, deliberately outside the production event loop.

Render: .venv/Scripts/python.exe .qa/pass1-revision2/ui_study.py
Explore: same command with --live (1/2 compare, B/L/T/M open, Esc close).
The study routes preview selection and material properties only. Production
commands are mapped in the accompanying handoff, not silently simulated here.
"""
import os, sys, pathlib, time, json, argparse
from unittest.mock import patch
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'Code'))
os.environ['SDL_VIDEODRIVER'] = 'windows'
import pygame
import blocFantome as b
from ui.fonts import load_ui_font
from ui.workshop import Workshop

OUT = pathlib.Path(__file__).resolve().parent
INK = (235, 237, 230)
MUTED = (163, 178, 178)
ACCENT = (208, 194, 153)


class Study:
    active = staticmethod(lambda app: True)
    def __init__(self, variant='anchored', scale=1):
        self.variant=variant; self.page=''; self.tab='Structures'
        self.font=load_ui_font(round(17*scale)); self.small=load_ui_font(round(14*scale))
        self.title=load_ui_font(round(25*scale)); self.hits=[]; self.panels=[]
        self.focus=0; self.captured=set(); self.scale=scale
        self.tool=''; self.note=''; self.materials=[]

    def text(self, app, text, pos, font=None, color=INK):
        app.screen.blit((font or self.font).render(text, True, color), pos)

    def plane(self, app, rect, alpha=238):
        surface=pygame.Surface(rect.size,pygame.SRCALPHA)
        pygame.draw.rect(surface,(19,28,31,alpha),surface.get_rect(),border_radius=7)
        app.screen.blit(surface,rect)
        self.panels.append(rect)

    def button(self, app, rect, label, action, selected=False):
        rect=pygame.Rect(rect); hover=rect.collidepoint(pygame.mouse.get_pos())
        if selected or hover:
            pygame.draw.rect(app.screen,(50,64,66) if hover else (43,54,56),rect,border_radius=4)
        if selected:pygame.draw.line(app.screen,ACCENT,(rect.x+12,rect.bottom-3),(rect.right-12,rect.bottom-3),2)
        label_img=self.small.render(label,True,ACCENT if selected else INK)
        assert label_img.get_width()<=rect.width-12,(label,rect,self.scale)
        app.screen.blit(label_img,label_img.get_rect(center=rect.center))
        self.hits.append((rect,action))

    def render(self,app):
        w,h=app.screen.get_size();self.hits=[];self.panels=[]
        desk=self.variant=='desk'
        if not desk:self.plane(app,pygame.Rect(24,20,458,46),225)
        else:
            # A soft scrim supports text, with no enclosing frame.
            scrim=pygame.Surface((w,90),pygame.SRCALPHA)
            for y in range(90):pygame.draw.line(scrim,(10,17,20,round(180*(1-y/90))),(0,y),(w,y))
            app.screen.blit(scrim,(0,0))
        for i,label in enumerate(('Build','Library','Tools','World','Menu')):
            self.button(app,(28+i*89,26,87,34),label,label.lower(),self.page==label.lower())
        self.plane(app,pygame.Rect(w-184,20,160,46),220)
        self.button(app,(w-178,26,72,34),'Undo','undo')
        self.button(app,(w-100,26,70,34),'Save','save')
        if self.tool:
            self.plane(app,pygame.Rect(w//2-200,78,400,42))
            self.text(app,self.tool+'   /   Esc cancels',(w//2-184,90),self.small,ACCENT)
        if not self.page:
            # One identity surface with relevant properties, no wrapper around it.
            box=pygame.Rect(24,h-187,320,107)
            if not desk:self.plane(app,box,226)
            else:
                self.plane(app,box,182)
                pygame.draw.line(app.screen,ACCENT,(24,h-183),(24,h-84),2)
            sprite=app.assetManager.getBlockSprite(app.selectedBlock)
            if sprite:app.screen.blit(sprite,(35,h-174))
            self.text(app,'BUILD',(110,h-174),self.small,MUTED)
            self.text(app,app.world.catalog.definitions[app.selectedBlock].name,(110,h-151))
            definition=app.world.catalog.definitions[app.selectedBlock]
            if definition.isStair or definition.isSlab:
                self.button(app,(34,h-117,142,30),'Half: '+app.previewSlabPosition.name.title(),'half')
                self.button(app,(181,h-117,150,30),'Turn: '+app.previewFacing.name.title(),'turn')
            else:
                self.button(app,(34,h-117,142,30),'Fill corners','tool:Fill')
                self.button(app,(181,h-117,150,30),'More tools','tools')
        if not self.page:
            self.plane(app,pygame.Rect(w-172,h-116,148,36),218)
            for i,(label,act) in enumerate((('Q','left'),('Fit','fit'),('E','right'))):
                self.button(app,(w-170+i*48,h-113,45,30),label,act)
        if self.page:self.drawer(app)
        if self.note:self.text(app,self.note,(24,h-220),self.small,ACCENT)

    def drawer(self,app):
        w,h=app.screen.get_size();desk=self.variant=='desk'; library=self.page=='library'
        wide=library or desk
        width=min(w-48,960) if wide else 356
        height=min(h-180,510) if wide else min(h-180,470)
        box=pygame.Rect((w-width)//2 if desk else 24,h-90-height if desk else 82,width,height)
        self.plane(app,box,246);x,y=box.x+22,box.y+18
        self.text(app,self.page.title(),(x,y),self.title)
        self.button(app,(box.right-82,y-2,64,32),'Close','close')
        if library:
            tabw=(width-44)//4
            for i,tab in enumerate(('Worlds','Biomes','Structures','Saved Builds')):
                self.button(app,(x+i*tabw,y+44,tabw-3,34),tab,'tab:'+tab,self.tab==tab)
            listw=round((width-62)*.37); rows_y=y+101
            count=max(1,(height-162)//64)
            for i,entry in enumerate(app.library.entries[:count]):
                rect=pygame.Rect(x,rows_y+i*64,listw,58)
                if entry==app.library.pending:pygame.draw.rect(app.screen,(43,54,56),rect,border_radius=4)
                thumb=app.previewImages.get(app,entry,(72,52))
                if thumb:app.screen.blit(thumb,(rect.x,rect.y+3))
                name=entry['name'];f=self.small
                while f.size(name)[0]>listw-83 and len(name)>3:name=name[:-4]+'...'
                self.text(app,name,(x+80,rect.y+18),f)
                self.hits.append((rect,'entry:'+str(i)))
            entry=app.library.pending
            if entry:
                dx=x+listw+24;dw=box.right-dx-22;ph=max(90,height-224)
                self.text(app,entry['name'],(dx,rows_y),self.font,ACCENT)
                preview=app.previewImages.get(app,entry,(dw,ph))
                if preview:app.screen.blit(preview,(dx,rows_y+34))
                self.text(app,'Preview first. Place when ready.' if entry['kind']=='structure' else 'Preview first. Open when ready.',(dx,box.bottom-75),self.small,MUTED)
                self.button(app,(dx,box.bottom-44,170,32),'Place structure' if entry['kind']=='structure' else 'Open '+self.tab.rstrip('s'),'proposed',True)
            self.text(app,'Browse files...',(x,box.bottom-37),self.small,MUTED)
        elif self.page=='build':
            self.text(app,'Materials',(x,y+52),self.font,ACCENT)
            names=['OAK_PLANKS','OAK_STAIRS','STONE_BRICKS','SMOOTH_QUARTZ','QUARTZ_PILLAR','GLASS','BRICKS','COBBLESTONE','GRASS','DIRT','SAND','WATER']
            self.materials=[getattr(b.BlockType,n) for n in names if hasattr(b.BlockType,n)]
            cols=4 if not desk else 6
            for i,block in enumerate(self.materials):
                rect=pygame.Rect(x+(i%cols)*74,y+89+(i//cols)*75,66,68)
                if block==app.selectedBlock:pygame.draw.rect(app.screen,(54,65,65),rect,border_radius=4)
                sprite=app.assetManager.getIconSprite(block)
                if sprite:app.screen.blit(sprite,sprite.get_rect(center=rect.center))
                self.hits.append((rect,'material:'+str(i)))
            self.text(app,'All materials   /   Search',(x,box.bottom-45),self.small,MUTED)
            if desk:
                self.text(app,'Oak Stairs',(x+500,y+64),self.title,ACCENT)
                self.text(app,'Shape, half and facing appear here.',(x+500,y+108),self.small,MUTED)
                self.text(app,'Select a material, return to building.',(x+500,y+138),self.small,MUTED)
        else:
            choices={
                'tools':['Fill','Select / copy / paste','Replace','Brush / wand','Mirror / radial symmetry','Blueprint / stamp','Measure / layers'],
                'world':['Dimensions','Terrain / canvas size','Weather / time','Lighting / simulation','World Map'],
                'menu':['Save / Save As / Open','History / undo / redo','Tutorial / shortcuts','Redstone Lab','Settings / audio','Pin controls / always show'],
            }[self.page]
            for i,label in enumerate(choices):
                self.button(app,(x,y+56+i*43,min(310,width-44),37),label,'tool:'+label)
            if desk:
                self.text(app,'One task at a time',(x+365,y+70),self.title,ACCENT)
                self.text(app,'Options stay with the selected tool.',(x+365,y+118),self.small,MUTED)
                self.text(app,'Close this desk to recover the canvas.',(x+365,y+150),self.small,MUTED)

    def act(self,action,app):
        self.note=''
        if action in ('build','library','tools','world','menu'):
            self.page='' if self.page==action else action
            if action=='library':app.library.open(app,self.tab);app.library.visible=False;app.library.pending=app.library.entries[0] if app.library.entries else None
        elif action=='close':self.page=''
        elif action.startswith('tab:'):
            self.tab=action[4:];app.library.open(app,self.tab);app.library.visible=False
            app.library.pending=app.library.entries[0] if app.library.entries else None
        elif action.startswith('entry:'):app.library.pending=app.library.entries[int(action[6:])]
        elif action.startswith('material:'):app.selectedBlock=self.materials[int(action[9:])];self.page=''
        elif action=='half':app.previewSlabPosition=type(app.previewSlabPosition)(1-app.previewSlabPosition.value)
        elif action=='turn':app.previewFacing=type(app.previewFacing)((app.previewFacing.value+1)%4)
        elif action=='fit':app._fitWorldToViewport()
        elif action in ('left','right'):app._rotateViewAndRecenter(-1 if action=='left' else 1)
        elif action=='tool:Fill':self.tool='Fill: choose two corners';self.page=''
        else:self.note='Design study: this command remains with the existing editor.'

    def handle(self,event,app):
        if event.type==pygame.KEYDOWN:
            if event.key in (pygame.K_1,pygame.K_2):self.variant='anchored' if event.key==pygame.K_1 else 'desk'
            elif event.key==pygame.K_ESCAPE:self.page='';self.tool='';self.note=''
            elif event.key in (pygame.K_b,pygame.K_l,pygame.K_t,pygame.K_m):self.act({pygame.K_b:'build',pygame.K_l:'library',pygame.K_t:'tools',pygame.K_m:'menu'}[event.key],app)
        if event.type==pygame.MOUSEBUTTONDOWN:
            for rect,action in reversed(self.hits):
                if rect.collidepoint(event.pos):
                    self.captured.add(event.button)
                    if event.button==1:self.act(action,app)
                    return True
            if any(r.collidepoint(event.pos) for r in self.panels):self.captured.add(event.button);return True
        if event.type==pygame.MOUSEBUTTONUP and event.button in self.captured:self.captured.remove(event.button);return True
        if event.type==pygame.MOUSEMOTION and self.captured:return True
        return False


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--live',action='store_true');args=parser.parse_args()
    with patch.object(b,'APP_CONFIG_FILE',str(OUT/'isolated-config.json')),patch.object(b.BlocFantome,'_saveAppConfig'),patch.object(b.TutorialScreen,'_saveConfig'),patch.object(b,'PANEL_WIDTH',0):
        app=b.BlocFantome();app.autoSaveEnabled=False;app.tutorialScreen.visible=False
        app.assetManager.loadAllAssets();app._generateStructurePreviews();app._createInitialFloor()
        app._renderPanel=lambda:None;app._renderPanelBlockTooltip=lambda:None;app._renderStructureTooltip=lambda:None
        app._renderTooltipNotification=lambda:None
        app.selectedBlock=b.BlockType.OAK_STAIRS;app.blocksExpanded=False;app.experimentalExpanded=False
        for x in range(3,9):
            for y in range(3,9):app.world.setBlock(x,y,1,b.BlockType.STONE_BRICKS)
        for x,y in ((3,3),(3,8),(8,3),(8,8)):
            for z in range(2,6):app.world.setBlock(x,y,z,b.BlockType.QUARTZ_PILLAR)
        for x in range(3,9):
            for y in (3,8):app.world.setBlock(x,y,6,b.BlockType.SMOOTH_QUARTZ)
        checks=[]
        try:
            for variant in ('anchored','desk'):
                for size in ((960,640),(1200,800),(1920,1080)):
                    app._applyWindowSize(*size);app._fitWorldToViewport();app.workshop=Study(variant)
                    for page in ('','build','library','tools'):
                        app.workshop.page=''
                        if page:app.workshop.act(page,app)
                        for _ in range(16):app._render();pygame.event.pump()
                        assert all(app.screen.get_rect().contains(r) for r,_ in app.workshop.hits)
                        pygame.image.save(app.screen,OUT/f'{variant}-{page or "quiet"}-{size[0]}.png')
                        checks.append(dict(variant=variant,page=page or 'quiet',size=size,hitboxes_inside=True))
                app._applyWindowSize(960,640);app._fitWorldToViewport();app.workshop=Study(variant,1.25)
                app._render();pygame.image.save(app.screen,OUT/f'{variant}-text125.png')
            app._applyWindowSize(1200,800);app._fitWorldToViewport();app.workshop=Study()
            app.workshop.tool='Fill: choose two corners';app._render();pygame.image.save(app.screen,OUT/'anchored-fill-1200.png')
            app.workshop.tool='';app._render()
            revision=app.world.revision;camera=(app.renderer.offsetX,app.renderer.offsetY,app.zoomLevel)
            for kind,kwargs in [(pygame.MOUSEBUTTONDOWN,dict(button=1,pos=(60,40))),(pygame.MOUSEMOTION,dict(pos=(600,400),rel=(540,360),buttons=(1,0,0))),(pygame.MOUSEBUTTONUP,dict(button=1,pos=(600,400)))]:
                assert app.workshop.handle(pygame.event.Event(kind,**kwargs),app)
            assert revision==app.world.revision and camera==(app.renderer.offsetX,app.renderer.offsetY,app.zoomLevel)
            (OUT/'visual-checks.json').write_text(json.dumps(dict(driver=pygame.display.get_driver(),screens=checks,gesture_captured=True,world_and_camera_unchanged=True,scope='Native design study; not a completed feature migration.'),indent=2))
            app.workshop.page=''
            if args.live:
                pygame.display.set_caption('Bloc Fantome | UI direction study | 1 / 2 compare')
                deadline=time.monotonic()+900
                while time.monotonic()<deadline:
                    events=pygame.event.get()
                    if any(e.type==pygame.QUIT for e in events):break
                    for event in events:app.workshop.handle(event,app)
                    app._render();app.clock.tick(60)
        finally:app.worldLoadExecutor.shutdown(wait=True,cancel_futures=True);pygame.quit()

if __name__=='__main__':main()
