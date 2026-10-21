"""Measured, two-column shortcut reference using the shared panel chrome."""
import pygame
from ui.chrome import panel, TEXT, MUTED
from ui.fonts import load_ui_font

SHORTCUTS = (
    ('Left click', 'Place block'), ('Right click', 'Remove / interact'),
    ('Middle drag', 'Pan view'), ('Wheel', 'Zoom canvas / scroll panel'),
    ('Q / E', 'Rotate view'), ('Home', 'Fit world'),
    ('1–9 / Shift+1–9', 'Select hotbar slot'), ('I', 'Build / interact mode'),
    ('R / Shift+R', 'Rotate preview / placed block'), ('F', 'Flip slab / fill tool'),
    ('B', 'Brush size'), ('G / X', 'Grid / X-ray'),
    ('M', 'Measure'), ('Shift+M / Ctrl+M', 'Mirror Y / X'),
    ('Ctrl+T', 'Radial symmetry'), ('Ctrl+C / Ctrl+V', 'Copy / paste'),
    ('[ / ]', 'Rotate clipboard'), ('Ctrl+B', 'Selection box'),
    ('Ctrl+Shift+B', 'Blueprint'), ('Ctrl+A', 'Fill selection'),
    ('Ctrl+Shift+F', 'Flood fill'), ('Ctrl+Shift+W', 'Magic wand'),
    ('Ctrl+H', 'Hollow selection / history'), ('P', 'Stamp copied blocks'),
    ('Ctrl+R', 'Replace block type'), ('Alt+click', 'Pick block'),
    ('Ctrl+F / Ctrl+D', 'Search / favorite block'), ('Tab', 'Minimap'),
    ('/  .  ,', 'Layer view / up / down'), ('L / K', 'Liquid flow / clear liquids'),
    ('Ctrl+S / Ctrl+Shift+S', 'Save / Save As'), ('Ctrl+O', 'Open Library'),
    ('Ctrl+Z / Ctrl+Y', 'Undo / redo'), ('Delete / C', 'Delete selection / clear world'),
    ('F11 / Alt+Enter', 'Fullscreen'), ('Ctrl+,', 'Settings'),
)


def handle_event(event,app):
    if not app.showShortcutsPanel:return False
    if event.type==pygame.KEYDOWN:
        if event.key in (pygame.K_ESCAPE,pygame.K_SLASH):app.showShortcutsPanel=False
        elif event.key in (pygame.K_RIGHT,pygame.K_PAGEDOWN):app.helpPage=min(getattr(app,'helpPages',1)-1,getattr(app,'helpPage',0)+1)
        elif event.key in (pygame.K_LEFT,pygame.K_PAGEUP):app.helpPage=max(0,getattr(app,'helpPage',0)-1)
    elif event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
        if getattr(app,'helpCloseRect',pygame.Rect(0,0,0,0)).collidepoint(event.pos):app.showShortcutsPanel=False
        for direction,rect in getattr(app,'helpPageRects',[]):
            if rect.collidepoint(event.pos):app.helpPage=max(0,min(app.helpPages-1,getattr(app,'helpPage',0)+direction))
    return event.type in (pygame.KEYDOWN,pygame.KEYUP,pygame.MOUSEBUTTONDOWN,pygame.MOUSEBUTTONUP,pygame.MOUSEMOTION,pygame.MOUSEWHEEL)


def render(app):
    if not app.showShortcutsPanel:return
    from ui.chrome import button,wrapped,ACCENT
    screen=app.screen;mouse=pygame.mouse.get_pos()
    overlay=pygame.Surface(screen.get_size(),pygame.SRCALPHA);overlay.fill((0,0,0,150));screen.blit(overlay,(0,0))
    box=pygame.Rect(0,0,min(1060,screen.get_width()-48),min(760,screen.get_height()-48));box.center=screen.get_rect().center
    panel(screen,box)
    screen.blit(app.sectionFont.render('Controls',True,TEXT),(box.x+24,box.y+18))
    app.helpCloseRect=pygame.Rect(box.right-112,box.y+18,88,36)
    button(screen,app.helpCloseRect,'Close',app.smallFont,app.helpCloseRect.collidepoint(mouse),quiet=True)
    font=load_ui_font(14);line=font.get_linesize();stride=line*2+14
    rows=max(1,(box.height-136)//stride);per_page=rows*2
    entries=SHORTCUTS+(('F1 / Ctrl+Tab','Reveal / focus controls'),)
    app.helpPages=(len(entries)+per_page-1)//per_page
    app.helpPage=min(getattr(app,'helpPage',0),app.helpPages-1)
    cw=(box.width-64)//2
    for i,(key,action) in enumerate(entries[app.helpPage*per_page:(app.helpPage+1)*per_page]):
        x=box.x+24+(i//rows)*(cw+16);y=box.y+72+(i%rows)*stride
        wrapped(screen,key,font,(x,y,cw,line+2),ACCENT)
        wrapped(screen,action,font,(x,y+line+2,cw,line+2),TEXT)
    app.helpPageRects=[]
    for direction,label,x in ((-1,'Previous',box.x+24),(1,'Next',box.right-124)):
        rect=pygame.Rect(x,box.bottom-49,100,32);app.helpPageRects.append((direction,rect))
        button(screen,rect,label,font,rect.collidepoint(mouse),enabled=0<=app.helpPage+direction<app.helpPages)
    text=font.render(f'{app.helpPage+1} / {app.helpPages}   ·   Esc closes',True,MUTED)
    screen.blit(text,text.get_rect(center=(box.centerx,box.bottom-33)))
