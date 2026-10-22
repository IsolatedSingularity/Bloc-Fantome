"""Bounded presentation renderer. The builder retains its existing renderer.

Uses the Windows OpenGL 1.1 compatibility API, supplied with Windows, and the
project's existing numpy/pygame dependencies. Meshes are built once. Text and
controls are rasterized at the display's actual pixel size.
"""
import ctypes as C
import math
import os

import numpy as np
import pygame

from domain.blocks import BlockType as B
from runtime_paths import TEXTURES_DIR


PALETTE = {
    'foundation':(.23,.29,.37),'base':(.45,.52,.58),'floor':(.88,.88,.84),
    'aisle':(.65,.74,.79),'stone':(1,.98,.93),'glass':(.75,.88,1),
    'amber':(1,.89,.66),'glow':(1,1,.9),'light':(.76,.81,.81),
    'dark':(.51,.61,.68),'distant':(.10,.17,.22),'distant_glow':(.37,.32,.22),
}
TRANSPARENT = {B.LIGHT_BLUE_STAINED_GLASS, B.YELLOW_STAINED_GLASS}
FACES = [
    ((1,0,0),[(1,0,0),(1,1,0),(1,1,1),(1,0,1)]),
    ((-1,0,0),[(0,1,0),(0,0,0),(0,0,1),(0,1,1)]),
    ((0,1,0),[(1,1,0),(0,1,0),(0,1,1),(1,1,1)]),
    ((0,-1,0),[(0,0,0),(1,0,0),(1,0,1),(0,0,1)]),
    ((0,0,1),[(0,0,1),(1,0,1),(1,1,1),(0,1,1)]),
    ((0,0,-1),[(0,1,0),(1,1,0),(1,0,0),(0,0,0)]),
]
TEXTURES = ['quartz_block_bottom.png','quartz_pillar.png','quartz_pillar_top.png',
            'quartz_bricks.png','chiseled_quartz_block.png','polished_andesite.png',
            'light_blue_stained_glass.png','yellow_stained_glass.png','glowstone.png',
            'smooth_stone.png']


class Camera:
    def __init__(self, size):
        self.size = tuple(size)
        self.angle = 135.0
        self.pitch = 25.0
        self.center = np.array((.5,.5,4.0))
        self.half = 10.5
        self.shake = (0.0,0.0)

    def matrix(self):
        a,p = map(math.radians,(self.angle,self.pitch))
        ca,sa,cp,sp = math.cos(a),math.sin(a),math.cos(p),math.sin(p)
        # World axes are x,y,z; GL axes are x,z,-y.
        return np.array(((ca,-sa,0),(sp*sa,sp*ca,cp),(-cp*sa,-cp*ca,sp)))

    def project(self, points):
        v = (np.asarray(points)-self.center) @ self.matrix().T
        scale = self.size[1]/(2*self.half)
        return np.stack((self.size[0]/2+v[...,0]*scale+self.shake[0],
                         self.size[1]/2-v[...,1]*scale+self.shake[1],v[...,2]),axis=-1)

    def worldToScreen(self, x,y,z):
        return tuple(self.project((x+.5,y+.5,z+.5))[:2])

    def ray(self, pos):
        scale = self.size[1]/(2*self.half)
        x=(pos[0]-self.size[0]/2-self.shake[0])/scale
        y=-(pos[1]-self.size[1]/2-self.shake[1])/scale
        matrix=self.matrix()
        return self.center+np.array((x,y,300))@matrix, np.array((0,0,-1))@matrix

    def hit(self, pos, low, high):
        origin,direction=self.ray(pos)
        lo=np.asarray(low);hi=np.asarray(high)
        # Parallel rays outside a slab miss; inside slabs impose no interval.
        parallel=np.abs(direction)<1e-10
        if np.any(parallel & ((origin<lo)|(origin>hi))):return None
        safe=np.where(parallel,1,direction)
        a=(lo-origin)/safe;b=(hi-origin)/safe
        near=np.where(parallel,-np.inf,np.minimum(a,b)).max()
        far=np.where(parallel,np.inf,np.maximum(a,b)).min()
        return float(max(0,near)) if far>=max(0,near) else None


