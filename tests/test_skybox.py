import os

import pygame
import pytest
from unittest.mock import patch

from engine.skybox import SKYBOX_VARIANTS, SkyboxRenderer
from runtime_paths import SKYBOXES_DIR


def setup_module():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.display.init()
    pygame.display.set_mode((1, 1))


def teardown_module():
    pygame.display.quit()


def test_all_supplied_cubemap_atlases_are_unique_and_available():
    paths = [
        variant.relative_path
        for variants in SKYBOX_VARIANTS.values()
        for variant in variants
    ]
    assert {dimension: len(variants) for dimension, variants in SKYBOX_VARIANTS.items()} == {
        "overworld": 3, "nether": 2, "end": 2,
    }
    assert len(paths) == len(set(paths)) == 7
    assert all(os.path.isfile(os.path.join(SKYBOXES_DIR, path)) for path in paths)

    renderer = SkyboxRenderer(SKYBOXES_DIR, (320, 180))
    assert renderer.selected_indices == {"overworld": 2, "nether": 0, "end": 1}
    assert renderer.active_name("overworld") == "Night"
    assert renderer.active_name("end") == "Void Aurora"


def test_renderer_builds_native_cubemap_views_with_bounded_drifting_views():
    renderer = SkyboxRenderer(SKYBOXES_DIR, (320, 180))
    target = pygame.Surface((320, 180))
    for dimension, variants in SKYBOX_VARIANTS.items():
        for index in range(len(variants)):
            renderer.selected_indices[dimension] = index
            renderer.update(0, dimension, view_rotation=index % 4)
            assert renderer.render(target, dimension)
    assert len(renderer._atlases) <= renderer.ATLAS_CACHE_LIMIT
    assert len(renderer._views) <= renderer.CACHE_LIMIT
    assert all(surface.get_size() == (320, 180) for surface in renderer._views.values())

    renderer.update(renderer.CROSSFADE_MS, renderer.current_dimension, view_rotation=renderer.view_rotation)
    renderer.render(target, renderer.current_dimension)
    before = target.copy()
    atlas_before = renderer._view(renderer.current_dimension, renderer.current_index, *renderer._quantized_orientation())
    for _ in range(20):
        renderer.update(
            16,
            renderer.current_dimension,
            view_rotation=renderer.view_rotation,
            camera_offset=(400.0 + _ * 80.0, -250.0 + _ * 40.0),
            zoom=0.4 + _ * 0.1,
        )
        assert renderer.render(target, renderer.current_dimension)
    assert atlas_before is renderer._view(renderer.current_dimension, renderer.current_index, *renderer._quantized_orientation())
    assert renderer.current_yaw > 0
    assert not hasattr(renderer, "layers")


def test_projection_samples_the_ceiling_floor_and_four_walls():
    renderer = SkyboxRenderer(SKYBOXES_DIR, (180, 360))
    face_colors = {
        "bottom": (255, 0, 0),
        "top": (0, 255, 0),
        "east": (0, 0, 255),
        "south": (255, 255, 0),
        "west": (255, 0, 255),
        "north": (0, 255, 255),
    }
    atlas = pygame.Surface((96, 64))
    for name, color in face_colors.items():
        column, row = renderer.FACE_COORDS[name]
        atlas.fill(color, (column * 32, row * 32, 32, 32))
    renderer._atlas = lambda _dimension, _index: atlas
    visible = set()
    for yaw in (0, 90, 180, 270):
        view = renderer._view("overworld", 0, yaw)
        visible.update(
            tuple(view.get_at((x, y))[:3])
            for x in range(0, view.get_width(), 12)
            for y in range(0, view.get_height(), 12)
        )
    assert set(face_colors.values()).issubset(visible)


def test_sky_drift_is_time_based_and_independent_of_canvas_orientation():
    steady=SkyboxRenderer(SKYBOXES_DIR,(320,180))
    moving=SkyboxRenderer(SKYBOXES_DIR,(320,180))
    for i in range(100):
        steady.update(10,'overworld')
        moving.update(10,'overworld',view_rotation=i%4,camera_offset=(i*80,-i*80),zoom=i+1)
    assert steady.current_yaw == pytest.approx(.8)
    assert moving.current_yaw == steady.current_yaw
    single=SkyboxRenderer(SKYBOXES_DIR,(320,180));single.update(1000,'overworld')
    assert single.current_yaw == pytest.approx(steady.current_yaw)
    before=moving.current_yaw
    moving.update(0,'end',view_rotation=3)
    assert moving.current_yaw == before


def test_manual_selection_wraps_crossfades_and_1080p_is_native_size():
    renderer = SkyboxRenderer(SKYBOXES_DIR, (1920, 1080))
    renderer.update(0, "nether", view_rotation=0)
    assert renderer.cycle("nether", 1) == "Ashen Dawn"
    assert renderer.previous_view == ("nether", 0, 0.0, 18.0)
    renderer.update(renderer.CROSSFADE_MS, "nether", view_rotation=0)
    assert renderer.previous_view is None
    target = pygame.Surface((1920, 1080))
    assert renderer.render(target, "nether")
    assert renderer._view("nether", 1, 0, 0).get_size() == (1920, 1080)
    assert renderer.cycle("nether", 1) == "Xen Sky 2"


def test_native_projection_matches_numpy_fallback_at_all_quarter_turns():
    from engine.native_acceleration import cubemap_rgb
    if cubemap_rgb(bytes(96*64*3),(96,64),(8,8),0,18,0.43) is None:
        pytest.skip('Optional native cubemap accelerator not built')
    import numpy as np
    atlas=pygame.Surface((96,64))
    for x in range(96):
        for y in range(64): atlas.set_at((x,y),(x*2,y*3,(x+y)%256))
    for yaw in (0,45,90,180,270):
        renderer=SkyboxRenderer(SKYBOXES_DIR,(240,180))
        renderer._atlas=lambda *_:atlas
        native=pygame.surfarray.array3d(renderer._view('overworld',0,yaw,18))
        renderer._views.clear()
        with patch('engine.native_acceleration.cubemap_rgb',return_value=None):
            portable=pygame.surfarray.array3d(renderer._view('overworld',0,yaw,18))
        # Nearest-neighbor half-texel tie rounding can differ by one texel.
        assert np.mean(np.any(native!=portable,axis=2))<0.02


def test_drift_prefetch_and_view_caches_stay_bounded():
    renderer=SkyboxRenderer(SKYBOXES_DIR,(160,90))
    target=pygame.Surface((160,90))
    for i in range(100):
        renderer.update(5000,'end',view_rotation=i%4)
        renderer.render(target,'end')
        assert len(renderer._views)<=renderer.CACHE_LIMIT
        assert len(renderer._prefetch)<=7
    assert not hasattr(renderer,'layers')
    if renderer._prefetch_worker:renderer._prefetch_worker.shutdown(wait=True)
