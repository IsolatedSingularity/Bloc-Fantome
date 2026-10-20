"""Authored cathedral motion study, isolated from the playable opening.

Positions are in sanctuary-local block coordinates. The four support targets
belong to real pier caps. Absolute-time sampling makes holds and contacts stable
across frame rates, seeking and focus loss. This is a review proof, not the final
35-50 second encounter.
"""
from dataclasses import dataclass
from functools import lru_cache
import math
from pathlib import Path

import numpy as np


DURATION = 14.0
SKIN = np.array((.085, .098, .102))
JOINT = np.array((.15, .15, .135))
CONTACTS = np.array(((-15.5, 16.25, 32.), (17.5, 16.25, 32.),
                     (-15.5, -14.25, 32.), (17.5, -14.25, 32.)))
HIGH_HANDS = np.array(((-11.5, 16.25, 40.), (13.5, 16.25, 40.)))


def ease(value):
    t = np.clip(value, 0., 1.)
    return t*t*t*(10.+t*(-15.+6.*t))


def track(t, keys):
    """Explicitly repeated values create genuine motionless holds."""
    if t <= keys[0][0]:
        return np.asarray(keys[0][1], dtype=float)
    for (a, p), (b, q) in zip(keys, keys[1:]):
        if t <= b:
            u = ease((t-a)/(b-a))
            return np.asarray(p)*(1-u)+np.asarray(q)*u
    return np.asarray(keys[-1][1], dtype=float)


def unit(vector):
    vector = np.asarray(vector, dtype=float)
    return vector / max(1e-10, np.linalg.norm(vector))


def hinge(root, end, pole, upper, lower):
    """Two fixed-length bones, with an authored bend side. Never stretch."""
    direction = np.asarray(end)-root
    distance = np.linalg.norm(direction)
    if not abs(upper-lower)+1e-6 < distance < upper+lower-1e-6:
        raise ValueError(f'Unreachable creature contact: {distance:.3f}')
    axis = direction/distance
    bend = unit(np.asarray(pole)-axis*np.dot(pole, axis))
    along = (upper*upper-lower*lower+distance*distance)/(2*distance)
    return root+axis*along+bend*math.sqrt(max(0, upper*upper-along*along))


@dataclass(frozen=True)
class Pose:
    spine: np.ndarray
    limbs: np.ndarray
    contacts: np.ndarray
    planted: tuple
    head: np.ndarray
    face: np.ndarray
    eye: float
    pull: float


