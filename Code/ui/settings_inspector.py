"""Compact Settings inspector. Rendering and input share measured rectangles."""
import pygame
from ui import chrome
from ui.fonts import TEXT_SCALE


def layout(app):
    from ui.fonts import TEXT_SCALE
    w,h=app.screen.get_size();line=app.smallFont.get_linesize()
    width=min(w-48,round(500*min(TEXT_SCALE,1.3)))
    row=max(30,line+6);audio=max(34,line+2)
    fields=[('Auto-save (5 min)','autoSaveEnabled'),('Smooth camera','smoothCameraEnabled'),
            ('Coordinates','showCoordinates'),('Block outline','showBlockOutline'),
            ('Block tooltip','showBlockTooltip'),('World-centered rotation','worldCenteredRotation'),
            ('Autoplay introduction','skip')]
    if not app.workshop.active(app):fields.insert(3,('Grid','showGrid'))
    title=max(42,app.sectionFont.get_linesize()+12);heading=line+4
    height=title+heading*2+3*audio+len(fields)*row+row+line+22
    rect=pygame.Rect((w-width)//2,max(30,(h-height)//2),width,height)
    x=rect.x+22;y=rect.y+title+heading
    sliders=[(kind,pygame.Rect(x,y+i*audio,width-44,audio)) for i,kind in enumerate(('music','ambient','effects'))]
    top=y+3*audio+heading
    controls=[(label,attr,pygame.Rect(x,top+i*row,width-44,row)) for i,(label,attr) in enumerate(fields)]
    controls.append(('Play Introduction','opening',pygame.Rect(x,top+len(fields)*row+10,min(width-44,app.smallFont.size('Play Introduction')[0]+28),row)))
    controls.append(('VSync unavailable in this display mode','vsync_unavailable',pygame.Rect(x,controls[-1][2].bottom+7,width-44,line)))
    return rect,sliders,controls


def close_rect(app,rect):
    size=max(28,app.smallFont.get_linesize()+4)
    return pygame.Rect(rect.right-size-14,rect.y+10,size,size)


def slider(app,label,value,x,y,width):
    screen=app.screen;font=app.smallFont;kind=label.split()[0].lower()
    line=font.get_linesize();cy=y+max(34,line+2)//2
    muted=getattr(app,kind+'Muted',False)
    text=font.render(kind.title(),True,chrome.TEXT);screen.blit(text,(x,cy-text.get_height()//2))
    mute=pygame.Rect(x+width-28,cy-13,28,26)
    if mute.collidepoint(pygame.mouse.get_pos()):chrome.rounded(screen,chrome.HOVER,mute,5)
    chrome.speaker(screen,mute,muted)
    label_width=max(font.size(n)[0] for n in ('Music','Ambient','Effects'))+20
    value_width=font.size('Muted')[0]+12
    track=pygame.Rect(x+label_width,cy-2,width-label_width-value_width-40,4)
    chrome.rounded(screen,(51,67,87),track,2)
    fill=track.copy();fill.width=round(track.width*value)
    if fill.width:chrome.rounded(screen,chrome.ACCENT if not muted else chrome.MUTED,fill,2)
    pygame.draw.circle(screen,chrome.TEXT,(track.x+round(track.width*value),cy),5)
    text=font.render('Muted' if muted else f'{round(value*100)}%',True,chrome.MUTED)
    screen.blit(text,text.get_rect(midright=(mute.x-8,cy)))
    app.volumeControlRects[kind]={'track':track,'mute':mute}


def render(app):
    screen=app.screen;rect,sliders,controls=layout(app);font=app.smallFont;mouse=pygame.mouse.get_pos()
    shade=pygame.Surface(screen.get_size(),pygame.SRCALPHA);shade.fill((3,8,16,105));screen.blit(shade,(0,0))
    chrome.panel(screen,rect,alpha=246)
    screen.blit(app.sectionFont.render('Settings',True,chrome.TEXT),(rect.x+22,rect.y+12))
    close=close_rect(app,rect);chrome.button(screen,close,'Close',font,close.collidepoint(mouse),quiet=True)
    heading=font.get_linesize()+4
    for label,y in (('Audio',sliders[0][1].y-heading),('Preferences',controls[0][2].y-heading)):
        text=font.render(label,True,chrome.ACCENT);screen.blit(text,(rect.x+22,y+5))
        pygame.draw.line(screen,(46,61,81),(rect.x+22+text.get_width()+12,y+heading//2),(rect.right-22,y+heading//2))
    app.volumeControlRects.clear()
    for kind,r in sliders:slider(app,kind,getattr(app,kind+'Volume'),r.x,r.y,r.width)
    from ui.opening_scene import skip_on_launch
    for label,attr,r in controls:
        if attr=='vsync_unavailable':
            chrome.wrapped(screen,label,font,r,chrome.MUTED);continue
        if attr=='opening':
            chrome.button(screen,r,label,font,r.collidepoint(mouse),quiet=True);continue
        value=not skip_on_launch() if attr=='skip' else getattr(app,attr,False)
        if r.collidepoint(mouse):chrome.rounded(screen,(28,41,60),r,5)
        text=font.render(label,True,chrome.TEXT);screen.blit(text,(r.x+2,r.centery-text.get_height()//2))
        track=pygame.Rect(r.right-38,r.centery-9,36,18)
        chrome.rounded(screen,(72,107,138) if value else (43,56,75),track,9)
        pygame.draw.circle(screen,chrome.TEXT if value else chrome.MUTED,(track.right-9 if value else track.x+9,track.centery),6)
    targets=focus_targets(app)
    focus=getattr(app,'_settingsFocus',None)
    if focus is not None and targets:
        r=targets[focus%len(targets)][1];pygame.draw.rect(screen,chrome.FOCUS,r.inflate(4,4),1,border_radius=5)


def focus_targets(app):
    rect,_,controls=layout(app)
    targets=[]
    for kind,c in app.volumeControlRects.items():
        targets.extend(((kind,c['track'].inflate(0,12)),(kind+'_mute',c['mute'])))
    targets.extend((attr,r) for _,attr,r in controls if attr!='vsync_unavailable')
    targets.append(('close',close_rect(app,rect)))
    return targets


def key(app,event):
    targets=focus_targets(app)
    if event.key==pygame.K_TAB:
        direction=-1 if getattr(event,'mod',0)&pygame.KMOD_SHIFT else 1
        current=getattr(app,'_settingsFocus',None)
        app._settingsFocus=((current if current is not None else -direction)+direction)%len(targets)
        return
    focus=getattr(app,'_settingsFocus',None)
    if focus is None:return
    name,r=targets[focus%len(targets)]
    if name in ('music','ambient','effects') and event.key in (pygame.K_LEFT,pygame.K_RIGHT,pygame.K_HOME,pygame.K_END):
        value=0 if event.key==pygame.K_HOME else 1 if event.key==pygame.K_END else getattr(app,name+'Volume')+(.05 if event.key==pygame.K_RIGHT else -.05)
        app._setVolume(name,value)
    elif event.key in (pygame.K_RETURN,pygame.K_SPACE):app._handleSettingsClick(*r.center)
