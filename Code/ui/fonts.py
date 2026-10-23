"""Shared UI typography for crisp, consistent Pygame text."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import pygame

from runtime_paths import FONTS_DIR


ZEKTON_RELATIVE_PATH = os.path.join("Zekton", "Zekton-Regular.otf")
TEXT_SCALE = 1.0


def set_text_scale(scale):
    """Change native rasterization size, never rescale rendered glyphs."""
    global TEXT_SCALE
    TEXT_SCALE = max(1.0, min(2.0, float(scale)))


def font_source(bold=False, fonts_dir=FONTS_DIR, fallback=None, italic=False, experiment=True):
    # Production Plex; explicit Segoe remains useful for comparison evidence.
    experiment=os.environ.get('BLOC_FONT_EXPERIMENT','plex-light') if experiment else ''
    if experiment in ('plex','plex-light') and not italic:
        weight='Text' if bold else 'Regular'
        path=Path(__file__).with_name('fonts')/'IBMPlexSans'/f'IBMPlexSans-{weight}.ttf'
        if path.is_file():return str(path)
    # SDL can resolve the family name to Segoe UI Light. Choose the installed
    # regular/semibold face explicitly. Never distribute Microsoft font files.
    installed = os.path.join(os.environ.get('WINDIR', 'C:/Windows'), 'Fonts',
                             'segoeuii.ttf' if italic else 'seguisb.ttf' if bold else 'segoeui.ttf')
    if os.path.isfile(installed): return installed
    matched = pygame.font.match_font('segoeuisemibold' if bold else 'segoeui')
    if matched: return matched
    licensed = zekton_path(fonts_dir)
    return licensed if os.path.isfile(licensed) else fallback


class UIFont:
    """Delegate to a native Pygame font while tracking bold text consistently."""

    def __init__(self, font: pygame.font.Font, *, letter_spacing: int = 0,
                 path=None, base_size=None):
        self._native = font
        self.path = path
        self.base_size = base_size
        self._scale = TEXT_SCALE
        self.letter_spacing = max(0, int(letter_spacing))

    @property
    def _font(self):
        if self.base_size is not None and self._scale != TEXT_SCALE:
            self._native = pygame.font.Font(self.path, round(self.base_size * TEXT_SCALE))
            self._scale = TEXT_SCALE
        return self._native

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
    italic: bool = False,
    experiment: bool = True,
) -> UIFont:
    """Resolve bundled Plex at final size, with OS and licensed fallbacks."""
    path = font_source(bold, fonts_dir, fallback, italic, experiment)
    if experiment and os.environ.get('BLOC_FONT_EXPERIMENT','plex-light')=='plex-light' and size>=20 and not italic:
        light=Path(__file__).with_name('fonts')/'IBMPlexSans'/'IBMPlexSans-Light.ttf'
        if light.is_file():path=str(light)
    try:
        font = pygame.font.Font(path, round(size * TEXT_SCALE))
    except (OSError, pygame.error):
        path = fallback
        font = pygame.font.Font(path, round(size * TEXT_SCALE))
    return UIFont(font, path=path, base_size=size)


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
