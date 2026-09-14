"""Inline preview shelves and shared image cache for all build libraries."""
from collections import OrderedDict
from pathlib import Path
import time
import pygame
from ui.library import Library
from ui.chrome import panel, wrapped, TEXT, MUTED
from ui.fonts import load_ui_font
from runtime_paths import BUNDLED_DATA_DIR, WORLDS_DIR


class PreviewImages:
    def __init__(self):
        self.images=OrderedDict();self.jobs={};self.failed=set()

    @staticmethod
    def _stage(app,path):
        snapshot=app._readBuildFile(path)[3]
        cells=snapshot.blocks
        # Data preparation only; all Pygame work stays on the display thread.
        visible=[(x,y,z,b) for (x,y,z),b in cells.items()
                 if any(p not in cells for p in ((x+1,y,z),(x,y+1,z),(x,y,z+1)))]
        return sorted(visible,key=lambda row:sum(row[:3]))

    def get(self,app,entry,size=(360,240)):
        kind=entry['kind'];value=entry['value'];key=(entry['key'],size)
        if key in self.images:
            self.images.move_to_end(key);return self.images[key]
        source=self.images.get((entry['key'],(600,400)))
        if source is not None:pass
        elif kind=='biome':source=app.biomePanel.preview(value,app.assetManager,(600,400))
        elif kind=='structure':source=app.structurePreviews.get(value)
        elif kind=='world':
            path=Path(BUNDLED_DATA_DIR)/'world_previews'/(value.scene_id+'.png')
            if path.exists():source=pygame.image.load(str(path)).convert_alpha()
        if source is None and kind in ('world','build'):
            path=str(Path(WORLDS_DIR)/value.filename) if kind=='world' else value.path
            if not path:return None
            jobkey=entry['key']
            if jobkey in self.failed:return None
            if jobkey not in self.jobs:
                # One decoded file at a time, leaving the load executor available.
                if self.jobs:return None
                self.jobs[jobkey]=app.worldLoadExecutor.submit(self._stage,app,path)
            job=self.jobs[jobkey]
            if hasattr(job,'done'):
                if not job.done():return None
                try:
                    rows=job.result()
                    if not rows:raise ValueError('Empty build')
                    left=min((x-y)*32 for x,y,z,b in rows)-32
                    top=min((x+y)*16-z*32 for x,y,z,b in rows)
                    right=max((x-y)*32 for x,y,z,b in rows)+32
                    bottom=max((x+y)*16-z*32 for x,y,z,b in rows)+64
                    scale=min(580/max(1,right-left),380/max(1,bottom-top))
                    surface=pygame.Surface((600,400),pygame.SRCALPHA)
                    offset=((600-(right-left)*scale)/2-left*scale,(400-(bottom-top)*scale)/2-top*scale)
                    job=[iter(rows),surface,scale,offset,{}];self.jobs[jobkey]=job
                except Exception:
                    self.failed.add(jobkey);self.jobs.pop(jobkey,None);return None
            rows,surface,scale,(ox,oy),sprites=job
            deadline=time.perf_counter()+.002
            while time.perf_counter()<deadline:
                row=next(rows,None)
                if row is None:
                    source=surface;self.jobs.pop(jobkey,None)
                    self.images[(entry['key'],(600,400))]=surface
                    break
                x,y,z,b=row
                if b not in sprites:
                    raw=app.assetManager.getBlockSprite(b)
                    sprites[b]=pygame.transform.scale(raw,(max(1,round(raw.get_width()*scale)),max(1,round(raw.get_height()*scale)))) if raw else None
                sprite=sprites[b]
                if sprite:surface.blit(sprite,(round((x-y)*32*scale+ox-sprite.get_width()/2),round(((x+y)*16-z*32)*scale+oy)))
            if source is None:return None
        if source is None:return None
        ratio=min(size[0]/source.get_width(),size[1]/source.get_height())
        result=pygame.Surface(size,pygame.SRCALPHA)
        fitted=pygame.transform.scale(source,(max(1,round(source.get_width()*ratio)),max(1,round(source.get_height()*ratio))))
        result.blit(fitted,fitted.get_rect(center=result.get_rect().center))
        self.images[key]=result
        while len(self.images)>160:self.images.popitem(last=False)
        return result


