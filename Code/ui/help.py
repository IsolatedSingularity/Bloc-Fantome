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


def render(app):
    if not app.showShortcutsPanel:return
    screen=app.screen
    overlay=pygame.Surface(screen.get_size(),pygame.SRCALPHA);overlay.fill((0,0,0,180));screen.blit(overlay,(0,0))
    box=pygame.Rect(0,0,min(920,screen.get_width()-32),min(700,screen.get_height()-32));box.center=screen.get_rect().center
    panel(screen,box,app.assetManager)
    from ui.chrome import heading
    heading(screen,(box.x+14,box.y+12,box.width-76,34),'Help / Shortcuts',app.assetManager,app.sectionFont)
    app.helpCloseRect=pygame.Rect(box.right-48,box.y+14,30,30)
    app.assetManager.drawButton(screen,app.helpCloseRect,'X',app.smallFont,app.helpCloseRect.collidepoint(pygame.mouse.get_pos()))
    font=load_ui_font(14)
    rows=(len(SHORTCUTS)+1)//2
    stride=(box.height-100)//rows
    cw=(box.width-40)//2
    for i,(key,action) in enumerate(SHORTCUTS):
        x=box.x+20+(i//rows)*cw;y=box.y+65+(i%rows)*stride
        screen.blit(font.render(key,True,(177,205,142)),(x,y))
        screen.blit(font.render(action,True,TEXT),(x+166,y))
    text=font.render('Esc closes this panel. Your build stays active underneath.',True,MUTED)
    screen.blit(text,text.get_rect(midbottom=(box.centerx,box.bottom-15)))
