"""Render the source-captured warped forest once, at native 4K resolution."""
import os
from pathlib import Path
import sys
from types import SimpleNamespace

os.environ.setdefault('SDL_VIDEODRIVER','dummy')
CODE = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(CODE))
import pygame
from ui.source_map import SourceMap


def render():
    pygame.display.init()
    pygame.display.set_mode((1,1))
    screen = pygame.Surface((3840,2160))
    screen.fill((9,23,24))
    renderer = SimpleNamespace(zoomLevel=.8, offsetX=1920-(110-95)*32*.8,
                               offsetY=1080-((110+95)*16-80*38*.6)*.8)
    SourceMap('nether','warped').render(screen,renderer)
    shade = pygame.Surface(screen.get_size(),pygame.SRCALPHA)
    shade.fill((2,12,18,70))
    screen.blit(shade,(0,0))
    target = CODE.parent/'Assets/Icons/Splash_Background_Warped_Forest.png'
    pygame.image.save(screen,target)
    pygame.display.quit()
    return target


if __name__=='__main__':
    print(render())
