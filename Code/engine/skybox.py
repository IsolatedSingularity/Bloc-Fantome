"""Lazy, time-based 2D panoramas derived from licensed OptiFine sky atlases."""

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


# Every supplied atlas is allocated exactly once. The original world0/world1
# grouping is intentionally redistributed so all three Bloc Fantome dimensions
# have distinct skies while this feature is being evaluated.
SKYBOX_VARIANTS = {
    "overworld": (
        SkyboxVariant("Day", os.path.join("world0", "day.png")),
        SkyboxVariant("Twilight", os.path.join("world0", "dusk.png")),
        SkyboxVariant("Night", os.path.join("world0", "night.png")),
    ),
    "nether": (
        SkyboxVariant("Dawn", os.path.join("world0", "dawn.png")),
        SkyboxVariant("Purple Rift", os.path.join("world1", "3.png")),
    ),
    "end": (
        SkyboxVariant("Void Aurora", os.path.join("world1", "1.png")),
        SkyboxVariant("Astral Veil", os.path.join("world1", "2.png")),
    ),
}


class SkyboxRenderer:
    """Render a smooth scrolling horizon using two cached blits per layer."""

    ROTATION_PIXELS_PER_SECOND = 7.0
    AUTO_SWAP_MS = 28_000
    CROSSFADE_MS = 1_200
    SIDE_FACES = ((2, 0), (2, 1), (1, 1), (0, 1))

    def __init__(self, root: str, viewport_size: tuple[int, int]):
        self.root = root
        self.viewport_size = tuple(map(int, viewport_size))
        self.rotation = 0.0
        self.elapsed_ms = 0
        self.current_dimension: Optional[str] = None
        self.current_index = 0
        self.previous_index: Optional[int] = None
        self.crossfade_elapsed = self.CROSSFADE_MS
        self._panoramas: OrderedDict[tuple[str, int], pygame.Surface] = OrderedDict()

    def variants(self, dimension: str) -> tuple[SkyboxVariant, ...]:
        return SKYBOX_VARIANTS.get(dimension, ())

    def available(self, dimension: str) -> bool:
        return any(
            os.path.isfile(os.path.join(self.root, variant.relative_path))
            for variant in self.variants(dimension)
        )

    def active_name(self, dimension: str) -> str:
        variants = self.variants(dimension)
        if not variants:
            return "Unavailable"
        return variants[self.current_index % len(variants)].name

    def _desired_index(
        self,
        dimension: str,
        *,
        celestial_enabled: bool,
        celestial_angle: float,
    ) -> int:
        variants = self.variants(dimension)
        if not variants:
            return 0
        if dimension == "overworld" and celestial_enabled and len(variants) >= 3:
            angle = float(celestial_angle) % 720.0
            if angle < 310.0:
                return 0
            if angle < 390.0 or angle >= 690.0:
                return 1
            return 2
        return (self.elapsed_ms // self.AUTO_SWAP_MS) % len(variants)

    def update(
        self,
        dt_ms: int,
        dimension: str,
        *,
        celestial_enabled: bool = False,
        celestial_angle: float = 0.0,
    ) -> None:
        dt_ms = max(0, int(dt_ms))
        self.rotation += self.ROTATION_PIXELS_PER_SECOND * dt_ms / 1000.0
        self.elapsed_ms += dt_ms
        if dimension != self.current_dimension:
            self.current_dimension = dimension
            self.current_index = 0
            self.previous_index = None
            self.crossfade_elapsed = self.CROSSFADE_MS
        desired = self._desired_index(
            dimension,
            celestial_enabled=celestial_enabled,
            celestial_angle=celestial_angle,
        )
        if desired != self.current_index:
            self.previous_index = self.current_index
            self.current_index = desired
            self.crossfade_elapsed = 0
        else:
            self.crossfade_elapsed = min(
                self.CROSSFADE_MS, self.crossfade_elapsed + dt_ms
            )
            if self.crossfade_elapsed >= self.CROSSFADE_MS:
                self.previous_index = None

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
        path = os.path.join(self.root, variants[index].relative_path)
        if not os.path.isfile(path):
            return None
        try:
            atlas = pygame.image.load(path).convert_alpha()
        except pygame.error:
            return None
        face_width = atlas.get_width() // 3
        face_height = atlas.get_height() // 2
        target_height = max(1, self.viewport_size[1])
        target_face_width = target_height
        panorama = pygame.Surface(
            (target_face_width * len(self.SIDE_FACES), target_height),
            pygame.SRCALPHA,
        ).convert_alpha()
        for order, (column, row) in enumerate(self.SIDE_FACES):
            face = atlas.subsurface(
                (column * face_width, row * face_height, face_width, face_height)
            )
            scaled = pygame.transform.smoothscale(
                face, (target_face_width, target_height)
            )
            panorama.blit(scaled, (order * target_face_width, 0))
        self._panoramas[key] = panorama
        self._panoramas.move_to_end(key)
        while len(self._panoramas) > 3:
            self._panoramas.popitem(last=False)
        return panorama

    def _blit_wrapped(
        self, target: pygame.Surface, panorama: pygame.Surface, alpha: int
    ) -> None:
        width, height = panorama.get_size()
        offset = int(self.rotation) % max(1, width)
        panorama.set_alpha(max(0, min(255, int(alpha))))
        remaining = target.get_width()
        destination_x = 0
        source_x = offset
        while remaining > 0:
            amount = min(width - source_x, remaining)
            target.blit(
                panorama,
                (destination_x, 0),
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
                return True
        self._blit_wrapped(target, current, 255)
        return True