def make_mesh(cells):
    opaque=[];glass=[]
    for (x,y,z),(block,tint) in cells.items():
        for normal,corners in FACES:
            other=cells.get((x+normal[0],y+normal[1],z+normal[2]))
            if other and (other[0] not in TRANSPARENT or block==other[0]):continue
            ti={B.SMOOTH_QUARTZ:0,B.QUARTZ_PILLAR:2 if normal[2] else 1,
                B.QUARTZ_BRICKS:3,B.CHISELED_QUARTZ:4,B.POLISHED_ANDESITE:5,
                B.LIGHT_BLUE_STAINED_GLASS:6,B.YELLOW_STAINED_GLASS:7,
                B.GLOWSTONE:8,B.SMOOTH_STONE:9}[block]
            shade=1 if block in TRANSPARENT or block==B.GLOWSTONE else .77+.23*max(0,normal[2]-.3*normal[0]-.5*normal[1])
            face=[]
            for corner,(u,v) in zip(corners,((0,1),(1,1),(1,0),(0,0))):
                pos=(x+corner[0],z+corner[2],-(y+corner[1]))
                uv=((ti*64+.5+u*63)/(64*len(TEXTURES)),(.5+v*63)/64)
                face.append((*pos,*uv,*(c*shade for c in PALETTE[tint]),1))
            (glass if block in TRANSPARENT else opaque).append(face)
    return tuple(np.asarray(faces,dtype='float32').reshape(-1,4,9) for faces in (opaque,glass))


