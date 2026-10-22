"""Exact scalar equivalence, including half ties and camera/metric changes."""
import numpy as np
from engine.renderer import IsometricRenderer, ProjectionMetrics


def test_batch_projection_is_pixel_exact_for_every_rotation_and_zoom():
    rng=np.random.default_rng(299)
    points=rng.integers(-4096,4097,(12000,3)).tolist()+[[0,0,0],[1,0,0],[-1,0,0]]
    for metrics in (ProjectionMetrics(),ProjectionMetrics(32,16,19)):
        renderer=IsometricRenderer(0,0,metrics)
        for rotation in range(4):
            renderer.setViewRotation(rotation)
            for zoom in (.05,.125,.333,1.,1.75,3.):
                renderer.setZoom(zoom);renderer.offsetX=113.5;renderer.offsetY=-48.5
                assert renderer.worldToScreenBatch(points)==[list(renderer.worldToScreen(*p)) for p in points]
        assert renderer.worldToScreenBatch([])==[]
