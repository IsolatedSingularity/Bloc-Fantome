"""Cached source-shaped rendering for stairs and door cells.

The element boxes match Minecraft's `stairs`, `inner_stairs`, `outer_stairs`,
and three-voxel-thick door models. Rasterization happens only when a variant is
first requested; the game loop blits cached surfaces.
"""

from typing import Iterable, Optional, Sequence, Tuple

import pygame

from engine.block_state import DoorHalf, DoorHinge, Facing, SlabPosition, StairShape


Box = Tuple[float, float, float, float, float, float]


class BlockModelRenderer:
    """Rasterize Minecraft-style axis-aligned element boxes isometrically."""

    def __init__(self, tile_width: int, tile_height: int, block_height: int) -> None:
        self.tile_width = tile_width
        self.tile_height = tile_height
        self.block_height = block_height
        self.surface_height = tile_height + block_height

    def _project(self, x: float, y: float, z: float) -> Tuple[float, float]:
        return (
            self.tile_width / 2 + (x - y) * self.tile_width / 32,
            (x + y) * self.tile_height / 32 + (16 - z) * self.block_height / 16,
        )

    @staticmethod
    def _shade(color, factor: float):
        return (
            int(color.r * factor),
            int(color.g * factor),
            int(color.b * factor),
            color.a,
        )

    def _draw_face(self, surface, points, texture, shade, uv_origin, uv_u, uv_v) -> None:
        p0, p1, p2, p3 = points
        min_x = max(0, int(min(point[0] for point in points)))
        max_x = min(surface.get_width() - 1, int(max(point[0] for point in points) + 1))
        min_y = max(0, int(min(point[1] for point in points)))
        max_y = min(surface.get_height() - 1, int(max(point[1] for point in points) + 1))
        ux, uy = p1[0] - p0[0], p1[1] - p0[1]
        vx, vy = p3[0] - p0[0], p3[1] - p0[1]
        determinant = ux * vy - uy * vx
        if abs(determinant) < 0.001:
            return
        width, height = texture.get_size()
        for py in range(min_y, max_y + 1):
            for px in range(min_x, max_x + 1):
                dx, dy = px + 0.5 - p0[0], py + 0.5 - p0[1]
                a = (dx * vy - dy * vx) / determinant
                b = (ux * dy - uy * dx) / determinant
                if -0.001 <= a <= 1.001 and -0.001 <= b <= 1.001:
                    u = uv_origin[0] + a * uv_u[0] + b * uv_v[0]
                    v = uv_origin[1] + a * uv_u[1] + b * uv_v[1]
                    tx = max(0, min(width - 1, int(u * width) % width))
                    ty = max(0, min(height - 1, int(v * height) % height))
                    color = texture.get_at((tx, ty))
                    if color.a:
                        surface.set_at((px, py), self._shade(color, shade))

    def _draw_box(self, surface, box: Box, top, side, front) -> None:
        x1, y1, z1, x2, y2, z2 = box
        # Visible Y face.
        y_face = [
            self._project(x1, y2, z2), self._project(x2, y2, z2),
            self._project(x2, y2, z1), self._project(x1, y2, z1),
        ]
        self._draw_face(surface, y_face, side, 0.70, (x1 / 16, (16 - z2) / 16),
                        ((x2 - x1) / 16, 0), (0, (z2 - z1) / 16))
        # Visible X face.
        x_face = [
            self._project(x2, y1, z2), self._project(x2, y2, z2),
            self._project(x2, y2, z1), self._project(x2, y1, z1),
        ]
        self._draw_face(surface, x_face, front, 0.85, (y1 / 16, (16 - z2) / 16),
                        ((y2 - y1) / 16, 0), (0, (z2 - z1) / 16))
        # Top face is last so shared edges remain crisp.
        top_face = [
            self._project(x1, y1, z2), self._project(x2, y1, z2),
            self._project(x2, y2, z2), self._project(x1, y2, z2),
        ]
        self._draw_face(surface, top_face, top, 1.0, (x1 / 16, y1 / 16),
                        ((x2 - x1) / 16, 0), (0, (y2 - y1) / 16))

    @staticmethod
    def _rotate_box(box: Box, turns: int) -> Box:
        x1, y1, z1, x2, y2, z2 = box
        for _ in range(turns % 4):
            x1, y1, x2, y2 = 16 - y2, x1, 16 - y1, x2
        return x1, y1, z1, x2, y2, z2

    @staticmethod
    def _invert_box(box: Box) -> Box:
        x1, y1, z1, x2, y2, z2 = box
        return x1, y1, 16 - z2, x2, y2, 16 - z1

    @staticmethod
    def cube_boxes() -> tuple[Box, ...]:
        return ((0, 0, 0, 16, 16, 16),)

    def stair_boxes(self, facing: Facing, shape: StairShape,
                    half: SlabPosition) -> tuple[Box, ...]:
        boxes: list[Box] = [(0, 0, 0, 16, 16, 8)]
        if shape == StairShape.STRAIGHT:
            boxes.append((8, 0, 8, 16, 16, 16))
        elif shape == StairShape.INNER_RIGHT:
            boxes.extend(((8, 0, 8, 16, 16, 16), (0, 8, 8, 8, 16, 16)))
        elif shape == StairShape.INNER_LEFT:
            boxes.extend(((8, 0, 8, 16, 16, 16), (0, 0, 8, 8, 8, 16)))
        elif shape == StairShape.OUTER_RIGHT:
            boxes.append((8, 8, 8, 16, 16, 16))
        else:
            boxes.append((8, 0, 8, 16, 8, 16))
        rotated = [self._rotate_box(box, facing.value) for box in boxes]
        if half == SlabPosition.TOP:
            rotated = [self._invert_box(box) for box in rotated]
        return tuple(rotated)

    @staticmethod
    def slab_boxes(half: SlabPosition) -> tuple[Box, ...]:
        if half == SlabPosition.TOP:
            return ((0, 0, 8, 16, 16, 16),)
        return ((0, 0, 0, 16, 16, 8),)

    def detail_boxes(self, kind: str, facing: Facing = Facing.SOUTH,
                     is_open: bool = False,
                     half: SlabPosition = SlabPosition.BOTTOM) -> tuple[Box, ...]:
        """Return compact Minecraft-shaped boxes for common structure details."""
        if kind == "fence":
            return (
                (6, 6, 0, 10, 10, 16),
                (0, 7, 6, 16, 9, 9), (0, 7, 12, 16, 9, 15),
                (7, 0, 6, 9, 16, 9), (7, 0, 12, 9, 16, 15),
            )
        if kind == "wall":
            return (
                (4, 4, 0, 12, 12, 16),
                (0, 5, 5, 16, 11, 14), (5, 0, 5, 11, 16, 14),
            )
        if kind == "trapdoor":
            if not is_open:
                return ((0, 0, 13 if half == SlabPosition.TOP else 0,
                         16, 16, 16 if half == SlabPosition.TOP else 3),)
            boxes = {
                Facing.NORTH: (0, 13, 0, 16, 16, 16),
                Facing.SOUTH: (0, 0, 0, 16, 3, 16),
                Facing.EAST: (0, 0, 0, 3, 16, 16),
                Facing.WEST: (13, 0, 0, 16, 16, 16),
            }
            return (boxes[facing],)
        if kind == "bed":
            return ((0, 0, 0, 16, 16, 9),)
        if kind == "banner":
            return ((7, 1, 0, 9, 15, 16),)
        if kind == "pane":
            return ((7, 0, 0, 9, 16, 16),)
        if kind == "torch":
            return ((7, 7, 0, 9, 9, 11),)
        if kind == "candle":
            return ((6, 6, 0, 10, 10, 12),)
        if kind == "bulb":
            return ((3, 3, 2, 13, 13, 14), (6, 6, 0, 10, 10, 2))
        if kind == "plant":
            return ((7, 0, 0, 9, 16, 16), (0, 7, 0, 16, 9, 16))
        return self.cube_boxes()

    @staticmethod
    def door_boxes(facing: Facing, is_open: bool,
                   hinge: DoorHinge) -> tuple[Box, ...]:
        thickness = 3
        if not is_open:
            box_by_facing = {
                Facing.EAST: (0, 0, 0, thickness, 16, 16),
                Facing.SOUTH: (0, 0, 0, 16, thickness, 16),
                Facing.WEST: (16 - thickness, 0, 0, 16, 16, 16),
                Facing.NORTH: (0, 16 - thickness, 0, 16, 16, 16),
            }
        else:
            box_by_facing = {
                Facing.EAST: (0, 16 - thickness if hinge == DoorHinge.RIGHT else 0, 0,
                              16, 16 if hinge == DoorHinge.RIGHT else thickness, 16),
                Facing.SOUTH: (0 if hinge == DoorHinge.RIGHT else 16 - thickness, 0, 0,
                               thickness if hinge == DoorHinge.RIGHT else 16, 16, 16),
                Facing.WEST: (0, 0 if hinge == DoorHinge.RIGHT else 16 - thickness, 0,
                              16, thickness if hinge == DoorHinge.RIGHT else 16, 16),
                Facing.NORTH: (16 - thickness if hinge == DoorHinge.RIGHT else 0, 0, 0,
                               16 if hinge == DoorHinge.RIGHT else thickness, 16, 16),
            }
        return (box_by_facing[facing],)

    @staticmethod
    def _point_in_polygon(point: tuple[float, float], polygon: Sequence[tuple[float, float]]) -> bool:
        px, py = point
        sign = 0
        for index, (x1, y1) in enumerate(polygon):
            x2, y2 = polygon[(index + 1) % len(polygon)]
            cross = (x2 - x1) * (py - y1) - (y2 - y1) * (px - x1)
            if abs(cross) < 0.001:
                continue
            current = 1 if cross > 0 else -1
            if sign and current != sign:
                return False
            sign = current
        return True

    def pick_box_face(self, local_x: float, local_y: float,
                      boxes: Iterable[Box]) -> Optional[str]:
        """Return the visible model face at a sprite-local pixel.

        Boxes and faces are checked in reverse raster order so picking follows
        exactly what the model renderer placed on top.
        """
        point = (local_x, local_y)
        for box in reversed(tuple(boxes)):
            x1, y1, z1, x2, y2, z2 = box
            faces = (
                ("top", (
                    self._project(x1, y1, z2), self._project(x2, y1, z2),
                    self._project(x2, y2, z2), self._project(x1, y2, z2),
                )),
                ("right", (
                    self._project(x2, y1, z2), self._project(x2, y2, z2),
                    self._project(x2, y2, z1), self._project(x2, y1, z1),
                )),
                ("left", (
                    self._project(x1, y2, z2), self._project(x2, y2, z2),
                    self._project(x2, y2, z1), self._project(x1, y2, z1),
                )),
            )
            for face_name, polygon in faces:
                if self._point_in_polygon(point, polygon):
                    return face_name
        return None

    def render_boxes(self, boxes: Iterable[Box], top, side, front) -> pygame.Surface:
        surface = pygame.Surface((self.tile_width, self.surface_height), pygame.SRCALPHA)
        for box in boxes:
            self._draw_box(surface, box, top, side, front)
        return surface

    def render_stair(self, top, side, front, facing: Facing, shape: StairShape,
                     half: SlabPosition) -> pygame.Surface:
        return self.render_boxes(self.stair_boxes(facing, shape, half), top, side, front)

    def render_door(self, texture, facing: Facing, is_open: bool,
                    hinge: DoorHinge, half: DoorHalf) -> pygame.Surface:
        return self.render_boxes(self.door_boxes(facing, is_open, hinge), texture, texture, texture)
