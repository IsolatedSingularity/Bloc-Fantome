"""Original sanctuary: repeated bays, open ribs and a terminal glass apse."""
import math
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
    # Four diagonal ribs converge at each bay's boss. The vault remains open,
    # so its load paths and the processional axis read from the orbiting camera.
    for cy in (-8,8):
        for sx in (-1,1):
            for sy in (-1,1):
                for sample in range(49):
                    u=sample/48
                    x=round(.5+sx*10*(1-u));y=round(cy+.5+sy*8*(1-u))
                    z=round(38+12*math.sin(u*math.pi/2))
                    for dz in (0,1):cells[x,y,z+dz]=(B.SMOOTH_QUARTZ,'stone')
        for x in (0,1):
            for y in (cy,cy+1):
                for z in (49,50,51):cells[x,y,z]=(B.CHISELED_QUARTZ,'stone')
    # Slender attached shafts articulate the large piers without closing bays.
    for x in (-10,10):
        for y in (-16,0,16):
            for dx,dy in ((-1,0),(2,1),(0,-1),(1,2)):
                for z in range(8,36):cells[x+dx,y+dy,z]=(B.QUARTZ_PILLAR,'stone')
    # Paired clerestory lights with a small circular tracery eye above them.
    # This is architectural stonework, not an additional interaction target.
    for x in (-10,10):
        for cy in (-8,8):
            for z in range(27,33):
                for thick in (0,1):cells[x+thick,cy,z]=(B.QUARTZ_PILLAR,'stone')
            for dy in range(-3,4):
                for dz in range(-3,4):
                    if 1.8<=math.hypot(dy,dz)<=2.8:
                        for thick in (0,1):cells[x+thick,cy+dy,34+dz]=(B.SMOOTH_QUARTZ,'stone')
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


def distant_arches():
    """Detached side arcades repeat the nave's bay axes; lantern towers mark arrival."""
    cells={}
    def box(x0,x1,y0,y1,z0,z1,b=B.SMOOTH_QUARTZ,t='distant'):
        for x in range(x0,x1+1):
            for y in range(y0,y1+1):
                for z in range(z0,z1+1):cells[x,y,z]=(b,t)
    # Three bays per side, aligned with the cathedral's 16-cell bay module.
    for side in (-1,1):
        x=side*40
        for y in (-32,-16,0,16):
            box(x-1,x+1,y-1,y+1,-5,26,B.QUARTZ_PILLAR)
            box(x-3,x+3,y-3,y+3,-7,-5,B.QUARTZ_BRICKS)
            box(x-2,x+2,y-2,y+2,24,25)
        for cy in (-24,-8,8):
            tops={u:round(26+10*math.sqrt(max(0,4-(abs(u)/8+1)**2))/math.sqrt(3)) for u in range(-8,9)}
            for u,top in tops.items():
                bottom=min(top,tops.get(u-1,top),tops.get(u+1,top))-1
                box(x-1,x+1,cy+u,cy+u,bottom,top+1)
        # A low cornice unifies each detached arcade without touching the nave.
        box(x-1,x+1,-32,16,23,24)
        # Stepped lantern towers flank the approach, smaller than the sanctuary.
        tx=side*27;ty=39
        for z,half in ((-9,4),(-8,4),(-7,3),(-6,3),(-5,2)):
            box(tx-half,tx+half,ty-half,ty+half,z,z,B.QUARTZ_BRICKS)
        box(tx-1,tx+1,ty-1,ty+1,-4,15,B.QUARTZ_PILLAR)
        box(tx-3,tx+3,ty-3,ty+3,16,17)
        for dx in (-2,2):
            for dy in (-2,2):box(tx+dx,tx+dx,ty+dy,ty+dy,18,23,B.QUARTZ_PILLAR)
        box(tx-1,tx+1,ty-1,ty+1,18,21,B.LIGHT_BLUE_STAINED_GLASS,'distant')
        box(tx,tx,ty,ty,20,21,B.GLOWSTONE,'distant_glow')
        box(tx-3,tx+3,ty-3,ty+3,24,24)
        box(tx-2,tx+2,ty-2,ty+2,25,25)
        box(tx-1,tx+1,ty-1,ty+1,26,27,B.CHISELED_QUARTZ)
    return cells
