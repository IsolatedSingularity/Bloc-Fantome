import os

import pygame

from ui.fonts import load_ui_font


def setup_module():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.font.init()


def test_bold_ui_fonts_use_native_one_pixel_tracking_with_matching_metrics():
    bold = load_ui_font(24, bold=True)
    regular = load_ui_font(24)
    text = "Advanced Tutorial"
    rendered = bold.render(text, True, (255, 255, 255))
    assert bold.letter_spacing == 1
    assert regular.letter_spacing == 0
    assert rendered.get_size() == bold.size(text)
    assert bold.size(text)[0] > regular.size(text)[0]