def sample(seconds):
    t = float(np.clip(seconds, 0, DURATION))
    # First shift weight toward the right supports, then unload the left hand.
    # The pelvis follows the thorax later, never as a rigid translated assembly.
    chest = track(t, ((0,(0,24,43)), (1,(0,24,43)), (1.5,(2,24,42)),
                     (3.4,(2,23,44)), (4.5,(-1,23,49)), (5,(-1,23,49)),
                     (6.6,(0,23,53)), (8.4,(0,23,53)), (8.55,(-3,24,54)),
                     (8.72,(1,23,51)), (9.5,(0,23,53)), (11,(0,23,53)),
                     (11.8,(0,24,52)), (12.4,(0,27,50)), (14,(0,27,50))))
    hip = track(t, ((0,(0,-22,39)), (3.7,(0,-22,39)), (5,(-1,-22,44)),
                   (6,(-1,-22,44)), (7,(0,-22,49)), (8.5,(0,-22,49)),
                   (8.8,(2,-22,48)), (9.7,(0,-22,49)), (14,(0,-22,49))))
    # Keep the back arch above the real transverse ribs and apse glazing.
    chest += (0,0,9)
    hip += (0,2,14)
    contacts = CONTACTS.copy()
    planted = [True]*4
    for i, (start, finish) in enumerate(((1.6,3.3),(4.7,6.2))):
        if start < t < finish:
            u = ease((t-start)/(finish-start))
            contacts[i] = CONTACTS[i]*(1-u)+HIGH_HANDS[i]*u
            # Lift forward of the cornice before crossing it. The hand lands
            # first; the chest only follows after contact is established.
            contacts[i] += (0, 7*math.sin(math.pi*u), 8*math.sin(math.pi*u))
            planted[i] = False
        elif t >= finish:
            contacts[i] = HIGH_HANDS[i]
    # Small physical extraction study, following the motion/eye checkpoint.
    pull = float(ease((t-11.8)/1.6))
    if pull > 0:
        contacts[0] += np.array((2,9,7))*pull
        planted[0] = False
    shoulders = [chest+(-4,0,0), chest+(4,0,0)]
    hips = [hip+(-2.7,0,0), hip+(2.7,0,0)]
    limbs = []
    for i, root in enumerate(shoulders+hips):
        end = contacts[i]+(0,0,1.2)
        side = -1 if i%2==0 else 1
        pole = (side, .55 if i<2 else -.7, .18)
        elbow = hinge(root, end, pole, 20 if i<2 else 18, 20 if i<2 else 18)
        limbs.append((root, elbow, end))
    crest = (hip+chest)/2+(0,0,15)
    spine = np.array((hip, hip*.55+crest*.45+(0,0,3), crest,
                      chest*.55+crest*.45+(0,0,4), chest))
    head = chest+track(t, ((0,(0,6,-8)), (7.7,(0,6,-8)), (8.4,(0,6,-9)),
                          (8.55,(-5,5,-3)), (8.72,(3,7,-6)),
                          (9.25,(0,7,-7)), (11,(0,7,-7)),
                          (12.4,(0,6,-9)), (14,(0,6,-9))))
    face = unit(track(t, ((0,(0,1,-.6)), (8.7,(0,1,-.6)),
                         (9.15,(-.31,.85,.42)), (10.1,(-.31,.85,.42)),
                         (10.5,(0,1,-.6)), (14,(0,1,-.6)))))
    eye = float(ease((t-9.1)/.13)*(1-ease((t-10.1)/.12)))
    # One brief lid spasm; no perpetual oscillation or full-screen glitch.
    eye *= 1-.85*float(ease((t-9.52)/.025)*(1-ease((t-9.58)/.025)))
    return Pose(spine, np.array(limbs), contacts, tuple(planted), head, face, eye, pull)


def _surface(points, colors):
    """World XYZ to the renderer's interleaved GL XZ-Y quad format."""
    points = np.asarray(points)
    out = np.zeros((*points.shape[:-1], 9), dtype='float32')
    out[...,0] = points[...,0]
    out[...,1] = points[...,2]
    out[...,2] = -points[...,1]
    out[...,5:8] = colors
    out[...,8] = 1
    return out.reshape(-1,4,9)


def tube(path, radii, color=SKIN, sides=12):
    """Tapered swept volume with continuous ring lighting and closed ends."""
    path = np.asarray(path, dtype=float)
    tangents = np.gradient(path, axis=0)
    tangents /= np.maximum(1e-10,np.linalg.norm(tangents,axis=1))[:,None]
    reference = np.tile((0.,1.,0.),(len(path),1))
    reference[np.abs(tangents[:,1])>.94] = (1,0,0)
    a = np.cross(tangents,reference)
    a /= np.linalg.norm(a,axis=1)[:,None]
    b = np.cross(tangents,a)
    theta = np.arange(sides)*2*math.pi/sides
    normals = a[:,None,:]*np.cos(theta)[None,:,None]+b[:,None,:]*np.sin(theta)[None,:,None]
    rings = path[:,None,:]+normals*np.asarray(radii)[:,None,None]
    lighting = .5+.5*np.maximum(0,normals@unit((-.7,.5,1)))
    colors = np.asarray(color)*lighting[...,None]
    nxt = np.roll(np.arange(sides),-1)
    points = np.stack((rings[:-1],rings[:-1,nxt],rings[1:,nxt],rings[1:]),axis=2)
    shades = np.stack((colors[:-1],colors[:-1,nxt],colors[1:,nxt],colors[1:]),axis=2)
    caps = np.array([[path[k],rings[k,i],rings[k,nxt[i]],path[k]]
                     for k in (0,-1) for i in range(sides)])
    return np.concatenate((_surface(points,shades),_surface(caps,np.asarray(color)*.6)))


