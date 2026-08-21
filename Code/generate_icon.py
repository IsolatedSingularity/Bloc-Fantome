"""Generate Bloc Fantome's padded multi-resolution Windows icon."""

from __future__ import annotations

import io
import os
from pathlib import Path
import struct

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from engine.app_icon import render_app_icon_surface


SIZES = (16, 24, 32, 48, 64, 128, 256)


def _png_bytes(surface: pygame.Surface) -> bytes:
    stream = io.BytesIO()
    pygame.image.save(surface, stream, "icon.png")
    return stream.getvalue()


def generate(output_path: Path) -> None:
    pygame.init()
    try:
        project = Path(__file__).resolve().parent.parent
        texture_path = project / "Assets" / "Texture Hub" / "blocks" / "end_stone.png"
        texture = pygame.image.load(str(texture_path)) if texture_path.is_file() else None
        images = [_png_bytes(render_app_icon_surface(texture, size)) for size in SIZES]

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

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("wb") as handle:
            handle.write(struct.pack("<HHH", 0, 1, len(images)))
            handle.writelines(entries)
            handle.writelines(images)
    finally:
        pygame.quit()


if __name__ == "__main__":
    generate(Path(__file__).resolve().parent.parent / "Assets" / "Icons" / "End_Stone.ico")
