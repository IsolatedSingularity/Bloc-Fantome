"""Render deterministic visual QA sheets for the refactored UI and models."""

import os
from pathlib import Path
import random
import sys
import time
from unittest.mock import patch

from PIL import Image


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


def save_gif(frames: list[pygame.Surface], path: Path, duration: int = 750) -> None:
    """Save a small, palette-bounded README animation from native frames."""
    images = []
    for surface in frames:
        rgb = pygame.image.tostring(surface, "RGB")
        image = Image.frombytes("RGB", surface.get_size(), rgb)
        image.thumbnail((960, 640), Image.Resampling.LANCZOS)
        images.append(image.quantize(colors=192, method=Image.Quantize.MEDIANCUT))
    images[0].save(
        path,
        save_all=True,
        append_images=images[1:],
        duration=duration,
        loop=0,
        optimize=True,
        disposal=2,
    )


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

    # Redstone component sheet: keep the source-shaped models visible in every
    # release QA run so a piston cycle or camera rotation cannot silently
    # regress into a full cube/incorrect face. These are the same cached
    # sprites used by the Lab, cropped only for presentation.
    redstone_sheet = pygame.Surface((1100, 560))
    redstone_sheet.fill((24, 20, 24))
    redstone_sheet.blit(
        font.render("Java 1.16.1 redstone component states", True, (240, 235, 225)),
        (24, 18),
    )
    redstone_entries = (
        ("DUST isolated", app.assetManager.getDetailSprite(
            app_module.BlockType.REDSTONE_DUST, app_module.Facing.SOUTH,
            False, app_module.SlabPosition.BOTTOM, powered=False, connections=0,
        )),
        ("DUST straight", app.assetManager.getDetailSprite(
            app_module.BlockType.REDSTONE_DUST, app_module.Facing.SOUTH,
            False, app_module.SlabPosition.BOTTOM, powered=True, power=15,
            connections=0b0101,
        )),
        ("DUST corner", app.assetManager.getDetailSprite(
            app_module.BlockType.REDSTONE_DUST, app_module.Facing.SOUTH,
            False, app_module.SlabPosition.BOTTOM, powered=True, power=15,
            connections=0b0011,
        )),
        ("REPEATER 1t", app.assetManager.getDetailSprite(
            app_module.BlockType.REPEATER, app_module.Facing.SOUTH,
            False, app_module.SlabPosition.BOTTOM, delay=1,
        )),
        ("REPEATER 4t ON", app.assetManager.getDetailSprite(
            app_module.BlockType.REPEATER, app_module.Facing.SOUTH,
            False, app_module.SlabPosition.BOTTOM, delay=4, powered=True,
        )),
        ("REPEATER LOCKED", app.assetManager.getDetailSprite(
            app_module.BlockType.REPEATER, app_module.Facing.SOUTH,
            False, app_module.SlabPosition.BOTTOM, delay=2, locked=True,
        )),
        ("LEVER OFF", app.assetManager.getDetailSprite(
            app_module.BlockType.LEVER, app_module.Facing.SOUTH,
            False, app_module.SlabPosition.BOTTOM, powered=False,
        )),
        ("LEVER ON", app.assetManager.getDetailSprite(
            app_module.BlockType.LEVER, app_module.Facing.SOUTH,
            False, app_module.SlabPosition.BOTTOM, powered=True,
        )),
        ("PISTON RETRACTED", app.assetManager.getDetailSprite(
            app_module.BlockType.PISTON, app_module.Facing.EAST,
            False, app_module.SlabPosition.BOTTOM,
        )),
        ("PISTON EXTENDED", app.assetManager.getDetailSprite(
            app_module.BlockType.PISTON, app_module.Facing.EAST,
            True, app_module.SlabPosition.BOTTOM,
        )),
        ("STICKY EXTENDED", app.assetManager.getDetailSprite(
            app_module.BlockType.STICKY_PISTON, app_module.Facing.EAST,
            True, app_module.SlabPosition.BOTTOM,
        )),
        ("HEAD STICKY", app.assetManager.getDetailSprite(
            app_module.BlockType.PISTON_HEAD, app_module.Facing.EAST,
            False, app_module.SlabPosition.BOTTOM, sticky=True,
        )),
    )
    for index, (label_text, sprite) in enumerate(redstone_entries):
        bounds = sprite.get_bounding_rect(min_alpha=1)
        cropped = sprite.subsurface(bounds)
        scale = min(142 / max(1, cropped.get_width()), 122 / max(1, cropped.get_height()))
        model = pygame.transform.scale(
            cropped,
            (max(1, round(cropped.get_width() * scale)),
             max(1, round(cropped.get_height() * scale))),
        )
        column = index % 6
        row = index // 6
        x = 24 + column * 178
        y = 60 + row * 245
        redstone_sheet.blit(model, model.get_rect(center=(x + 72, y + 58)))
        label = small.render(label_text, True, (215, 205, 195))
        redstone_sheet.blit(label, label.get_rect(center=(x + 72, y + 142)))
    save_capture(redstone_sheet, output_dir / "redstone_components.png")

    orientation_sheet = pygame.Surface((960, 700))
    orientation_sheet.fill((24, 20, 24))
    orientation_sheet.blit(
        font.render("Four-way redstone orientation", True, (240, 235, 225)),
        (24, 18),
    )
    for column, facing in enumerate((
        app_module.Facing.NORTH, app_module.Facing.EAST,
        app_module.Facing.SOUTH, app_module.Facing.WEST,
    )):
        heading = small.render(facing.name, True, (238, 91, 69))
        orientation_sheet.blit(heading, heading.get_rect(center=(120 + column * 235, 66)))
        models = (
            ("REPEATER", app.assetManager.getDetailSprite(
                app_module.BlockType.REPEATER, facing, False,
                app_module.SlabPosition.BOTTOM, delay=3, powered=True,
            )),
            ("PISTON", app.assetManager.getDetailSprite(
                app_module.BlockType.PISTON, facing, False,
                app_module.SlabPosition.BOTTOM,
            )),
            ("EXTENDED + HEAD", app.assetManager.getDetailSprite(
                app_module.BlockType.STICKY_PISTON, facing, True,
                app_module.SlabPosition.BOTTOM,
            )),
        )
        for row, (label_text, sprite) in enumerate(models):
            bounds = sprite.get_bounding_rect(min_alpha=1)
            cropped = sprite.subsurface(bounds)
            scale = min(170 / max(1, cropped.get_width()), 145 / max(1, cropped.get_height()))
            model = pygame.transform.scale(
                cropped,
                (max(1, round(cropped.get_width() * scale)),
                 max(1, round(cropped.get_height() * scale))),
            )
            center = (120 + column * 235, 155 + row * 195)
            orientation_sheet.blit(model, model.get_rect(center=center))
            label = small.render(label_text, True, (215, 205, 195))
            orientation_sheet.blit(label, label.get_rect(center=(center[0], center[1] + 82)))
    save_capture(orientation_sheet, output_dir / "redstone_orientations.png")

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
        app.skyboxRenderer.update(0, dimension, view_rotation=app.renderer.viewRotation)
        app._render()
        save_capture(screen, output_dir / filename)
    app.skyboxesEnabled = False

    app._toggleRedstoneLab()
    app._render()
    save_capture(screen, output_dir / "redstone_lab.png")
    for turns in (1, 2, 3):
        app.renderer.viewRotation = turns
        app._fitWorldToViewport(notify=False)
        app.renderer.offsetX = app.targetOffsetX
        app.renderer.offsetY = app.targetOffsetY
        app._render()
        save_capture(screen, output_dir / f"redstone_lab_rotation_{turns}.png")
    app.renderer.viewRotation = 0
    app._fitWorldToViewport(notify=False)
    app.renderer.offsetX = app.targetOffsetX
    app.renderer.offsetY = app.targetOffsetY
    app._setInteractionMode(True)
    app.hoveredSourceBlock = (9, 10, 2)
    app.hoveredFace = "top"
    app.hoveredCell = (9, 10, 3)
    app._render()
    save_capture(screen, output_dir / "redstone_lab_hand_cursor.png")
    app._setInteractionMode(False)
    # Explicit transition QA: the Lab's temporary palette/stage must not leak
    # into the World Map or back into the live editor's inventory/grid state.
    app._openWorldMap()
    app._render()
    save_capture(screen, output_dir / "redstone_lab_to_world_map.png")
    app._exitWorldMap()
    app._render()
    save_capture(screen, output_dir / "redstone_lab_return_to_build.png")

    # World Map product art: four dedicated selector hubs, an objective, and
    # the exact selector marker behavior framed inside the real editor window.
    map_frames = []
    app._openWorldMap()
    for dimension in app_module.WORLD_MAP_DIMENSIONS:
        app._switchWorldMapHub(dimension)
        app.renderer.offsetX = app.targetOffsetX
        app.renderer.offsetY = app.targetOffsetY
        app._render()
        frame = screen.copy()
        map_frames.append(frame)
        save_capture(frame, output_dir / f"world_map_{dimension}.png")
        if dimension == app_module.DIMENSION_OVERWORLD:
            # Capture the recovered WorldBuilder 200 ms hover-swap frame and
            # mission copy beneath the palette-correct selector.
            app.worldMapView._hovered_node = 1
            with patch("pygame.time.get_ticks", return_value=200):
                app._render()
            save_capture(screen, output_dir / "world_map_overworld_hover.png")
            app.worldMapView._hovered_node = None
    montage = pygame.Surface((1200, 322))
    montage.fill((17, 18, 23))
    montage_font = app_module.load_ui_font(24, bold=True)
    for index, (dimension, frame) in enumerate(zip(app_module.WORLD_MAP_DIMENSIONS, map_frames)):
        panel = pygame.transform.smoothscale(frame, (288, 192))
        x = 6 + index * 296
        montage.blit(panel, (x, 62))
        label = montage_font.render(dimension.upper(), True, (246, 231, 179))
        montage.blit(label, label.get_rect(center=(x + 144, 32)))
        pygame.draw.rect(montage, (126, 130, 142), (x, 62, 288, 192), 1)
    save_capture(montage, output_dir / "world_map_montage.png")

    for dimension in app_module.WORLD_MAP_DIMENSIONS:
        if dimension == "ocean":
            continue
        for route_index in range(2):
            app._switchWorldMapHub(dimension)
            app._startWorldMapLevel(route_index)
            app.renderer.offsetX = app.targetOffsetX
            app.renderer.offsetY = app.targetOffsetY
            app._render()
            filename = f"world_map_objective_{dimension}_{route_index + 1}.png"
            save_capture(screen, output_dir / filename)
            if dimension == app_module.DIMENSION_OVERWORLD and route_index == 0:
                save_capture(screen, output_dir / "world_map_objective.png")
    app._exitWorldMap()

    # Native 1080p regression: rebuild sprites at the resized zoom and capture
    # the campaign HUD without scaling a 1200x800 framebuffer.
    app._applyWindowSize(1920, 1080)
    screen = app.screen
    app._openWorldMap()
    for dimension in app_module.WORLD_MAP_DIMENSIONS:
        app._switchWorldMapHub(dimension)
        app.renderer.offsetX = app.targetOffsetX
        app.renderer.offsetY = app.targetOffsetY
        app._render()
        save_capture(screen, output_dir / f"world_map_{dimension}_1080p.png")
    app._switchWorldMapHub(app_module.DIMENSION_OVERWORLD)
    app._startWorldMapLevel(0)
    app.renderer.offsetX = app.targetOffsetX
    app.renderer.offsetY = app.targetOffsetY
    app._render()
    save_capture(screen, output_dir / "world_map_objective_1080p.png")
    app._exitWorldMap()
    app._applyWindowSize(1200, 800)
    screen = app.screen

    # Compact hover demonstrations for README: the held terrain seed preview
    # and the paired center-preserving canvas controls.
    app.currentDimension = app_module.DIMENSION_OVERWORLD
    app.world.setDimension(app_module.DIMENSION_OVERWORLD)
    app.world.resize(32, 32, 24, min_y=0, preserve=False)
    app._createInitialFloor()
    app._fitWorldToViewport(notify=False)
    app.renderer.offsetX = app.targetOffsetX
    app.renderer.offsetY = app.targetOffsetY
    app._render()
    terrain_frames = [screen.copy()]
    with patch.object(pygame.mouse, "get_pos", return_value=app.terrainNoiseButtonRect.center):
        app._render()
        terrain_frames.append(screen.copy())
    terrain_frames.append(terrain_frames[0])
    save_gif(terrain_frames, output_dir / "terrain_hover.gif")

    control_frames = []
    for point in (
        (-100, -100), app.growCanvasButtonRect.center,
        app.shrinkCanvasButtonRect.center, (-100, -100),
    ):
        with patch.object(pygame.mouse, "get_pos", return_value=point):
            app._render()
            control_frames.append(screen.copy())
    save_gif(control_frames, output_dir / "canvas_controls.gif", duration=650)

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

    app._toggleRedstoneLab()
    app._setInteractionMode(False)
    app._render()
    save_capture(screen, output_dir / "redstone_lab_signal_build.png")
    app._loadRedstoneLabCircuit("redstone_ring_riser")
    app._setInteractionMode(True)
    app._render()
    save_capture(screen, output_dir / "redstone_lab_ring_test.png")
    app._setInteractionMode(False)
    app._toggleRedstoneLab()

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

    # README dimension art: renderer-only captures in the structure's actual
    # dimension. These intentionally omit the panel, HUD, hotbar, and controls.
    def capture_clean_dimension(world_name: str, dimension: str, filename: str) -> None:
        app._loadBuildingFromPath(
            str(Path(app_module.WORLDS_DIR) / world_name),
            silent=True,
        )
        app.currentDimension = dimension
        app.world.setDimension(dimension)
        app.assetManager._createBackground(dimension)
        if app.sceneStructurePositions:
            app._fitPositionsToViewport(app.sceneStructurePositions, notify=False)
        else:
            app._fitWorldToViewport(notify=False)
        app.renderer.offsetX = app.targetOffsetX
        app.renderer.offsetY = app.targetOffsetY
        clean = pygame.Surface((app_module.WINDOW_WIDTH - app_module.PANEL_WIDTH, app_module.WINDOW_HEIGHT))
        old_screen = app.screen
        app.screen = clean
        app.skyboxRenderer.resize(clean.get_size())
        app.skyboxRenderer.update(0, dimension, view_rotation=app.renderer.viewRotation)
        if not app.skyboxRenderer.render(clean, dimension):
            app.assetManager.drawBackground(clean)
        app._renderWorld()
        save_capture(clean, output_dir / filename)
        app.screen = old_screen
        app.skyboxRenderer.resize(old_screen.get_size())

    capture_clean_dimension(
        "bastion_bridge_1161.json.gz",
        app_module.DIMENSION_NETHER,
        "nether.png",
    )
    capture_clean_dimension(
        "end_city_1161.json.gz",
        app_module.DIMENSION_END,
        "end.png",
    )

    # Additional editor-frame art for the Worlds gallery.
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
