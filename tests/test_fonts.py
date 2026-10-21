import os

import pygame

from ui.fonts import load_ui_font


def setup_module():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.font.init()


def test_semibold_ui_fonts_use_native_face_with_matching_metrics():
    bold = load_ui_font(24, bold=True)
    regular = load_ui_font(24)
    text = "Advanced Tutorial"
    rendered = bold.render(text, True, (255, 255, 255))
    assert bold.letter_spacing == 0
    assert regular.letter_spacing == 0
    assert rendered.get_size() == bold.size(text)
    assert not bold.get_bold()  # Real installed weight, no synthetic emboldening.


def test_text_scale_rerasterizes_existing_fonts():
    from ui.fonts import set_text_scale
    font=load_ui_font(18)
    native=font._font
    try:
        set_text_scale(1.25)
        assert font.size('Library')[1]>native.size('Library')[1]
        assert font._font is not native
        assert font.render('Library',True,'white').get_size()==font.size('Library')
    finally:set_text_scale(1)
