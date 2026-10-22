"""Native enlarged cube geometry without replacing or smoothing source texels."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import numpy as np
import pygame
from engine import native_cube
from engine.lighting import shade_sprite


def test_projection_keeps_source_palette_inside_each_face():
    texture=pygame.Surface((16,16),pygame.SRCALPHA)
    for x in range(16):
        for y in range(16):texture.set_at((x,y),(32+x*12,32+y*12,128,255))
    sprite=pygame.Surface((64,70),pygame.SRCALPHA)
    native_cube.register(sprite,(texture,texture,texture))
    image=native_cube.enlarged(sprite,(128,140),32/70)
    assert image.get_size()==(128,140)
    # Native face centers, away from antialiased silhouette/definition lines.
    for pos,shade in (((64,30),1.),((30,80),.7),((98,80),.85)):
        color=image.get_at(pos)
        palette={tuple(int(c*shade) for c in texture.get_at((x,y))[:3]) for x in range(16) for y in range(16)}
        assert color[:3] in palette and color.a==255
    alpha=pygame.surfarray.array_alpha(image)
    assert np.any((alpha>0)&(alpha<255))
    assert image.get_at((0,0)).a==0


def test_unregistered_and_transparent_models_keep_original_path():
    sprite=pygame.Surface((64,70),pygame.SRCALPHA)
    assert native_cube.enlarged(sprite,(128,140),32/70) is None
    transparent=pygame.Surface((16,16),pygame.SRCALPHA)
    native_cube.register(sprite,(transparent,transparent,transparent))
    assert native_cube.enlarged(sprite,(128,140),32/70) is None


def test_lighting_is_applied_after_native_projection_with_same_alpha():
    texture=pygame.Surface((16,16));texture.fill((180,140,100))
    sprite=pygame.Surface((64,70),pygame.SRCALPHA)
    native_cube.register(sprite,(texture,texture,texture))
    lit=shade_sprite(sprite,.6,9,(255,210,200))
    actual=native_cube.enlarged(lit,(96,105),32/70)
    expected=shade_sprite(native_cube.enlarged(sprite,(96,105),32/70),.6,9,(255,210,200))
    assert pygame.image.tobytes(actual,'RGBA')==pygame.image.tobytes(expected,'RGBA')
