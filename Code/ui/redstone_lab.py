"""Native-size workbench chrome and direct manipulation for the Redstone Lab."""
import pygame
from domain.blocks import BlockType as B, BlockProperties, Facing
from engine.redstone_lab import LAB_CIRCUITS

INK=(20,23,28)
PANEL=(27,31,37)
EDGE=(65,71,79)
TEXT=(236,232,222)
MUTED=(159,166,174)
ACCENT=(226,94,78)


def label(app,text,pos,color=TEXT,font=None):
    app.screen.blit((font or app.labSmallFont).render(text,True,color),pos)


def button(app,rect,text,selected=False):
    hovered=rect.collidepoint(pygame.mouse.get_pos())
    pygame.draw.rect(app.screen,(72,42,42) if selected else (45,51,60) if hovered else PANEL,rect,border_radius=5)
    pygame.draw.rect(app.screen,ACCENT if selected else EDGE,rect,1,border_radius=5)
    image=app.labSmallFont.render(text,True,TEXT)
    app.screen.blit(image,image.get_rect(center=rect.center))


def wrapped(app,text,x,y,width,max_lines=3):
    line='';lines=[]
    for word in text.split():
        trial=(line+' '+word).strip()
        if app.labSmallFont.size(trial)[0]>width and line:
            lines.append(line);line=word
        else:line=trial
    if line:lines.append(line)
    for line in lines[:max_lines]:label(app,line,(x,y),MUTED);y+=17
    return y


def thumbnail(app,circuit,size=(48,32)):
    """Real block silhouettes, cached per exhibit; never scale interface text."""
    cache=app.redstoneLabPreviews
    if circuit.key in cache:return cache[circuit.key]
    cells=[]
    for (x,y,z),(block,state) in circuit.cells.items():
        if (x,y,z) in circuit.shell:continue
        sprite=app.assetManager.getBlockSprite(block)
        if sprite is not None:cells.append(((x-y)*16,(x+y)*8-z*16,sprite))
    if not cells:return None
    left=min(x for x,y,s in cells);top=min(y for x,y,s in cells)
    right=max(x+s.get_width() for x,y,s in cells);bottom=max(y+s.get_height() for x,y,s in cells)
    surface=pygame.Surface((right-left,bottom-top),pygame.SRCALPHA)
    for x,y,sprite in cells:surface.blit(sprite,(x-left,y-top))
    ratio=min(size[0]/surface.get_width(),size[1]/surface.get_height())
    result=pygame.transform.smoothscale(surface,(max(1,int(surface.get_width()*ratio)),max(1,int(surface.get_height()*ratio))))
    cache[circuit.key]=result
    return result


