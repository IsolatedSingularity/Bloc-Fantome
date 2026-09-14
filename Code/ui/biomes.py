"""Dimension-filtered biome cards rendered from the same cells opened in editor."""
from collections import OrderedDict

import pygame

from domain.blocks import BlockType
from engine.biome_catalog import BIOMES, BY_ID
from ui.fonts import load_ui_font
from runtime_paths import BUNDLED_DATA_DIR
from pathlib import Path

# Editorial familiarity order, with related variants grouped after their family.
FAMILIES=('plains','forest','desert','taiga','mountains','swamp','jungle','savanna',
          'ocean','river','beach','shore','badlands','mushroom','nether_wastes',
          'crimson_forest','warped_forest','soul_sand_valley','basalt_deltas',
          'the_end','end_highlands','end_midlands','small_end_islands','end_barrens')
UNUSED={'the_void','deep_warm_ocean','mountain_edge'}

# A small, intentional set per recognizable landscape family. The full source
# catalog and captures remain available for imports, saves and reference work.
BIOME_FAMILIES = {
    'Plains': ('plains', 'sunflower_plains'),
    'Forest': ('forest', 'flower_forest'),
    'Birch forest': ('birch_forest',),
    'Dark forest': ('dark_forest',),
    'Desert': ('desert',),
    'Taiga': ('taiga', 'giant_tree_taiga'),
    'Snow': ('snowy_tundra', 'ice_spikes'),
    'Snowy taiga': ('snowy_taiga',),
    'Mountains': ('mountains', 'wooded_mountains'),
    'Swamp': ('swamp',),
    'Jungle': ('jungle', 'bamboo_jungle'),
    'Savanna': ('savanna', 'shattered_savanna'),
    'Ocean': ('ocean', 'warm_ocean'),
    'Frozen ocean': ('frozen_ocean',),
    'River': ('river', 'frozen_river'),
    'Beach': ('beach', 'stone_shore'),
    'Badlands': ('badlands', 'eroded_badlands'),
    'Mushroom': ('mushroom_fields',),
    'Nether wastes': ('nether_wastes',),
    'Crimson forest': ('crimson_forest',),
    'Warped forest': ('warped_forest',),
    'Soul sand valley': ('soul_sand_valley',),
    'Basalt deltas': ('basalt_deltas',),
    'Central End': ('the_end',),
    'Outer End': ('end_highlands', 'small_end_islands'),
}
CURATED_IDS = tuple(name for names in BIOME_FAMILIES.values() for name in names)

def familiar_order(entry):
    name=entry['id']
    if entry['dimension']=='nether':
        return (False,('nether_wastes','crimson_forest','warped_forest','soul_sand_valley','basalt_deltas').index(name),False,name)
    if entry['dimension']=='end':
        return (False,('the_end','end_highlands','end_midlands','small_end_islands','end_barrens').index(name),False,name)
    family=next((i for i,f in enumerate(FAMILIES) if f in name),len(FAMILIES))
    return (name in UNUSED,family,name not in FAMILIES,name)


