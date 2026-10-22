"""Measured native drawer layouts sharing the editor's command owner."""
import pygame
from ui import chrome
from ui.workshop_actions import TOOLS,WORLD,MENU,ACTIONS
from ui.help import SHORTCUTS
from ui.tool_icons import draw as icon


def draw_drawer(shell,app):
    screen=app.screen;w,h=screen.get_size();scale=shell.text_scale
    compact=w<1100 or scale>1.25
    width=min(w-48,round((420 if compact else 600)*min(scale,1.25))) if shell.page=='build' else min(w-48,round(400*scale))
    y=shell.operation_rect.bottom+8 if shell.operation_rect.height else 82
    box=pygame.Rect(w-width-24 if shell.page in ('tools','world','menu') else 24,y,width,h-y-84)
    shell._panel(screen,box,234);shell.shortcuts_rect=pygame.Rect(0,0,0,0);shell.category_rect=pygame.Rect(0,0,0,0)
    x=box.x+16;y=box.y+12
    screen.blit(shell.title.render(shell.page.title(),True,chrome.TEXT),(x,y))
    shell._button(screen,(box.right-94,y,78,max(30,shell.small.get_height()+6)),'Close','close',quiet=True)
    top=y+max(42,shell.title.get_linesize()+8)
    shell.list_rect=pygame.Rect(x,top,width-32,max(30,box.bottom-top-16))
    if shell.page=='build':build(shell,app,box,compact)
    elif shell.page=='world':world(shell,app,box)
    elif shell.page=='menu':menu(shell,app,box)
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
        pygame.draw.polygon(screen,chrome.HOVER,[(r.right-38,r.y),(r.right,r.y),(r.right,r.y+38)])
        icon(screen,action,pygame.Rect(r.right-32,r.y+4,26,26),chrome.ACCENT if value else chrome.MUTED)
    screen.set_clip(old)


def world(s,app,box):
    screen=app.screen;area=s.list_rect;gap=8;cols=3
    toggles=[r for r in WORLD if r[4]]
    actions=[r for r in WORLD if not r[4] and r[0] not in ('grow','shrink','noise','map')]
    tile=(area.width-2*gap)//3;tile_h=min(104,max(72,tile));row=max(36,s.small.get_linesize()+12)
    toggle_h=((len(toggles)+2)//3)*(tile_h+gap)
    action_h=((len(actions)+1)//2)*(row+6)
    s.max_scroll=max(0,toggle_h+24+action_h-area.height);s.scroll=s.scroller.update(s.max_scroll,s.visibility.reduced_motion)
    old=screen.get_clip();screen.set_clip(area);tip=None
    colors={'rain':(113,176,229),'snow':(195,225,244),'sun':(240,194,102),'lighting':(240,215,133),'clouds':(182,198,221),'sky':(152,162,232),'flow':(96,205,189),'horror_rain':(221,116,132)}
    for i,(action,label,route,args,field) in enumerate(toggles):
        value=bool(getattr(app,field));r=pygame.Rect(area.x+i%3*(tile+gap),area.y+i//3*(tile_h+gap)-s.scroll,tile,tile_h)
        if not r.colliderect(area):continue
        s.hits.append((r.clip(area),action,True))
        level=s.tile_levels.get(action,float(value));level+= (float(value)-level)*(1 if s.visibility.reduced_motion else min(1,s.frame_dt/.16));s.tile_levels[action]=level
        color=colors[action];bg=tuple(round(a+(b*.45-a)*level) for a,b in zip(chrome.CONTROL,color))
        chrome.rounded(screen,(*bg,235),r,14)
        focused=s.focus==action or r.collidepoint(pygame.mouse.get_pos())
        if focused:
            pygame.draw.rect(screen,chrome.FOCUS,r.inflate(-2,-2),1,border_radius=13)
            tip=label+' · '+('On' if value else 'Off')
        icon(screen,action,pygame.Rect(r.centerx-25,r.centery-25,50,50),color if value else chrome.MUTED,
             phase=pygame.time.get_ticks()/1000 if value and not s.visibility.reduced_motion else 0)
    top=area.y+toggle_h+16-s.scroll;aw=(area.width-gap)//2
    for i,(action,label,*_) in enumerate(actions):
        r=pygame.Rect(area.x+i%2*(aw+gap),top+i//2*(row+6),aw,row)
        s._button(screen,r,label,action,quiet=True)
    screen.set_clip(old)
    if tip:
        r=pygame.Rect(box.x+12,box.bottom-38,box.width-24,30);chrome.panel(screen,r,250)
        chrome.wrapped(screen,tip,s.small,r.inflate(-12,-4))


def menu(s,app,box):
    screen=app.screen;area=s.list_rect;row=max(36,s.small.get_linesize()+12);gap=6
    groups=[('',('save','open','settings')),('Workspace',('save_as','undo','redo','history','screenshot','fullscreen')),
            ('Explore',('tutorial','advanced_tutorial','lab','help')),('Presentation',('pin','always','motion','text_scale','clean','legacy')),
            ('Quick save',tuple('quick_save_'+str(i) for i in range(1,5))),('Quick load',tuple('quick_load_'+str(i) for i in range(1,5)))]
    header=s.small.get_linesize()+12
    height=sum((header if title else 0)+((len(keys)+(3 if not title else 2)-1)//(3 if not title else 2))*(row+(22 if not title else 0)+gap)+12 for title,keys in groups)
    s.max_scroll=max(0,height-area.height);s.scroll=s.scroller.update(s.max_scroll,s.visibility.reduced_motion)
    old=screen.get_clip();screen.set_clip(area);y=area.y-s.scroll
    for title,keys in groups:
        if title:screen.blit(s.small.render(title,True,chrome.MUTED),(area.x,y));y+=header
        cols=3 if not title else 2;cw=(area.width-(cols-1)*gap)//cols;rh=row+(22 if not title else 0)
        for i,key in enumerate(keys):
            label=ACTIONS[key][1]
            label={'open':'Open','settings':'Settings','always':'Always visible','pin':'Pin controls','help':'Controls','fullscreen':'Fullscreen','advanced_tutorial':'Advanced tour'}.get(key,label)
            if key.startswith('quick_'):label=key.rsplit('_',1)[1]
            s._button(screen,(area.x+i%cols*(cw+gap),y+i//cols*(rh+gap),cw,rh),label,key,quiet=bool(title))
        y+=((len(keys)+cols-1)//cols)*(rh+gap)+12
    screen.set_clip(old)
