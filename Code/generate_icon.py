"""Generate Bloc Fantôme's independent splash, taskbar, and Explorer assets."""

from __future__ import annotations

import io
import os
from pathlib import Path
import struct

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from engine.app_icon import (
    render_explorer_icon_surface,
    render_runtime_icon_surface,
    render_splash_background_surface,
    render_splash_logo_surface,
)


# Include common Windows DPI-scaled shell/taskbar sizes instead of asking the
# shell to interpolate one of the neighbouring resources.
SIZES = (16, 20, 24, 32, 40, 48, 64, 96, 128, 256)


def _png_bytes(surface: pygame.Surface) -> bytes:
    stream = io.BytesIO()
    pygame.image.save(surface, stream, "icon.png")
    return stream.getvalue()


def _render_ico_entry(texture: pygame.Surface | None, size: int) -> pygame.Surface:
    """Render one native Explorer resource without non-uniform correction."""
    return render_explorer_icon_surface(texture, size)


def generate(output_path: Path) -> None:
    pygame.init()
    try:
        project = Path(__file__).resolve().parent.parent
        texture_path = project / "Assets" / "Texture Hub" / "blocks" / "end_stone.png"
        texture = pygame.image.load(str(texture_path)) if texture_path.is_file() else None
        output_path.parent.mkdir(parents=True, exist_ok=True)
        pygame.image.save(
            render_splash_logo_surface(texture, 288),
            output_path.parent / "Splash_End_Stone.png",
        )
        pygame.image.save(
            render_splash_background_surface(texture),
            output_path.parent / "Splash_Background_End_Stone.png",
        )
        pygame.image.save(
            render_runtime_icon_surface(texture, 256),
            output_path.parent / "Taskbar_End_Stone.png",
        )
        images = [_png_bytes(_render_ico_entry(texture, size)) for size in SIZES]

        header_size = 6 + 16 * len(images)
        offset = header_size
        entries = []
        for size, payload in zip(SIZES, images):
            encoded_size = 0 if size == 256 else size
            entries.append(struct.pack(
                "<BBBBHHII", encoded_size, encoded_size, 0, 0,
                1, 32, len(payload), offset,
            ))
            offset += len(payload)

        with output_path.open("wb") as handle:
            handle.write(struct.pack("<HHH", 0, 1, len(images)))
            handle.writelines(entries)
            handle.writelines(images)
    finally:
        pygame.quit()


if __name__ == "__main__":
    generate(Path(__file__).resolve().parent.parent / "Assets" / "Icons" / "End_Stone.ico")
