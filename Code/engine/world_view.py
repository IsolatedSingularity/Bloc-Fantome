"""Bounded projection data owned independently of the application and SDL.

Callers supply a revision token and an immutable draw-order key. Camera changes
reuse coordinates; document/geometry changes discard them. Returned indices stay
in the original global painter order. Rasterization remains with the renderer.
"""
from collections import OrderedDict
from dataclasses import dataclass
from operator import itemgetter
import sys

import numpy as np


def draw_coordinates(draw_items):
    """Extract xyz in C-backed tuple iteration, without a Python loop per scalar."""
    return np.fromiter(map(itemgetter(1, 2, 3), draw_items),
                       dtype=np.dtype((np.float64, 3)), count=len(draw_items))


def select_draw_items(draw_items, indices):
    """Select ascending indices in one pass, including segmented draw orders.

    A Sequence need not provide constant-time indexing. Retain its efficient
    iterator and global painter order without materializing a second full list.
    """
    targets = iter(indices)
    target = next(targets, None)
    if target is None:
        return
    for index, item in enumerate(draw_items):
        if index == target:
            yield item
            target = next(targets, None)
            if target is None:
                return


@dataclass(frozen=True)
class ProjectionState:
    rotation: int
    half_width: float
    half_height: float
    block_height: float
    offset_x: float
    offset_y: float


class WorldViewGeometry:
    def __init__(self, byte_budget=8 * 1024 * 1024):
        self.byte_budget = max(0, int(byte_budget))
        self.retained_bytes = 0
        self._revision = None
        self._coordinates = OrderedDict()
        self._projected = None

    def _drop_projection(self):
        if self._projected is not None:
            self.retained_bytes -= self._projected[2]
            self._projected = None

    def projected_columns(self, key, items, projector):
        """Reuse one immutable painter-order batch across incremental frames.

        ``items`` is lazy so cache hits do not traverse a segmented order again.
        The caller's key includes the exact camera, revision and batch range.
        Python integer columns retain the renderer's rounding and fast blit path.
        Their conservative deep size shares the coordinate byte budget.
        """
        if self._projected is not None and self._projected[0] == key:
            return self._projected[1]
        self._drop_projection()
        columns = projector(items(), draw_items=True, columns=True)
        size = sum(sys.getsizeof(column) + sum(map(sys.getsizeof, column)) for column in columns)
        if size <= self.byte_budget:
            while self._coordinates and self.retained_bytes + size > self.byte_budget:
                _, previous = self._coordinates.popitem(last=False)
                self.retained_bytes -= previous.nbytes
            self._projected = (key, columns, size)
            self.retained_bytes += size
        return columns

    def begin_revision(self, revision):
        if revision != self._revision:
            self._coordinates.clear()
            self._projected = None
            self.retained_bytes = 0
            self._revision = revision

    def coordinates(self, key, draw_items):
        """The key must identify this exact immutable order within the revision."""
        cached = self._coordinates.get(key)
        if cached is not None:
            if len(cached) != len(draw_items):
                raise ValueError("Draw-order key reused for a different geometry")
            self._coordinates.move_to_end(key)
            return cached
        points = draw_coordinates(draw_items)
        # Scalar integer sums/subtractions must remain exact before multiplication.
        # Unusual out-of-range input takes the caller's scalar reference path.
        if len(points) and (not np.isfinite(points).all() or np.abs(points).max() > 2**51):
            return None
        points.setflags(write=False)
        if points.nbytes <= self.byte_budget:
            while self._coordinates and self.retained_bytes + points.nbytes > self.byte_budget:
                _, previous = self._coordinates.popitem(last=False)
                self.retained_bytes -= previous.nbytes
            if self.retained_bytes + points.nbytes > self.byte_budget:
                self._drop_projection()
            # Bound entry overhead as well as the coordinate buffers.
            while len(self._coordinates) >= 2:
                _, previous = self._coordinates.popitem(last=False)
                self.retained_bytes -= previous.nbytes
            self._coordinates[key] = points
            self.retained_bytes += points.nbytes
        return points

    def visible_indices(self, key, draw_items, view, bounds):
        """Inclusive rounded pixel bounds, with scalar arithmetic operation order.

        NumPy rint and Python round both use nearest-even ties. No sorting,
        occlusion, material substitution, water filtering or geometry is changed.
        """
        points = self.coordinates(key, draw_items)
        if points is None:
            return None
        x, y, z = points.T
        if view.rotation == 0:
            rx, ry = x, y
        elif view.rotation == 1:
            rx, ry = -y, x
        elif view.rotation == 2:
            rx, ry = -x, -y
        else:
            rx, ry = y, -x
        sx = np.rint((rx - ry) * view.half_width + view.offset_x)
        sy = np.rint((rx + ry) * view.half_height - z * view.block_height + view.offset_y)
        left, top, right, bottom = bounds
        return np.flatnonzero((sx >= left) & (sx <= right) &
                              (sy >= top) & (sy <= bottom)).tolist()
