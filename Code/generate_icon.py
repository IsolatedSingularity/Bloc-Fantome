"""Generate derived splash and taskbar assets from supplied branding."""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from engine.app_icon import (
    render_ancient_city_background_surface,
    render_runtime_icon_surface,
    render_splash_background_surface,
)


# Include common Windows DPI-scaled shell/taskbar sizes instead of asking the
# shell to interpolate one of the neighbouring resources.
SIZES = (16, 20, 24, 32, 40, 48, 64, 96, 128, 256)


def generate(output_path: Path) -> None:
    pygame.init()
    try:
        project = Path(__file__).resolve().parent.parent
        icon_dir = project / "Assets" / "Icons"
        artwork_path = icon_dir / "Respawn_Anchor.png"
        deepslate_path = project / "Assets" / "Texture Hub" / "blocks" / "deepslate.png"
        artwork = pygame.image.load(str(artwork_path)) if artwork_path.is_file() else None
        deepslate = pygame.image.load(str(deepslate_path)) if deepslate_path.is_file() else None
        output_path.parent.mkdir(parents=True, exist_ok=True)
        pygame.image.save(
            render_splash_background_surface(deepslate),
            output_path.parent / "Splash_Background_Deepslate.png",
        )
        ancient_names = (
            "deepslate_tiles.png",
            "cracked_deepslate_tiles.png",
            "sculk.png",
            "sculk_catalyst_top.png",
            "reinforced_deepslate_top.png",
            "sculk_shrieker_top.png",
        )
        ancient_textures = []
        for name in ancient_names:
            path = project / "Assets" / "Texture Hub" / "blocks" / name
            ancient_textures.append(pygame.image.load(str(path)) if path.is_file() else None)
        pygame.image.save(
            render_ancient_city_background_surface(ancient_textures),
            output_path.parent / "Splash_Background_Ancient_City.png",
        )
        pygame.image.save(
            render_runtime_icon_surface(artwork, 256),
            output_path.parent / "Taskbar_Respawn_Anchor.png",
        )
    finally:
        pygame.quit()


if __name__ == "__main__":
    generate(Path(__file__).resolve().parent.parent / "Assets" / "Icons" / "Respawn_Anchor.ico")
