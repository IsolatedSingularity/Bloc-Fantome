"""Viewport-cached, native-size atlas rendering of vanilla selector captures."""
import math
import hashlib
import json
from collections import defaultdict
import pygame

from engine.world_map_regions import REGION_ROOT, load_region


class SourceMap:
    def __init__(self, dimension, key):
        data = load_region(dimension, key)
        self.origin = tuple(data["origin"])
        self.dimension = dimension
        self.presentation = data["presentation"]
        records = sorted(data["blocks"], key=lambda r: r[0]+r[1]+r[2])
        self.height_scale = 0.6 if dimension == 'nether' else 1.0
        self.records = tuple(((x-z)*32, (x+z)*16-y*38*self.height_scale, pid) for x,z,y,pid in records)
        self.bins=defaultdict(list)
        for index,(x,y,_pid) in enumerate(self.records):
            self.bins[(x//1024,y//1024)].append(index)
        self.projected_bounds = (
            min(p[0] for p in self.records)-64, min(p[1] for p in self.records)-36,
            max(p[0] for p in self.records)+64, max(p[1] for p in self.records)+108,
        )
        self.palette = data["palette"]
        manifest=json.loads((REGION_ROOT/'atlas.json').read_text())
        if manifest['palettes'][f'{dimension}_{key}.json.gz'] != hashlib.sha256(json.dumps(self.palette,sort_keys=True).encode()).hexdigest():
            raise ValueError('World Map capture and model atlas are out of sync; rebake the source atlas')
        self.atlas = pygame.image.load(str(REGION_ROOT / f"{dimension}_{key}.png")).convert_alpha()
        self.sprites = []
        for index in range(len(self.palette)):
            cell = self.atlas.subsurface(((index%16)*128,(index//16)*208,128,208))
            bounds = cell.get_bounding_rect()
            self.sprites.append((cell.subsurface(bounds).copy(), (bounds.x-64,bounds.y-96)))
        self.scaled = {}
        self.cache_key = None
        self.surface = None
        self.crystals = tuple(tuple(e["Pos"]) for e in data["entities"] if e["id"] == "minecraft:end_crystal")
        self.crystal_sprites=[]
        if self.crystals:
            atlas=pygame.image.load(str(REGION_ROOT/'end_crystals.png')).convert_alpha()
            for index in range(25):
                cell=atlas.subsurface(((index%16)*128,(index//16)*208,128,208))
                bounds=cell.get_bounding_rect()
                self.crystal_sprites.append((cell.subsurface(bounds).copy(),(bounds.x-64,bounds.y-96)))
        self.crystal_scaled={}
        emissive={i for i,p in enumerate(data['palette']) if p['Name'] in ('minecraft:lava','minecraft:shroomlight','minecraft:glowstone')}
        emitters=[r for r in self.records if r[2] in emissive]
        self.glows=emitters[::max(1,len(emitters)//32)][:32]
        self.glow=pygame.Surface((48,48),pygame.SRCALPHA)
        for radius in range(23,0,-1):
            pygame.draw.circle(self.glow,(218,91,23,round((24-radius)*.35)),(24,24),radius)
        self.backdrop=None
        self.water_atmosphere=None

    def frame_overview(self, renderer, size):
        width,height=size
        left,top,right,bottom=self.projected_bounds
        zoom=min((width-64)/(right-left),(height-230)/(bottom-top))
        renderer.setZoom(max(.025,min(1.0,zoom)))
        renderer.offsetX=width/2-(left+right)/2*renderer.zoomLevel
        renderer.offsetY=(height+8)/2-(top+bottom)/2*renderer.zoomLevel

    def render(self, screen, renderer):
        if self.backdrop is None or self.backdrop.get_size()!=screen.get_size():
            width,height=screen.get_size()
            self.backdrop=pygame.Surface((width,height),pygame.SRCALPHA)
            color={'nether':(105,47,23),'end':(69,40,99),
                   'overworld':(76,110,79),'ocean':(29,107,139)}[self.dimension]
            for y in range(height):
                alpha=round(18*math.sin(math.pi*y/height)**2)
                pygame.draw.line(self.backdrop,(*color,alpha),(0,y),(width,y))
        screen.blit(self.backdrop,(0,0))
        zoom = renderer.zoomLevel
        left,top,right,bottom=self.projected_bounds
        full_width=max(1,math.ceil((right-left)*zoom))
        full_height=max(1,math.ceil((bottom-top)*zoom))
        full_map=full_width*full_height <= 32_000_000
        # Keep a crisp overscanned viewport at close zoom. Small camera changes
        # translate the cached pixels instead of rebuilding thousands of blocks.
        margin = 256
        anchor_x = math.floor(renderer.offsetX/margin)*margin
        anchor_y = math.floor(renderer.offsetY/margin)*margin
        key = (zoom,) if full_map else (screen.get_size(), zoom, anchor_x, anchor_y)
        if key != self.cache_key:
            width,height = (full_width,full_height) if full_map else (screen.get_width()+margin*2,screen.get_height()+margin*2)
            offset_x,offset_y=(-left*zoom,-top*zoom) if full_map else (anchor_x+margin,anchor_y+margin)
            # Assemble downsampled geometry at twice the display resolution.
            # This avoids one-pixel cracks at fractional block zooms; UI text
            # is drawn separately at its final display size.
            factor=2 if width*height<=5_000_000 else 1
            surface = pygame.Surface((width*factor,height*factor),pygame.SRCALPHA)
            scale_key=(zoom,factor)
            if scale_key not in self.scaled:
                self.scaled.clear()
                self.scaled[scale_key] = [
                    (pygame.transform.scale(sprite,(max(1,round(sprite.get_width()*zoom*factor)),max(1,round(sprite.get_height()*zoom*factor)))),
                     (round(offset[0]*zoom*factor),round(offset[1]*zoom*factor)))
                    for sprite,offset in self.sprites
                ]
            sprites = self.scaled[scale_key]
            clip_left,clip_right = -offset_x/zoom-128,(width-offset_x)/zoom+128
            clip_top,clip_bottom = -offset_y/zoom-144,(height-offset_y)/zoom+144
            draws = []
            candidates=self.records
            if not full_map:
                indices=[]
                for bx in range(math.floor(clip_left/1024),math.floor(clip_right/1024)+1):
                    for by in range(math.floor(clip_top/1024),math.floor(clip_bottom/1024)+1):
                        indices.extend(self.bins.get((bx,by),()))
                candidates=(self.records[index] for index in sorted(indices))
            for x,y,pid in candidates:
                if full_map or (clip_left < x < clip_right and clip_top < y < clip_bottom):
                    sprite,offset = sprites[pid]
                    draws.append((sprite,(round((x*zoom+offset_x)*factor)+offset[0],round((y*zoom+offset_y)*factor)+offset[1])))
            surface.blits(draws,doreturn=False)
            self.surface=pygame.transform.smoothscale(surface,(width,height)) if factor==2 else surface
            self.cache_key = key
        screen.blit(self.surface,(round(left*zoom+renderer.offsetX),round(top*zoom+renderer.offsetY)) if full_map else (round(renderer.offsetX-anchor_x-margin),round(renderer.offsetY-anchor_y-margin)))
        if self.dimension == 'ocean':
            if self.water_atmosphere is None or self.water_atmosphere.get_size()!=screen.get_size():
                width,height=screen.get_size()
                self.water_atmosphere=pygame.Surface((width,height),pygame.SRCALPHA)
                for y in range(height):
                    pygame.draw.line(self.water_atmosphere,(7,57,82,45+round(28*y/height)),(0,y),(width,y))
                rays=pygame.Surface((width,height),pygame.SRCALPHA)
                for x in range(-width,width,320):
                    pygame.draw.polygon(rays,(123,213,225,12),((x,0),(x+60,0),(x+height//2+180,height),(x+height//2,height)))
                self.water_atmosphere.blit(rays,(0,0))
            screen.blit(self.water_atmosphere,(0,0))
        if self.dimension=='nether':
            self.glow.set_alpha(round(150+25*math.sin(pygame.time.get_ticks()*.001)))
            for x,y,_pid in self.glows:
                screen.blit(self.glow,(round(x*zoom+renderer.offsetX)-24,round(y*zoom+renderer.offsetY)-24))
        # Source-defined entity cuboids, atlas UVs, rotation, and bobbing.
        # EndCrystalEntityRenderer.getYOffset: (g*g+g)*.4-1.4.
        ticks = pygame.time.get_ticks()/50
        if self.crystals and zoom not in self.crystal_scaled:
            self.crystal_scaled.clear()
            self.crystal_scaled[zoom]=[(pygame.transform.scale(sprite,(max(1,round(sprite.get_width()*zoom)),max(1,round(sprite.get_height()*zoom)))),(round(offset[0]*zoom),round(offset[1]*zoom))) for sprite,offset in self.crystal_sprites]
        for index,(x,y,z) in enumerate(self.crystals):
            g=math.sin(ticks*.2)/2+.5
            bob=(g*g+g)*.4-1.4
            for frame,height in ((24,y),(int(ticks//5)%24,y+bob)):
                px,py=renderer.worldToScreen(x-self.origin[0],z-self.origin[1],height)
                sprite,offset=self.crystal_scaled[zoom][frame]
                screen.blit(sprite,(px+offset[0],py+offset[1]))
