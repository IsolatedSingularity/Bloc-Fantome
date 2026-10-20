"""Skinned source rig with continuous motion blending and cathedral contacts."""
import ctypes
import math
from pathlib import Path
import numpy as np
import pygame
from runtime_paths import ASSETS_DIR
from ui.opening_creature import ease, hinge, unit


def blend_quaternions(a,b,t):
    b=np.where((a*b).sum(-1,keepdims=True)<0,-b,b)
    q=a*(1-t)+b*t
    return q/np.maximum(1e-12,np.linalg.norm(q,axis=-1,keepdims=True))


def matrices(q,translation):
    x,y,z,w=q.T
    result=np.tile(np.eye(4,dtype='float32'),(len(q),1,1))
    result[:,0,:3]=np.stack((1-2*(y*y+z*z),2*(x*y+z*w),2*(x*z-y*w)),axis=1)
    result[:,1,:3]=np.stack((2*(x*y-z*w),1-2*(x*x+z*z),2*(y*z+x*w)),axis=1)
    result[:,2,:3]=np.stack((2*(x*z+y*w),2*(y*z-x*w),1-2*(x*x+y*y)),axis=1)
    result[:,3,:3]=translation
    return result


def rotation(axis,angle):
    axis=unit(axis);x,y,z=axis*math.sin(angle/2)
    return matrices(np.array([[x,y,z,math.cos(angle/2)]]),np.zeros((1,3)))[0,:3,:3]


def align(a,b):
    a,b=unit(a),unit(b);cross=np.cross(a,b)
    if np.linalg.norm(cross)<1e-8:return np.eye(3)
    return rotation(cross,math.acos(float(np.clip(a@b,-1,1))))


