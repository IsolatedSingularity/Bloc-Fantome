"""Capture only fully prepared scenes and complete time-sliced world surfaces."""
import time


def settle_scene(app,timeout=120):
    deadline=time.perf_counter()+timeout
    frames=0
    while time.perf_counter()<deadline:
        app._update();app._render();frames+=1
        pending=any(getattr(app,name,None) for name in
                    ('_pendingTourLoad','pendingWorldLoad','pendingBiomeLoad'))
        if not pending and app._worldSurfaceBuild is None:
            assert not app.tooltipText.startswith('Could not load tutorial scene:'),app.tooltipText
            return frames
        time.sleep(.001)
    raise AssertionError('Scene preparation or complete rendering timed out')