class PreviewBrowser:
    SECTIONS=('Worlds','Biomes','Structures')
    def __init__(self):
        self.catalog=Library();self.expanded=None;self.hits=[];self.hovered=None
        self.filter='All';self.font=load_ui_font(14);self.small=load_ui_font(13)
        self.page=0

    def expand(self,app,section):
        self.expanded=section;self.page=0;self.filter='All'
        if section:
            self.catalog.tab=section;self.catalog.dimension=app.currentDimension
            self.catalog.refresh(app)

    def height(self):
        return 120+(370 if self.expanded else 0)

    def click(self,app,pos):
        for rect,action,value in self.hits:
            if not rect.collidepoint(pos):continue
            app.assetManager.playClickSound()
            if action=='section':
                self.expand(app,None if self.expanded==value else value)
                if self.expanded:app.blocksExpanded=app.experimentalExpanded=False
                app.inventoryScroll=app.inventoryScrollTarget=0
            elif action=='dimension':
                self.catalog.dimension=value;self.catalog.refresh(app);self.page=0
            elif action=='filter':self.filter=value;self.page=0;self.catalog.pending=None
            elif action=='page':self.page+=value
            elif action=='item':
                self.catalog.pending=value
                if value['kind']=='structure':self.catalog.activate(app)
            elif action=='open':self.catalog.activate(app)
            return True
        return False

    def render(self,app,x,y,width):
        self.hits=[];self.hovered=None;clip=app.screen.get_clip();mouse=pygame.mouse.get_pos()
        def button(rect,label,action,value,selected=False,font=None):
            app.assetManager.drawButton(app.screen,rect,label,font or self.small,rect.collidepoint(mouse),selected)
            hit=rect.clip(clip)
            if hit.width and hit.height:self.hits.append((hit,action,value))
        for section in self.SECTIONS:
            rect=pygame.Rect(x+8,y,width-16,35)
            app.lessonControlRects[section.lower()]=rect
            button(rect,section,'section',section,self.expanded==section,app.sectionFont);y+=40
            if self.expanded!=section:continue
            if section in ('Worlds','Biomes'):
                for i,(key,label) in enumerate((('overworld','Overworld'),('nether','Nether'),('end','End'))):
                    button(pygame.Rect(x+10+i*(width-20)//3,y,(width-26)//3,27),label,'dimension',key,self.catalog.dimension==key)
                y+=33
                entries=self.catalog.entries
            else:
                groups=('All','Buildings','Nature')
                for i,label in enumerate(groups):button(pygame.Rect(x+10+i*(width-20)//3,y,(width-26)//3,27),label,'filter',label,self.filter==label)
                y+=33
                def nature(entry):return any(token in entry['key'] for token in ('tree','forest','mushroom','coral'))
                entries=[e for e in self.catalog.entries if self.filter=='All' or nature(e)==(self.filter=='Nature')]
            pages=max(1,(len(entries)+5)//6);self.page=max(0,min(pages-1,self.page))
            cw=(width-26)//2
            for i,entry in enumerate(entries[self.page*6:self.page*6+6]):
                tile=pygame.Rect(x+10+(i%2)*(cw+6),y+(i//2)*92,cw,87)
                if not tile.colliderect(clip):continue
                button(tile,'','item',entry,self.catalog.pending==entry)
                art=app.previewImages.get(app,entry,(cw-8,55))
                if art:app.screen.blit(art,(tile.x+4,tile.y+3))
                else:wrapped(app.screen,'Preparing...',self.small,(tile.x+4,tile.y+15,cw-8,20),MUTED)
                wrapped(app.screen,entry['name'],self.small,(tile.x+5,tile.y+58,cw-10,28))
                if tile.clip(clip).collidepoint(mouse):self.hovered=entry
            y+=276
            button(pygame.Rect(x+10,y,30,26),'<','page',-1)
            text=self.small.render(f'{self.page+1} / {pages}',True,MUTED)
            app.screen.blit(text,text.get_rect(center=(x+width//2,y+13)))
            button(pygame.Rect(x+width-40,y,30,26),'>','page',1);y+=30
            if section!='Structures':
                button(pygame.Rect(x+10,y,width-20,27),'Open scene' if self.catalog.pending else 'Choose a preview','open',None,bool(self.catalog.pending))
            else:wrapped(app.screen,'Choose a build, then click to place.',self.small,(x+10,y,width-20,27),MUTED)
            y+=31
        return y

    def render_hover(self,app):
        if not self.hovered or app.library.visible:return
        entry=self.hovered;w=380;h=296
        rect=pygame.Rect(app._worldViewportRight()-w-12,max(48,min(app.screen.get_height()-h-85,pygame.mouse.get_pos()[1]-h//2)),w,h)
        panel(app.screen,rect,app.assetManager)
        art=app.previewImages.get(app,entry,(w-24,230))
        if art:app.screen.blit(art,(rect.x+12,rect.y+10))
        wrapped(app.screen,entry['name'],app.smallFont,(rect.x+14,rect.bottom-50,w-28,44))
