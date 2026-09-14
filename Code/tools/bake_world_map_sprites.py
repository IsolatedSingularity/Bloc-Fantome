"""Bake selector block states from the local 1.16.1 client models/textures.

Uses inherited model elements, multipart connections, and state rotations.
The runtime reads only the resulting atlas, never the reference JAR.
"""
from __future__ import annotations
import gzip
import hashlib
import io
import json
import math
import os
import re
from pathlib import Path
import sys
import zipfile
import numpy as np

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame

CODE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODE))
from engine.model_renderer import BlockModelRenderer
from engine.world_map_regions import NETHER_HEIGHT_SCALE

CELL = (128, 208)
ANCHOR = (64, 96)


def save_atlas(surface, target):
    # OneDrive can briefly hold an existing image open while syncing it.
    # Publish a completed file instead of truncating an atlas in place.
    temporary = target.with_suffix('.pending.png')
    pygame.image.save(surface, temporary)
    temporary.replace(target)


class Baker:
    def __init__(self):
        self.jar = zipfile.ZipFile(CODE.parent / "Game Reference/01_upstream/minecraft-1.16.1-client.jar")
        self.models, self.textures = {}, {}
        self.raster = BlockModelRenderer(64, 32, 38)
        self.height_scale = 1.0
        self.biome_id = None
        self.biome_settings = {}
        biome_root = CODE.parent / 'Game Reference/05_mapped_sources/net/minecraft/world/biome'
        for number, biome_class in re.findall(r'register\((\d+), "[^"]+", new (\w+)\(', (biome_root/'Biomes.java').read_text()):
            source = (biome_root/f'{biome_class}.java').read_text()
            values = []
            for field, default in (('temperature',0.5),('downfall',1.0),('waterColor',4159204)):
                match = re.search(r'\.'+field+r'\((-?[\d.]+)F?\)',source)
                values.append(float(match.group(1)) if match else default)
            self.biome_settings[int(number)] = values

    def tint(self, state):
        name = state['Name'].split(':')[1]
        constants = {'spruce_leaves':6396257, 'birch_leaves':8431445, 'lily_pad':2129968}
        temperature,humidity,water = self.biome_settings.get(self.biome_id,(0.5,1.0,4159204))
        if name in constants or name == 'water':
            value = int(water) if name == 'water' else constants[name]
            return ((value>>16)&255,(value>>8)&255,value&255)
        temperature = max(0,min(1,temperature))
        humidity = max(0,min(1,humidity))*temperature
        kind = 'foliage' if name.endswith('_leaves') or name=='vine' else 'grass'
        return self.texture('colormap/'+kind).get_at((int((1-temperature)*255),int((1-humidity)*255)))[:3]

    @staticmethod
    def matrix(translation=(0,0,0), scale=(1,1,1), axis=(0,1,0), angle=0):
        axis = np.asarray(axis,dtype=float)
        axis /= np.linalg.norm(axis)
        x,y,z = axis
        c,s = math.cos(math.radians(angle)),math.sin(math.radians(angle))
        rotation = c*np.eye(3)+(1-c)*np.outer(axis,axis)+s*np.array([[0,-z,y],[z,0,-x],[-y,x,0]])
        result = np.eye(4)
        result[:3,:3] = rotation @ np.diag(scale)
        result[:3,3] = translation
        return result

    def entity_part(self, low, size, uv, texture, matrix, *, mirror=False):
        """ModelPart.Cuboid/Quad vertex and UV layout, in original model units."""
        x,y,z = low
        dx,dy,dz = size
        x1,y1,z1 = x+dx,y+dy,z+dz
        if mirror:
            x,x1=x1,x
        vertices = ((x,y,z),(x1,y,z),(x1,y1,z),(x,y1,z),
                    (x,y,z1),(x1,y,z1),(x1,y1,z1),(x,y1,z1))
        u,v = uv
        j,k,l,m,n,o = u,u+dz,u+dz+dx,u+dz+2*dx,u+2*dz+dx,u+2*dz+2*dx
        p,q,r = v,v+dz,v+dz+dy
        quads = (((5,4,0,1),(k,p,l,q),(0,-1,0)),((2,3,7,6),(l,q,m,p),(0,1,0)),
                 ((0,4,7,3),(j,q,k,r),(-1,0,0)),((1,0,3,2),(k,q,l,r),(0,0,-1)),
                 ((5,1,2,6),(l,q,n,r),(1,0,0)),((4,5,6,7),(n,q,o,r),(0,0,1)))
        queue = []
        tw,th=texture.get_size()
        for indices,rect,normal in quads:
            normal=np.asarray(normal,dtype=float)
            if mirror:normal[0]*=-1
            normal=matrix[:3,:3]@normal
            if normal.sum()<=0:continue
            a,b,c,d=indices
            points=[(matrix @ np.asarray((*vertices[i],1)))[:3] for i in (b,a,d,c)]
            projected=[(ANCHOR[0]+(p[0]-p[2])*2,ANCHOR[1]+p[0]+p[2]+(16-p[1])*38/16*self.height_scale) for p in points]
            u0,v0,u1,v1=rect
            shade=1 if normal[1]>max(normal[0],normal[2]) else .85 if normal[0]>normal[2] else .7
            queue.append((sum(sum(p) for p in points),projected,texture,shade,(u0/tw,v0/th),((u1-u0)/tw,0),(0,(v1-v0)/th)))
        return queue

    def entity_sprite(self, state):
        name=state['Name'].split(':')[1]
        props=state.get('Properties',{})
        facing=props.get('facing','south')
        direction={'south':(0,1),'west':(-1,0),'north':(0,-1),'east':(1,0)}[facing]
        facing_angle={'south':0,'west':90,'north':180,'east':270}[facing]
        queue=[]
        if name in ('chest','ender_chest'):
            texture=self.texture('entity/chest/ender' if name=='ender_chest' else 'entity/chest/normal')
            transform=self.matrix(translation=(8,0,8),angle=-facing_angle)@self.matrix(translation=(-8,0,-8))
            for low,size,uv in (((1,0,1),(14,10,14),(0,19)),((1,9,1),(14,5,14),(0,0)),((7,7,15),(2,4,1),(0,0))):
                queue.extend(self.entity_part(low,size,uv,texture,transform))
        elif name=='dragon_wall_head':
            texture=self.texture('entity/enderdragon/dragon')
            transform=(self.matrix(translation=(8-direction[0]*4,4,8-direction[1]*4),scale=(-1,-1,1))
                       @ self.matrix(translation=(0,-.374375*16,0),scale=(.75,.75,.75))
                       @ self.matrix(angle=180+facing_angle))
            parts=(((-6,-1,-24),(12,5,16),(176,44),False),((-8,-8,-10),(16,16,16),(112,30),False),
                   ((-5,-12,-4),(2,4,6),(0,0),True),((-5,-3,-22),(2,2,4),(112,0),True),
                   ((3,-12,-4),(2,4,6),(0,0),False),((3,-3,-22),(2,2,4),(112,0),False))
            for low,size,uv,mirror in parts:
                queue.extend(self.entity_part(low,size,uv,texture,transform,mirror=mirror))
            jaw=transform@self.matrix(translation=(0,4,-8),axis=(1,0,0),angle=math.degrees(.2))
            queue.extend(self.entity_part((-6,0,-16),(12,4,16),(176,65),texture,jaw))
        elif name.endswith('_bed'):
            # BedBlockEntityRenderer.method_3558 and its original ModelParts.
            texture = self.texture('entity/bed/'+name[:-4])
            head = props.get('part') == 'head'
            rotation = {'south':0,'west':90,'north':180,'east':270}[props['facing']]
            transform = (self.matrix(translation=(0,9,0)) @ self.matrix(axis=(1,0,0),angle=90)
                         @ self.matrix(translation=(8,8,8)) @ self.matrix(axis=(0,0,1),angle=180+rotation)
                         @ self.matrix(translation=(-8,-8,-8)))
            queue.extend(self.entity_part((0,0,0),(16,16,6),(0,0 if head else 22),texture,transform))
            legs = (((0,6,-16),0,0),((0,6,0),6,90),((-16,6,-16),12,270),((-16,6,0),18,180))
            for index in ((1,3) if head else (0,2)):
                low,v,roll = legs[index]
                matrix = transform @ self.matrix(axis=(0,0,1),angle=roll) @ self.matrix(axis=(1,0,0),angle=90)
                queue.extend(self.entity_part(low,(3,3,3),(50,v),texture,matrix))
        surface=pygame.Surface(CELL,pygame.SRCALPHA)
        for _,points,texture,shade,origin,u,v in sorted(queue,key=lambda q:q[0]):
            self.raster._draw_face(surface,points,texture,shade,origin,u,v)
        return surface

    def crystal(self, tick, *, base=False):
        texture=self.texture('entity/end_crystal/end_crystal')
        transform=self.matrix(translation=(0,-16,0),scale=(2,2,2))
        if base:
            queue=self.entity_part((-6,0,-6),(12,4,12),(0,16),texture,transform)
        else:
            transform=transform@self.matrix(angle=tick*3)@self.matrix(translation=(0,24,0))
            queue=[]
            for index in range(3):
                if index:
                    transform=transform@self.matrix(scale=(.875,.875,.875))
                transform=transform@self.matrix(axis=(1,0,1),angle=60)
                if index:
                    transform=transform@self.matrix(angle=tick*3)
                queue.extend(self.entity_part((-4,-4,-4),(8,8,8),(32,0) if index==2 else (0,0),texture,transform))
        surface=pygame.Surface(CELL,pygame.SRCALPHA)
        for _,points,texture,shade,origin,u,v in sorted(queue,key=lambda q:q[0]):
            self.raster._draw_face(surface,points,texture,shade,origin,u,v)
        return surface

    def read(self, path):
        return json.loads(self.jar.read("assets/minecraft/" + path))

    def model(self, name):
        name = name.replace("minecraft:", "")
        if name in self.models:
            return self.models[name]
        data = self.read(f"models/{name}.json")
        parent = data.get("parent", "")
        base = self.model(parent) if parent and not parent.startswith("builtin/") else {}
        result = {**base, **data, "textures": {**base.get("textures", {}), **data.get("textures", {})}}
        self.models[name] = result
        return result

    def texture(self, name):
        name = name.replace("minecraft:", "")
        if name not in self.textures:
            image = pygame.image.load(io.BytesIO(self.jar.read(f"assets/minecraft/textures/{name}.png"))).convert_alpha()
            # First native animation frame; runtime lighting supplies gentle motion.
            if image.get_height() > image.get_width():
                image = image.subsurface((0, 0, image.get_width(), image.get_width())).copy()
            self.textures[name] = image
        return self.textures[name]

    @staticmethod
    def matches(condition, props):
        if "OR" in condition:
            return any(Baker.matches(c, props) for c in condition["OR"])
        if "AND" in condition:
            return all(Baker.matches(c, props) for c in condition["AND"])
        return all(props.get(k, "false") in str(v).split("|") for k, v in condition.items())

    def variants(self, state):
        name = state["Name"].split(":")[1]
        if name in ("air", "lava", "water", "chest", "ender_chest", "dragon_wall_head"):
            return []
        data = self.read(f"blockstates/{name}.json")
        props = state.get("Properties", {})
        result = []
        for key, value in data.get("variants", {}).items():
            condition = dict(s.split("=") for s in key.split(",") if s)
            if self.matches(condition, props):
                result.append(value[0] if isinstance(value, list) else value)
                break
        for part in data.get("multipart", []):
            if self.matches(part.get("when", {}), props):
                value = part["apply"]
                result.append(value[0] if isinstance(value, list) else value)
        if not result:
            raise ValueError(f"No model for {state}")
        return result

    @staticmethod
    def rotate(point, axis, degrees, origin=(8, 8, 8)):
        p = [point[i] - origin[i] for i in range(3)]
        angle = math.radians(degrees)
        a, b = {"x": (1, 2), "y": (2, 0), "z": (0, 1)}[axis]
        p[a], p[b] = p[a] * math.cos(angle) - p[b] * math.sin(angle), p[a] * math.sin(angle) + p[b] * math.cos(angle)
        return tuple(p[i] + origin[i] for i in range(3))

    @staticmethod
    def faces(element):
        x0, y0, z0 = element["from"]
        x1, y1, z1 = element["to"]
        # Vertex order is top-left, top-right, bottom-right, bottom-left in UV space.
        return {
            "up": ([(x0,y1,z0),(x1,y1,z0),(x1,y1,z1),(x0,y1,z1)], [x0,z0,x1,z1], (0,1,0)),
            "down": ([(x0,y0,z1),(x1,y0,z1),(x1,y0,z0),(x0,y0,z0)], [x0,16-z1,x1,16-z0], (0,-1,0)),
            "south": ([(x0,y1,z1),(x1,y1,z1),(x1,y0,z1),(x0,y0,z1)], [x0,16-y1,x1,16-y0], (0,0,1)),
            "north": ([(x1,y1,z0),(x0,y1,z0),(x0,y0,z0),(x1,y0,z0)], [16-x1,16-y1,16-x0,16-y0], (0,0,-1)),
            "east": ([(x1,y1,z1),(x1,y1,z0),(x1,y0,z0),(x1,y0,z1)], [16-z1,16-y1,16-z0,16-y0], (1,0,0)),
            "west": ([(x0,y1,z0),(x0,y1,z1),(x0,y0,z1),(x0,y0,z0)], [z0,16-y1,z1,16-y0], (-1,0,0)),
        }

    def bake(self, state):
        if state['Name'] == 'minecraft:bubble_column':
            state = {'Name':'minecraft:water','Properties':{'level':'0'}}
        surface = pygame.Surface(CELL, pygame.SRCALPHA)
        name = state["Name"].split(":")[1]
        if name == "air":
            return surface
        if name in ('chest','ender_chest','dragon_wall_head') or name.endswith('_bed'):
            return self.entity_sprite(state)
        variants = self.variants(state)
        if name == 'end_gateway':
            element = {'from':[0,0,0],'to':[16,16,16]}
            element['faces'] = {face:{'texture':'#all'} for face in self.faces(element)}
            variants = [{'inline':{'elements':[element],'textures':{'all':'entity/end_portal'}}}]
        if name in ("lava", "water"):
            texture = self.texture(f"block/{name}_still")
            level = int(state.get("Properties", {}).get("level", 0))
            height = 16 if level >= 8 else (14 if level == 0 else max(2, 14 - level * 1.75))
            element = {"from": [0,0,0], "to": [16,height,16], "faces": {f:{"texture":"#all", **({'tintindex':0} if name=='water' else {})} for f in self.faces({"from":[0,0,0],"to":[16,height,16]})}}
            variants = [{"inline": {"elements": [element], "textures": {"all": f"block/{name}_still"}}}]
        queue = []
        for variant in variants:
            model = variant.get("inline") or self.model(variant["model"])
            for element in model.get("elements", []):
                for face, (points, default_uv, normal) in self.faces(element).items():
                    if face not in element.get("faces", {}):
                        continue
                    data = element["faces"][face]
                    name = data["texture"]
                    while name.startswith("#"):
                        name = model["textures"][name[1:]]
                    texture = self.texture(name)
                    if 'tintindex' in data:
                        texture = texture.copy()
                        texture.fill((*self.tint(state),255), special_flags=pygame.BLEND_RGBA_MULT)
                    def transform(point, vector=False):
                        rotation = element.get("rotation")
                        if rotation:
                            point = self.rotate(point, rotation["axis"], rotation["angle"], (0,0,0) if vector else rotation["origin"])
                        for axis in ("x", "y"):
                            point = self.rotate(point, axis, -variant.get(axis,0), (0,0,0) if vector else (8,8,8))
                        return self.rotate(point,'y',-90*getattr(self,'view_rotation',0),(0,0,0) if vector else (8,8,8))
                    points = [transform(p) for p in points]
                    nx, ny, nz = transform(normal, True)
                    if nx + ny + nz <= 0.001:
                        continue
                    projected = [(ANCHOR[0] + (x-z)*2, ANCHOR[1] + (x+z) + (16-y)*38/16*self.height_scale) for x,y,z in points]
                    uv = data.get("uv", default_uv)
                    corners = [(uv[0]/16,uv[1]/16),(uv[2]/16,uv[1]/16),(uv[2]/16,uv[3]/16),(uv[0]/16,uv[3]/16)]
                    rotation = data.get("rotation",0)//90
                    corners = corners[rotation:]+corners[:rotation]
                    origin, right, _, bottom = corners
                    shade = 1.0 if ny > .5 else .85 if nx > .5 else .70
                    queue.append((sum(sum(p) for p in points), projected, texture, shade, origin, (right[0]-origin[0],right[1]-origin[1]), (bottom[0]-origin[0],bottom[1]-origin[1])))
        for _, points, texture, shade, origin, u, v in sorted(queue, key=lambda q:q[0]):
            self.raster._draw_face(surface, points, texture, shade, origin, u, v)
        return surface