def panel(app):
    width,height=app.screen.get_size();x=app._worldViewportRight();w=width-x
    pygame.draw.rect(app.screen,INK,(x,0,w,height))
    pygame.draw.line(app.screen,EDGE,(x,0),(x,height))
    label(app,'REDSTONE LAB',(x+14,16),TEXT,app.smallFont)
    label(app,'Java 1.16.1  /  ordinary power',(x+14,43),MUTED)
    app.redstoneLabModeRects={key:pygame.Rect(x+12+i*(w-20)//2,69,(w-28)//2,30) for i,key in enumerate(('test','build'))}
    for key,rect in app.redstoneLabModeRects.items():button(app,rect,'INTERACT' if key=='test' else 'BUILD',(key=='test')==app.interactionMode)
    app.redstoneLabActionRects={key:pygame.Rect(x+12+i*(w-20)//3,108,(w-32)//3,28) for i,key in enumerate(('pause','step','reset'))}
    for key,rect in app.redstoneLabActionRects.items():
        button(app,rect,('RESUME' if app.redstoneLabPaused else 'PAUSE') if key=='pause' else key.upper(),key=='pause' and app.redstoneLabPaused)
    app.redstoneLabCircuitRects={};app.redstoneLabComponentRects={};app.redstoneLabControlRects={}
    c=LAB_CIRCUITS.get(app.redstoneLabCircuitKey)
    y=149
    if app.interactionMode:
        label(app,'CIRCUIT COLLECTION',(x+14,y),MUTED);y+=23
        row=28 if height<760 else 42
        for key,circuit in LAB_CIRCUITS.items():
            rect=pygame.Rect(x+12,y,w-24,row-4);app.redstoneLabCircuitRects[key]=rect
            selected=key==app.redstoneLabCircuitKey
            pygame.draw.rect(app.screen,(59,38,40) if selected else PANEL,rect,border_radius=4)
            pygame.draw.rect(app.screen,ACCENT if selected else EDGE,rect,1,border_radius=4)
            preview=thumbnail(app,circuit)
            if preview:
                if preview.get_height()>rect.height-4:
                    ratio=(rect.height-4)/preview.get_height()
                    preview=pygame.transform.smoothscale(preview,(max(1,int(preview.get_width()*ratio)),rect.height-4))
                app.screen.blit(preview,preview.get_rect(center=(x+40,rect.centery)))
            label(app,circuit.name,(x+69,rect.centery-7))
            y+=row
        y+=5
        if c:
            y=wrapped(app,c.description,x+14,y,w-28,3)+8
            for title,pos in (() if c.key=='counter' else c.controls):
                rect=pygame.Rect(x+12,y,w-24,25);app.redstoneLabControlRects[pos]=rect
                props=app.world.getBlockProperties(*pos)
                valid=app.world.getBlock(*pos) in (B.LEVER,B.STONE_BUTTON)
                button(app,rect,title+('  ON' if props and props.powered else ''),bool(valid and props and props.powered))
                y+=30
            if c.key=='counter':
                bits=[int(bool((app.world.getBlockProperties(*pos) or BlockProperties()).redstonePower)) for pos in c.outputs]
                value=sum(bit<<i for i,bit in enumerate(bits))
                label(app,f'{value:02d}   /   '+''.join(map(str,reversed(bits))),(x+14,y),ACCENT,app.smallFont)
                y+=29
                pulse=pygame.Rect(x+12,y,w-24,28)
                app.redstoneLabActionRects['pulse']=pulse
                button(app,pulse,'PULSE +1' if app.redstoneLabPulseStart is None else 'CLOCK CYCLE IN PROGRESS',app.redstoneLabPulseStart is not None)
                y+=34
    else:
        label(app,'COMPONENTS',(x+14,y),MUTED);y+=24
        components=((B.REDSTONE_DUST,'Dust'),(B.REDSTONE_TORCH,'Torch'),(B.REDSTONE_WALL_TORCH,'Wall torch'),
                    (B.LEVER,'Lever'),(B.STONE_BUTTON,'Button'),(B.REPEATER,'Repeater'),
                    (B.PISTON,'Piston'),(B.STICKY_PISTON,'Sticky'),(B.REDSTONE_LAMP,'Lamp'),
                    (B.REDSTONE_BLOCK,'Power'),(B.SLIME_BLOCK,'Slime'),(B.HONEY_BLOCK,'Honey'),
                    (B.SMOOTH_STONE,'Support'),(B.QUARTZ_BLOCK,'Quartz'),(B.COMPARATOR,'Compare'))
        for i,(block,name) in enumerate(components):
            rect=pygame.Rect(x+12+(i%3)*(w-20)//3,y+(i//3)*58,(w-32)//3,53)
            app.redstoneLabComponentRects[block]=rect
            button(app,rect,'',block==app.selectedBlock)
            sprite=app.assetManager.getPanelPreviewIcon(block)
            if sprite:
                sprite=pygame.transform.scale(sprite,(28,28));app.screen.blit(sprite,sprite.get_rect(midtop=(rect.centerx,rect.top+2)))
            text=app.labSmallFont.render(name,True,TEXT);app.screen.blit(text,text.get_rect(midbottom=(rect.centerx,rect.bottom-4)))
        y+=5*58+10
        label(app,'Facing: '+app.previewFacing.name,(x+14,y),ACCENT);y+=24
        y=wrapped(app,'R rotates the preview. Shift+R rotates a placed component. Ctrl+Z undoes edits.',x+14,y,w-28,3)
    app.redstoneLabRulesRect=pygame.Rect(x+12,min(y+6,height-106),w-24,24)
    cut=pygame.Rect(x+12,height-80,w-24,28)
    app.redstoneLabActionRects['cutaway']=cut
    button(app,cut,'CUTAWAY  '+('ON' if app.redstoneLabCutaway else 'OFF'),app.redstoneLabCutaway)
    app.redstoneLabButtonRect=pygame.Rect(x+12,height-41,w-24,29)
    button(app,app.redstoneLabButtonRect,'RETURN TO BUILD')


def header(app):
    c=LAB_CIRCUITS.get(app.redstoneLabCircuitKey)
    if not c:return
    w=app._worldViewportRight()
    rect=pygame.Rect(16,14,w-32,86)
    pygame.draw.rect(app.screen,INK,rect,border_radius=6)
    pygame.draw.line(app.screen,ACCENT,(rect.x+14,rect.y+15),(rect.x+14,rect.bottom-15),3)
    label(app,c.name.upper(),(rect.x+27,rect.y+12),TEXT,app.smallFont)
    wrapped(app,c.instruction,rect.x+27,rect.y+39,rect.width-48,2)
    foot=pygame.Rect(16,app.screen.get_height()-42,w-32,27)
    pygame.draw.rect(app.screen,INK,foot,border_radius=5)
    label(app,'Click to use  /  I build-interact  /  Q E rotate  /  wheel zoom  /  middle drag',(foot.x+10,foot.y+6),MUTED)


def cursor(app):
    if not app.interactionMode or not app.hoveredSourceBlock:return
    pos=app.hoveredSourceBlock;block=app.world.getBlock(*pos)
    if block not in (B.LEVER,B.STONE_BUTTON,B.REPEATER,B.COMPARATOR):return
    sx,sy=app.renderer.worldToScreen(*pos)
    center=(int(sx),int(sy+32*app.zoomLevel))
    pygame.draw.circle(app.screen,ACCENT,center,max(12,int(12*app.zoomLevel)),2)
    props=app.world.getBlockProperties(*pos) or BlockProperties()
    text=('Subtract' if props.comparatorSubtract else 'Compare') if block==B.COMPARATOR else 'Delay: '+str(props.repeaterDelay)+' redstone ticks' if block==B.REPEATER else 'Click to press' if block==B.STONE_BUTTON else 'Click to turn '+('off' if props.powered else 'on')
    badge=app.labSmallFont.render(text,True,TEXT)
    rect=badge.get_rect(midbottom=(center[0],center[1]-18)).inflate(14,10)
    rect.clamp_ip(pygame.Rect(8,105,app._worldViewportRight()-16,app.screen.get_height()-155))
    pygame.draw.rect(app.screen,INK,rect,border_radius=4)
    app.screen.blit(badge,badge.get_rect(center=rect.center))


def pick_control(app,mx,my):
    """Give visible controls a screen-sized target without reaching through walls."""
    from domain.blocks import SlabPosition
    candidates=[]
    order=app._visibleBlocksInDrawOrder()
    for depth,x,y,z,block in order:
        if block not in (B.LEVER,B.STONE_BUTTON,B.REPEATER,B.COMPARATOR):continue
        sx,sy=app.renderer.worldToScreen(x,y,z)
        # Reject distant cells before requesting model geometry or properties.
        # The padding includes the minimum 28-pixel interaction target.
        if abs(mx-sx)>32*app.zoomLevel+28 or not sy-28<=my<=sy+96*app.zoomLevel+28:
            continue
        props=app.world.getBlockProperties(x,y,z) or BlockProperties()
        sprite=app.assetManager.getDetailSprite(block,props.facing.in_view(app.renderer.viewRotation),
            props.comparatorSubtract if block==B.COMPARATOR else False,SlabPosition.BOTTOM,
            powered=props.powered,power=props.redstonePower,delay=props.repeaterDelay,locked=props.repeaterLocked)
        if sprite is None:continue
        bounds=sprite.get_bounding_rect()
        rect=pygame.Rect(sx-sprite.get_width()*app.zoomLevel/2+bounds.x*app.zoomLevel,
                         sy+bounds.y*app.zoomLevel,max(1,bounds.width*app.zoomLevel),max(1,bounds.height*app.zoomLevel))
        target=rect.inflate(max(0,28-rect.width),max(0,28-rect.height))
        if not target.collidepoint(mx,my):continue
        hidden=False
        for front_depth,fx,fy,fz,front in reversed(order):
            if front_depth<=depth:break
            definition=app.world.catalog.definitions.get(front)
            if definition and not definition.transparent and not definition.modelKind:
                if app._pickRenderedBlockFace(mx,my,fx,fy,fz,front) is not None:
                    hidden=True;break
        if not hidden:
            candidates.append(((mx-rect.centerx)**2+(my-rect.centery)**2,(x,y,z)))
    return min(candidates)[1] if candidates else None