class PresentationRenderer:
    def __init__(self):
        self.gl=C.WinDLL('opengl32.dll')
        U,I,F,D,P=C.c_uint,C.c_int,C.c_float,C.c_double,C.c_void_p
        signatures={
            'glViewport':[I,I,I,I],'glEnable':[U],'glDisable':[U],'glClearColor':[F,F,F,F],
            'glClear':[U],'glMatrixMode':[U],'glLoadIdentity':[],'glOrtho':[D,D,D,D,D,D],
            'glClipPlane':[U,P],'glRotatef':[F,F,F,F],'glTranslatef':[F,F,F],'glVertexPointer':[I,U,I,P],
            'glTexCoordPointer':[I,U,I,P],'glColorPointer':[I,U,I,P],
            'glEnableClientState':[U],'glDrawArrays':[U,I,I],'glFinish':[],
            'glTexParameteri':[U,U,I],'glTexImage2D':[U,I,I,I,I,I,U,U,P],
            'glTexSubImage2D':[U,I,I,I,I,I,U,U,P],'glBindTexture':[U,U],
            'glGenTextures':[I,P],'glDeleteTextures':[I,P],
            'glBlendFunc':[U,U],'glDepthMask':[C.c_ubyte],
            'glReadPixels':[I,I,I,I,U,U,P],'glPixelStorei':[U,I],
        }
        for name,args in signatures.items():
            f=getattr(self.gl,name);f.restype=None;f.argtypes=args
        self.gl.glGetError.restype=U
        self.gl.glGetString.restype=C.c_char_p
        self.gl.glGetString.argtypes=[U]
        ids=(U*2)();self.gl.glGenTextures(2,ids)
        self.ids=ids;self.overlay_size=None
        self.region_id=None;self.region_size=None
        atlas=pygame.Surface((64*len(TEXTURES),64),pygame.SRCALPHA)
        for n,name in enumerate(TEXTURES):
            tile=pygame.transform.scale(pygame.image.load(os.path.join(TEXTURES_DIR,name)),(64,64))
            if 'stained_glass' in name:
                tile=tile.convert_alpha()
                alpha=pygame.surfarray.pixels_alpha(tile)
                alpha[:]=np.maximum(75,alpha//2);del alpha
            atlas.blit(tile,(n*64,0))
        self.upload(atlas,self.ids[0],initial=True,linear=False)
        for state in (0x8074,0x8078,0x8076):self.gl.glEnableClientState(state)
        self.gl.glEnable(0x0BE2);self.gl.glBlendFunc(0x0302,0x0303)

    def upload(self,surface,texture,*,initial=False,linear=True):
        gl=self.gl;gl.glBindTexture(0x0DE1,texture)
        pixels=pygame.image.tobytes(surface,'RGBA')
        pointer=C.c_char_p(pixels)
        w,h=surface.get_size()
        if initial:
            for param in (0x2801,0x2800):gl.glTexParameteri(0x0DE1,param,0x2601 if linear else 0x2600)
            for param in (0x2802,0x2803):gl.glTexParameteri(0x0DE1,param,0x812F)
            gl.glTexImage2D(0x0DE1,0,0x1908,w,h,0,0x1908,0x1401,pointer)
        else:gl.glTexSubImage2D(0x0DE1,0,0,0,w,h,0x1908,0x1401,pointer)

    def draw(self,data,mode=0x0007):
        if not len(data):return
        gl=self.gl;data=np.ascontiguousarray(data.reshape(-1,9))
        gl.glVertexPointer(3,0x1406,36,data.ctypes.data)
        gl.glTexCoordPointer(2,0x1406,36,data.ctypes.data+12)
        gl.glColorPointer(4,0x1406,36,data.ctypes.data+20)
        gl.glDrawArrays(mode,0,len(data))

    def flat(self,quad,colors,texture=None):
        gl=self.gl
        if texture is None:gl.glDisable(0x0DE1)
        else:gl.glEnable(0x0DE1);gl.glBindTexture(0x0DE1,texture)
        data=np.array([(*p, *uv, *color) for p,uv,color in zip(quad,((0,0),(1,0),(1,1),(0,1)),colors)],dtype='float32')
        self.draw(data)

    def screen_space(self,size):
        gl=self.gl;w,h=size
        gl.glDisable(0x0B71);gl.glMatrixMode(0x1701);gl.glLoadIdentity()
        gl.glOrtho(0,w,h,0,-1,1);gl.glMatrixMode(0x1700);gl.glLoadIdentity()

    def begin(self,camera,elapsed):
        gl=self.gl;w,h=camera.size
        gl.glViewport(0,0,w,h);gl.glDepthMask(1)
        gl.glClearColor(.008,.017,.03,1);gl.glClear(0x4000|0x0100)
        self.screen_space(camera.size)
        self.flat(((0,0,0),(w,0,0),(w,h,0),(0,h,0)),
                  ((.009,.023,.042,1),(.009,.023,.042,1),(.023,.058,.079,1),(.023,.058,.079,1)))
        # Layered shafts have transparent edges and slowly breathing intensity.
        for i in range(7):
            center=w*(.34+i*.054)+math.sin(elapsed*.08+i)*w*.012
            spread=w*(.035+i*.003)
            alpha=.009+.002*math.sin(elapsed*.3+i)
            self.flat(((center-spread*.25,0,0),(center+spread*.25,0,0),
                       (center+spread*2,h*.9,0),(center-spread*2,h*.9,0)),
                      ((.6,.71,.7,alpha),(.6,.71,.7,alpha),(.3,.55,.65,0),(.3,.55,.65,0)))
        gl.glEnable(0x0B71);gl.glEnable(0x0DE1);gl.glBindTexture(0x0DE1,self.ids[0])
        gl.glMatrixMode(0x1701);gl.glLoadIdentity()
        half=camera.half;aspect=w/h
        dx=camera.shake[0]*2*half/h;dy=-camera.shake[1]*2*half/h
        gl.glOrtho(-half*aspect-dx,half*aspect-dx,-half-dy,half-dy,-350,350)
        gl.glMatrixMode(0x1700);gl.glLoadIdentity()
        gl.glRotatef(camera.pitch,1,0,0);gl.glRotatef(camera.angle,0,1,0)
        x,y,z=camera.center;gl.glTranslatef(-x,-z,y)

    def clip_below(self,height):
        # Capture a world-horizontal plane before per-mesh translations. The
        # rising architecture emerges through the void, with no visible underside.
        equation=(C.c_double*4)(0,1,0,-height)
        self.gl.glClipPlane(0x3000,equation);self.gl.glEnable(0x3000)

    def clear_clip(self):
        self.gl.glDisable(0x3000)

    def mesh(self,mesh,camera,offset=(0,0,0)):
        gl=self.gl;dx,dy,dz=offset;gl.glTranslatef(dx,dz,-dy)
        opaque,glass=mesh
        self.draw(opaque)
        if len(glass):
            a,p=map(math.radians,(camera.angle,camera.pitch))
            centers=glass[:,:,:3].mean(axis=1)
            depths=(-math.sin(a)*centers[:,0]+math.cos(a)*centers[:,2])*math.cos(p)+centers[:,1]*math.sin(p)
            gl.glDepthMask(0);self.draw(glass[np.argsort(depths)]);gl.glDepthMask(1)
        gl.glTranslatef(-dx,-dz,dy)

    def overlay(self,surface):
        self.screen_space(surface.get_size())
        initial=self.overlay_size!=surface.get_size()
        self.upload(surface,self.ids[1],initial=initial)
        self.overlay_size=surface.get_size()
        w,h=surface.get_size()
        self.flat(((0,0,0),(w,0,0),(w,h,0),(0,h,0)),((1,1,1,1),)*4,self.ids[1])

    def capture(self,size):
        w,h=size;data=np.empty((h,w,3),dtype=np.uint8)
        self.gl.glPixelStorei(0x0D05,1)
        self.gl.glReadPixels(0,0,w,h,0x1907,0x1401,data.ctypes.data)
        return pygame.image.frombytes(data[::-1].tobytes(),size,'RGB')

    def overlay_region(self,surface,rect,viewport):
        """Native-size control overlay without an FHD texture upload."""
        self.screen_space(viewport)
        if self.region_id is None:
            self.region_id=(C.c_uint*1)();self.gl.glGenTextures(1,self.region_id)
        initial=self.region_size!=surface.get_size()
        self.upload(surface,self.region_id[0],initial=initial,linear=False)
        self.region_size=surface.get_size()
        x,y,w,h=rect
        self.flat(((x,y,0),(x+w,y,0),(x+w,y+h,0),(x,y+h,0)),((1,1,1,1),)*4,self.region_id[0])

    def close(self):
        if self.region_id is not None:self.gl.glDeleteTextures(1,self.region_id);self.region_id=None
        self.gl.glDeleteTextures(2,self.ids)
