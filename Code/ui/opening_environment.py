"""Continuous faceted ground, deep shrine foundations and sparse flowers."""
import math
import numpy as np
from domain.blocks import BlockType as B
from ui.presentation_renderer import make_mesh


def foundations():
    cells={}
    for x in range(-5,6):
        for y in range(-5,6):
            if abs(x)+abs(y)>8:continue
            for z in range(-180,-1):
                # Buttresses and recesses carry the shrine down into darkness.
                edge=abs(x)==5 or abs(y)==5 or abs(x)+abs(y)==8
                if not edge or (x+y)%3==0 or z>-8:
                    cells[x,y,z]=(B.POLISHED_ANDESITE,'base')
    mesh=make_mesh(cells)
    for data in mesh:
        depth=data[:,:,1]
        data[:,:,5:8]*=np.clip(np.exp((depth+2)/15),.006,.65)[...,None]
    return mesh


class AbyssGround:
    def __init__(self):
        axis=np.arange(-320,321,6,dtype='float32')
        x,y=np.meshgrid(axis,axis)
        # Shared vertices prevent gaps while triangular faces remain legible.
        x=x+1.8*np.sin(y*.15+x*.08)
        y=y+1.4*np.cos(x*.18-y*.06)
        self.xy=np.stack((x,y),axis=-1)
        self.radius=np.sqrt((x+44)**2+(y+36)**2)
        self.depth_falloff=np.exp(-self.radius/65)
        ids=np.arange(x.size).reshape(x.shape)
        self.indices=np.stack((ids[:-1,:-1],ids[:-1,1:],ids[1:,1:],
                               ids[:-1,:-1],ids[1:,1:],ids[1:,:-1]),axis=-1).reshape(-1,3)
        ids=ids[::6,::6]
        self.coarse_indices=np.stack((ids[:-1,:-1],ids[:-1,1:],ids[1:,1:],
                                     ids[:-1,:-1],ids[1:,1:],ids[1:,:-1]),axis=-1).reshape(-1,3)

    def mesh(self,t,swallow=0,*,coarse=False):
        x,y=self.xy[...,0],self.xy[...,1]
        z=-19+1.6*np.sin(x*.032+t*.26)*np.cos(y*.026-t*.20)
        z+=.65*np.sin(x*.07+y*.045-t*.42)
        # Long directional swells dominate, with a weaker oblique component.
        # Shared vertices and incommensurate directions avoid seams/short loops.
        z+=.22*np.sin(x*.11-y*.083+t*.31)
        z-=swallow*15*self.depth_falloff
        points=np.stack((x,z,-y),axis=-1).reshape(-1,3)[self.coarse_indices if coarse else self.indices]
        normal=np.cross(points[:,1]-points[:,0],points[:,2]-points[:,0])
        normal/=np.maximum(1e-8,np.linalg.norm(normal,axis=1,keepdims=True))
        shade=.017+.028*np.abs(normal@np.array((.3,.8,.5)))
        shade+=.006*np.sin(points[:,:,0].mean(1)*.27+points[:,:,2].mean(1)*.21)
        data=np.zeros((*points.shape[:2],9),dtype='float32')
        data[:,:,:3]=points;data[:,:,5:8]=shade[:,None,None]*np.array((.72,.83,1.))
        data[:,:,8]=1
        return data


def flowers():
    """Small irregular clumps, dark stems, individually folded red petals."""
    rng=np.random.default_rng(1703);faces=[]
    for side in (-1,1):
        for y in (-22,-9,3,15):
            for _ in range(3):
                x=side*rng.uniform(14.2,15.7);yy=y+rng.uniform(-1,1)
                h=rng.uniform(.65,1.3);z=4.
                stem=np.array(((x-.04,z,-yy),(x+.04,z,-yy),(x+.04,z+h,-yy),(x-.04,z+h,-yy)))
                faces.append(np.array([(*p,0,0,.045,.085,.042,1) for p in stem]))
                for petal in range(5):
                    a=petal*math.tau/5+rng.uniform(-.15,.15)
                    radial=np.array((math.cos(a),0,math.sin(a)))*.28
                    tangent=np.array((-math.sin(a),0,math.cos(a)))*.16
                    center=np.array((x,z+h,-yy))
                    points=(center,center+radial-tangent+(.0,.12,0),center+radial*1.5+(.0,.18,0),center+radial+tangent+(.0,.12,0))
                    color=(rng.uniform(.23,.36),.025,.035)
                    faces.append(np.array([(*p,0,0,*color,1) for p in points]))
    return np.asarray(faces,dtype='float32')
