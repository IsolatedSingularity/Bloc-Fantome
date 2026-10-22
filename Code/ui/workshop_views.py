"""Measured native drawer layouts sharing the editor's command owner."""
import pygame
from ui import chrome
from ui.workshop_actions import TOOLS,WORLD,MENU,ACTIONS
from ui.help import SHORTCUTS
from ui.tool_icons import draw as icon


def draw_drawer(shell,app):
    if shell.page == "menu":
        from ui.command_palette import render
        return render(shell, app)
    screen=app.screen;w,h=screen.get_size();scale=shell.text_scale
    compact=w<1100 or scale>1.25
    width=min(w-48,round((420 if compact else 600)*min(scale,1.25))) if shell.page=='build' else min(w-48,round(400*scale))
    y=shell.operation_rect.bottom+8 if shell.operation_rect.height else 82
    box=pygame.Rect(w-width-24 if shell.page in ('tools','world','menu') else 24,y,width,h-y-84)
    shell._panel(screen,box,234);shell.shortcuts_rect=pygame.Rect(0,0,0,0);shell.category_rect=pygame.Rect(0,0,0,0)
    x=box.x+16;y=box.y+12
    screen.blit(shell.title.render(shell.page.title(),True,chrome.TEXT),(x,y))
    close_width=chrome.close_size(shell.small)
    shell._button(screen,(box.right-16-close_width,y,close_width,close_width),'Close','close',quiet=True)
    top=y+max(42,shell.title.get_linesize()+8)
    shell.list_rect=pygame.Rect(x,top,width-32,max(30,box.bottom-top-16))
    if shell.page=='build':build(shell,app,box,compact)
    elif shell.page=='world':world(shell,app,box)
    else:tools(shell,app,box)
    if shell.max_scroll:
        rect=shell.list_rect;thumb=max(20,round(rect.height**2/(rect.height+shell.max_scroll)))
        pygame.draw.rect(screen,chrome.MUTED,(rect.right+5,rect.y+round((rect.height-thumb)*shell.scroll/shell.max_scroll),2,thumb))


