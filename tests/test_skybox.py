import os

import pygame

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


def test_renderer_builds_native_cubemap_views_without_automatic_motion():
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
    for _ in range(20):
        renderer.update(
            16,
            renderer.current_dimension,
            view_rotation=renderer.view_rotation,
            camera_offset=(400.0 + _ * 80.0, -250.0 + _ * 40.0),
            zoom=0.4 + _ * 0.1,
        )
        assert renderer.render(target, renderer.current_dimension)
    assert pygame.image.tostring(before, "RGB") == pygame.image.tostring(target, "RGB")


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


def test_camera_quarter_turn_tweens_through_perspective_cube_views():
    renderer = SkyboxRenderer(SKYBOXES_DIR, (320, 180))
    renderer.update(0, "overworld", view_rotation=0)
    first = renderer._view("overworld", renderer.current_index, 0)
    renderer.update(16, "overworld", view_rotation=1)
    assert renderer.previous_view is None
    assert 0.0 < renderer.current_yaw < 90.0
    renderer.update(renderer.ROTATION_MS, "overworld", view_rotation=1)
    assert renderer.current_yaw == 90.0
    second = renderer._view("overworld", renderer.current_index, 90)
    assert pygame.image.tostring(first, "RGB") != pygame.image.tostring(second, "RGB")


def test_manual_selection_wraps_crossfades_and_1080p_is_native_size():
    renderer = SkyboxRenderer(SKYBOXES_DIR, (1920, 1080))
    renderer.update(0, "nether", view_rotation=0)
    assert renderer.cycle("nether", 1) == "Ashen Dawn"
    assert renderer.previous_view == ("nether", 0, 0.0, 0.0)
    renderer.update(renderer.CROSSFADE_MS, "nether", view_rotation=0)
    assert renderer.previous_view is None
    target = pygame.Surface((1920, 1080))
    assert renderer.render(target, "nether")
    assert renderer._view("nether", 1, 0, 0).get_size() == (1920, 1080)
    assert renderer.cycle("nether", 1) == "Xen Sky 2"
