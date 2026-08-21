"""Fast sprite shading helpers for the optional block-light renderer."""

from typing import Tuple

import pygame


def shade_sprite(
    sprite: pygame.Surface,
    brightness: float,
    light_level: int,
    light_color: Tuple[int, int, int],
) -> pygame.Surface:
    """Apply brightness and a restrained color cast using SDL blend paths.

    The former implementation performed Python `get_at`/`set_at` calls for
    every pixel after each lighting invalidation. Pygame's blend operations do
    the same bulk work in native code while preserving transparent pixels.
    """

    brightness = max(0.0, min(1.0, float(brightness)))
    result = sprite.copy()
    multiplier = max(0, min(255, round(brightness * 255)))
    result.fill((multiplier, multiplier, multiplier, 255), special_flags=pygame.BLEND_RGBA_MULT)

    if light_level > 0:
        strength = min(1.0, light_level / 15.0) * 0.4
        red, green, blue = light_color
        additions = (
            max(0, min(48, round((red - 200) / 100.0 * strength * 60))),
            max(0, min(32, round((green - 200) / 100.0 * strength * 40))),
            max(0, min(48, round((blue - 200) / 100.0 * strength * 60))),
            0,
        )
        if any(additions[:3]):
            result.fill(additions, special_flags=pygame.BLEND_RGBA_ADD)
    return result
