"""Render deterministic visual QA sheets for the refactored UI and models."""

import os
from pathlib import Path
import random
import sys


os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Code"))

import pygame
import blocFantome as app_module
from splash import SplashScreen
from engine.app_icon import render_app_icon_surface


def render(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    pygame.display.set_mode((1200, 800))
    screen = pygame.display.get_surface()
    app = app_module.BlocFantome()
    if not app.assetManager.loadAllAssets():
        raise RuntimeError("Could not load visual-check assets")

    splash = SplashScreen(
        screen,
        pygame.time.Clock(),
        app_module.TEXTURES_DIR,
        app_module.FONTS_DIR,
        app_module.ICONS_DIR,
    )
    splash._draw_background(screen)
    screen.blit(splash.icon, splash.icon.get_rect(center=(600, 335)))
    title = splash.title_font.render("Bloc Fantôme", True, (255, 255, 255))
    screen.blit(title, title.get_rect(center=(600, 585)))
    pygame.image.save(screen, output_dir / "splash.png")

    pygame.image.save(
        render_app_icon_surface(splash.texture, 256),
        output_dir / "app_icon.png",
    )

    sheet = pygame.Surface((1100, 620))
    sheet.fill((24, 20, 24))
    font = pygame.font.Font(None, 25)
    small = pygame.font.Font(None, 20)
    sheet.blit(font.render("Source-shaped stair variants", True, (240, 235, 225)), (24, 18))
    stair = app_module.BlockType.OAK_STAIRS
    for row, half in enumerate(app_module.SlabPosition):
        for column, shape in enumerate(app_module.StairShape):
            sprite = app.assetManager.getStairSprite(
                stair, app_module.Facing.EAST, shape, half
            )
            large = pygame.transform.scale(sprite, (128, 140))
            x, y = 24 + column * 205, 50 + row * 205
            sheet.blit(large, (x + 32, y))
            label = small.render(f"{half.name} {shape.name}", True, (215, 205, 195))
            sheet.blit(label, (x, y + 148))

    sheet.blit(font.render("Two-cell door state", True, (240, 235, 225)), (24, 455))
    for column, (facing, opened, hinge) in enumerate((
        (app_module.Facing.EAST, False, app_module.DoorHinge.LEFT),
        (app_module.Facing.SOUTH, False, app_module.DoorHinge.RIGHT),
        (app_module.Facing.EAST, True, app_module.DoorHinge.LEFT),
        (app_module.Facing.SOUTH, True, app_module.DoorHinge.RIGHT),
    )):
        x = 250 + column * 190
        for offset, half in enumerate((app_module.DoorHalf.UPPER, app_module.DoorHalf.LOWER)):
            sprite = app.assetManager.getDoorSprite(
                app_module.BlockType.OAK_DOOR, facing, opened, hinge, half
            )
            sheet.blit(sprite, (x, 455 + offset * 38))
        label = small.render(
            f"{facing.name} {'OPEN' if opened else 'CLOSED'} {hinge.name}",
            True,
            (215, 205, 195),
        )
        sheet.blit(label, (x - 22, 580))
    pygame.image.save(sheet, output_dir / "block_models.png")

    app._openLoadDialog()
    app.assetManager.drawBackground(screen)
    app.buildLibrary.render(screen)
    pygame.image.save(screen, output_dir / "build_library.png")

    app.buildLibrary.close()
    app._generateStructurePreviews()
    app.blocksExpanded = False
    app.problemsExpanded = False
    app.experimentalExpanded = False
    app.structuresExpanded = True
    app.inventoryScroll = 0
    app.assetManager.drawBackground(screen)
    app._renderPanel()
    pygame.image.save(screen, output_dir / "structure_panel.png")

    app._openWorldLibrary()
    app.assetManager.drawBackground(screen)
    app.worldLibrary.render(screen)
    pygame.image.save(screen, output_dir / "world_library.png")
    app.worldLibrary.close()

    # README art: a full editor frame, not an isolated renderer export.
    app.structuresExpanded = False
    app.worldsExpanded = False
    app._loadBuildingFromPath(
        str(Path(app_module.WORLDS_DIR) / "bastion_bridge_1161.json.gz"),
        silent=True,
    )
    app.zoomLevel = 0.25
    app.renderer.setZoom(0.25)
    app._centerOnCell(128, 128, 48)
    app.renderer.offsetX = app.targetOffsetX
    app.renderer.offsetY = app.targetOffsetY
    app._render()
    pygame.image.save(screen, output_dir / "worlds_bastion.png")

    random.seed(1161)
    app._switchDimension(app_module.DIMENSION_OVERWORLD)
    app._generateTerrainSlice()
    app.zoomLevel = 0.5
    app.renderer.setZoom(0.5)
    center_height = app.world.getHighestBlock(64, 64)
    app._centerOnCell(64, 64, center_height)
    app.renderer.offsetX = app.targetOffsetX
    app.renderer.offsetY = app.targetOffsetY
    app.experimentalExpanded = True
    app.lightingEnabled = True
    app.lightingDirty = True
    app.inventoryScroll = 0
    app._render()
    pygame.image.save(screen, output_dir / "terrain_slice.png")


if __name__ == "__main__":
    destination = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "visual-checks"
    render(destination)
