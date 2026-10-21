"""Native history presentation using the original undo manager and jump routes."""
import pygame
from ui.chrome import panel,button,wrapped,TEXT,MUTED,ACCENT


def render(app):
    if not app.historyPanelOpen:return
    screen=app.screen;font=app.smallFont;mouse=pygame.mouse.get_pos()
    box=pygame.Rect(0,0,min(760,screen.get_width()-48),min(600,screen.get_height()-48))
    box.center=screen.get_rect().center;app.historyPanelRect=box
    shade=pygame.Surface(screen.get_size(),pygame.SRCALPHA);shade.fill((0,0,0,150));screen.blit(shade,(0,0));panel(screen,box)
    screen.blit(app.sectionFont.render('History',True,TEXT),(box.x+24,box.y+18))
    app.historyCloseRect=pygame.Rect(box.right-112,box.y+18,88,36)
    button(screen,app.historyCloseRect,'Close',font,app.historyCloseRect.collidepoint(mouse),quiet=True)
    row_h=max(42,font.get_linesize()+18);width=(box.width-64)//2
    footer_height=2*(font.get_linesize()+3)
    available=max(1,(box.height-112-footer_height)//row_h);app.historyHitRects=[]
    entries_by_column=(('Undo',False,app.undoManager.get_undo_history(max_items=50)),('Redo',True,app.undoManager.get_redo_history(max_items=50)))
    app.historyScrollRect=pygame.Rect(box.x+24,box.y+76+font.get_linesize()+10,box.width-48,available*row_h)
    app.historyMaxScroll=max(0,max(len(v) for _,_,v in entries_by_column)*row_h-app.historyScrollRect.height)
    from ui.scroll import update_field
    offset=update_field(app,'historyPanelScroll',app.historyMaxScroll,app.workshop.visibility.reduced_motion)
    for col,(label,redo,entries) in enumerate(entries_by_column):
        x=box.x+24+col*(width+16);y=box.y+76
        screen.blit(font.render(f'{label} · {len(entries)}',True,ACCENT),(x,y))
        old=screen.get_clip();screen.set_clip(app.historyScrollRect)
        for i,(index,description) in enumerate(entries):
            rect=pygame.Rect(x,app.historyScrollRect.y+i*row_h-offset,width,row_h-6)
            if not rect.colliderect(app.historyScrollRect):continue
            button(screen,rect,f'{index+1}. {description}',font,rect.collidepoint(mouse),quiet=True)
            app.historyHitRects.append((rect.clip(app.historyScrollRect),index,redo))
        screen.set_clip(old)
    wrapped(screen,'Choose an action to jump through history. Scroll for earlier actions.',font,(box.x+24,box.bottom-footer_height-12,box.width-48,footer_height),MUTED)
