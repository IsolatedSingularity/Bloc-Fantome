"""Render deterministic visual QA sheets for the refactored UI and models."""

import os
from pathlib import Path
import random
import sys
import time


os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Code"))

import pygame
import blocFantome as app_module
from splash import SplashScreen
from engine.app_icon import (
    render_explorer_icon_surface,
    render_runtime_icon_surface,
)


def save_capture(surface: pygame.Surface, path: Path) -> None:
    """Write through a temporary PNG so OneDrive cannot truncate QA captures."""
    temporary = path.with_name(f".{path.stem}.new.png")
    pygame.image.save(surface, temporary)
    for attempt in range(20):
        try:
            os.replace(temporary, path)
            return
        except PermissionError:
            if attempt == 19:
                raise
            time.sleep(0.05)


def render(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    pygame.display.set_mode((1200, 800))
    screen = pygame.display.get_surface()
    app = app_module.BlocFantome()
    if not app.assetManager.loadAllAssets():
        raise RuntimeError("Could not load visual-check assets")
    app.tutorialScreen.setAssets(
        app.assetManager.buttonNormal,
        app.assetManager.buttonHover,
        app.assetManager.checkboxTexture,
        app.assetManager.checkboxSelectedTexture,
        app.assetManager.clickSound,
        app.assetManager,
    )

    splash = SplashScreen(
        screen,
        pygame.time.Clock(),
        app_module.TEXTURES_DIR,
        app_module.FONTS_DIR,
        app_module.ICONS_DIR,
    )
    splash._draw_background(screen)
    screen.blit(splash.title, splash.title.get_rect(center=(600, 400)))
    save_capture(screen, output_dir / "splash.png")

    artwork = pygame.image.load(
        ROOT / "Assets" / "Icons" / "Respawn_Anchor.png"
    ).convert_alpha()

    save_capture(
        render_runtime_icon_surface(artwork, 256),
        output_dir / "app_icon.png",
    )

    icon_sheet = pygame.Surface((980, 330))
    icon_sheet.fill((34, 34, 38))
    icon_font = pygame.font.Font(None, 25)
    icon_sheet.blit(
        icon_font.render("Independent runtime and Explorer icon routes", True, (245, 245, 245)),
        (20, 14),
    )
    sizes = (16, 20, 24, 32, 40, 48, 64, 96, 128, 256)
    x = 20
    for size in sizes:
        icon = render_explorer_icon_surface(artwork, size)
        preview = pygame.transform.scale(icon, (96, 96))
        icon_sheet.blit(preview, (x, 55))
        label = icon_font.render(f"ICO {size}", True, (220, 220, 220))
        icon_sheet.blit(label, label.get_rect(center=(x + 48, 165)))
        x += 94
    runtime = render_runtime_icon_surface(artwork, 256)
    icon_sheet.blit(pygame.transform.scale(runtime, (128, 128)), (20, 190))
    icon_sheet.blit(icon_font.render("Taskbar/window", True, (220, 220, 220)), (160, 238))
    save_capture(icon_sheet, output_dir / "icon_routes.png")

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
    save_capture(sheet, output_dir / "block_models.png")

    special_sheet = pygame.Surface((1100, 730))
    special_sheet.fill((24, 20, 24))
    special_sheet.blit(
        font.render("Finished special blocks", True, (240, 235, 225)),
        (24, 18),
    )
    special_blocks = (
        app_module.BlockType.OXIDIZING_COPPER,
        app_module.BlockType.ENCHANTING_TABLE,
        app_module.BlockType.SCULK_SENSOR,
        app_module.BlockType.FIRE,
        app_module.BlockType.SOUL_FIRE,
        app_module.BlockType.MATRIX,
        app_module.BlockType.LANTERN,
        app_module.BlockType.SOUL_LANTERN,
        app_module.BlockType.CHAIN,
        app_module.BlockType.LADDER,
        app_module.BlockType.END_PORTAL_FRAME,
        app_module.BlockType.END_GATEWAY,
        app_module.BlockType.END_PORTAL,
        app_module.BlockType.CHEST,
        app_module.BlockType.GLASS,
    )
    for index, block_type in enumerate(special_blocks):
        sprite = app.assetManager.getBlockSprite(block_type)
        bounds = sprite.get_bounding_rect(min_alpha=1)
        cropped = sprite.subsurface(bounds)
        scale = min(132 / cropped.get_width(), 150 / cropped.get_height())
        model = pygame.transform.scale(
            cropped,
            (max(1, round(cropped.get_width() * scale)),
             max(1, round(cropped.get_height() * scale))),
        )
        column = index % 6
        row = index // 6
        x = 24 + column * 178
        y = 130 + row * 235
        special_sheet.blit(model, model.get_rect(center=(x + 72, y)))
        label = small.render(
            app_module.BLOCK_DEFINITIONS[block_type].name,
            True,
            (215, 205, 195),
        )
        special_sheet.blit(label, label.get_rect(center=(x + 72, y + 105)))
    save_capture(special_sheet, output_dir / "special_blocks.png")

    app._openLoadDialog()
    app.assetManager.drawBackground(screen)
    app.buildLibrary.render(screen)
    save_capture(screen, output_dir / "build_library.png")

    app.buildLibrary.close()

    # UI-pass captures: native-font HUD, movable tutorial states, centered
    # resize preview, and protected local terrain sculpting.
    app.currentDimension = app_module.DIMENSION_OVERWORLD
    app.world.setDimension(app_module.DIMENSION_OVERWORLD)
    app.world.resize(12, 12, 12, min_y=0, preserve=False)
    app._createInitialFloor()
    app._frameCurrentCanvas()
    app.renderer.offsetX = app.targetOffsetX
    app.renderer.offsetY = app.targetOffsetY
    app.hoveredCell = (6, 6, 1)
    app._render()
    save_capture(screen, output_dir / "hud_crisp_alignment.png")

    app.renderer.setViewRotation(1)
    app._render()
    save_capture(screen, output_dir / "hud_rotated_alignment.png")
    app.renderer.setViewRotation(0)

    tutorial = app.tutorialScreen
    tutorial.visible = True
    tutorial.minimized = False
    tutorial.currentStep = 0
    tutorial.panelX = 720
    tutorial.panelY = 130
    tutorial._layoutPanelControls()
    app._render()
    save_capture(screen, output_dir / "tutorial_window.png")
    tutorial.minimized = True
    app._render()
    save_capture(screen, output_dir / "tutorial_minimized.png")
    tutorial.visible = False
    tutorial.minimized = False

    app._beginTutorial(advanced=True)
    app._render()
    save_capture(screen, output_dir / "tutorial_advanced.png")
    for step_index, filename in (
        (6, "tutorial_advanced_mirror.png"),
        (8, "tutorial_advanced_liquids.png"),
        (11, "tutorial_advanced_end.png"),
    ):
        tutorial.currentStep = step_index
        app._onTutorialStepChange(step_index)
        app._render()
        save_capture(screen, output_dir / filename)
    tutorial.hide()

    app._render()
    growDimensions, _ = app._canvasResizeImpact(16)
    app._renderCanvasResizePreview(16, growDimensions)
    save_capture(screen, output_dir / "canvas_resize_preview.png")

    app.world.setBlock(5, 5, 1, app_module.BlockType.DIAMOND_BLOCK)
    app._render()
    terrain_seed = 8731
    terrain_plan = app._terrainNoisePlanForSeed(terrain_seed)
    app._renderTerrainNoisePreview(terrain_plan)
    save_capture(screen, output_dir / "terrain_noise_preview.png")
    app._applyLocalTerrainNoise(terrain_seed)
    app._frameCurrentCanvas()
    app.renderer.offsetX = app.targetOffsetX
    app.renderer.offsetY = app.targetOffsetY
    app._render()
    save_capture(screen, output_dir / "terrain_noise_local.png")

    app._generateStructurePreviews()
    app.blocksExpanded = True
    app.experimentalExpanded = False
    app.structuresExpanded = False
    app.inventoryScroll = 0
    for category in app_module.CATEGORY_ORDER:
        app.expandedCategories[category] = False
    app.assetManager.drawBackground(screen)
    app._renderPanel()
    save_capture(screen, output_dir / "blocks_categories.png")

    app.blocksExpanded = False
    app.experimentalExpanded = False
    app.structuresExpanded = False
    app.inventoryScroll = 0
    app.inventoryScrollTarget = 0
    app._renderPanel()
    app.inventoryScroll = app.maxScroll
    app.inventoryScrollTarget = app.maxScroll
    app.assetManager.drawBackground(screen)
    app._renderPanel()
    save_capture(screen, output_dir / "panel_controls.png")

    app.blocksExpanded = False
    app.experimentalExpanded = True
    app.rainEnabled = True
    app.snowEnabled = False
    app.cloudsEnabled = True
    app.lightingEnabled = True
    for dimension, filename in (
        (app_module.DIMENSION_OVERWORLD, "toggles_overworld.png"),
        (app_module.DIMENSION_NETHER, "toggles_nether.png"),
        (app_module.DIMENSION_END, "toggles_end.png"),
    ):
        app.currentDimension = dimension
        app.world.setDimension(dimension)
        app.inventoryScroll = 0
        app.assetManager.drawBackground(screen)
        app._renderPanel()
        save_capture(screen, output_dir / filename)
    app.rainEnabled = False

    app.snowEnabled = True
    for dimension, filename in (
        (app_module.DIMENSION_OVERWORLD, "toggles_overworld_snow.png"),
        (app_module.DIMENSION_NETHER, "toggles_nether_snow.png"),
        (app_module.DIMENSION_END, "toggles_end_snow.png"),
    ):
        app.currentDimension = dimension
        app.world.setDimension(dimension)
        app.inventoryScroll = 0
        app.assetManager.drawBackground(screen)
        app._renderPanel()
        save_capture(screen, output_dir / filename)
    app.snowEnabled = False

    app.skyboxesEnabled = True
    for dimension, filename in (
        (app_module.DIMENSION_OVERWORLD, "skybox_overworld_app.png"),
        (app_module.DIMENSION_NETHER, "skybox_nether_app.png"),
        (app_module.DIMENSION_END, "skybox_end_app.png"),
    ):
        app.currentDimension = dimension
        app.world.setDimension(dimension)
        app.skyboxRenderer.update(0, dimension)
        app._render()
        save_capture(screen, output_dir / filename)
    app.skyboxesEnabled = False

    app._toggleRedstoneLab()
    app._render()
    save_capture(screen, output_dir / "redstone_lab.png")
    app._toggleRedstoneLab()

    random.seed(1161)
    for dimension, effect, filename in (
        (app_module.DIMENSION_OVERWORLD, "rain", "weather_overworld_rain.png"),
        (app_module.DIMENSION_OVERWORLD, "snow", "weather_overworld_snow.png"),
        (app_module.DIMENSION_NETHER, "rain", "weather_nether_embers.png"),
        (app_module.DIMENSION_NETHER, "snow", "weather_nether_souls.png"),
        (app_module.DIMENSION_END, "rain", "weather_end_void.png"),
        (app_module.DIMENSION_END, "snow", "weather_end_shards.png"),
    ):
        app.currentDimension = dimension
        app.world.setDimension(dimension)
        app.world.resize(
            app_module.GRID_WIDTH,
            app_module.GRID_DEPTH,
            app_module.GRID_HEIGHT,
            min_y=0,
            preserve=False,
        )
        app._createInitialFloor()
        app._frameCurrentCanvas()
        app.renderer.offsetX = app.targetOffsetX
        app.renderer.offsetY = app.targetOffsetY
        if effect == "rain":
            app.rainEnabled = True
            app._startRain()
            app.splashSpawnTimer = 1000
            app._updateRain(16)
        else:
            app.snowEnabled = True
            app._startSnow()
            app.snowImpactTimer = 1000
            app._updateSnow(16)
        app._render()
        save_capture(screen, output_dir / filename)
        app.rainEnabled = False
        app.snowEnabled = False
        app._stopRain()
        app._stopSnow()

    app.currentDimension = app_module.DIMENSION_OVERWORLD
    app.world.setDimension(app_module.DIMENSION_OVERWORLD)

    app.blocksExpanded = False
    app.problemsExpanded = False
    app.experimentalExpanded = False
    app.structuresExpanded = True
    app.inventoryScroll = 0
    app.assetManager.drawBackground(screen)
    app._renderPanel()
    save_capture(screen, output_dir / "structure_panel.png")

    def capture_piston_door(key, prefix):
        app.world.resize(12, 12, 12, min_y=0, preserve=False)
        app.redstone.active_motions.clear()
        door = app_module.PREMADE_STRUCTURES[key]
        with app.world.bulkUpdate():
            for block in door["blocks"]:
                x, y, z, block_type, props = app_module._structureBlockParts(block)
                app.world.setBlock(x, y, z, block_type)
                if props is not None:
                    app.world.setBlockProperties(x, y, z, props.copy())
        app.redstone.mark_dirty()
        app.redstone.update(50)
        app.redstone.update(100)
        app._interactBlock(0, 2, 1)
        app.redstone.update(50)
        app.redstone.update(100)
        app._fitWorldToViewport(notify=False)
        app.renderer.offsetX = app.targetOffsetX
        app.renderer.offsetY = app.targetOffsetY
        app.tooltipTimer = 0
        app._render()
        save_capture(screen, output_dir / f"{prefix}_closed.png")
        app._interactBlock(0, 2, 1)
        app.redstone.update(50)
        app.redstone.update(50)
        app._render()
        save_capture(screen, output_dir / f"{prefix}_motion.png")
        app.redstone.update(50)
        app._render()
        save_capture(screen, output_dir / f"{prefix}_open.png")

    capture_piston_door("piston_door", "redstone_piston_door")
    capture_piston_door("flush_piston_door", "redstone_flush_door")

    # Dense connected clear glass: internal seams are culled while the stone
    # specimen remains visible through the pavilion.
    app.world.resize(16, 16, 16, min_y=0, preserve=False)
    with app.world.bulkUpdate():
        app._createInitialFloor()
        for x in range(3, 13):
            for y in range(3, 13):
                for z in range(1, 9):
                    if x in (3, 12) or y in (3, 12) or z in (1, 8):
                        app.world.setBlock(x, y, z, app_module.BlockType.GLASS)
        for z in range(1, 7):
            app.world.setBlock(8, 8, z, app_module.BlockType.REDSTONE_BLOCK)
    app._fitWorldToViewport(notify=False)
    app._render()
    save_capture(screen, output_dir / "connected_clear_glass.png")

    app._openWorldLibrary()
    app.assetManager.drawBackground(screen)
    app.worldLibrary.render(screen)
    save_capture(screen, output_dir / "world_library.png")
    app.worldLibrary.close()

    app.assetManager.drawBackground(screen)
    app.settingsMenuOpen = True
    app._renderSettingsMenu()
    save_capture(screen, output_dir / "settings.png")
    app.settingsMenuOpen = False

    for step_index, filename in (
        (10, "tutorial_nether.png"),
        (11, "tutorial_end.png"),
        (12, "tutorial_weather.png"),
        (13, "tutorial_lighting.png"),
    ):
        app._onTutorialStepChange(step_index)
        if step_index >= 12:
            app._fitWorldToViewport(notify=False)
        app.renderer.offsetX = app.targetOffsetX
        app.renderer.offsetY = app.targetOffsetY
        app._render()
        save_capture(screen, output_dir / filename)

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
    save_capture(screen, output_dir / "worlds_bastion.png")

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
    save_capture(screen, output_dir / "terrain_slice.png")


if __name__ == "__main__":
    destination = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "visual-checks"
    render(destination)