def ellipsoid(center, axes, radii, color=SKIN, rings=12, sides=20):
    lat = np.linspace(-math.pi/2,math.pi/2,rings+1)
    lon = np.arange(sides)*2*math.pi/sides
    sphere = np.stack(np.broadcast_arrays(np.cos(lat)[:,None]*np.cos(lon),
                      np.cos(lat)[:,None]*np.sin(lon),np.sin(lat)[:,None]),axis=-1)
    normals = sphere@np.asarray(axes)
    vertices = (sphere*np.asarray(radii))@np.asarray(axes)+center
    colors = np.asarray(color)*(.5+.5*np.maximum(0,normals@unit((-.7,.5,1))))[...,None]
    nxt = np.roll(np.arange(sides),-1)
    return _surface(np.stack((vertices[:-1],vertices[:-1,nxt],vertices[1:,nxt],vertices[1:]),axis=2),
                    np.stack((colors[:-1],colors[:-1,nxt],colors[1:,nxt],colors[1:]),axis=2))


def _catmull(points, count=6):
    p = np.vstack((points[0],points,points[-1]))
    result=[]
    for i in range(1,len(p)-2):
        a,b,c,d=p[i-1:i+3]
        for t in np.linspace(0,1,count,endpoint=False):
            result.append(.5*((2*b)+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t))
    return np.vstack((result,points[-1]))


@lru_cache(maxsize=1)
def _iris_photo():
    # Preserve the original photograph. Only the material sampling coordinates
    # are changed here; attribution and the adaptation terms live beside it.
    import pygame
    path=Path(__file__).resolve().parents[2]/'Assets/Opening/Creature/Eye_iris.jpg'
    return pygame.surfarray.array3d(pygame.image.load(str(path))).astype(float)/255


def _iris_material(x,y):
    photo=_iris_photo()
    u=np.clip(1150+(x+.08)/.43*800,0,photo.shape[0]-2)
    v=np.clip(960-y/.43*800,0,photo.shape[1]-2)
    ix=u.astype(int);iy=v.astype(int);fx=(u-ix)[...,None];fy=(v-iy)[...,None]
    return ((photo[ix,iy]*(1-fx)+photo[ix+1,iy]*fx)*(1-fy)
            +(photo[ix,iy+1]*(1-fx)+photo[ix+1,iy+1]*fx)*fy)*.72


def eye_mesh(pose, resolution=(161,65)):
    """Curved almond aperture: shaded sclera, radial iris fibres, round pupil,
    limbal ring, wet highlight and dark upper lid. No emissive white eye sprite.
    Geometry is attached to the face, participates in the scene's depth test.
    """
    if pose.eye <= .001:
        return np.empty((0,4,9),dtype='float32')
    normal=pose.face
    right=unit(np.cross((0,0,1),normal))
    up=np.cross(normal,right)
    center=pose.head+normal*2.22+up*.45-right*.9
    x=np.linspace(-1,1,resolution[0])
    v=np.linspace(-1,1,resolution[1])
    xx,vv=np.meshgrid(x,v)
    yy=vv*(1-xx*xx)**.65*.49*pose.eye
    zz=.30*(1-xx*xx)*(1-vv*vv)
    points=center+xx[...,None]*right*1.25+yy[...,None]*up*1.25+zz[...,None]*normal
    radius=np.sqrt((xx+.08)**2+(yy*1.04)**2)
    shade=.38+.22*(1-vv)/2-.17*np.abs(xx)
    colors=np.stack((shade*.79,shade*.80,shade*.72),axis=-1)
    iris=radius<.43
    iris_color=_iris_material(xx,yy)
    iris_color*=np.clip((.43-radius)/.025, .2,1)[...,None]
    colors[iris]=iris_color[iris]
    # Sparse scleral capillaries follow curved paths, never a repeating pattern.
    for sign in (-1,1):
        for offset in (-.19,.14):
            curve=offset+sign*.12*(xx-sign*.45)**2
            vessel=np.exp(-((yy-curve)/.004)**2)*np.clip((sign*xx-.5)*1.3,0,.35)
            colors[...,1:]*=(1-vessel[...,None])
    highlight=np.exp(-((xx+.19)**2/.0012+(yy-.16)**2/.0007))
    colors=colors*(1-highlight[...,None])+.78*highlight[...,None]
    # Lid shadow is darkest at the upper margin, tear corners stay subdued.
    colors*=np.clip((1-np.abs(vv))/.16,.18,1)[...,None]
    eye=_surface(np.stack((points[:-1,:-1],points[:-1,1:],points[1:,1:],points[1:,:-1]),axis=2),
                 np.stack((colors[:-1,:-1],colors[:-1,1:],colors[1:,1:],colors[1:,:-1]),axis=2))
    lids=[]
    for edge in (0,-1):
        lids.append(tube(points[edge],np.full(len(x),.045),SKIN*1.35,6))
    return np.concatenate((eye,*lids))


