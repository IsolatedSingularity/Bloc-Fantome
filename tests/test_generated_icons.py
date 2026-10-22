"""Generated icon fidelity and active-only animation regression checks."""
import pygame
import numpy as np
from ui.generated_icons import NAMES,ANIMATED,artwork,draw


def test_generated_masks_are_distinct_white_and_transparent():
    masks=artwork();assert set(masks)==set(NAMES)
    hashes=set()
    for mask in masks.values():
        alpha=pygame.surfarray.array_alpha(mask);rgb=pygame.surfarray.array3d(mask)
        assert alpha.max()==255 and (alpha==0).any()
        assert np.all(rgb[alpha>0]==255)
        assert min(mask.get_size())>150
        hashes.add(pygame.image.tostring(mask,'RGBA'))
    assert len(hashes)==len(NAMES)


def test_all_world_icons_animate_but_static_render_is_repeatable():
    for name in ANIMATED:
        def frame(phase):
            surface=pygame.Surface((80,80),pygame.SRCALPHA)
            draw(surface,name,(4,4,72,72),phase)
            return pygame.image.tostring(surface,'RGBA')
        assert frame(0)==frame(0)
        assert frame(.3)!=frame(1.1),name


def test_art_stays_inside_control_bounds():
    for name in NAMES:
        for phase in (0,.3,1.1,2.7):
            s=pygame.Surface((100,100),pygame.SRCALPHA)
            draw(s,name,(16,16,68,68),phase)
            assert pygame.Rect(16,16,68,68).contains(s.get_bounding_rect()),name


def test_sky_action_pair_has_consistent_optical_size():
    masks=artwork()
    left,right=(masks[name] for name in ('sky_previous','sky_next'))
    assert abs(left.get_height()/left.get_width()-right.get_height()/right.get_width())<.15
