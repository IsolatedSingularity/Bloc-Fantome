"""Bounded voxel scenery with the same projection as the six-face sky.

Meshes are made once, keep exposed faces only, and move as coherent islands.
No spawning, textures, or viewport-sized surfaces are created during animation.
"""
import math
import random
import pygame

def merge_faces(faces):
    """Merge adjacent coplanar voxel faces once, retaining the stepped silhouette."""
    groups={}
    for corners,normal,color in faces:
        axis=next(i for i,n in enumerate(normal) if n)
        u,v=[i for i in range(3) if i!=axis]
        plane=round(corners[0][axis]/2.5)
        cell=(round(min(p[u] for p in corners)/2.5),round(min(p[v] for p in corners)/2.5))
        groups.setdefault((normal,color,axis,u,v,plane),set()).add(cell)
    result=[]
    for (normal,color,axis,u,v,plane),cells in groups.items():
        while cells:
            x,y=min(cells);w=1;h=1
            while (x+w,y) in cells:w+=1
            while all((x+i,y+h) in cells for i in range(w)):h+=1
            for i in range(w):
                for j in range(h):cells.remove((x+i,y+j))
            corners=[]
            for a,b in ((x,y),(x+w,y),(x+w,y+h),(x,y+h)):
                p=[0,0,0];p[axis]=plane*2.5;p[u]=a*2.5;p[v]=b*2.5;corners.append(tuple(p))
            result.append((tuple(corners),normal,color))
    return tuple(result)

class SkyLayers:
    def __init__(self):
        self.elapsed=0.0
        self.pan=(0.0,0.0)
        self.forms={}
        for dimension,seed in (('overworld',172),('nether',918),('end',623)):
            rng=random.Random(seed); clusters=[]
            for index in range(8):
                angle=index*math.tau/8+rng.uniform(-.14,.14)
                radius=rng.uniform(180,260)
                height=rng.uniform(42,72) if dimension=='overworld' else rng.uniform(-20,45)
                voxels={}
                for x in range(-5,6):
                    for z in range(-4,5):
                        distance=(x/5)**2+(z/4)**2
                        if distance>rng.uniform(.78,1.12):continue
                        if dimension=='overworld':
                            top=round(1.5*(1-distance));bottom=-1
                        else:
                            top=round((1-distance)*2+rng.random())
                            bottom=-round((1-distance)*(8 if dimension=='nether' else 5))-1
                        for y in range(bottom,top+1):
                            base=(139,155,184) if dimension=='overworld' else (65,48,67) if dimension=='nether' else (138,126,156)
                            if dimension=='nether' and x==0 and y<0 and z%3==0:base=(132,60,62)
                            voxels[x,y,z]=base
                if dimension=='end':
                    for y in range(3,8):voxels[1,y,0]=(72,54,85)
                    for x in range(-1,4):voxels[x,6,0]=(79,58,91)
                    voxels[-1,7,0]=(135,114,153);voxels[3,7,0]=(135,114,153)
                faces=[]
                specs=(((1,0,0),((1,0,0),(1,1,0),(1,1,1),(1,0,1))),
                       ((-1,0,0),((0,0,1),(0,1,1),(0,1,0),(0,0,0))),
                       ((0,1,0),((0,1,0),(0,1,1),(1,1,1),(1,1,0))),
                       ((0,-1,0),((0,0,1),(0,0,0),(1,0,0),(1,0,1))),
                       ((0,0,1),((1,0,1),(1,1,1),(0,1,1),(0,0,1))),
                       ((0,0,-1),((0,0,0),(0,1,0),(1,1,0),(1,0,0))))
                for (x,y,z),color in voxels.items():
                    for normal,corners in specs:
                        if (x+normal[0],y+normal[1],z+normal[2]) in voxels:continue
                        vertices=tuple(((x+dx)*2.5,(y+dy)*2.5,(z+dz)*2.5) for dx,dy,dz in corners)
                        shade=1 if normal[1]>0 else .52 if normal[1]<0 else .74 if normal[0] else .86
                        faces.append((vertices,normal,tuple(round(c*shade) for c in color)))
                clusters.append((angle,radius,height,merge_faces(faces)))
            self.forms[dimension]=tuple(clusters)

    def update(self,dt_ms,camera_offset=None):
        self.elapsed+=max(0,dt_ms)/1000
        if camera_offset is not None:self.pan=tuple(max(-12,min(12,v*.008)) for v in camera_offset)

    def render(self,target,dimension,yaw,pitch,vertical_center=.45):
        width,height=target.get_size();focal=width/(2*math.tan(math.radians(47)))
        sy,cy=math.sin(math.radians(yaw)),math.cos(math.radians(yaw))
        sp,cp=math.sin(math.radians(pitch)),math.cos(math.radians(pitch))
        polygons=[]
        for i,(angle,radius,elevation,faces) in enumerate(self.forms.get(dimension,())):
            angle+=self.elapsed*.006
            ox=math.sin(angle)*radius-self.pan[0]
            oz=math.cos(angle)*radius
            oy=elevation+self.pan[1]+math.sin(self.elapsed*.18+i)*1.8
            center_depth=(oz*cy+ox*sy)*cp+oy*sp
            if center_depth<35:continue
            center_x=ox*cy-oz*sy
            center_y=oy*cp-(oz*cy+ox*sy)*sp
            margin=55*focal/center_depth
            if abs(center_x*focal/center_depth)>width/2+margin:continue
            if height*vertical_center-center_y*focal/center_depth+margin<0:continue
            if height*vertical_center-center_y*focal/center_depth-margin>height:continue
            for corners,normal,color in faces:
                # Back-face rejection in world space; avoid painting hidden faces over the front.
                center=tuple(sum(p[a] for p in corners)/4+(ox,oy,oz)[a] for a in range(3))
                if sum(normal[a]*center[a] for a in range(3))>=0:continue
                projected=[];depths=[]
                for x,y,z in corners:
                    x+=ox;y+=oy;z+=oz
                    rx=x*cy-z*sy;rz=z*cy+x*sy
                    ry=y*cp-rz*sp;depth=rz*cp+y*sp
                    if depth<18:break
                    projected.append((round(width/2+rx/depth*focal),round(height*vertical_center-ry/depth*focal)))
                    depths.append(depth)
                if len(projected)!=4:continue
                if max(p[0] for p in projected)<0 or min(p[0] for p in projected)>width:continue
                polygons.append((sum(depths)/4,color,projected))
        for _,color,points in sorted(polygons,key=lambda p:-p[0]):pygame.draw.polygon(target,color,points)
