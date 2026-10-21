"""Small original line silhouettes, drawn at their final display resolution."""
import pygame


def draw(surface, action, rect, color):
    x,y=rect.center; r=min(rect.width,rect.height)//3
    line=lambda points:pygame.draw.lines(surface,color,False,points,2)
    if action in ('rain','snow','clouds','horror_rain'):
        pygame.draw.arc(surface,color,(x-r,y-r,r*2,r+4),0,3.14,2)
        line([(x-r,y),(x+r,y)])
        for dx in (() if action=='clouds' else (-r,0,r)):
            line([(x+dx,y+3),(x+dx-2,y+7)])
            if action=='snow':line([(x+dx-3,y+5),(x+dx+2,y+5)])
    elif action in ('sun','lighting','sky'):
        pygame.draw.circle(surface,color,(x,y),max(2,r//2),2)
        for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
            line([(x+dx*(r-1),y+dy*(r-1)),(x+dx*(r+3),y+dy*(r+3))])
    elif action in ('grow','shrink','noise','terrain','terrain_view'):
        pygame.draw.polygon(surface,(88,130,102),[(x-r,y),(x,y-r//2),(x+r,y),(x,y+r//2)])
        pygame.draw.polygon(surface,(104,88,69),[(x-r,y),(x,y+r//2),(x+r,y),(x+r,y+5),(x,y+r//2+5),(x-r,y+5)])
        if action=='noise':
            line([(x-r,y),(x-3,y-5),(x+1,y-2),(x+5,y-7),(x+r,y)])
        else:
            line([(x-4,y-8),(x+4,y-8)])
            if action=='grow':line([(x,y-12),(x,y-4)])
    elif action=='flow':
        for dy in (-4,3):line([(x-r,y+dy),(x-3,y+dy-3),(x+3,y+dy+3),(x+r,y+dy)])
    elif action=='brush':
        line([(x-r,y+r),(x+2,y-2)])
        pygame.draw.polygon(surface,color,[(x,y-4),(x+4,y-8),(x+8,y-4),(x+4,y)],1)
    elif action in ('fill','flood','replace'):
        pygame.draw.polygon(surface,color,[(x-r,y-r),(x+r,y-r),(x+r-3,y+r),(x-r+3,y+r)],1)
        line([(x-r+2,y),(x+r-2,y)])
        if action=='replace':line([(x-r,y+r+3),(x+r,y+r+3),(x+r-3,y+r)])
    elif action in ('clip_left','clip_right','turn','turn_placed','half'):
        pygame.draw.arc(surface,color,(x-r,y-r,r*2,r*2),.3,5,2)
        dx=-r if action=='clip_left' else r
        pygame.draw.polygon(surface,color,[(x+dx,y-r),(x+dx-4,y-r+4),(x+dx+3,y-r+5)])
    elif action in ('copy','paste','stamp','blueprint'):
        pygame.draw.rect(surface,color,(x-r,y-r,r+4,r+5),1)
        pygame.draw.rect(surface,color,(x-2,y-2,r+3,r+4),2)
    elif action in ('selection','fill_selection','hollow','delete','wand'):
        pygame.draw.rect(surface,color,(x-r,y-r,r*2,r*2),1)
        if action in ('fill_selection','wand'):line([(x-r,y+r),(x+r,y-r)])
        if action=='delete':line([(x-r,y-r),(x+r,y+r)])
    elif action in ('mirror_x','mirror_y','radial','layers','layer_up','layer_down'):
        line([(x-r,y-r),(x-r,y+r)]);line([(x+r,y-r),(x+r,y+r)])
        line([(x,y-r-2),(x,y+r+2)])
    elif action in ('measure','grid','center','xray','minimap'):
        pygame.draw.rect(surface,color,(x-r,y-r,r*2,r*2),1)
        line([(x-r,y),(x+r,y)]);line([(x,y-r),(x,y+r)])
    else:
        line([(x-r,y+r),(x+r,y-r)])
        pygame.draw.polygon(surface,color,[(x+r-5,y-r),(x+r,y-r-4),(x+r+4,y-r),(x+r,y-r+5)],1)
