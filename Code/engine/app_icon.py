"""Independent End Stone render paths for splash, taskbar, and Explorer."""

from __future__ import annotations

from typing import Optional

import pygame

from engine.model_renderer import BlockModelRenderer


FALLBACK_END_STONE = (219, 222, 158, 255)
SPLASH_VERTICAL_RATIO = 0.625
RUNTIME_ICON_VERTICAL_RATIO = 0.625
EXPLORER_ICON_VERTICAL_RATIO = 0.625


def _rgba_texture(texture: Optional[pygame.Surface]) -> pygame.Surface:
    if texture is None:
        result = pygame.Surface((16, 16), pygame.SRCALPHA)
        result.fill(FALLBACK_END_STONE)
        return result
    if texture.get_flags() & pygame.SRCALPHA:
        return texture
    result = pygame.Surface(texture.get_size(), pygame.SRCALPHA)
    result.blit(texture, (0, 0))
    return result


def _render_cube(
    texture: Optional[pygame.Surface], tile_width: int, vertical_ratio: float
) -> pygame.Surface:
    tile_width = max(16, int(tile_width))
    texture = _rgba_texture(texture)
    renderer = BlockModelRenderer(
        tile_width,
        tile_width // 2,
        round(tile_width * vertical_ratio),
    )
    return renderer.render_boxes(
        ((0, 0, 0, 16, 16, 16),), texture, texture, texture
    )


def render_splash_logo_surface(
    texture: Optional[pygame.Surface], tile_width: int
) -> pygame.Surface:
    """Render only the large splash logo; Windows icon tuning cannot affect it."""
    return _render_cube(texture, tile_width, SPLASH_VERTICAL_RATIO)


def render_splash_background_surface(
    texture: Optional[pygame.Surface], size=(1200, 800), cube_width: int = 64
) -> pygame.Surface:
    """Render a gap-free dim isometric cube tessellation for the splash."""
    width, height = size
    cube_width = max(32, int(cube_width))
    # Background cubes use the standard 2:1 tile and half-width vertical axis.
    # This exact 3/4-row lattice interlocks the hexagonal silhouettes without
    # the transparent bands created by spacing full-height splash-logo cubes.
    cube = _render_cube(texture, cube_width, 0.5)
    row_step = cube_width * 3 // 4
    result = pygame.Surface((width, height))
    result.fill((31, 33, 25))
    rows = height // row_step + 4
    columns = width // cube_width + 4
    for row in range(-2, rows):
        offset_x = (row & 1) * (cube_width // 2)
        for column in range(-2, columns):
            result.blit(cube, (column * cube_width + offset_x, row * row_step))
    darkness = pygame.Surface(result.get_size(), pygame.SRCALPHA)
    darkness.fill((4, 5, 7, 172))
    result.blit(darkness, (0, 0))
    return result


def render_runtime_icon_surface(
    texture: Optional[pygame.Surface], size: int = 64
) -> pygame.Surface:
    """Render the dedicated Pygame window/taskbar icon with small-size padding."""
    size = max(16, int(size))
    source_width = max(192, size * 4)
    cube = _render_cube(texture, source_width, RUNTIME_ICON_VERTICAL_RATIO)
    cube = cube.subsurface(cube.get_bounding_rect(min_alpha=1))
    padding = max(2, round(size * 0.09))
    available = size - padding * 2
    fit = min(available / cube.get_width(), available / cube.get_height())
    fitted = pygame.transform.scale(
        cube,
        (max(1, round(cube.get_width() * fit)), max(1, round(cube.get_height() * fit))),
    )
    icon = pygame.Surface((size, size), pygame.SRCALPHA)
    icon.blit(fitted, fitted.get_rect(center=icon.get_rect().center))
    return icon


def render_explorer_icon_surface(
    texture: Optional[pygame.Surface], size: int
) -> pygame.Surface:
    """Render one unsquashed embedded ICO entry independently of the taskbar."""
    size = max(16, int(size))
    source_width = max(288, size * 6)
    cube = _render_cube(texture, source_width, EXPLORER_ICON_VERTICAL_RATIO)
    cube = cube.subsurface(cube.get_bounding_rect(min_alpha=1))
    padding = max(1, round(size * 0.04))
    available = size - padding * 2
    fit = min(available / cube.get_width(), available / cube.get_height())
    fitted = pygame.transform.scale(
        cube,
        (max(1, round(cube.get_width() * fit)), max(1, round(cube.get_height() * fit))),
    )
    icon = pygame.Surface((size, size), pygame.SRCALPHA)
    icon.blit(fitted, fitted.get_rect(center=icon.get_rect().center))
    return icon


# Compatibility exports for existing visual checks and third-party imports.
render_logo_cube_surface = render_splash_logo_surface
render_app_icon_surface = render_runtime_icon_surface