def body_mesh(pose):
    pieces=[]
    spine=_catmull(pose.spine)
    radii=np.interp(np.linspace(0,1,len(spine)),(0,.2,.45,.7,1),(2.8,2.0,1.6,2.8,4.1))
    pieces.append(tube(spine,radii,sides=16))
    pieces.append(ellipsoid(pose.spine[-1],np.eye(3),(4.3,3.7,2.8),SKIN,rings=12,sides=24))
    pieces.append(ellipsoid(pose.spine[0],np.eye(3),(3.2,2.6,2.2),SKIN,rings=10,sides=20))
    # Paired rib ridges sit close to the thorax. Most of the volume stays matte.
    for k in range(6):
        center=spine[-2-k]
        arc=np.linspace(0,math.pi,12)
        rib=np.column_stack((3.4*np.cos(arc),np.zeros(12),-2.1*np.sin(arc)))+center
        pieces.append(tube(rib,np.full(12,.23),SKIN*1.6,8))
    for i,(root,joint,end) in enumerate(pose.limbs):
        upper=np.array((root,root*.7+joint*.3,root*.3+joint*.7,joint))
        lower=np.array((joint,joint*.65+end*.35,joint*.18+end*.82,end))
        upper_curve=_catmull(upper,4);lower_curve=_catmull(lower,4)
        pieces.append(tube(upper_curve,np.interp(np.linspace(0,3,len(upper_curve)),range(4),
                                                (2.3,2.0,1.25,.88) if i<2 else (2.6,2.4,1.4,.9)),sides=16))
        pieces.append(tube(lower_curve,np.interp(np.linspace(0,3,len(lower_curve)),range(4),(.9,1.2,.66,.6)),sides=16))
        pieces.append(ellipsoid(joint,np.eye(3),(1.02,1.02,1.02),JOINT,rings=6,sides=12))
        pieces.append(ellipsoid(end,np.eye(3),(1.05,1.5,.7),SKIN*1.25,rings=6,sides=12))
        contact=pose.contacts[i]
        for finger in range(4):
            spread=(finger-1.5)*.48
            length=1.05+(1-abs(finger-1.5)/2)*.65
            direction=1 if i<2 else -1
            path=np.array((end+(spread,.4*direction,-.05),
                           contact+(spread*1.35,length*.65*direction,1.15),
                           contact+(spread*1.5,length*direction,.12)))
            pieces.append(tube(path,(.25,.2,.12),SKIN*1.4,7))
        thumb=end+((1.35 if i%2 else -1.35),0,-.25)
        pieces.append(tube((end,thumb,thumb+(0,1,-.55)),(.34,.28,.15),SKIN*1.25,8))
    chest=pose.spine[-1]
    pieces.append(tube((chest,chest+(0,3,-1),pose.head),(2.2,1.35,1.2),sides=14))
    right=unit(np.cross((0,0,1),pose.face));up=np.cross(pose.face,right)
    axes=np.array((right,pose.face,up))
    pieces.append(ellipsoid(pose.head,axes,(3.0,2.2,4.3),SKIN*.8,rings=18,sides=28))
    # A restrained brow and chin retain human facial proportions in silhouette.
    pieces.append(ellipsoid(pose.head+pose.face*1.4-up*2.7,axes,(1.7,1.1,1.45),SKIN*.85))
    pieces.append(ellipsoid(pose.head+pose.face*2.02-up*.25,axes,(.35,.44,.65),SKIN*.8))
    pieces.append(eye_mesh(pose))
    return np.concatenate(pieces)
