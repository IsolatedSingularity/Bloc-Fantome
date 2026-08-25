"""Shared UI typography for crisp, consistent Pygame text."""

from __future__ import annotations

import os
from typing import Optional

import pygame

from runtime_paths import FONTS_DIR


ZEKTON_RELATIVE_PATH = os.path.join("Zekton", "Zekton-Regular.otf")


class UIFont:
    """Delegate to a native Pygame font while tracking bold text consistently."""

    def __init__(self, font: pygame.font.Font, *, letter_spacing: int = 0):
        self._font = font
        self.letter_spacing = max(0, int(letter_spacing))

    def render(self, text, antialias, color, background=None, wraplength=0):
        text = str(text)
        if self.letter_spacing <= 0 or len(text) <= 1 or wraplength:
            if wraplength:
                try:
                    return self._font.render(
                        text, antialias, color, background, wraplength
                    )
                except TypeError:
                    pass
            return self._font.render(text, antialias, color, background)
        glyphs = [
            self._font.render(character, antialias, color, background)
            for character in text
        ]
        width = sum(glyph.get_width() for glyph in glyphs)
        width += self.letter_spacing * (len(glyphs) - 1)
        height = max((glyph.get_height() for glyph in glyphs), default=1)
        flags = pygame.SRCALPHA if background is None else 0
        result = pygame.Surface((max(1, width), max(1, height)), flags)
        if background is not None:
            result.fill(background)
        x = 0
        for glyph in glyphs:
            result.blit(glyph, (x, (height - glyph.get_height()) // 2))
            x += glyph.get_width() + self.letter_spacing
        return result

    def size(self, text):
        text = str(text)
        if not self.letter_spacing or len(text) <= 1:
            return self._font.size(text)
        glyph_sizes = [self._font.size(character) for character in text]
        width = sum(size[0] for size in glyph_sizes)
        width += self.letter_spacing * (len(glyph_sizes) - 1)
        return width, max((size[1] for size in glyph_sizes), default=1)

    def __getattr__(self, name):
        return getattr(self._font, name)


def zekton_path(fonts_dir: str = FONTS_DIR) -> str:
    """Return the user-licensed local Zekton font path."""
    return os.path.join(fonts_dir, ZEKTON_RELATIVE_PATH)


def load_ui_font(
    size: int,
    *,
    fonts_dir: str = FONTS_DIR,
    fallback: Optional[str] = None,
    bold: bool = False,
) -> UIFont:
    """Load Zekton at native size, falling back without scaling rendered text."""
    path = zekton_path(fonts_dir)
    try:
        font = pygame.font.Font(path if os.path.isfile(path) else fallback, int(size))
    except (OSError, pygame.error):
        font = pygame.font.Font(fallback, int(size))
    font.set_bold(bool(bold))
    return UIFont(font, letter_spacing=1 if bold else 0)


def render_tracked_text(
    font: pygame.font.Font,
    text: str,
    color,
    letter_spacing: int = 1,
) -> pygame.Surface:
    """Render native-size glyphs with restrained tracking between characters."""
    spacing = max(0, int(letter_spacing))
    if not text or spacing == 0:
        return font.render(text, True, color)
    glyphs = [font.render(character, True, color) for character in text]
    width = sum(glyph.get_width() for glyph in glyphs) + spacing * (len(glyphs) - 1)
    height = max(glyph.get_height() for glyph in glyphs)
    result = pygame.Surface((max(1, width), max(1, height)), pygame.SRCALPHA)
    x = 0
    for glyph in glyphs:
        result.blit(glyph, (x, (height - glyph.get_height()) // 2))
        x += glyph.get_width() + spacing
    return result
