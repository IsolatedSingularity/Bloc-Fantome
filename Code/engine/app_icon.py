"""Small-format Windows icon rendering, independent from the splash screen."""

from __future__ import annotations

from typing import Optional

import pygame

from engine.model_renderer import BlockModelRenderer


FALLBACK_END_STONE = (219, 222, 158, 255)


def render_app_icon_surface(
    texture: Optional[pygame.Surface], size: int = 64
) -> pygame.Surface:
    """Render a padded, textured cube that remains legible at taskbar sizes."""
    size = max(16, int(size))
    # Rasterize small icons above their destination resolution. This keeps the
    # isometric silhouette and the End Stone mottling visible after Windows
    # scales the taskbar resource.
    scale = 8 if size <= 24 else (4 if size <= 48 else 2)
    working_size = size * scale
    padding_ratio = 0.14 if size <= 24 else 0.09
    padding = max(2 * scale, round(working_size * padding_ratio))
    inner = working_size - padding * 2
    inner -= inner % 2

    if texture is None:
        texture = pygame.Surface((16, 16), pygame.SRCALPHA)
        texture.fill(FALLBACK_END_STONE)
    elif texture.get_flags() & pygame.SRCALPHA == 0:
        # This helper intentionally also runs before display creation and in
        # the headless icon generator, where convert_alpha is unavailable.
        source = texture
        texture = pygame.Surface(source.get_size(), pygame.SRCALPHA)
        texture.blit(source, (0, 0))

    renderer = BlockModelRenderer(inner, inner // 2, inner // 2)
    cube = renderer.render_boxes(((0, 0, 0, 16, 16, 16),), texture, texture, texture)
    working = pygame.Surface((working_size, working_size), pygame.SRCALPHA)
    working.blit(cube, cube.get_rect(center=working.get_rect().center))
    icon = pygame.transform.smoothscale(working, (size, size))

    # A one-pixel alpha-aware contour prevents the 16 and 24 pixel resources
    # from reading as a flat square against a dark Windows taskbar.
    outline = pygame.Surface((size, size), pygame.SRCALPHA)
    for x in range(size):
        for y in range(size):
            if icon.get_at((x, y)).a != 0:
                continue
            if any(
                0 <= x + dx < size
                and 0 <= y + dy < size
                and icon.get_at((x + dx, y + dy)).a > 32
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1))
            ):
                outline.set_at((x, y), (55, 57, 41, 210))
    outline.blit(icon, (0, 0))
    return outline