class ThornRig:
    SCALE=.082

    def __init__(self):
        self.path=Path(ASSETS_DIR)/'Opening/Creature/Thorn'
        with np.load(self.path/'rig.npz') as source:self.data={k:source[k] for k in source.files}
        self.parents=self.data['parents']
        self.children=[]
        for bone in range(len(self.parents)):
            descendants={bone}
            for child,parent in enumerate(self.parents):
                if parent in descendants:descendants.add(child)
            self.children.append(np.array(sorted(descendants)))
        vertices=np.column_stack((self.data['positions'],np.ones(len(self.data['positions']))))
        self.local=np.einsum('ni,nkij->nkj',vertices,np.linalg.inv(self.data['bind'])[self.data['bones']]).astype('float32')
        self.ids=None;self.owner=None
        self._sampled=None

    def clip(self,name,seconds,loop=True):
        q=self.data['rotation_'+name];p=self.data['translation_'+name]
        frame=seconds*30
        frame=frame%(len(q)-1) if loop else min(len(q)-1,max(0,frame))
        i=int(frame);j=min(len(q)-1,i+1);u=frame-i
        return blend_quaternions(q[i],q[j],u),p[i]*(1-u)+p[j]*u

    def _rotate_branch(self,pose,bone,origin,turn):
        ids=self.children[bone]
        pose[ids,:3,:3]=pose[ids,:3,:3]@turn
        pose[ids,3,:3]=(pose[ids,3,:3]-origin)@turn+origin

    def _contact(self,pose,shoulder,elbow,wrist,target,pole,amount):
        if amount<=0:return
        a,b,c=pose[[shoulder,elbow,wrist],3,:3].copy()
        end=c+(target-c)*amount
        upper,lower=np.linalg.norm(b-a),np.linalg.norm(c-b)
        distance=np.linalg.norm(end-a)
        end=a+unit(end-a)*np.clip(distance,abs(upper-lower)+.01,upper+lower-.01)
        middle=hinge(a,end,pole,upper,lower)
        self._rotate_branch(pose,shoulder,a,align(b-a,middle-a))
        b,c=pose[[elbow,wrist],3,:3].copy()
        self._rotate_branch(pose,elbow,b,align(c-b,end-b))

    def pose(self,t):
        # Source performance supplies the full-body overturn and recovery.
        # Each cue runs through its actual motion rather than holding a pose.
        q,p=self.clip('00A',t*.82)
        for name,start,duration,speed in (('51A',15.5,6.3,1.23),
                                        ('55A',22,3.7,.75),
                                        ('52A',26,15,.78)):
            amount=float(ease((t-start)/.65)*(1-ease((t-start-duration)/.8)))
            if amount:
                b,c=self.clip(name,max(0,t-start)*speed,False)
                q=blend_quaternions(q,b,amount)
                c=c.copy();c[0]=p[0]
                p=p*(1-amount)+c*amount
        local=matrices(q,p)
        # Several overlapping traveling contractions, each with a quick onset
        # and slower release, move through spine, shoulder, fingers and ribbons.
        for bone in (3,4,5,24,25,32,38,81,82,89,95,52,53,54,61,62,109,110,118,119,127,145):
            breath=.045*math.sin(t*1.7-bone*.19)+.02*math.sin(t*4.3+bone*.31)
            spasm=0.
            for onset,amplitude in ((15.2,.25),(18.4,-.32),(21.1,.45),(24.3,-.6),(26.7,.5),(28.5,-.7),(30.2,.4)):
                age=t-onset-(bone%7)*.024
                if 0<age<1.3:spasm+=amplitude*(1-math.exp(-age*65))*math.exp(-age*4.4)*math.sin(age*17)
            local[bone,:3,:3]=local[bone,:3,:3]@rotation((1,.3,.7),breath+spasm)
        pose=local.copy()
        for bone,parent in enumerate(self.parents):
            if parent>=0:pose[bone]=pose[bone]@pose[parent]
        # Normalize source battle travel at the pelvis, retaining every local
        # joint rotation. The staged path has a visible ground approach, weight
        # transfer onto the arcade, an overbalance, and a dragging recovery.
        hip=self.hip_path(t)
        pelvis=pose[124,3,:3].copy()
        origin=hip-pelvis[[0,2,1]]*(1,-1,1)*self.SCALE
        # Aim the articulated spine/neck at real stone, not an arbitrary local
        # rotation axis (the imported bones have different rest orientations).
        for hit in (25.45,26.55,27.65):
            age=t-hit
            if -.32<age<.7:
                if age<-.1:
                    amount=math.sin(math.pi*float(ease((age+.32)/.22)))*.22
                    target=np.array((13.2,35.,86.))
                else:
                    amount=float(ease((age+.1)/.1)) if age<0 else float(1-ease(age/.65))
                    target=np.array((13.2,21.6,49.))
                native=(target-origin)[[0,2,1]]*(1,1,-1)/self.SCALE
                self._contact(pose,3,5,68,native,(0,0,1),amount)
        for shoulder,elbow,wrist,target,pole,strength in self.contacts(t):
            target=np.asarray(target)-origin
            native=np.array((target[0],target[2],-target[1]))/self.SCALE
            self._contact(pose,shoulder,elbow,wrist,native,pole,strength)
        return pose,origin

    @staticmethod
    def hip_path(t):
        keys=((0,(100,25,18)),(2,(78,25,18)),(4,(53,25,19)),
              (6,(32,25,22)),(8,(22,25,29)),(10,(12,22,38)),
              (12,(3,19,47)),(15.5,(0,18,49)),(17,(1,17,52)),
              (19,(-18,22,37)),(20.5,(-28,28,12)),(22,(-23,27,15)),
              (25,(-12,27,33)),(28,(0,23,42)),(33,(0,22,46)),
              (39,(0,22,48)),(44,(0,22,48)))
        for (a,start),(b,end) in zip(keys,keys[1:]):
            if t<=b:return np.array(start)+(np.array(end)-start)*float(ease((t-a)/(b-a)))
        return np.array(keys[-1][1],dtype=float)

    def contacts(self,t):
        result=[]
        # Alternating stance holds each sole in world space while the pelvis
        # advances. A lifted foot follows a smooth arc to its next foothold.
        for side,hip,knee,ankle,phase in ((1,126,127,128,0),(-1,144,145,146,1)):
            if t<6:
                cycle=max(0,t+phase);step=int(cycle//2);u=cycle/2-step
                a=max(0,step*2-phase);b=min(6,a+2)
                start=self.hip_path(a)+np.array((side*10,-3,-37))
                end=self.hip_path(b)+np.array((side*10,-3,-37))
                swing=float(ease((u-.58)/.42))
                point=start+(end-start)*swing;point[2]=-14+8*math.sin(math.pi*swing)
                result.append((hip,knee,ankle,point,(side,.2,1),1.))
            else:
                start=6.2 if side==1 else 8.2
                amount=float(ease((t-start)/1.6)*(1-ease((t-15.5)/.8)))
                result.append((hip,knee,ankle,(side*20,20,37),(side,0,1),amount))
        # Grips are on the actual front cornice. Each stays fixed through the
        # climb, then releases before the imported overturn begins.
        for side,shoulder,elbow,wrist,start in ((1,24,25,32,5.6),(-1,81,82,89,7.6)):
            amount=float(ease((t-start)/1.1)*(1-ease((t-15.2)/.7)))
            amount=max(amount,float(ease((t-24.8)/.4)*(1-ease((t-27.8)/.4))))
            result.append((shoulder,elbow,wrist,(side*13+1,20,48),(side,0,-1),amount))
        return result

    def geometry(self,t):
        if self._sampled is not None and self._sampled[0]==t:return self._sampled[1:]
        pose,origin=self.pose(t)
        points=np.einsum('nki,nkij,nk->nj',self.local,pose[self.data['bones']],self.data['weights'])[:,:3]
        points*=self.SCALE
        points+=origin[[0,2,1]]*(1,1,-1)
        data=np.ones((len(points),9),dtype='float32')
        data[:,:3]=points;data[:,3:5]=self.data['uv']
        # Preserve texture relief and folds. Cool grazing light distinguishes
        # the dark form from the ground without making its body luminous.
        triangles=points.reshape(-1,3,3)
        normals=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0])
        normals/=np.maximum(1e-8,np.linalg.norm(normals,axis=1,keepdims=True))
        light=.19+.22*np.abs(normals@unit((.3,.7,-.6)))
        data[:,5:8]=np.repeat(light,3)[:,None]*np.array((.68,.79,.84))
        head=pose[68,3,:3]*self.SCALE
        head=head[[0,2,1]]*(1,-1,1)+origin
        self._sampled=(t,data,head)
        return data,head

    def draw(self,gpu,t,offset=(0,0,0)):
        if self.owner is not gpu:
            self.ids=(ctypes.c_uint*7)();gpu.gl.glGenTextures(7,self.ids)
            for i in range(7):gpu.upload(pygame.image.load(self.path/f'{i}.png'),self.ids[i],initial=True)
            self.owner=gpu
        data,head=self.geometry(t)
        dx,dy,dz=offset;gpu.gl.glTranslatef(dx,dz,-dy)
        for i in range(7):
            gpu.gl.glEnable(0x0DE1);gpu.gl.glBindTexture(0x0DE1,self.ids[i])
            gpu.draw(data[self.data['material']==i],0x0004)
        gpu.gl.glTranslatef(-dx,-dz,dy)
        gpu.gl.glBindTexture(0x0DE1,gpu.ids[0]);gpu.gl.glEnable(0x0DE1)

    def close(self,gpu):
        if self.ids is not None and self.owner is gpu:gpu.gl.glDeleteTextures(7,self.ids)
        self.ids=None;self.owner=None
