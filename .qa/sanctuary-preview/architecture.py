"""Static architecture study. Not imported by the application."""
import os,sys,math,json,time
from pathlib import Path
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'Code'))
from domain.blocks import BlockType as B


def sanctuary():
    cells={}
    def put(x,y,z,b=B.SMOOTH_QUARTZ,t='stone'):
        for dx in (0,1):
            for dy in (0,1):
                for dz in (0,1):cells[(2*x+dx,2*y+dy,2*z+dz)]=(b,t)
    def box(x0,x1,y0,y1,z0,z1,b=B.SMOOTH_QUARTZ,t='stone'):
        for x in range(x0,x1+1):
            for y in range(y0,y1+1):
                for z in range(z0,z1+1):put(x,y,z,b,t)
    def arch(axis,fixed,center,half,spring,rise,base=3,glass=False):
        # One pointed profile reused for the nave, arcades and glazing.
        for u in range(-half*2,half*2+2):
            distance=min(1,abs((u-.5)/(half*2)))
            curve=math.sqrt(max(0,4-(distance+1)**2))/math.sqrt(3)
            top=round(2*(spring+rise*curve))
            adjacent=[]
            for neighbor in (u-1,u+1):
                d=min(1,abs((neighbor-.5)/(half*2)))
                adjacent.append(round(2*(spring+rise*math.sqrt(max(0,4-(d+1)**2))/math.sqrt(3))))
            rib_bottom=min(top,*adjacent)
            for z in range(base*2,top+2):
                rim=u<=-half*2+1 or u>=half*2 or z>=rib_bottom
                if not rim and not glass:continue
                block=B.SMOOTH_QUARTZ if rim else B.LIGHT_BLUE_STAINED_GLASS
                tint='stone' if rim else 'glass'
                for thick in (0,1):
                    x,y=(center*2+u,fixed*2+thick) if axis=='x' else (fixed*2+thick,center*2+u)
                    cells[(x,y,z)]=(block,tint)
    # Single axial plan, with a clipped apse rather than an arbitrary platform.
    for x in range(-9,10):
        for y in range(-15,11):
            if y<-11 and abs(x)>9+(y+11):continue
            put(x,y,0,B.POLISHED_ANDESITE,'foundation')
            put(x,y,1,B.QUARTZ_BRICKS,'base')
            if abs(x)<=6:
                put(x,y,2,B.SMOOTH_QUARTZ,'floor' if abs(x)>2 else 'aisle')
    for y,height in ((14,0),(13,0),(12,1),(11,1),(10,2)):
        box(-3,3,y,y,0,height,B.SMOOTH_QUARTZ,'stone')
    # Two 8-block bays: repeated piers, arcade openings and aligned buttresses.
    for sign in (-1,1):
        x=sign*5
        for y in (-8,0,8):
            box(x-1,x+1,y-1,y+1,3,3,B.QUARTZ_BRICKS)
            box(x,x,y,y,4,19,B.QUARTZ_PILLAR)
            box(x-1,x+1,y-1,y+1,18,18)
            # Outer pier and an inclined flying strut carry the same bay line.
            ox=sign*8
            box(ox,ox,y,y,2,10,B.QUARTZ_BRICKS,'base')
            box(ox,ox,y,y,11,13,B.QUARTZ_PILLAR)
            put(ox,y,14,B.CHISELED_QUARTZ)
            for d in range(1,4):
                box(sign*(5+d),sign*(5+d),y,y,19-d*2,21-d*2)
        for cy in (-4,4):
            arch('y',x,cy,4,7,4)
            arch('y',x,cy,3,15,3,base=13,glass=True)
        # Continuous string course ties the two bays together.
        box(x,x,-8,8,13,13)
        box(x,x,-8,8,19,19)
    # Open transverse ribs keep the interior readable from above.
    for y in (-8,0,8):arch('x',y,0,5,19,6,base=19)
    # Apse: tall central lancet, flanking oblique windows, stepped sanctuary.
    for y,half in ((-9,5),(-10,5),(-11,4),(-12,4),(-13,3)):
        box(-half,half,y,y,3,4,B.SMOOTH_QUARTZ,'floor')
    arch('x',-13,0,4,16,5,base=5,glass=True)
    # Slim stone mullion and a diamond of amber remain the only warm glass accent.
    box(0,0,-13,-13,5,15,B.QUARTZ_PILLAR)
    for x,z in ((0,18),(-1,17),(0,17),(1,17),(0,16)):
        put(x,-13,z,B.YELLOW_STAINED_GLASS,'amber')
    for sign in (-1,1):
        for x,y in ((sign*5,-9),(sign*5,-10),(sign*4,-11),(sign*4,-12)):
            for z in range(5,17):
                put(x,y,z,B.QUARTZ_PILLAR if y%2 else B.LIGHT_BLUE_STAINED_GLASS,
                    'stone' if y%2 else 'glass')
            put(x,y,17)
    # A low reliquary on the axis, with light recessed into its stone base.
    box(-1,1,-11,-10,5,5,B.CHISELED_QUARTZ)
    put(0,-10,6,B.GLOWSTONE,'glow')
    return cells


