"""Cached source-shaped rendering for stairs and door cells.

The element boxes match Minecraft's `stairs`, `inner_stairs`, `outer_stairs`,
and three-voxel-thick door models. Rasterization happens only when a variant is
first requested; the game loop blits cached surfaces.
"""

import math
from typing import Iterable, Optional, Sequence, Tuple

import pygame

from engine.block_state import DoorHalf, DoorHinge, Facing, SlabPosition, StairShape


Box = Tuple[float, float, float, float, float, float]
Voxel = Tuple[int, int, int]


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

    def _draw_box_normalized(self, surface, box: Box, top, side, front) -> None:
        """Draw a box while mapping each supplied face texture edge-to-edge."""
        x1, y1, z1, x2, y2, z2 = box
        y_face = (
            self._project(x1, y2, z2), self._project(x2, y2, z2),
            self._project(x2, y2, z1), self._project(x1, y2, z1),
        )
        x_face = (
            self._project(x2, y1, z2), self._project(x2, y2, z2),
            self._project(x2, y2, z1), self._project(x2, y1, z1),
        )
        top_face = (
            self._project(x1, y1, z2), self._project(x2, y1, z2),
            self._project(x2, y2, z2), self._project(x1, y2, z2),
        )
        self._draw_face(surface, y_face, side, 0.70, (0, 0), (1, 0), (0, 1))
        self._draw_face(surface, x_face, front, 0.85, (0, 0), (1, 0), (0, 1))
        self._draw_face(surface, top_face, top, 1.0, (0, 0), (1, 0), (0, 1))

    def render_redstone_dust(
        self, top_texture: pygame.Surface, wall_texture: pygame.Surface,
        up_connections: int = 0,
    ) -> pygame.Surface:
        """Render Java wire's 0.25-voxel top model plus vertical UP connections.

        Dust is not a one-voxel block. Drawing it through ``render_boxes``
        used to give every isolated wire a visible cuboid wall and made a
        straight run read like a row of red blocks. The vanilla model is a
        horizontal plane at y=0.25 (the renderer's local z axis).
        """
        surface = pygame.Surface((self.tile_width, self.surface_height), pygame.SRCALPHA)
        top_face = (
            self._project(0, 0, 0.25), self._project(16, 0, 0.25),
            self._project(16, 16, 0.25), self._project(0, 16, 0.25),
        )
        self._draw_face(surface, top_face, top_texture, 1.0, (0, 0), (1, 0), (0, 1))
        # The Java ``redstone_dust_up`` model is a *vertical* sheet at the
        # boundary with the supporting block.  (The similarly named
        # ``redstone_dust_side`` model is the horizontal half-cell plane.)
        # Keep the sheet one model pixel inside the edge, as vanilla does, so
        # an ascending wire reads as a thin connection rather than a full
        # solid wall.  The old editor used the wrong horizontal half-cell
        # geometry here, which made upward runs disappear into the floor.
        planes = {
            0: (
                self._project(0, 0.25, 0), self._project(16, 0.25, 0),
                self._project(16, 0.25, 16), self._project(0, 0.25, 16),
            ),
            2: (
                self._project(0, 15.75, 0), self._project(16, 15.75, 0),
                self._project(16, 15.75, 16), self._project(0, 15.75, 16),
            ),
            1: (
                self._project(15.75, 0, 0), self._project(15.75, 16, 0),
                self._project(15.75, 16, 16), self._project(15.75, 0, 16),
            ),
            3: (
                self._project(0.25, 0, 0), self._project(0.25, 16, 0),
                self._project(0.25, 16, 16), self._project(0.25, 0, 16),
            ),
        }
        for bit, points in planes.items():
            if up_connections & (1 << bit):
                self._draw_face(
                    surface, points, wall_texture, 1.0,
                    (0, 0), (1, 0), (0, 1),
                )
        return surface

    def render_repeater(
        self,
        top_texture: pygame.Surface,
        side_texture: pygame.Surface,
        torch_texture: pygame.Surface,
        facing: Facing,
        delay: int = 1,
        powered: bool = False,
        locked: bool = False,
        lock_texture: Optional[pygame.Surface] = None,
    ) -> pygame.Surface:
        """Render a source-shaped repeater, including delay and lock state.

        The repeater is not a full cube: it is a smooth-stone two-pixel slab
        with two redstone torches. The bundled Java models move the output
        torch by two model pixels for each delay setting and replace the
        torches with a cross-shaped lit model when powered. Keeping the
        geometry here (rather than painting a single 16x16 repeater texture on
        every face) preserves orientation when the camera rotates.
        """
        delay = max(1, min(4, int(delay)))
        turns = (facing.value - Facing.SOUTH.value) % 4

        def rotate_boxes(boxes: Iterable[Box]) -> tuple[Box, ...]:
            return tuple(self._rotate_box(box, turns) for box in boxes)

        surface = pygame.Surface((self.tile_width, self.surface_height), pygame.SRCALPHA)
        # The top carries the repeater texture; all slab sides are smooth stone.
        self._draw_box(surface, (0, 0, 0, 16, 16, 2), side_texture, side_texture, side_texture)
        # Redstone's model uses the top face for the colored repeater graphic.
        # Rotate the atlas with the model (the blockstate does not use
        # ``uvlock``), so the arrows and torch markings follow R/camera turns.
        oriented_top = pygame.transform.rotate(top_texture, turns * 90)
        self._draw_face(
            surface,
            (
                self._project(0, 0, 2), self._project(16, 0, 2),
                self._project(16, 16, 2), self._project(0, 16, 2),
            ),
            oriented_top, 1.0, (0, 0), (1, 0), (0, 1),
        )

        # The unrotated Java model is the ``facing=south`` state. Its input
        # torch is on the south/FACING edge (model z=6) and its output torch
        # is on the north/opposite edge (model z=2). FACING is the side
        # sampled for input, not the arrow/output direction.
        input_y = 6
        output_y = 2 + (delay - 1) * 2
        if powered:
            # Exact source cross-prisms for the two lit torches. The small
            # top pixels are covered by these source-sized boxes at editor
            # scale and remain visible at every camera rotation.
            input_boxes = (
                (7, input_y - 1, 2, 9, input_y + 3, 8),
                (6, input_y, 2, 10, input_y + 2, 8),
            )
            output_boxes = (
                (7, output_y - 1, 2, 9, output_y + 3, 8),
                (6, output_y, 2, 10, output_y + 2, 8),
            )
        elif locked:
            # A locked, unpowered repeater keeps only the source model's
            # unlit output torch. The lock bar occupies the input-torch end;
            # drawing an input torch underneath it made the state look like a
            # second, incorrectly powered repeater.
            input_boxes = ()
            output_boxes = ((7, output_y, 2, 9, output_y + 5, 7),)
        else:
            input_boxes = ((7, input_y, 2, 9, input_y + 5, 7),)
            output_boxes = ((7, output_y, 2, 9, output_y + 5, 7),)
        torch_boxes = rotate_boxes(input_boxes + output_boxes)
        torch_sprite = self.render_boxes(torch_boxes, torch_texture, torch_texture, torch_texture)
        surface.blit(torch_sprite, (0, 0))

        if locked:
            lock_texture = lock_texture or side_texture
            # Source locked repeater element is [2,2,z]..[14,4,z+2], where
            # z=6,8,10,12 for the four delay states. Map model (x,y,z) to
            # renderer (x,z,y) before applying the facing rotation.
            lock_y = 6 + (delay - 1) * 2
            lock_box = self._rotate_box((2, lock_y, 2, 14, lock_y + 2, 4), turns)
            lock_sprite = self.render_boxes((lock_box,), lock_texture, lock_texture, lock_texture)
            surface.blit(lock_sprite, (0, 0))
        return surface

    @staticmethod
    def _texture_region(texture, rect) -> pygame.Surface:
        region = texture.subsurface(pygame.Rect(rect)).copy()
        return pygame.transform.scale(region, (16, 16))

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

    @staticmethod
    def _rotate_voxel(voxel: Voxel, turns: int) -> Voxel:
        """Rotate one cell in the canonical 2 x 2 x 2 stair volume."""
        x, y, z = voxel
        for _ in range(turns % 4):
            x, y = 1 - y, x
        return x, y, z

    def stair_occupancy(self, facing: Facing, shape: StairShape,
                        half: SlabPosition) -> frozenset[Voxel]:
        """Return the connected Minecraft stair volume as eight-unit voxels.

        Every bottom stair begins with the same continuous lower slab. Shape
        variants only change which upper quadrants are occupied; facing and
        top-half stairs are strict transforms of that canonical volume.
        """
        occupied: set[Voxel] = {
            (x, y, 0) for x in range(2) for y in range(2)
        }
        if shape == StairShape.STRAIGHT:
            occupied.update(((1, 0, 1), (1, 1, 1)))
        elif shape == StairShape.INNER_RIGHT:
            occupied.update(((1, 0, 1), (1, 1, 1), (0, 1, 1)))
        elif shape == StairShape.INNER_LEFT:
            occupied.update(((1, 0, 1), (1, 1, 1), (0, 0, 1)))
        elif shape == StairShape.OUTER_RIGHT:
            occupied.add((1, 1, 1))
        else:
            occupied.add((1, 0, 1))

        # The canonical upper step above is authored on +X (east), while
        # Minecraft's NORTH state rises toward -Y. Rotate the canonical volume
        # back one quarter-turn before applying the Java facing. The previous
        # direct mapping made every village roof stair appear 90 degrees off.
        rotated = {
            self._rotate_voxel(voxel, facing.value - 1) for voxel in occupied
        }
        if half == SlabPosition.TOP:
            rotated = {(x, y, 1 - z) for x, y, z in rotated}
        return frozenset(rotated)

    def stair_boxes(self, facing: Facing, shape: StairShape,
                    half: SlabPosition) -> tuple[Box, ...]:
        return tuple(
            (x * 8, y * 8, z * 8, (x + 1) * 8, (y + 1) * 8, (z + 1) * 8)
            for x, y, z in sorted(self.stair_occupancy(facing, shape, half))
        )

    def _stair_faces(self, occupied: frozenset[Voxel]):
        """Return only exterior faces of a stair's occupied union."""
        faces = []
        for x, y, z in occupied:
            x1, y1, z1 = x * 8, y * 8, z * 8
            x2, y2, z2 = x1 + 8, y1 + 8, z1 + 8
            if (x, y + 1, z) not in occupied:
                points = (
                    self._project(x1, y2, z2), self._project(x2, y2, z2),
                    self._project(x2, y2, z1), self._project(x1, y2, z1),
                )
                faces.append(("left", points, 0.70,
                              (x1 / 16, (16 - z2) / 16),
                              ((x2 - x1) / 16, 0),
                              (0, (z2 - z1) / 16), 0))
            if (x + 1, y, z) not in occupied:
                points = (
                    self._project(x2, y1, z2), self._project(x2, y2, z2),
                    self._project(x2, y2, z1), self._project(x2, y1, z1),
                )
                faces.append(("right", points, 0.85,
                              (y1 / 16, (16 - z2) / 16),
                              ((y2 - y1) / 16, 0),
                              (0, (z2 - z1) / 16), 0))
            if (x, y, z + 1) not in occupied:
                points = (
                    self._project(x1, y1, z2), self._project(x2, y1, z2),
                    self._project(x2, y2, z2), self._project(x1, y2, z2),
                )
                faces.append(("top", points, 1.0, (x1 / 16, y1 / 16),
                              ((x2 - x1) / 16, 0),
                              (0, (y2 - y1) / 16), 1))
        return sorted(
            faces,
            key=lambda face: (
                sum(point[1] for point in face[1]) / 4.0,
                face[6],
            ),
        )

    @staticmethod
    def slab_boxes(half: SlabPosition) -> tuple[Box, ...]:
        if half == SlabPosition.TOP:
            return ((0, 0, 8, 16, 16, 16),)
        return ((0, 0, 0, 16, 16, 8),)

    def detail_boxes(self, kind: str, facing: Facing = Facing.SOUTH,
                     is_open: bool = False,
                     half: SlabPosition = SlabPosition.BOTTOM,
                     delay: int = 1) -> tuple[Box, ...]:
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
        if kind == "ladder":
            return ({
                Facing.NORTH: (0, 0, 0, 16, 1, 16),
                Facing.SOUTH: (0, 15, 0, 16, 16, 16),
                Facing.EAST: (15, 0, 0, 16, 16, 16),
                Facing.WEST: (0, 0, 0, 1, 16, 16),
            }[facing],)
        if kind == "chain":
            return ((6, 6, 0, 10, 10, 16),)
        if kind == "lantern":
            if is_open:
                return ((5, 5, 1, 11, 11, 8), (6, 6, 8, 10, 10, 16))
            return ((5, 5, 0, 11, 11, 7), (6, 6, 7, 10, 10, 11))
        if kind == "torch":
            return ((7, 7, 0, 9, 9, 11),)
        if kind == "redstone_torch":
            return ((7, 7, 0, 9, 9, 10),)
        if kind == "redstone_dust":
            return ((0, 0, 0, 16, 16, 1),)
        if kind == "repeater":
            delay = max(1, min(4, int(delay)))
            # Source Java model coordinates map x -> x, model z -> our y,
            # and model y -> our vertical z. The input torch is fixed at the
            # near end; only the output torch moves for the four delay states.
            canonical = (
                (0, 0, 0, 16, 16, 2),
                (7, 6, 2, 9, 8, 7),
                (7, 2 + (delay - 1) * 2, 2, 9, 4 + (delay - 1) * 2, 7),
            )
            turns = (facing.value - Facing.SOUTH.value) % 4
            return tuple(self._rotate_box(box, turns) for box in canonical)
        if kind == "lever":
            # Source lever base is 6x8x3 (x=5..11, z=4..12 in the Java
            # model). The old approximation used a 6x7 base in a different
            # quadrant and two disconnected cuboids for the handle.
            turns = facing.value % 4
            return (
                self._rotate_box((5, 4, 0, 11, 12, 3), turns),
                self._rotate_box((7, 7, 3, 9, 9, 12), turns),
            )
        if kind == "button":
            depth = 1 if is_open else 2
            return ({
                Facing.NORTH: (5, 16 - depth, 6, 11, 16, 10),
                Facing.SOUTH: (5, 0, 6, 11, depth, 10),
                Facing.EAST: (16 - depth, 5, 6, 16, 11, 10),
                Facing.WEST: (0, 5, 6, depth, 11, 10),
            }[facing],)
        if kind == "piston":
            if not is_open:
                return self.cube_boxes()
            # ``piston_extended`` is the source Java 1.16.1 base model: the
            # casing stops four model pixels short of the front. The piston
            # head owns the separate four-pixel rod in its neighbouring cell;
            # duplicating that rod here made cycling states smear a second
            # casing-colored strip across the base sprite.
            canonical = ((0, 4, 0, 16, 16, 16),)
            turns = (facing.value - Facing.NORTH.value) % 4
            return tuple(self._rotate_box(box, turns) for box in canonical)
        if kind == "piston_head":
            head = {
                Facing.NORTH: (0, 0, 0, 16, 4, 16),
                Facing.SOUTH: (0, 12, 0, 16, 16, 16),
                Facing.EAST: (12, 0, 0, 16, 16, 16),
                Facing.WEST: (0, 0, 0, 4, 16, 16),
            }[facing]
            stem = {
                # The template piston-head rod extends four model pixels
                # into the adjacent piston cell. Keeping it inside 0..16
                # clipped the rod at every facing and left a broken-looking
                # gap during extension/retraction.
                Facing.NORTH: (6, 4, 6, 10, 20, 10),
                Facing.SOUTH: (6, -4, 6, 10, 12, 10),
                Facing.EAST: (-4, 6, 6, 12, 10, 10),
                Facing.WEST: (4, 6, 6, 20, 10, 10),
            }[facing]
            return head, stem
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

    def pick_stair_face(self, local_x: float, local_y: float, facing: Facing,
                        shape: StairShape, half: SlabPosition) -> Optional[str]:
        """Pick the topmost exterior face of the connected stair volume."""
        point = (local_x, local_y)
        faces = self._stair_faces(self.stair_occupancy(facing, shape, half))
        for face_name, polygon, *_rest in reversed(faces):
            if self._point_in_polygon(point, polygon):
                return face_name
        return None

    def render_boxes(self, boxes: Iterable[Box], top, side, front) -> pygame.Surface:
        surface = pygame.Surface((self.tile_width, self.surface_height), pygame.SRCALPHA)
        for box in boxes:
            self._draw_box(surface, box, top, side, front)
        return surface

    def render_clear_glass(self, neighbor_mask: int) -> pygame.Surface:
        """Render a six-neighbor connected clear-glass variant.

        Neighbor bits are above, below, visible-Y, opposite-Y, visible-X, and
        opposite-X. Shared face boundaries are omitted, so a glass wall reads
        as one clear sheet while objects behind it remain visible.
        """
        surface = pygame.Surface((self.tile_width, self.surface_height), pygame.SRCALPHA)
        top = (
            self._project(0, 0, 16), self._project(16, 0, 16),
            self._project(16, 16, 16), self._project(0, 16, 16),
        )
        left = (
            self._project(0, 16, 16), self._project(16, 16, 16),
            self._project(16, 16, 0), self._project(0, 16, 0),
        )
        right = (
            self._project(16, 0, 16), self._project(16, 16, 16),
            self._project(16, 16, 0), self._project(16, 0, 0),
        )
        above = bool(neighbor_mask & 1)
        below = bool(neighbor_mask & 2)
        visible_y = bool(neighbor_mask & 4)
        opposite_y = bool(neighbor_mask & 8)
        visible_x = bool(neighbor_mask & 16)
        opposite_x = bool(neighbor_mask & 32)
        outline = (194, 230, 241, 115)

        def face(points, fill, boundaries):
            pygame.draw.polygon(surface, fill, points)
            for connected, start, end in boundaries:
                if not connected:
                    pygame.draw.line(surface, outline, start, end, 1)

        if not above:
            face(top, (118, 202, 228, 18), (
                (opposite_y, top[0], top[1]), (visible_x, top[1], top[2]),
                (visible_y, top[2], top[3]), (opposite_x, top[3], top[0]),
            ))
        if not visible_y:
            face(left, (91, 166, 198, 14), (
                (above, left[0], left[1]), (visible_x, left[1], left[2]),
                (below, left[2], left[3]), (opposite_x, left[3], left[0]),
            ))
        if not visible_x:
            face(right, (103, 181, 211, 14), (
                (above, right[0], right[1]), (visible_y, right[1], right[2]),
                (below, right[2], right[3]), (opposite_y, right[3], right[0]),
            ))
        return surface

    def render_piston(self, cap, side, back, facing: Facing,
                      extended: bool, inner=None) -> pygame.Surface:
        """Render an oriented piston body with source face roles.

        ``cap`` is the piston platform, ``side`` is the casing texture,
        ``back`` is the bottom texture used on the retracted opposite face,
        and ``inner`` is the recessed texture exposed by an extended piston.
        Keeping those roles distinct prevents the bottom texture from being
        smeared across the visible casing whenever the piston cycles.
        """
        surface = pygame.Surface((self.tile_width, self.surface_height), pygame.SRCALPHA)
        boxes = self.detail_boxes("piston", facing, extended)
        if not extended:
            y_face = cap if facing == Facing.SOUTH else back if facing == Facing.NORTH else side
            x_face = cap if facing == Facing.EAST else back if facing == Facing.WEST else side
            self._draw_box(surface, boxes[0], side, y_face, x_face)
            return surface

        # In the extended model the face toward the head exposes
        # ``piston_inner``; the opposite face retains ``piston_bottom``. The
        # head itself supplies the wooden/green platform texture.
        inner = inner or back
        y_face = inner if facing == Facing.SOUTH else back if facing == Facing.NORTH else side
        x_face = inner if facing == Facing.EAST else back if facing == Facing.WEST else side
        self._draw_box(surface, boxes[0], side, y_face, x_face)
        return surface

    def render_lever(self, base_texture, handle_texture, facing: Facing,
                     powered: bool) -> pygame.Surface:
        """Render the floor lever from the Java base and rotated handle model."""
        surface = pygame.Surface((self.tile_width, self.surface_height), pygame.SRCALPHA)

        def rotate(point, turns):
            x, y, z = point
            for _ in range(turns % 4):
                x, y = 16 - y, x
            return x, y, z

        base = (5, 4, 0, 11, 12, 3)
        rotated_base = tuple(rotate((x, y, z), facing.value)
                             for x, y, z in (
                                 (base[0], base[1], base[2]),
                                 (base[3], base[4], base[5]),
                             ))
        # Rotation can swap the min/max corners, so normalize them again.
        xs = [point[0] for point in rotated_base]
        ys = [point[1] for point in rotated_base]
        self._draw_box_normalized(
            surface,
            (min(xs), min(ys), base[2], max(xs), max(ys), base[5]),
            base_texture, base_texture, base_texture,
        )

        # The source handle is a 2x2x10 prism rotated around the hinge at
        # (8,1,8) by +/-45 degrees. Apply that actual model transform instead
        # of faking the lean with a horizontal offset; the latter made the
        # lever read as a flat plank and flipped its on/off silhouette.
        angle = math.radians(-45 if powered else 45)

        def transform(point):
            x, model_y, model_z = point
            dy, dz = model_y - 1.0, model_z - 8.0
            tilted_y = 1.0 + math.cos(angle) * dy - math.sin(angle) * dz
            tilted_z = 8.0 + math.sin(angle) * dy + math.cos(angle) * dz
            # Blockstate y rotation is around the center of the block. Source
            # x/z become the renderer's x/y axes after this transform.
            for _ in range(facing.value % 4):
                x, tilted_z = 16.0 - tilted_z, x
            return x, tilted_z, tilted_y

        points = [
            transform((7, 1, 7)), transform((9, 1, 7)),
            transform((9, 11, 7)), transform((7, 11, 7)),
        ]
        projected = [self._project(x, y, z) for x, y, z in points]
        # The vanilla lever texture is intentionally narrow; at the editor's
        # native tile size it needs a restrained bronze underlay so the
        # control remains legible without becoming a full block.
        handle_color = (177, 113, 49) if powered else (109, 76, 43)
        edge_color = (238, 177, 82) if powered else (154, 109, 52)
        pygame.draw.polygon(surface, handle_color, projected)
        pygame.draw.line(surface, edge_color, projected[0], projected[3], 1)
        center_start = self._project(*transform((8, 1, 8)))
        center_end = self._project(*transform((8, 11, 8)))
        pygame.draw.line(surface, (62, 39, 25), center_start, center_end, 2)
        pygame.draw.line(surface, edge_color, center_start, center_end, 1)
        self._draw_face(surface, projected, handle_texture, 1.0,
                        (0, 0), (1, 0), (0, 1))
        return surface

    def render_piston_head(self, platform, side, unsticky, facing: Facing) -> pygame.Surface:
        """Render a piston head with the source platform/unsticky face roles."""
        surface = pygame.Surface((self.tile_width, self.surface_height), pygame.SRCALPHA)
        plate, stem = self.detail_boxes("piston_head", facing)
        # The north face is the piston platform, while the opposite face is
        # the unsticky wooden face. Which one is visible depends on the block's
        # facing after the camera-space transform.
        y_face = platform if facing == Facing.SOUTH else unsticky if facing == Facing.NORTH else side
        x_face = platform if facing == Facing.EAST else unsticky if facing == Facing.WEST else side
        self._draw_box(surface, plate, side, y_face, x_face)
        self._draw_box(surface, stem, side, side, side)
        return surface

    def render_crossed_planes(self, texture, z1: float = 0,
                              z2: float = 16) -> pygame.Surface:
        """Render a transparent Minecraft-style crossed-plane block."""
        surface = pygame.Surface((self.tile_width, self.surface_height), pygame.SRCALPHA)
        planes = (
            ((0, 0), (16, 16)),
            ((16, 0), (0, 16)),
        )
        for start, end in planes:
            points = (
                self._project(start[0], start[1], z1),
                self._project(end[0], end[1], z1),
                self._project(end[0], end[1], z2),
                self._project(start[0], start[1], z2),
            )
            self._draw_face(
                surface, points, texture, 1.0,
                (0, 1), (1, 0), (0, -1),
            )
        return surface

    def _draw_vertical_plane(self, surface, start, end, z1, z2, texture,
                             uv_origin=(0, 1), uv_u=(1, 0), uv_v=(0, -1)) -> None:
        points = (
            self._project(start[0], start[1], z1),
            self._project(end[0], end[1], z1),
            self._project(end[0], end[1], z2),
            self._project(start[0], start[1], z2),
        )
        self._draw_face(
            surface, points, texture, 1.0, uv_origin, uv_u, uv_v
        )

    def render_fire(self, texture) -> pygame.Surface:
        """Render the four intersecting floor-fire planes from the Java model."""
        surface = pygame.Surface((self.tile_width, self.surface_height), pygame.SRCALPHA)
        planes = (
            ((0, 7.2), (16, 7.2)),
            ((0, 8.8), (16, 8.8)),
            ((7.2, 0), (7.2, 16)),
            ((8.8, 0), (8.8, 16)),
        )
        for index, (start, end) in enumerate(planes):
            self._draw_vertical_plane(
                surface, start, end, 0, 16, texture,
                (1, 1) if index % 2 else (0, 1),
                (-1, 0) if index % 2 else (1, 0),
            )
        return surface

    def render_ladder(self, texture, facing: Facing) -> pygame.Surface:
        """Render the 0.8/16 wall-mounted ladder plane in its placement state."""
        surface = pygame.Surface((self.tile_width, self.surface_height), pygame.SRCALPHA)
        planes = {
            Facing.NORTH: ((0, 0.8), (16, 0.8)),
            Facing.SOUTH: ((16, 15.2), (0, 15.2)),
            Facing.EAST: ((15.2, 0), (15.2, 16)),
            Facing.WEST: ((0.8, 16), (0.8, 0)),
        }
        self._draw_vertical_plane(surface, *planes[facing], 0, 16, texture)
        return surface

    def render_chain(self, texture) -> pygame.Surface:
        """Render the two diagonal, unshaded strips of the 1.16 chain model."""
        surface = pygame.Surface((self.tile_width, self.surface_height), pygame.SRCALPHA)
        self._draw_vertical_plane(
            surface, (6, 6), (10, 10), 0, 16, texture,
            (0, 1), (3 / 16, 0), (0, -1),
        )
        self._draw_vertical_plane(
            surface, (10, 6), (6, 10), 0, 16, texture,
            (3 / 16, 1), (3 / 16, 0), (0, -1),
        )
        return surface

    def render_lantern(self, texture, hanging: bool = False) -> pygame.Surface:
        """Render the source model's body, cap, and crossed iron handle."""
        surface = pygame.Surface((self.tile_width, self.surface_height), pygame.SRCALPHA)
        if hanging:
            boxes = ((5, 5, 1, 11, 11, 8), (6, 6, 8, 10, 10, 10))
            handle_bottom, handle_top = 10, 16
        else:
            boxes = ((5, 5, 0, 11, 11, 7), (6, 6, 7, 10, 10, 9))
            handle_bottom, handle_top = 9, 11
        bodyTop = self._texture_region(texture, (0, 9, 6, 6))
        bodySide = self._texture_region(texture, (0, 2, 6, 7))
        capTop = self._texture_region(texture, (1, 10, 4, 4))
        capSide = self._texture_region(texture, (1, 0, 4, 2))
        self._draw_box_normalized(surface, boxes[0], bodyTop, bodySide, bodySide)
        self._draw_box_normalized(surface, boxes[1], capTop, capSide, capSide)
        self._draw_vertical_plane(
            surface, (6.5, 6.5), (9.5, 9.5),
            handle_bottom, handle_top, texture, (11 / 16, 12 / 16),
            (3 / 16, 0), (0, -(handle_top - handle_bottom) / 16),
        )
        self._draw_vertical_plane(
            surface, (9.5, 6.5), (6.5, 9.5),
            handle_bottom, handle_top, texture, (11 / 16, 12 / 16),
            (3 / 16, 0), (0, -(handle_top - handle_bottom) / 16),
        )
        return surface

    def render_horizontal_plane(self, texture, height: float) -> pygame.Surface:
        """Render a texture on one horizontal block-entity face."""
        surface = pygame.Surface((self.tile_width, self.surface_height), pygame.SRCALPHA)
        points = (
            self._project(0, 0, height), self._project(16, 0, height),
            self._project(16, 16, height), self._project(0, 16, height),
        )
        self._draw_face(surface, points, texture, 1.0, (0, 0), (1, 0), (0, 1))
        return surface

    def render_end_portal_frame(self, top, side, bottom,
                                eye=None) -> pygame.Surface:
        """Render the source 13/16 frame base and optional 8x3x8 eye."""
        surface = pygame.Surface((self.tile_width, self.surface_height), pygame.SRCALPHA)
        self._draw_box(surface, (0, 0, 0, 16, 16, 13), top, side, side)
        if eye is not None:
            self._draw_box(surface, (4, 4, 13, 12, 12, 16), eye, eye, eye)
        return surface

    def render_chest(self, lid_top, lid_side, lid_front,
                     body_side, body_front, latch,
                     facing: Facing = Facing.SOUTH) -> pygame.Surface:
        """Render the single-chest entity mesh: 14x10 body, 14x5 lid, 2x4 latch."""
        surface = pygame.Surface((self.tile_width, self.surface_height), pygame.SRCALPHA)
        y_front = lid_front if facing == Facing.SOUTH else lid_side
        x_front = lid_front if facing == Facing.EAST else lid_side
        self._draw_box_normalized(
            surface, (1, 1, 0, 15, 15, 10), body_side,
            body_front if facing == Facing.SOUTH else body_side,
            body_front if facing == Facing.EAST else body_side,
        )
        self._draw_box_normalized(
            surface, (1, 1, 10, 15, 15, 15), lid_top, y_front, x_front
        )
        latch_boxes = {
            Facing.SOUTH: (7, 15, 8, 9, 16, 12),
            Facing.EAST: (15, 7, 8, 16, 9, 12),
            Facing.NORTH: (7, 0, 8, 9, 1, 12),
            Facing.WEST: (0, 7, 8, 1, 9, 12),
        }
        self._draw_box_normalized(surface, latch_boxes[facing], latch, latch, latch)
        return surface

    def render_sculk_sensor(self, top, side, bottom, tendril) -> pygame.Surface:
        """Render the canonical half-block base and four diagonal tendrils."""
        surface = self.render_boxes(((0, 0, 0, 16, 16, 8),), top, side, side)
        tendrils = (
            ((0.17, 0.17), (5.83, 5.83)),
            ((10.17, 5.83), (15.83, 0.17)),
            ((10.17, 10.17), (15.83, 15.83)),
            ((0.17, 15.83), (5.83, 10.17)),
        )
        for start, end in sorted(
            tendrils,
            key=lambda plane: sum(self._project(*point, 12)[1] for point in plane),
        ):
            points = (
                self._project(start[0], start[1], 8),
                self._project(end[0], end[1], 8),
                self._project(end[0], end[1], 16),
                self._project(start[0], start[1], 16),
            )
            self._draw_face(
                surface, points, tendril, 1.0,
                (0.25, 1.0), (0.5, 0), (0, -0.5),
            )
        return surface

    def render_enchanting_table(self, top, side, bottom, cover, pages,
                                phase: float = 0.0) -> pygame.Surface:
        """Render the 12/16 table base with a lightweight animated open book."""
        surface = self.render_boxes(((0, 0, 0, 16, 16, 12),), top, side, side)
        flutter = math.sin(phase) * 0.7
        cover_faces = (
            ((8, 3, 14.3), (1, 4, 13.5), (1, 12, 13.5), (8, 13, 14.3)),
            ((8, 3, 14.3), (15, 4, 13.5), (15, 12, 13.5), (8, 13, 14.3)),
        )
        page_faces = (
            ((8, 3.5, 14.6), (1.7, 4.4, 14.0), (1.7, 11.6, 14.0), (8, 12.5, 14.6)),
            ((8, 3.5, 14.6 + flutter), (14.3, 4.4, 14.0),
             (14.3, 11.6, 14.0), (8, 12.5, 14.6 + flutter)),
        )
        for face in cover_faces:
            self._draw_face(
                surface, tuple(self._project(*point) for point in face),
                cover, 0.82, (0, 0), (1, 0), (0, 1),
            )
        for face in page_faces:
            self._draw_face(
                surface, tuple(self._project(*point) for point in face),
                pages, 1.0, (0, 0), (1, 0), (0, 1),
            )
        return surface

    def render_mine_crafter(self, outer_top, inner_top, side, bottom) -> pygame.Surface:
        """Render Mojang's 25w14craftmine Mine Crafter element layout."""
        surface = pygame.Surface((self.tile_width, self.surface_height), pygame.SRCALPHA)
        self._draw_box(surface, (0, 0, 0, 16, 16, 8), inner_top, side, side)
        self._draw_box(surface, (1, 1, 8, 15, 15, 15), outer_top, side, side)
        return surface

    def render_stair(self, top, side, front, facing: Facing, shape: StairShape,
                     half: SlabPosition) -> pygame.Surface:
        surface = pygame.Surface((self.tile_width, self.surface_height), pygame.SRCALPHA)
        textures = {"top": top, "left": side, "right": front}
        faces = self._stair_faces(self.stair_occupancy(facing, shape, half))
        for face_name, points, shade, uv_origin, uv_u, uv_v, _priority in faces:
            self._draw_face(
                surface, points, textures[face_name], shade,
                uv_origin, uv_u, uv_v,
            )
        return surface

    def render_door(self, texture, facing: Facing, is_open: bool,
                    hinge: DoorHinge, half: DoorHalf) -> pygame.Surface:
        return self.render_boxes(self.door_boxes(facing, is_open, hinge), texture, texture, texture)