class BiomePanel:
    STRIDE = 210
    def __init__(self):
        self.expanded = False
        self.pending = None
        self.dimension = None
        self.cards = []
        self.previews = OrderedDict()
        self.header = pygame.Rect(0,0,0,0)
        self.confirm = pygame.Rect(0,0,0,0)
        self.cancel = pygame.Rect(0,0,0,0)
        self.font = load_ui_font(15)
        self.small = load_ui_font(12)
        self.scroll=0
        self.browser=pygame.Rect(0,0,0,0)
        self.close=pygame.Rect(0,0,0,0)

    def entries(self, dimension):
        return [BY_ID[name] for name in CURATED_IDS if BY_ID[name]['dimension'] == dimension]

    def height(self, dimension):
        return 40

    def handle_event(self,event,app):
        if not self.expanded:return False
        if event.type==pygame.KEYDOWN and event.key==pygame.K_ESCAPE:
            self.expanded=False;return True
        if event.type==pygame.MOUSEWHEEL and self.browser.collidepoint(pygame.mouse.get_pos()):
            self.scroll=max(0,min(self.max_scroll,self.scroll-event.y*70));return True
        if event.type==pygame.MOUSEBUTTONDOWN and self.browser.collidepoint(event.pos):
            if event.button==1:
                if self.close.collidepoint(event.pos):self.expanded=False
                else:
                    action=self.click(event.pos)
                    if action:
                        app.assetManager.playClickSound()
                        if action[0]=='open':app._queueBiomeScene(action[1]['id']);self.expanded=False
            return True
        return False

    def click(self, pos):
        if self.header.collidepoint(pos):
            self.expanded = not self.expanded
            self.pending = None
            return ('handled',None)
        if not self.expanded: return None
        if self.pending and self.confirm.collidepoint(pos):
            entry = self.pending
            self.pending = None
            return ('open',entry)
        if self.pending and self.cancel.collidepoint(pos):
            self.pending = None
            return ('handled',None)
        for rect, entry in self.cards:
            if rect.collidepoint(pos):
                self.pending = entry
                return ('handled',None)
        return None

    def preview(self, entry, assets, size=(460,300)):
        key = (entry['id'],size)
        if key in self.previews:
            self.previews.move_to_end(key)
            return self.previews[key]
        path=Path(BUNDLED_DATA_DIR)/'biome_captures'/f"{entry['id']}.png"
        if path.exists():
            source=pygame.image.load(str(path)).convert_alpha()
            scale=min(size[0]/source.get_width(),size[1]/source.get_height())
            surface=pygame.Surface(size,pygame.SRCALPHA)
            fitted=pygame.transform.smoothscale(source,(round(source.get_width()*scale),round(source.get_height()*scale)))
            surface.blit(fitted,fitted.get_rect(center=surface.get_rect().center))
            self.previews[key]=surface
            while len(self.previews)>18:self.previews.popitem(last=False)
            return surface
        raise FileNotFoundError(f'Missing source biome preview: {path}')

    def render(self, app, x, y, width):
        if self.dimension!=app.currentDimension:
            self.dimension=app.currentDimension
            self.pending=None
            self.scroll=0
        self.header=pygame.Rect(x+8,y,width-16,35)
        app.assetManager.drawButton(app.screen,self.header,'Biomes',app.font,self.header.collidepoint(pygame.mouse.get_pos()),self.expanded,letterSpacing=1)
        return y+40

    def render_browser(self,app):
        if not self.expanded:return
        screen=app.screen
        width=min(560,screen.get_width()-390)
        x=screen.get_width()-width-8;y=68
        self.browser=pygame.Rect(x,y,width,screen.get_height()-y-12)
        from ui.chrome import panel
        panel(screen,self.browser,app.assetManager)
        screen.blit(app.font.render('BIOMES',True,(231,231,205)),(x+16,y+10))
        self.close=pygame.Rect(self.browser.right-42,y+8,30,28)
        app.assetManager.drawButton(screen,self.close,'X',self.font,False,False)
        y+=42
        screen = app.screen
        if self.dimension != app.currentDimension:
            self.dimension = app.currentDimension
            self.pending = None
            self.scroll=0
        self.cards=[]
        self.confirm=pygame.Rect(0,0,0,0)
        self.cancel=pygame.Rect(0,0,0,0)
        screen.blit(self.small.render('Java 1.16.1  /  Captured terrain',True,(187,196,177)),(x+12,y+2))
        if self.pending:
            screen.blit(self.small.render('Open replaces this canvas. Save first.',True,(236,201,146)),(x+12,y+15))

        else:
            screen.blit(self.small.render('Select a scene to preview and open.',True,(166,172,165)),(x+12,y+24))
        y += 48
        old_clip=screen.get_clip()
        viewport=pygame.Rect(x+4,y,width-8,self.browser.bottom-y-5)
        screen.set_clip(viewport)
        entries=self.entries(app.currentDimension)
        self.max_scroll=max(0,((len(entries)+1)//2)*self.STRIDE-viewport.height)
        self.scroll=min(self.scroll,self.max_scroll)
        y-=self.scroll
        made_preview = False
        card_width=(width-27)//2
        for index,entry in enumerate(entries):
            rect=pygame.Rect(x+9+(index%2)*(card_width+9),y+(index//2)*self.STRIDE,card_width,self.STRIDE-8)
            if rect.colliderect(screen.get_clip()):
                self.cards.append((rect.clip(screen.get_clip()),entry))
                selected=self.pending is not None and self.pending['id']==entry['id']
                app.assetManager.drawSlot(screen,rect,selected)
                size=(rect.width-8,130)
                key=(entry['id'],size)
                if key in self.previews or not made_preview:
                    was_cached=key in self.previews
                    image=self.preview(entry,app.assetManager,size)
                    made_preview |= not was_cached
                    screen.blit(image,(rect.x+4,rect.y+3))
                else:
                    screen.blit(self.small.render('Preparing landscape...',True,(139,155,146)),(rect.x+14,rect.y+60))
                if selected:
                    self.confirm=pygame.Rect(rect.x+8,rect.y+99,rect.width-82,27)
                    self.cancel=pygame.Rect(rect.right-66,rect.y+99,58,27)
                    app.assetManager.drawButton(screen,self.confirm,'Open scene',self.font,False,True)
                    app.assetManager.drawButton(screen,self.cancel,'Cancel',self.small,False,False)
                name=entry['id'].replace('_',' ').title()
                words=name.split(); lines=['']
                for word in words:
                    candidate=(lines[-1]+' '+word).strip()
                    if self.font.size(candidate)[0]>rect.width-16: lines.append(word)
                    else: lines[-1]=candidate
                for i,line in enumerate(lines):
                    screen.blit(self.font.render(line,True,(236,232,211)),(rect.x+8,rect.y+134+i*17))
                from engine.biome_capture import manifest
                kind=manifest()[entry['id']]['kind']
                special=kind!='natural'
                label='Minecraft Void preset' if kind=='void_preset' else 'Single-biome generation' if special else 'Natural world capture'
                screen.blit(self.small.render(label,True,(184,164,120) if special else (129,159,145)),(rect.x+8,rect.bottom-21))
                pygame.draw.rect(screen,(177,205,142) if selected else (100,100,100),rect,2 if selected else 1)
        screen.set_clip(old_clip)
        self.confirm=self.confirm.clip(viewport)
        self.cancel=self.cancel.clip(viewport)
        if self.max_scroll:
            track=pygame.Rect(self.browser.right-5,viewport.y,3,viewport.height)
            thumb_height=max(20,round(viewport.height*viewport.height/(viewport.height+self.max_scroll)))
            thumb=pygame.Rect(track.x,track.y+round((track.height-thumb_height)*self.scroll/self.max_scroll),3,thumb_height)
            pygame.draw.rect(screen,(52,62,57),track)
            pygame.draw.rect(screen,(151,177,150),thumb)