def render():
    import pygame
    from blocFantome import BlocFantome
    from engine.renderer import IsometricRenderer
    from ui.opening_scene import OpeningScene
    app=BlocFantome();assert app.assetManager.loadAllAssets()
    cells=sanctuary();out=ROOT/'.qa/sanctuary-preview'
    size=(1920,1080)
    screen=pygame.display.set_mode(size)
    scene=OpeningScene(size,app.assetManager)
    palette={'foundation':(69,84,104),'base':(179,184,184),'floor':(211,211,201),
             'aisle':(163,180,188),'stone':(251,244,225),'glass':(152,188,204),
             'amber':(242,205,140),'glow':(255,234,187)}
    for rotation in (0,1,2,3):
        renderer=IsometricRenderer(0,0);renderer.setViewRotation(rotation)
        points=[renderer.worldToScreen(*p) for p in cells]
        minx=min(x for x,y in points)-32;maxx=max(x for x,y in points)+32
        miny=min(y for x,y in points);maxy=max(y for x,y in points)+70
        zoom=min((size[0]-220)/(maxx-minx),(size[1]-130)/(maxy-miny))
        renderer.setZoom(zoom);renderer.offsetX=size[0]/2-(minx+maxx)*zoom/2
        renderer.offsetY=size[1]/2-(miny+maxy)*zoom/2
        screen.blit(scene.backdrop,(0,0))
        scene.pool.set_alpha(180);screen.blit(scene.pool,scene.pool.get_rect(center=(960,790)))
        sprites={}
        start=time.perf_counter()
        for p,(b,t) in sorted(cells.items(),key=lambda v:(renderer.depthKey(*v[0]),v[0][2])):
            k=(b,t)
            if k not in sprites:
                raw=app.assetManager.getBlockSprite(b)
                sprite=app.assetManager.getScaledSprite(raw,zoom,flipped=rotation in (1,3)).copy()
                sprite.fill((*palette[t],255),special_flags=pygame.BLEND_RGBA_MULT)
                sprites[k]=sprite
            sprite=sprites[k];px,py=renderer.worldToScreen(*p)
            screen.blit(sprite,(px-sprite.get_width()//2,py))
        pygame.image.save(screen,out/f'sanctuary-view-{rotation}.png')
        print(rotation,round(zoom,3),round((time.perf_counter()-start)*1000,2))
    (out/'geometry.json').write_text(json.dumps([dict(x=x,y=y,z=z,block=b.name,tint=t) for (x,y,z),(b,t) in cells.items()]))
    app.worldLoadExecutor.shutdown(wait=True);pygame.quit()

if __name__=='__main__':render()
