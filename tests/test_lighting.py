import os
from pathlib import Path
import sys
import unittest


os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Code"))

try:
    import pygame
    from engine.lighting import shade_sprite
except ImportError:
    pygame = None
    shade_sprite = None


@unittest.skipIf(pygame is None, "Pygame runtime is not installed")
class LightingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.display.init()
        pygame.display.set_mode((1, 1))

    def test_shading_preserves_alpha_and_dims_rgb(self):
        sprite = pygame.Surface((8, 8), pygame.SRCALPHA)
        sprite.fill((200, 160, 120, 0))
        sprite.set_at((4, 4), (200, 160, 120, 255))
        shaded = shade_sprite(sprite, 0.5, 0, (255, 200, 150))
        self.assertEqual(shaded.get_at((0, 0)).a, 0)
        center = shaded.get_at((4, 4))
        self.assertEqual(center.a, 255)
        self.assertLess(center.r, 200)


if __name__ == "__main__":
    unittest.main()
