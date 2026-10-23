"""Compact File/Edit/View groups routed through the existing workshop commands."""
import pygame
from ui import chrome
from ui.workshop_actions import ACTIONS

GROUPS = {
    'File': ('save_as', 'screenshot', 'menu_slots'),
    'Edit': ('undo', 'redo', 'history'),
    'View': ('fullscreen', 'pin', 'always', 'motion', 'text_scale', 'clean', 'legacy'),
    'More': ('tutorial', 'advanced_tutorial', 'lab', 'help'),
}


def render(s, app):
    screen=app.screen;w,h=screen.get_size();scale=s.text_scale
    width=min(w-48,round(352*min(scale,1.5)))
    row=max(32,s.small.get_linesize()+12);gap=4
    group=s.menu_group;slots=s.menu_slots and group=='File'
    keys=GROUPS[group];content=(len(keys)+(4 if slots else 0))*(row+gap)
    top=s.operation_rect.bottom+8 if s.operation_rect.height else 82
    height=min(h-top-84,2*row+52+content)
    box=pygame.Rect(w-width-24,top,width,height)
    s._panel(screen,box,232,major=True)
    start=len(s.hits);x=box.x+12;inner=width-24;cw=(inner-8)//3
    for i,key in enumerate(('save','open','settings')):
        s._button(screen,(x+i*(cw+4),top+12,cw,row),key.title(),key)
    gy=top+row+20;close_width=chrome.close_size(s.small);gw=(inner-close_width-20)//4
    for i,name in enumerate(GROUPS):
        s._button(screen,(x+i*(gw+4),gy,gw,row),name,'menu_group:'+name,selected=name==group,quiet=True)
    s._button(screen,(box.right-12-close_width,gy,close_width,row),'Close','close',quiet=True)
    y=gy+row+10
    pygame.draw.line(screen,chrome.HOVER,(x,y-5),(box.right-12,y-5))
    s.list_rect=pygame.Rect(x,y,inner,box.bottom-y-12)
    s.max_scroll=max(0,content-s.list_rect.height)
    s.scroll=s.scroller.update(s.max_scroll,s.visibility.reduced_motion)
    old=screen.get_clip();screen.set_clip(s.list_rect);y-=s.scroll
    labels={'menu_slots':'Quick slots', 'always':'Always show controls','pin':'Pin working controls',
            'motion':'Reduced motion','text_scale':f'Text size · {round(scale*100)}%',
            'help':'Controls / shortcuts','advanced_tutorial':'Advanced tutorial'}
    shortcuts={'save_as':'Ctrl+Shift+S','undo':'Ctrl+Z','redo':'Ctrl+Y','fullscreen':'F11'}
    for key in keys:
        rect=pygame.Rect(x,y,inner,row);s._button(screen,rect,'',key,quiet=True)
        label=labels.get(key,ACTIONS[key][1] if key in ACTIONS else key)
        suffix=('−' if slots else '+') if key=='menu_slots' else shortcuts.get(key,'')
        if key in ('always','pin','motion'):
            field={'always':'always','pin':'pinned','motion':'reduced_motion'}[key]
            suffix='On' if getattr(s.visibility,field) else 'Off'
        sw=s.small.size(suffix)[0]
        chrome.wrapped(screen,label,s.small,(x+10,y+5,inner-sw-30,row-4))
        if suffix:screen.blit(s.small.render(suffix,True,chrome.MUTED),(rect.right-sw-10,y+5))
        y+=row+gap
        if key=='menu_slots' and slots:
            from pathlib import Path
            from runtime_paths import SAVES_DIR
            for slot in range(1,5):
                occupied=any((Path(SAVES_DIR)/f'quicksave_{slot}{ext}').is_file() for ext in ('.json.gz','.json'))
                text=f'{slot} · '+('Saved' if occupied else 'Empty')
                screen.blit(s.small.render(text,True,chrome.MUTED),(x+12,y+5))
                label_width=max(100,s.small.size('4 · Saved')[0]+24);bw=(inner-label_width-4)//2
                for i,action in enumerate(('save','load')):
                    s._button(screen,(x+label_width+i*(bw+4),y,bw,row),action.title(),
                              f'quick_{action}_{slot}',enabled=action=='save' or occupied,quiet=True)
                y+=row+gap
    screen.set_clip(old);s.menu_hits=s.hits[start:]
    s.shortcuts_rect=s.category_rect=pygame.Rect(0,0,0,0)
    if s.max_scroll:
        track=s.list_rect;thumb=max(20,round(track.height**2/(track.height+s.max_scroll)))
        pygame.draw.rect(screen,chrome.MUTED,(track.right+5,track.y+round((track.height-thumb)*s.scroll/s.max_scroll),2,thumb))
