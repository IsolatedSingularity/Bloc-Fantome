"""Cached spherical sky panoramas derived from licensed OptiFine cube atlases."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
import os
from typing import Optional

import pygame


@dataclass(frozen=True)
class SkyboxVariant:
    name: str
    relative_path: str

    @property
    def panorama_path(self) -> str:
        return os.path.join("panoramas", self.relative_path)


SKYBOX_VARIANTS = {
    "overworld": (
        SkyboxVariant("sky_day01_07", os.path.join("world0", "day.png")),
        SkyboxVariant("Twilight", os.path.join("world0", "dusk.png")),
        SkyboxVariant("Night", os.path.join("world0", "night.png")),
    ),
    "nether": (
        SkyboxVariant("Xen Sky 2", os.path.join("world1", "2.png")),
        SkyboxVariant("Ashen Dawn", os.path.join("world0", "dawn.png")),
    ),
    "end": (
        SkyboxVariant("Xen Sky 6", os.path.join("world1", "3.png")),
        SkyboxVariant("Void Aurora", os.path.join("world1", "1.png")),
    ),
}


class SkyboxRenderer:
    """Render a slow 60 FPS panorama with bounded caches and manual presets."""

    ROTATION_PIXELS_PER_SECOND = 7.0
    CROSSFADE_MS = 900
    CACHE_LIMIT = 3
    SIDE_FACES = ((2, 0), (2, 1), (1, 1), (0, 1))

    def __init__(self, root: str, viewport_size: tuple[int, int]):
        self.root = root
        self.viewport_size = tuple(map(int, viewport_size))
        self.rotation = 0.0
        self.current_dimension: Optional[str] = None
        self.current_index = 0
        self.previous_index: Optional[int] = None
        self.crossfade_elapsed = self.CROSSFADE_MS
        self.selected_indices = {dimension: 0 for dimension in SKYBOX_VARIANTS}
        self._panoramas: OrderedDict[tuple[str, int], pygame.Surface] = OrderedDict()
        self._atmospheres: dict[str, pygame.Surface] = {}

    def variants(self, dimension: str) -> tuple[SkyboxVariant, ...]:
        return SKYBOX_VARIANTS.get(dimension, ())

    def resize(self, viewport_size: tuple[int, int]) -> None:
        """Rebuild only viewport-sized derivatives after a window resize."""
        viewport_size = tuple(map(int, viewport_size))
        if viewport_size == self.viewport_size:
            return
        self.viewport_size = viewport_size
        self._panoramas.clear()
        self._atmospheres.clear()

    def _source_path(self, variant: SkyboxVariant) -> str:
        projected = os.path.join(self.root, variant.panorama_path)
        return projected if os.path.isfile(projected) else os.path.join(
            self.root, variant.relative_path
        )

    def available(self, dimension: str) -> bool:
        return any(os.path.isfile(self._source_path(variant)) for variant in self.variants(dimension))

    def active_name(self, dimension: str) -> str:
        variants = self.variants(dimension)
        if not variants:
            return "Unavailable"
        index = self.selected_indices.get(dimension, 0) % len(variants)
        return variants[index].name

    def set_selection(self, dimension: str, index: int, *, crossfade: bool = True) -> None:
        variants = self.variants(dimension)
        if not variants:
            return
        desired = int(index) % len(variants)
        old = self.selected_indices.get(dimension, 0) % len(variants)
        self.selected_indices[dimension] = desired
        if dimension == self.current_dimension and desired != old:
            self.previous_index = old if crossfade else None
            self.current_index = desired
            self.crossfade_elapsed = 0 if crossfade else self.CROSSFADE_MS

    def cycle(self, dimension: str, delta: int) -> str:
        variants = self.variants(dimension)
        if not variants:
            return "Unavailable"
        self.set_selection(
            dimension, self.selected_indices.get(dimension, 0) + int(delta)
        )
        return self.active_name(dimension)

    def update(
        self, dt_ms: int, dimension: str, *,
        celestial_enabled: bool = False, celestial_angle: float = 0.0,
    ) -> None:
        del celestial_enabled, celestial_angle
        dt_ms = max(0, int(dt_ms))
        self.rotation += self.ROTATION_PIXELS_PER_SECOND * dt_ms / 1000.0
        if dimension != self.current_dimension:
            self.current_dimension = dimension
            self.current_index = self.selected_indices.get(dimension, 0)
            self.previous_index = None
            self.crossfade_elapsed = self.CROSSFADE_MS
        else:
            self.current_index = self.selected_indices.get(dimension, 0)
        self.crossfade_elapsed = min(self.CROSSFADE_MS, self.crossfade_elapsed + dt_ms)
        if self.crossfade_elapsed >= self.CROSSFADE_MS:
            self.previous_index = None

    def _fallback_strip(self, atlas: pygame.Surface) -> pygame.Surface:
        face_width = atlas.get_width() // 3
        face_height = atlas.get_height() // 2
        target_height = max(1, self.viewport_size[1])
        panorama = pygame.Surface(
            (target_height * len(self.SIDE_FACES), target_height), pygame.SRCALPHA
        ).convert_alpha()
        for order, (column, row) in enumerate(self.SIDE_FACES):
            face = atlas.subsurface(
                (column * face_width, row * face_height, face_width, face_height)
            )
            panorama.blit(
                pygame.transform.smoothscale(face, (target_height, target_height)),
                (order * target_height, 0),
            )
        return panorama

    def _panorama(self, dimension: str, index: int) -> Optional[pygame.Surface]:
        variants = self.variants(dimension)
        if not variants:
            return None
        index %= len(variants)
        key = (dimension, index)
        cached = self._panoramas.get(key)
        if cached is not None:
            self._panoramas.move_to_end(key)
            return cached
        variant = variants[index]
        path = self._source_path(variant)
        if not os.path.isfile(path):
            return None
        try:
            source = pygame.image.load(path).convert_alpha()
        except pygame.error:
            return None
        projected_root = os.path.normpath(os.path.join(self.root, "panoramas"))
        if os.path.normpath(path).startswith(projected_root):
            target_height = max(1, self.viewport_size[1])
            target_width = max(
                self.viewport_size[0] + 2,
                round(source.get_width() * target_height / source.get_height()),
            )
            panorama = pygame.transform.smoothscale(source, (target_width, target_height))
        else:
            panorama = self._fallback_strip(source)
        self._panoramas[key] = panorama
        self._panoramas.move_to_end(key)
        while len(self._panoramas) > self.CACHE_LIMIT:
            self._panoramas.popitem(last=False)
        return panorama

    def _atmosphere(self, dimension: str) -> pygame.Surface:
        cached = self._atmospheres.get(dimension)
        if cached is not None:
            return cached
        width, height = self.viewport_size
        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        haze = {
            "overworld": (106, 126, 142),
            "nether": (82, 25, 31),
            "end": (68, 38, 92),
        }.get(dimension, (72, 72, 82))
        horizon = int(height * 0.62)
        for y in range(height):
            horizon_alpha = max(0, 38 - abs(y - horizon) * 38 // max(1, height // 4))
            edge_alpha = int(46 * abs(y - height / 2) / max(1, height / 2))
            pygame.draw.line(overlay, (*haze, horizon_alpha), (0, y), (width, y))
            if edge_alpha:
                pygame.draw.line(overlay, (5, 5, 9, edge_alpha), (0, y), (width, y))
        vignette_width = min(120, width // 4)
        for x in range(vignette_width):
            alpha = int(28 * (1.0 - x / max(1, vignette_width)))
            pygame.draw.line(overlay, (4, 4, 8, alpha), (x, 0), (x, height))
            pygame.draw.line(overlay, (4, 4, 8, alpha), (width - 1 - x, 0), (width - 1 - x, height))
        self._atmospheres[dimension] = overlay
        return overlay

    def _blit_wrapped(self, target: pygame.Surface, panorama: pygame.Surface, alpha: int) -> None:
        width, height = panorama.get_size()
        offset = int(self.rotation) % max(1, width)
        panorama.set_alpha(max(0, min(255, int(alpha))))
        remaining = target.get_width()
        destination_x = 0
        source_x = offset
        while remaining > 0:
            amount = min(width - source_x, remaining)
            target.blit(
                panorama, (destination_x, 0),
                pygame.Rect(source_x, 0, amount, min(height, target.get_height())),
            )
            remaining -= amount
            destination_x += amount
            source_x = 0
        panorama.set_alpha(None)

    def render(self, target: pygame.Surface, dimension: str) -> bool:
        current = self._panorama(dimension, self.current_index)
        if current is None:
            return False
        if self.previous_index is not None:
            previous = self._panorama(dimension, self.previous_index)
            if previous is not None:
                self._blit_wrapped(target, previous, 255)
                alpha = 255 * self.crossfade_elapsed // self.CROSSFADE_MS
                self._blit_wrapped(target, current, alpha)
            else:
                self._blit_wrapped(target, current, 255)
        else:
            self._blit_wrapped(target, current, 255)
        target.blit(self._atmosphere(dimension), (0, 0))
        return True
