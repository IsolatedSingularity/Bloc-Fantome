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


def test_all_supplied_skies_are_uniquely_distributed_across_dimensions():
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


def test_renderer_smoothscales_lazily_rotates_and_bounds_its_cache():
    renderer = SkyboxRenderer(SKYBOXES_DIR, (320, 180))
    target = pygame.Surface((320, 180), pygame.SRCALPHA)
    for dimension, variants in SKYBOX_VARIANTS.items():
        assert renderer.available(dimension)
        for index in range(len(variants)):
            renderer.current_index = index
            assert renderer.render(target, dimension)
    assert len(renderer._panoramas) == 3
    assert all(surface.get_height() == 180 for surface in renderer._panoramas.values())

    start = renderer.rotation
    renderer.update(16, "overworld")
    assert renderer.rotation > start


def test_automatic_swap_and_celestial_mapping_crossfade_in_time():
    renderer = SkyboxRenderer(SKYBOXES_DIR, (320, 180))
    renderer.update(0, "nether")
    renderer.update(renderer.AUTO_SWAP_MS, "nether")
    assert renderer.current_index == 1
    assert renderer.previous_index == 0
    renderer.update(renderer.CROSSFADE_MS, "nether")
    assert renderer.previous_index is None

    renderer.update(0, "overworld", celestial_enabled=True, celestial_angle=500)
    assert renderer.current_index == 2
    renderer.update(0, "overworld", celestial_enabled=True, celestial_angle=330)
    assert renderer.current_index == 1
