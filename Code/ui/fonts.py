"""Shared UI typography for crisp, consistent Pygame text."""

from __future__ import annotations

import os
from typing import Optional

import pygame

from runtime_paths import FONTS_DIR


ZEKTON_RELATIVE_PATH = os.path.join("Zekton", "Zekton-Regular.otf")


def zekton_path(fonts_dir: str = FONTS_DIR) -> str:
    """Return the user-licensed local Zekton font path."""
    return os.path.join(fonts_dir, ZEKTON_RELATIVE_PATH)


def load_ui_font(
    size: int,
    *,
    fonts_dir: str = FONTS_DIR,
    fallback: Optional[str] = None,
    bold: bool = False,
) -> pygame.font.Font:
    """Load Zekton at native size, falling back without scaling rendered text."""
    path = zekton_path(fonts_dir)
    try:
        font = pygame.font.Font(path if os.path.isfile(path) else fallback, int(size))
    except (OSError, pygame.error):
        font = pygame.font.Font(fallback, int(size))
    font.set_bold(bool(bold))
    return font


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
