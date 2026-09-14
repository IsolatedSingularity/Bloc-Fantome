"""Independently turning cubemap skies from the licensed OptiFine atlases."""

from __future__ import annotations

from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import math
import os
from typing import Optional

import pygame



@dataclass(frozen=True)
class SkyboxVariant:
    name: str
    relative_path: str
    vertical_center: float = 0.46


SKYBOX_VARIANTS = {
    "overworld": (
        SkyboxVariant("sky_day01_07", os.path.join("world0", "day.png"), 0.43),
        SkyboxVariant("Twilight", os.path.join("world0", "dusk.png"), 0.43),
        SkyboxVariant("Night", os.path.join("world0", "night.png"), 0.44),
    ),
    "nether": (
        SkyboxVariant("Xen Sky 2", os.path.join("world1", "2.png"), 0.50),
        SkyboxVariant("Ashen Dawn", os.path.join("world0", "dawn.png"), 0.43),
    ),
    "end": (
        SkyboxVariant("Xen Sky 6", os.path.join("world1", "3.png"), 0.47),
        SkyboxVariant("Void Aurora", os.path.join("world1", "1.png"), 0.48),
    ),
}


class SkyboxRenderer:
    """Render a complete six-face cubemap around the isometric camera.

    Each cached viewport pixel is cast through a perspective camera into the
    dominant cube face, including the atlas ceiling and floor. The sky is
    infinitely distant. Its slow rotation follows elapsed time independently
    of canvas rotation, panning and zooming.
    """

    CROSSFADE_MS = 420
    ROTATION_MS = 360
    DRIFT_DEGREES_PER_SECOND = 0.8
    YAW_QUANTUM = 15.0
    PITCH_QUANTUM = 1.5
    CACHE_LIMIT = 12
    ATLAS_CACHE_LIMIT = 3
    FACE_COORDS = {
        "bottom": (0, 0), "top": (1, 0), "east": (2, 0),
        "south": (0, 1), "west": (1, 1), "north": (2, 1),
    }
    VIEW_ORDER = ("south", "east", "north", "west")

    def __init__(self, root: str, viewport_size: tuple[int, int]):
        self.root = root
        self.viewport_size = tuple(map(int, viewport_size))
        self.current_dimension: Optional[str] = None
        self.current_index = 0
        self.view_rotation = 0
        self.current_yaw = 0.0
        self.current_pitch = 18.0
        self._yaw_from = 0.0
        self._yaw_to = 0.0
        self._rotation_elapsed = self.ROTATION_MS
        self.previous_view: Optional[tuple[str, int, float, float]] = None
        self.crossfade_elapsed = self.CROSSFADE_MS
        self.selected_indices = {"overworld": 2, "nether": 0, "end": 1}
        self._atlases: OrderedDict[tuple[str, int], pygame.Surface] = OrderedDict()
        self._native_atlases = OrderedDict()
        self._prefetch = {}
        self._prefetch_identity = None
        self._prefetch_worker = None
        self._views: OrderedDict[tuple[str, int, float, float], pygame.Surface] = OrderedDict()

    def variants(self, dimension: str) -> tuple[SkyboxVariant, ...]:
        return SKYBOX_VARIANTS.get(dimension, ())

    def resize(self, viewport_size: tuple[int, int]) -> None:
        """Rebuild only viewport derivatives after a native window resize."""
        viewport_size = tuple(map(int, viewport_size))
        if viewport_size == self.viewport_size:
            return
        self.viewport_size = viewport_size
        self._views.clear()
        self._cancel_prefetch()

    def _cancel_prefetch(self):
        for future in self._prefetch.values():
            future.cancel()
        self._prefetch.clear()
        self._prefetch_identity = None

    def _prefetch_rotation(self, dimension, pitch, needed):
        """Prepare upcoming orientations off-thread; only RGB bytes cross threads."""
        from engine.native_acceleration import cubemap_rgb
        identity = (dimension, self.current_index, self.viewport_size, pitch)
        if identity != self._prefetch_identity:
            self._cancel_prefetch()
            self._prefetch_identity = identity
        for key, future in list(self._prefetch.items()):
            if not future.done():
                continue
            self._prefetch.pop(key)
            pixels = future.result()
            if pixels is not None and key not in self._views:
                self._views[key] = pygame.image.frombuffer(pixels,self.viewport_size,'RGB').convert()
                while len(self._views) > self.CACHE_LIMIT:
                    self._views.popitem(last=False)
        atlas_data = self._native_atlases.get((dimension,self.current_index))
        if atlas_data is None:
            return
        atlas, pixels = atlas_data
        if self._prefetch_worker is None:
            self._prefetch_worker = ThreadPoolExecutor(max_workers=1,thread_name_prefix='sky-view')
        start = math.floor(self.current_yaw / self.YAW_QUANTUM) * self.YAW_QUANTUM
        for offset in range(1,4):
            raw_yaw = start + offset * self.YAW_QUANTUM
            yaw = raw_yaw % 360
            key = (dimension,self.current_index,yaw,pitch)
            if yaw in needed or key in self._views or key in self._prefetch:
                continue
            self._prefetch[key] = self._prefetch_worker.submit(
                cubemap_rgb,pixels,atlas.get_size(),self.viewport_size,yaw,pitch,
                self.variants(dimension)[self.current_index].vertical_center,
            )
            if len(self._prefetch) >= 7:
                break

    def _source_path(self, variant: SkyboxVariant) -> str:
        return os.path.join(self.root, variant.relative_path)

    def available(self, dimension: str) -> bool:
        return any(
            os.path.isfile(self._source_path(variant))
            for variant in self.variants(dimension)
        )

    def active_name(self, dimension: str) -> str:
        variants = self.variants(dimension)
        if not variants:
            return "Unavailable"
        index = self.selected_indices.get(dimension, 0) % len(variants)
        return variants[index].name

    @staticmethod
    def _shortest_turn(start: float, target: float) -> float:
        return start + ((target - start + 180.0) % 360.0 - 180.0)

    def _quantized_orientation(self) -> tuple[float, float]:
        yaw = round(self.current_yaw / self.YAW_QUANTUM) * self.YAW_QUANTUM
        pitch = round(self.current_pitch / self.PITCH_QUANTUM) * self.PITCH_QUANTUM
        return yaw % 360.0, max(-30.0, min(30.0, pitch))

    def _active_key(self) -> Optional[tuple[str, int, float, float]]:
        if self.current_dimension is None:
            return None
        yaw, pitch = self._quantized_orientation()
        return (self.current_dimension, self.current_index, yaw, pitch)

    def set_selection(self, dimension: str, index: int, *, crossfade: bool = True) -> None:
        variants = self.variants(dimension)
        if not variants:
            return
        desired = int(index) % len(variants)
        old = self.selected_indices.get(dimension, 0) % len(variants)
        if desired == old:
            return
        before = self._active_key()
        self.selected_indices[dimension] = desired
        if dimension == self.current_dimension:
            self.previous_view = before if crossfade else None
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
        self,
        dt_ms: int,
        dimension: str,
        *,
        view_rotation: int = 0,
        celestial_enabled: bool = False,
        celestial_angle: float = 0.0,
        camera_offset: Optional[tuple[float, float]] = None,
        zoom: Optional[float] = None,
    ) -> None:
        del celestial_enabled, celestial_angle, view_rotation, camera_offset, zoom
        dt_ms = max(0, int(dt_ms))
        desired_index = self.selected_indices.get(dimension, 0)
        if (self.current_dimension, self.current_index) != (dimension, desired_index):
            before = self._active_key()
            self.previous_view = before if before and before[0] == dimension else None
            self.current_dimension = dimension
            self.current_index = desired_index
            self.crossfade_elapsed = 0 if self.previous_view else self.CROSSFADE_MS
        self.current_yaw = (self.current_yaw + dt_ms * self.DRIFT_DEGREES_PER_SECOND / 1000.0) % 360.0
        self.crossfade_elapsed = min(self.CROSSFADE_MS, self.crossfade_elapsed + dt_ms)
        if self.crossfade_elapsed >= self.CROSSFADE_MS:
            self.previous_view = None

    def _atlas(self, dimension: str, index: int) -> Optional[pygame.Surface]:
        variants = self.variants(dimension)
        if not variants:
            return None
        index %= len(variants)
        key = (dimension, index)
        cached = self._atlases.get(key)
        if cached is not None:
            self._atlases.move_to_end(key)
            return cached
        path = self._source_path(variants[index])
        if not os.path.isfile(path):
            return None
        try:
            cached = pygame.image.load(path).convert()
        except pygame.error:
            return None
        self._atlases[key] = cached
        self._atlases.move_to_end(key)
        while len(self._atlases) > self.ATLAS_CACHE_LIMIT:
            self._atlases.popitem(last=False)
        return cached

    def _face(self, atlas: pygame.Surface, name: str) -> pygame.Surface:
        face_width = atlas.get_width() // 3
        face_height = atlas.get_height() // 2
        column, row = self.FACE_COORDS[name]
        face = atlas.subsurface(
            (column * face_width, row * face_height, face_width, face_height)
        )
        return pygame.transform.flip(face, True, False)

    def _view(
        self, dimension: str, index: int, yaw: float, pitch: float = 0.0
    ) -> Optional[pygame.Surface]:
        variants = self.variants(dimension)
        if not variants:
            return None
        index %= len(variants)
        yaw = round(float(yaw) / self.YAW_QUANTUM) * self.YAW_QUANTUM % 360.0
        pitch = round(float(pitch) / self.PITCH_QUANTUM) * self.PITCH_QUANTUM
        key = (dimension, index, yaw, pitch)
        cached = self._views.get(key)
        if cached is not None:
            self._views.move_to_end(key)
            return cached
        atlas = self._atlas(dimension, index)
        if atlas is None:
            return None

        width, height = self.viewport_size
        from engine.native_acceleration import cubemap_rgb
        atlas_key = (dimension, index)
        if atlas_key not in self._native_atlases or self._native_atlases[atlas_key][0] is not atlas:
            self._native_atlases[atlas_key] = (atlas, pygame.image.tostring(atlas, 'RGB'))
            while len(self._native_atlases) > self.ATLAS_CACHE_LIMIT:
                self._native_atlases.popitem(last=False)
        pixels = cubemap_rgb(self._native_atlases[atlas_key][1], atlas.get_size(),
                             (width,height),yaw,pitch,variants[index].vertical_center)
        if pixels is not None:
            cached = pygame.image.frombuffer(pixels,(width,height),'RGB').convert()
            self._views[key] = cached
            while len(self._views) > self.CACHE_LIMIT: self._views.popitem(last=False)
            return cached
        try:
            import numpy as np

            atlas_pixels = pygame.surfarray.array3d(atlas)
            face_width = atlas.get_width() // 3
            face_height = atlas.get_height() // 2
            horizontal_fov = math.radians(94.0)
            focal = (width / 2.0) / math.tan(horizontal_fov / 2.0)
            center_x = width / 2.0
            center_y = height * variants[index].vertical_center

            screen_x = (
                np.arange(width, dtype=np.float32) + 0.5 - center_x
            )[:, None] / focal
            screen_y = (
                center_y - np.arange(height, dtype=np.float32) - 0.5
            )[None, :] / focal
            camera_z = np.ones((1, 1), dtype=np.float32)
            pitch_radians = math.radians(pitch)
            pitch_cos = math.cos(pitch_radians)
            pitch_sin = math.sin(pitch_radians)
            direction_y = screen_y * pitch_cos + camera_z * pitch_sin
            direction_z = camera_z * pitch_cos - screen_y * pitch_sin
            yaw_radians = math.radians(yaw)
            yaw_cos = math.cos(yaw_radians)
            yaw_sin = math.sin(yaw_radians)
            direction_x = screen_x * yaw_cos + direction_z * yaw_sin
            direction_z = direction_z * yaw_cos - screen_x * yaw_sin

            # Broadcast the three ray components to the complete viewport and
            # select all six faces by the dominant world-space axis.
            dx = np.broadcast_to(direction_x, (width, height))
            dy = np.broadcast_to(direction_y, (width, height))
            dz = np.broadcast_to(direction_z, (width, height))
            dominant = np.maximum.reduce((np.abs(dx), np.abs(dy), np.abs(dz)))
            output = np.zeros((width, height, 3), dtype=np.uint8)
            claimed = np.zeros((width, height), dtype=bool)
            face_maps = (
                ("bottom", (np.abs(dy) == dominant) & (dy < 0), -dz, dx),
                ("top", (np.abs(dy) == dominant) & (dy >= 0), -dz, -dx),
                ("east", (np.abs(dx) == dominant) & (dx >= 0), dz, -dy),
                ("south", (np.abs(dz) == dominant) & (dz >= 0), -dx, -dy),
                ("west", (np.abs(dx) == dominant) & (dx < 0), -dz, -dy),
                ("north", (np.abs(dz) == dominant) & (dz < 0), dx, -dy),
            )
            for face_name, candidate, local_x, local_z in face_maps:
                mask = candidate & ~claimed
                if not np.any(mask):
                    continue
                columns, rows = np.nonzero(mask)
                axis = dominant[mask]
                sample_x = np.clip(
                    (0.5 + 0.5 * local_x[mask] / axis) * (face_width - 1),
                    0.0, face_width - 1.0,
                )
                normalized_y = 0.5 + 0.5 * local_z[mask] / axis
                sample_y = np.clip(
                    normalized_y * (face_height - 1), 0.0, face_height - 1.0
                )
                source_x = np.rint(sample_x).astype(np.int32)
                source_y = np.rint(sample_y).astype(np.int32)
                face_column, face_row = self.FACE_COORDS[face_name]
                face = atlas_pixels[
                    face_column * face_width:(face_column + 1) * face_width,
                    face_row * face_height:(face_row + 1) * face_height,
                ]
                # Every source face is 1024px square, so direct sampling is
                # already native-detail at both 1200x800 and 1920x1080. It is
                # substantially faster than per-pixel bilinear interpolation
                # and keeps Q/E rotation responsive instead of blurring a
                # lower-resolution intermediate surface.
                output[columns, rows] = face[source_x, source_y]
                claimed |= mask
            cached = pygame.surfarray.make_surface(output).convert()
        except (ImportError, pygame.error):
            # Portable fallback for source checkouts without NumPy. It still
            # uses perspective side-face rays and never scrolls a panorama.
            faces = {name: self._face(atlas, name) for name in self.VIEW_ORDER}
            cached = pygame.Surface((width, height)).convert()
            horizontal_fov = math.radians(94.0)
            focal = (width / 2.0) / math.tan(horizontal_fov / 2.0)
            center_x = width / 2.0
            center_y = height * variants[index].vertical_center
            for output_x in range(width):
                ray_x = (output_x + 0.5 - center_x) / focal
                column_angle = yaw + math.degrees(math.atan(ray_x))
                face_index = int(math.floor((column_angle + 45.0) / 90.0)) % 4
                delta = math.radians(
                    (column_angle - face_index * 90.0 + 180.0) % 360.0 - 180.0
                )
                face = faces[self.VIEW_ORDER[face_index]]
                source_x = round((0.5 + math.tan(delta) * 0.5) * (face.get_width() - 1))
                source_x = max(0, min(face.get_width() - 1, source_x))
                visible_height = max(1, round(face.get_height() * 0.54))
                source = face.subsurface((source_x, 0, 1, visible_height))
                column_height = max(height, round(height / max(0.72, math.cos(delta))))
                column = pygame.transform.smoothscale(source, (1, column_height))
                cached.blit(column, (output_x, round(center_y - column_height / 2)))
        self._views[key] = cached
        self._views.move_to_end(key)
        while len(self._views) > self.CACHE_LIMIT:
            self._views.popitem(last=False)
        return cached

    @staticmethod
    def _blit_alpha(target: pygame.Surface, source: pygame.Surface, alpha: int) -> None:
        if alpha >= 255:
            target.blit(source, (0, 0))
            return
        source.set_alpha(max(0, min(255, int(alpha))))
        target.blit(source, (0, 0))
        source.set_alpha(None)

    def render(self, target: pygame.Surface, dimension: str) -> bool:
        if self.current_dimension != dimension:
            self.update(0, dimension, view_rotation=self.view_rotation)
        _, pitch = self._quantized_orientation()
        yaw = math.floor(self.current_yaw / self.YAW_QUANTUM) * self.YAW_QUANTUM % 360
        self._prefetch_rotation(dimension,pitch,{yaw,(yaw+self.YAW_QUANTUM)%360})
        current = self._view(dimension, self.current_index, yaw, pitch)
        if current is None:
            return False
        if self.previous_view is not None:
            previous = self._view(*self.previous_view)
            if previous is not None:
                target.blit(previous, (0, 0))
                alpha = 255 * self.crossfade_elapsed // self.CROSSFADE_MS
                self._blit_alpha(target, current, alpha)
            else:
                target.blit(current, (0, 0))
        else:
            target.blit(current, (0, 0))
        # Blend adjacent perspective samples: native-resolution, bounded cache,
        # and continuous visual rotation without 60 expensive raycasts/second.
        fraction = (self.current_yaw % self.YAW_QUANTUM) / self.YAW_QUANTUM
        if fraction > 0.001 and self.previous_view is None:
            following = self._view(dimension, self.current_index, yaw + self.YAW_QUANTUM, pitch)
            if following is not None:
                self._blit_alpha(target, following, round(255 * fraction))
        return True
