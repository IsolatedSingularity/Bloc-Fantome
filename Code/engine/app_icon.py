"""Independent charged-respawn-anchor branding and splash background paths."""

from __future__ import annotations

from typing import Optional, Sequence

import pygame

from engine.model_renderer import BlockModelRenderer


FALLBACK_DEEPSLATE = (48, 48, 54, 255)
SPLASH_VERTICAL_RATIO = 0.625
RUNTIME_ICON_VERTICAL_RATIO = 0.625
EXPLORER_ICON_VERTICAL_RATIO = 0.625


def _rgba_texture(texture: Optional[pygame.Surface]) -> pygame.Surface:
    if texture is None:
        result = pygame.Surface((16, 16), pygame.SRCALPHA)
        result.fill(FALLBACK_DEEPSLATE)
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
    """Aspect-fit the supplied charged respawn anchor without distortion."""
    return _fit_artwork(texture, tile_width, padding_ratio=0.0)


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
    result.fill((16, 17, 21))
    rows = height // row_step + 4
    columns = width // cube_width + 4
    for row in range(-2, rows):
        offset_x = (row & 1) * (cube_width // 2)
        for column in range(-2, columns):
            result.blit(cube, (column * cube_width + offset_x, row * row_step))
    darkness = pygame.Surface(result.get_size(), pygame.SRCALPHA)
    darkness.fill((2, 3, 6, 206))
    result.blit(darkness, (0, 0))
    return result


def render_ancient_city_background_surface(
    textures: Sequence[Optional[pygame.Surface]],
    size=(1200, 800),
    cube_width: int = 64,
) -> pygame.Surface:
    """Render a deterministic Ancient City mosaic with sculk-lit accents."""
    width, height = size
    cube_width = max(32, int(cube_width))
    usable = [texture for texture in textures if texture is not None]
    if not usable:
        return render_splash_background_surface(None, size, cube_width)
    cubes = [_render_cube(texture, cube_width, 0.5) for texture in usable]
    row_step = cube_width * 3 // 4
    result = pygame.Surface((width, height))
    result.fill((4, 7, 10))
    rows = height // row_step + 4
    columns = width // cube_width + 4
    # The first textures are the quieter deepslate base. Later sculk and
    # reinforced variants occur as deliberate, irregular points of interest.
    pattern = (0, 1, 0, 2, 0, 3, 1, 0, 4, 0, 2, 5, 0, 1, 3, 0)
    for row in range(-2, rows):
        offset_x = (row & 1) * (cube_width // 2)
        for column in range(-2, columns):
            selector = pattern[(column * 5 + row * 7) % len(pattern)] % len(cubes)
            result.blit(cubes[selector], (column * cube_width + offset_x, row * row_step))
    darkness = pygame.Surface(result.get_size(), pygame.SRCALPHA)
    darkness.fill((1, 3, 7, 158))
    result.blit(darkness, (0, 0))
    # A restrained central cyan-violet haze ties the sculk field to the title
    # without flattening the individual block textures.
    glow = pygame.Surface(result.get_size(), pygame.SRCALPHA)
    pygame.draw.ellipse(
        glow,
        (30, 92, 105, 34),
        (width // 8, height // 6, width * 3 // 4, height * 2 // 3),
    )
    pygame.draw.ellipse(
        glow,
        (88, 35, 118, 24),
        (width // 5, height // 4, width * 3 // 5, height // 2),
    )
    result.blit(glow, (0, 0))
    return result


def render_runtime_icon_surface(
    texture: Optional[pygame.Surface], size: int = 64
) -> pygame.Surface:
    """Aspect-fit the supplied artwork with shell-safe transparent padding."""
    return _fit_artwork(texture, size, padding_ratio=0.08)


def render_explorer_icon_surface(
    texture: Optional[pygame.Surface], size: int
) -> pygame.Surface:
    """Render one embedded ICO entry with the proven runtime proportions.

    This remains a separate Explorer-only route so changing the packaged ICO
    cannot alter the Pygame window/taskbar surface or the splash artwork.
    """
    return _fit_artwork(texture, size, padding_ratio=0.08)


def _fit_artwork(
    artwork: Optional[pygame.Surface], size: int, *, padding_ratio: float
) -> pygame.Surface:
    size = max(16, int(size))
    result = pygame.Surface((size, size), pygame.SRCALPHA)
    if artwork is None:
        pygame.draw.rect(result, FALLBACK_DEEPSLATE, result.get_rect(), border_radius=max(2, size // 8))
        return result
    source = _rgba_texture(artwork)
    bounds = source.get_bounding_rect(min_alpha=1)
    if bounds.width and bounds.height:
        source = source.subsurface(bounds)
    padding = max(0, round(size * padding_ratio))
    available = max(1, size - padding * 2)
    scale = min(available / source.get_width(), available / source.get_height())
    dimensions = (
        max(1, round(source.get_width() * scale)),
        max(1, round(source.get_height() * scale)),
    )
    fitted = pygame.transform.smoothscale(source, dimensions)
    result.blit(fitted, fitted.get_rect(center=result.get_rect().center))
    return result


# Compatibility exports for existing visual checks and third-party imports.
render_logo_cube_surface = render_splash_logo_surface
render_app_icon_surface = render_runtime_icon_surface