if __name__ == "__main__":
    pygame.display.init()
    pygame.display.set_mode((1,1))
    baker = Baker()
    manifest={'format':1,'minecraft_version':'Java 1.16.1','cell':CELL,'anchor':ANCHOR,
              'client_sha1':hashlib.sha1(Path(baker.jar.filename).read_bytes()).hexdigest(),'palettes':{}}
    crystals=pygame.Surface((CELL[0]*16,CELL[1]*2),pygame.SRCALPHA)
    for index,tick in enumerate(range(0,120,5)):
        crystals.blit(baker.crystal(tick),((index%16)*CELL[0],(index//16)*CELL[1]))
    crystals.blit(baker.crystal(0,base=True),(8*CELL[0],CELL[1]))
    save_atlas(crystals,CODE/'world_map_regions/end_crystals.png')
    for path in sorted((CODE / "world_map_regions").glob("*.json.gz")):
        data = json.loads(gzip.decompress(path.read_bytes()))
        if "palette" not in data:
            continue
        palette = data["palette"]
        baker.height_scale = NETHER_HEIGHT_SCALE if data['dimension']=='nether' else 1.0
        manifest['palettes'][path.name]=hashlib.sha256(json.dumps(palette,sort_keys=True).encode()).hexdigest()
        atlas = pygame.Surface((CELL[0]*16,CELL[1]*math.ceil(len(palette)/16)),pygame.SRCALPHA)
        for index,state in enumerate(palette):
            baker.biome_id = data.get('palette_biomes',[None]*len(palette))[index]
            atlas.blit(baker.bake(state),((index%16)*CELL[0],(index//16)*CELL[1]))
        target = path.with_name(path.name.replace(".json.gz", ".png"))
        save_atlas(atlas,target)
        print(target.name,len(palette),flush=True)
    (CODE/'world_map_regions/atlas.json').write_text(json.dumps(manifest,indent=2)+'\n')
