"""Conservative screen bounds, retaining the original global painter order.

Only one order and two float arrays are retained. Camera translation does not
rebuild them. Exact model/alpha tests remain owned by the application.
"""
import numpy as np


def candidates(app, mouse_x, mouse_y):
    order = app._visibleBlocksInDrawOrder()
    renderer = app.renderer
    key = (app._visibleOrderCacheKey, renderer.viewRotation)
    cache = getattr(app, '_pickProjection', None)
    if cache is None or cache[0] != key:
        rows = tuple(order)
        cells = np.asarray([row[1:4] for row in rows], dtype=np.float64).reshape(-1, 3)
        x, y, z = cells.T
        rx, ry = ((x, y), (-y, x), (-x, -y), (y, -x))[renderer.viewRotation]
        # Base coordinates before camera zoom/translation, not rounded pixels.
        px = (rx-ry) * renderer._tileWHalf / app.zoomLevel
        py = ((rx+ry)*renderer._tileHHalf-z*renderer._blockH) / app.zoomLevel
        cache = app._pickProjection = (key, rows, px, py)
    _, rows, px, py = cache
    zoom = app.zoomLevel
    x = (mouse_x-renderer.offsetX)/zoom
    y = (mouse_y-renderer.offsetY)/zoom
    # Captured plants reach 96 source pixels above the cell, full atlas 128x208.
    # Include rounding and the existing thin-component interaction halo.
    pad = 2/zoom+12
    indices = np.flatnonzero((abs(px-x)<=64+pad) & (py-y<=96+pad) & (y-py<=112+pad))
    return (rows[int(i)] for i in indices[::-1])