def build(s,app,box,compact):
    screen=app.screen;area=s.list_rect.copy();row=max(36,s.small.get_linesize()+14)
    search=pygame.Rect(area.x,area.y,area.width,row)
    s._button(screen,search,s.query or 'Search materials…','search',app.searchActive)
    top=search.bottom+8;names=['All','Favorites',*s.categories]
    names=[n for n in names if n!='Recent']
    if compact:
        s._button(screen,(area.x,top,area.width,row),('‹  '+s.category if s.category_menu else s.category+'  ›'),'categories',quiet=True)
        top+=row+8
    rail_width=round(170*s.text_scale) if not compact else area.width
    if not compact or s.category_menu:
        rail=pygame.Rect(area.x,top,rail_width,area.bottom-top);s.category_rect=rail
        s.category_max=max(0,len(names)*(row+4)-rail.height)
        offset=s.category_scroller.update(s.category_max,s.visibility.reduced_motion)
        old=screen.get_clip();screen.set_clip(rail)
        for i,name in enumerate(names):
            r=pygame.Rect(rail.x,rail.y+i*(row+4)-offset,rail.width-4,row)
            if not r.colliderect(rail):continue
            s._button(screen,r,'','category:'+name,s.category==name,quiet=True)
            blocks=s.categories.get(name,app.favoriteBlocks if name=='Favorites' else app.hotbar)
            if blocks:
                spr=app.assetManager.getIconSprite(blocks[0]);size=min(28,row-8)
                if spr:screen.blit(pygame.transform.smoothscale(spr,(size,size)),(r.x+5,r.centery-size//2))
            chrome.wrapped(screen,name,s.small,(r.x+38,r.y+(row-s.small.get_height())//2,r.width-42,row))
        screen.set_clip(old)
    if compact and s.category_menu:
        s.list_rect=pygame.Rect(0,0,0,0);s.max_scroll=0;return
    left=area.x if compact else area.x+rail_width+12
    s.list_rect=pygame.Rect(left,top,area.right-left,area.bottom-top)
    blocks=s.filtered_blocks(app);cols=max(3,s.list_rect.width//72);cell=s.list_rect.width//cols
    s.max_scroll=max(0,((len(blocks)+cols-1)//cols)*cell-s.list_rect.height)
    s.scroll=s.scroller.update(s.max_scroll,s.visibility.reduced_motion)
    old=screen.get_clip();screen.set_clip(s.list_rect)
    for i,block in enumerate(blocks):
        r=pygame.Rect(left+i%cols*cell,top+i//cols*cell-s.scroll,cell-5,cell-5)
        if not r.colliderect(s.list_rect):continue
        s._button(screen,r,'','block:'+block.name,block==app.selectedBlock,quiet=True)
        spr=app.assetManager.getIconSprite(block)
        if spr:
            ratio=min((cell-12)/spr.get_width(),(cell-12)/spr.get_height())
            spr=pygame.transform.scale(spr,(max(1,round(spr.get_width()*ratio)),max(1,round(spr.get_height()*ratio))))
            screen.blit(spr,spr.get_rect(center=r.center))
        if block in app.favoriteBlocks:screen.blit(s.small.render('★',True,chrome.ACCENT),(r.x+3,r.y+1))
        if r.collidepoint(pygame.mouse.get_pos()):
            app.tooltipText=app.world.catalog.definitions[block].name;app.tooltipTimer=250
    screen.set_clip(old)


def tools(s,app,box):
    screen=app.screen;area=s.list_rect.copy();row=max(38,s.small.get_height()+16)
    s.list_rect.height=max(45,round(area.height*.49))
    divider=s.list_rect.bottom+10
    pygame.draw.line(screen,chrome.HOVER,(area.x,divider),(area.right,divider))
    screen.blit(s.small.render('Hotkeys',True,chrome.ACCENT),(area.x,divider+8))
    top=divider+12+s.small.get_linesize()
    s.shortcuts_rect=pygame.Rect(area.x,top,area.width,max(20,area.bottom-top))
    shortcuts=(('Ctrl+Z / Ctrl+Y','Undo / redo'),('Home / Shift+Home','Fit world / center selection'),('F1 / Ctrl+Tab','Reveal / focus controls'))+tuple(item for item in SHORTCUTS if item[0] not in ('Ctrl+Z / Ctrl+Y','Home'))
    stride=s.small.get_linesize()+s.italic.get_linesize()+18
    s.shortcut_max=max(0,len(shortcuts)*stride-s.shortcuts_rect.height)
    offset=s.shortcut_scroller.update(s.shortcut_max,s.visibility.reduced_motion)
    old=screen.get_clip();screen.set_clip(s.shortcuts_rect)
    for i,(keys,label) in enumerate(shortcuts):
        sy=top+i*stride-offset
        if sy+stride<top or sy>s.shortcuts_rect.bottom:continue
        cap=pygame.Rect(area.x,sy,min(area.width,s.small.size(keys)[0]+16),s.small.get_linesize()+4)
        chrome.rounded(screen,chrome.CONTROL,cap,5)
        screen.blit(s.small.render(chrome.ellipsize(keys,s.small,cap.width-12),True,chrome.TEXT),(cap.x+6,cap.y+1))
        chrome.wrapped(screen,label,s.italic,(area.x+4,cap.bottom+3,area.width-8,s.italic.get_linesize()+2),chrome.MUTED)
    screen.set_clip(old)
    s.max_scroll=max(0,len(TOOLS)*(row+6)-s.list_rect.height);s.scroll=s.scroller.update(s.max_scroll,s.visibility.reduced_motion)
    screen.set_clip(s.list_rect)
    for i,(action,label,route,args,field) in enumerate(TOOLS):
        r=pygame.Rect(area.x,area.y+i*(row+6)-s.scroll,area.width,row)
        if not r.colliderect(s.list_rect):continue
        value=getattr(app,field,False) if field else False
        s._button(screen,r,'',action,bool(value))
        chrome.wrapped(screen,label,s.small,(r.x+10,r.y+(row-s.small.get_height())//2,r.width-54,row))
        size=min(32,row-8)
        icon(screen,action,pygame.Rect(r.right-size-8,r.centery-size//2,size,size),chrome.ACCENT if value else chrome.MUTED)
    screen.set_clip(old)


def world(s,app,box):
    screen=app.screen;area=s.list_rect;gap=8;cols=3
    toggles=[r for r in WORLD if r[4]]
    actions=[r for r in WORLD if not r[4] and r[0] not in ('grow','shrink','noise','map')]
    tile=(area.width-2*gap)//3;tile_h=min(104,max(72,tile));row=max(36,s.small.get_linesize()+12)
    toggle_h=((len(toggles)+2)//3)*(tile_h+gap)
    action_h=((len(actions)+3)//4)*56
    s.max_scroll=max(0,toggle_h+24+action_h-area.height);s.scroll=s.scroller.update(s.max_scroll,s.visibility.reduced_motion)
    old=screen.get_clip();screen.set_clip(area);tip=None
    colors={'rain':(113,176,229),'snow':(195,225,244),'sun':(240,194,102),'lighting':(240,215,133),'clouds':(182,198,221),'sky':(152,162,232),'flow':(96,205,189),'horror_rain':(221,116,132)}
    for i,(action,label,route,args,field) in enumerate(toggles):
        value=bool(getattr(app,field));r=pygame.Rect(area.x+i%3*(tile+gap),area.y+i//3*(tile_h+gap)-s.scroll,tile,tile_h)
        if not r.colliderect(area):continue
        s.hits.append((r.clip(area),action,True))
        level=s.tile_levels.get(action,float(value));delta=s.frame_dt/.20
        level=float(value) if s.visibility.reduced_motion else min(float(value),level+delta) if value else max(0.,level-delta)
        s.tile_levels[action]=level
        color=colors[action];bg=tuple(round(a+(b*.45-a)*level) for a,b in zip(chrome.CONTROL,color))
        chrome.rounded(screen,(*bg,235),r,14)
        if value and not s.visibility.reduced_motion:
            from ui.generated_icons import weather_effect
            weather_effect(screen,action,r,pygame.time.get_ticks()/1000)
        focused=s.focus==action or r.collidepoint(pygame.mouse.get_pos())
        if focused:
            pygame.draw.rect(screen,chrome.FOCUS,r.inflate(-2,-2),1,border_radius=13)
            tip=label+' · '+('On' if value else 'Off')
        track=pygame.Rect(r.right-38,r.bottom-16,28,8)
        pygame.draw.rect(screen,chrome.MUTED,track,1,border_radius=4)
        pygame.draw.circle(screen,color if value else chrome.MUTED,(track.x+4+round(20*level),track.centery),3)
        state=s.small.render('On' if value else 'Off',True,color if value else chrome.MUTED)
        screen.blit(state,(r.x+10,r.bottom-state.get_height()-6))
        icon_size=min(68,tile_h-32,tile-20)
        icon(screen,action,pygame.Rect(r.centerx-icon_size//2,r.centery-icon_size//2,icon_size,icon_size),color if value else chrome.MUTED,
             phase=pygame.time.get_ticks()/1000 if value and not s.visibility.reduced_motion else 0)
    top=area.y+toggle_h+16-s.scroll;aw=(area.width-3*gap)//4
    pygame.draw.line(screen,chrome.HOVER,(area.x,top-8),(area.right,top-8))
    for i,(action,label,*_) in enumerate(actions):
        r=pygame.Rect(area.x+i%4*(aw+gap),top+i//4*56,aw,48)
        if not r.colliderect(area):continue
        active=action==app.currentDimension
        s._button(screen,r,'',action,selected=False)
        if active:
            accent={'overworld':(78,143,94),'nether':(168,66,60),'end':(132,91,171)}[action]
            chrome.rounded(screen,(*accent,235),r,10)
        focused=s.focus==action or r.collidepoint(pygame.mouse.get_pos())
        if focused:tip=label
        icon(screen,action,pygame.Rect(r.centerx-19,r.centery-19,38,38),(255,255,255),
             phase=pygame.time.get_ticks()/1000 if (active or focused) and not s.visibility.reduced_motion else 0)
    screen.set_clip(old)
    if tip:
        r=pygame.Rect(box.x+12,box.bottom-38,box.width-24,30);chrome.panel(screen,r,250)
        chrome.wrapped(screen,tip,s.small,r.inflate(-12,-4))
