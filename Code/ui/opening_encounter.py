"""Finite encounter and physically moving masonry, independent of editor data."""
import numpy as np
from ui.opening_creature import ease
from ui.opening_rig import ThornRig
from ui.presentation_renderer import make_mesh

DURATION=44.
ARCHITECTURE_SCALE=1.2


def architecture_mesh(cells):
    mesh=make_mesh(cells)
    for layer in mesh:layer[:,:,:3]*=ARCHITECTURE_SCALE
    return mesh


class OpeningEncounter:
    def __init__(self,cells):
        self.rig=ThornRig()
        self.fragments=[]
        groups={}
        for pos,value in cells.items():
            key=(pos[0]//8,pos[1]//8,pos[2]//8)
            groups.setdefault(key,{})[pos]=value
        for key,group in sorted(groups.items()):
            mesh=architecture_mesh(group)
            center=(np.mean(list(group),axis=0)+.5)*ARCHITECTURE_SCALE
            # Upper bays detach first; foundations follow in a broad collapse.
            start=29.8+(63-center[2])*.075+(center[1]+36)*.02+abs(center[0])*.025
            self.fragments.append((mesh,center,start))
        self.batches=[]
        for layer in (0,1):
            arrays=[];centers=[];starts=[]
            for mesh,center,start in self.fragments:
                arrays.append(mesh[layer]);centers.extend([center]*len(mesh[layer]));starts.extend([start]*len(mesh[layer]))
            self.batches.append((np.concatenate(arrays),np.asarray(centers),np.asarray(starts)))

    def masonry(self,t):
        if t<29.8:return None
        _,head=self.rig.geometry(t)
        target=head+np.array((0,1,-5))
        transformed=[]
        for original,center,start in self.batches:
            u=ease((t-start)/5.2);keep=u<1
            data=original[keep].copy();center=center[keep];u=u[keep]
            path=(target-center)*u[:,None];path[:,2]+=10*np.sin(np.pi*u)
            scale=1-.96*ease((u-.57)/.43)
            origin=center[:,[0,2,1]]*(1,1,-1)
            relative=(data[:,:,:3]-origin[:,None])*scale[:,None,None]
            angle=u*u*(.5+abs(center[:,0])*.025);c=np.cos(angle)[:,None];s=np.sin(angle)[:,None]
            x,z=relative[:,:,0].copy(),relative[:,:,2].copy()
            relative[:,:,0]=x*c-z*s;relative[:,:,2]=x*s+z*c
            data[:,:,:3]=relative+origin[:,None]+(path[:,[0,2,1]]*(1,1,-1))[:,None]
            transformed.append(data)
        return [(tuple(transformed),(0,0,0))]

    def surroundings(self,mesh,offset,t,start,duration=5):
        """Pull whole remote monuments into the same physical consumption."""
        if t<=start:return mesh,offset
        u=float(ease((t-start)/duration))
        _,head=self.rig.geometry(t)
        result=[]
        for layer in mesh:
            data=layer.copy()
            if u>=1:data=data[:0]
            else:
                center=np.asarray(offset)[[0,2,1]]*(1,1,-1)
                target=head[[0,2,1]]*(1,1,-1)
                data[:,:,:3]=(data[:,:,:3]+center)*(1-u)+target*u
                data[:,:,1]+=12*np.sin(np.pi*u)
            result.append(data)
        return tuple(result),(0,0,0)

    def close(self,gpu):
        self.rig.close(gpu)
