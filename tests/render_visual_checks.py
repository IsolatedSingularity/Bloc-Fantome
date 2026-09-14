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
        (5, "tutorial_advanced_mirror.png"),
        (15, "tutorial_advanced_liquids.png"),
        (19, "tutorial_advanced_horror.png"),
    ):
        tutorial.selectLesson(step_index)
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
    save_capture(screen, output_dir / "redstone_lab_door_build.png")
    app._loadRedstoneLabCircuit("clock")
    app._setInteractionMode(True)
    app._render()
    save_capture(screen, output_dir / "redstone_lab_clock_interact.png")
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

    app._beginTutorial(advanced=True)
    for key,biome,filename in (
        ('biomes','warped_forest','tutorial_nether.png'),
        ('biomes','end_highlands','tutorial_end.png'),
        ('skies',None,'tutorial_weather.png'),
        ('lighting',None,'tutorial_lighting.png'),
    ):
        tutorial.selectLesson(next(i for i,step in enumerate(tutorial.TUTORIAL_STEPS) if step['id']==key))
        if biome: app._openBiomeScene(biome)
        app._render()
        save_capture(screen,output_dir/filename)
    tutorial.hide()

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


def render_redstone(output_dir: Path):
    """Focused Lab QA, using the live renderer at final display resolutions."""
    from engine.redstone_lab import LAB_CIRCUITS
    output_dir.mkdir(parents=True, exist_ok=True)
    app = app_module.BlocFantome()
    assert app.assetManager.loadAllAssets()
    app._toggleRedstoneLab()
    for size in ((1200,800),(960,640),(1920,1080)):
        app_module.WINDOW_WIDTH,app_module.WINDOW_HEIGHT=size
        app.screen=pygame.display.set_mode(size)
        for key in LAB_CIRCUITS:
            app._loadRedstoneLabCircuit(key)
            app._setInteractionMode(True)
            for _ in range(40):app.redstone.update(50)
            app._render()
            save_capture(app.screen,output_dir/f'{key}_{size[0]}.png')
        app._setInteractionMode(False)
        app._render()
        save_capture(app.screen,output_dir/f'build_{size[0]}.png')
        for rect in app.redstoneLabComponentRects.values():
            assert rect.bottom < app.redstoneLabActionRects['cutaway'].top
    app_module.WINDOW_WIDTH,app_module.WINDOW_HEIGHT=1200,800
    app.screen=pygame.display.set_mode((1200,800))
    app._loadRedstoneLabCircuit('piston_door')
    app._setInteractionMode(True)
    for rotation in range(4):
        app.renderer.viewRotation=rotation
        app._fitWorldToViewport(False)
        for on in (True,False):
            pos=LAB_CIRCUITS['piston_door'].controls[0][1]
            if app.world.getBlockProperties(*pos).powered != on:app._interactBlock(*pos)
            for _ in range(20):app.redstone.update(50)
            app._invalidateViewCaches();app._render()
            save_capture(app.screen,output_dir/f'door_r{rotation}_{on}.png')
    for key in ('staircase','hidden_entrance','clock','slow_clock'):
        app.renderer.viewRotation = 0
        app._loadRedstoneLabCircuit(key)
        app._interactBlock(*LAB_CIRCUITS[key].controls[0][1])
        for _ in range(40):app.redstone.update(50)
        app._invalidateViewCaches();app._render()
        save_capture(app.screen,output_dir/f'{key}_active.png')
        app._redstoneLabAction('cutaway');app._render()
        save_capture(app.screen,output_dir/f'{key}_cutaway.png')
        app.redstoneLabCutaway=False
    # Native model textures at an enlarged integer zoom, with native-size labels.
    sheet=pygame.Surface((1200,650));sheet.fill((31,35,42))
    for column,facing in enumerate(app_module.Facing):
        sheet.blit(app.smallFont.render(facing.name,True,(236,232,222)),(column*200+45,12))
        for row,(block,extended) in enumerate(((app_module.BlockType.STICKY_PISTON,False),
                (app_module.BlockType.STICKY_PISTON,True),(app_module.BlockType.PISTON_HEAD,False))):
            sprite=app.assetManager.getDetailSprite(block,facing,extended,
                app_module.SlabPosition.BOTTOM,sticky=True)
            sheet.blit(pygame.transform.scale(sprite,(sprite.get_width()*2,sprite.get_height()*2)),
                       (column*200+35,45+row*190))
    save_capture(sheet,output_dir/'piston_six_facings.png')
    pygame.quit()


def render_world_map_regions(output_dir: Path) -> None:
    """Exercise every source region, camera controls, UI size, and cached pan."""
    import json
    from engine.world_map_regions import REGIONS
    output_dir.mkdir(parents=True,exist_ok=True)
    app=app_module.BlocFantome()
    if not app.assetManager.loadAllAssets():
        raise RuntimeError('Assets failed to load')
    app._openWorldMap()
    measurements=[]
    for width,height in ((960,640),(1200,800),(1920,1080)):
        app._applyWindowSize(width,height)
        splash = SplashScreen(app.screen, app.clock, app_module.TEXTURES_DIR,
                              app_module.FONTS_DIR, app_module.ICONS_DIR)
        splash.present()
        save_capture(app.screen,output_dir/f'splash_{width}.png')
        for dimension,regions in REGIONS.items():
            app._switchWorldMapHub(dimension)
            for key,_label in regions:
                app._handleWorldMapAction('region:'+key)
                app._render()
                save_capture(app.screen,output_dir/f'{dimension}_{key}_{width}.png')
                # Every source region button stays inside its native viewport.
                assert all(app.screen.get_rect().contains(rect) for rect in app.worldMapView.region_rects.values())
                assert len(app.worldMapView.node_hit_rects)==2
                assert all(rect.width>0 for rect in app.worldMapView.node_hit_rects)
                for rect in app.worldMapView.node_hit_rects:
                    assert app.worldMapView.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=rect.center)) is None
                times=[]
                for frame in range(24):
                    app.renderer.offsetX+=3
                    app.renderer.offsetY-=1
                    start=time.perf_counter()
                    app._render()
                    times.append((time.perf_counter()-start)*1000)
                measurements.append({'dimension':dimension,'region':key,'size':[width,height],
                                     'pan_p95_ms':sorted(times)[22],'max_ms':max(times)})
                # Hover each genuine mission marker and retain a visual sample.
                if app.worldMapView.node_hit_rects:
                    point=app.worldMapView.node_hit_rects[0].center
                    app.worldMapView.handle_event(pygame.event.Event(pygame.MOUSEMOTION,pos=point))
                    app._render()
                    save_capture(app.screen,output_dir/f'{dimension}_{key}_hover_{width}.png')
                app._handleWorldMapAction('overview')
                app._render()
                save_capture(app.screen,output_dir/f'{dimension}_{key}_overview_{width}.png')
        for dimension in ('overworld','ocean'):
            app._switchWorldMapHub(dimension)
            app._render()
            save_capture(app.screen,output_dir/f'{dimension}_{width}.png')
    (output_dir/'performance.json').write_text(json.dumps(measurements,indent=2)+'\n')
    app._exitWorldMap()
    app._render()
    save_capture(app.screen,output_dir/'builder_after_map.png')
    pygame.quit()


def render_guided(output_dir: Path) -> None:
    """Exercise the full biome roster, both courses, and native sky rotation."""
    import json
    from engine.biome_catalog import BIOMES
    output_dir.mkdir(parents=True,exist_ok=True)
    app=app_module.BlocFantome()
    if not app.assetManager.loadAllAssets(): raise RuntimeError('Assets unavailable')
    app.tutorialScreen.setAssets(app.assetManager.buttonNormal,app.assetManager.buttonHover,
        app.assetManager.checkboxTexture,app.assetManager.checkboxSelectedTexture,app.assetManager.clickSound,app.assetManager)
    montage=pygame.Surface((8*250,10*182))
    montage.fill((23,29,27))
    font=app_module.load_ui_font(13)
    for i,entry in enumerate(BIOMES):
        x,y=(i%8)*250,(i//8)*182
        preview=app.biomePanel.preview(entry,app.assetManager,(242,140))
        montage.blit(preview,(x+4,y+2))
        words=entry['id'].replace('_',' ').title().split()
        lines=['']
        for word in words:
            candidate=(lines[-1]+' '+word).strip()
            if font.size(candidate)[0]>240: lines.append(word)
            else: lines[-1]=candidate
        for j,line in enumerate(lines): montage.blit(font.render(line,True,(228,229,205)),(x+5,y+144+j*16))
    save_capture(montage,output_dir/'all_79_biomes.png')
    measurements=[]
    for width,height in ((1200,800),(960,640),(1920,1080)):
        app._applyWindowSize(width,height)
        splash=SplashScreen(app.screen,app.clock,app_module.TEXTURES_DIR,app_module.FONTS_DIR,app_module.ICONS_DIR)
        splash.present()
        save_capture(app.screen,output_dir/f'splash_{width}.png')
        app._beginTutorial(advanced=False)
        app.tutorialScreen.hintVisible=True
        app._render()
        save_capture(app.screen,output_dir/f'getting_started_{width}.png')
        app.tutorialScreen.hide()
        app._beginTutorial(advanced=True)
        app._render()
        save_capture(app.screen,output_dir/f'handbook_contents_{width}.png')
        for i,step in enumerate(app.tutorialScreen.TUTORIAL_STEPS):
            app.tutorialScreen.selectLesson(i)
            app.tutorialScreen.hintVisible=True
            app._render()
            save_capture(app.screen,output_dir/f'lesson_{step["id"]}_{width}.png')
        app.tutorialScreen.minimized=True
        app._render()
        save_capture(app.screen,output_dir/f'tutorial_minimized_{width}.png')
        app.tutorialScreen.hide()
        app.blocksExpanded=False
        app.experimentalExpanded=False
        app.structuresExpanded=False
        app.biomePanel.expanded=True
        app.inventoryScroll=app.inventoryScrollTarget=0
        for dimension,biome in (('overworld','birch_forest'),('nether','warped_forest'),('end','end_highlands')):
            app._openBiomeScene(biome)
            app.tooltipTimer=0
            app.skyboxesEnabled=True
            app.skyboxRenderer.update(0,dimension,view_rotation=0)
            app.skyboxRenderer.update(400,dimension,view_rotation=0)
            for _ in range(5):app._render()
            save_capture(app.screen,output_dir/f'biomes_{dimension}_{width}.png')
            timings=[]
            for _ in range(20):
                start=time.perf_counter()
                app._render()
                timings.append((time.perf_counter()-start)*1000)
            measurements.append(dict(kind='settled',dimension=dimension,size=[width,height],p95_ms=sorted(timings)[18]))
            timings=[]
            for step in range(24):
                app.clock.tick(60)
                start=time.perf_counter()
                app.skyboxRenderer.update(16,dimension,view_rotation=1)
                app._render()
                timings.append((time.perf_counter()-start)*1000)
            measurements.append(dict(kind='sky_rotation',dimension=dimension,size=[width,height],p95_ms=sorted(timings)[22],max_ms=max(timings)))
            save_capture(app.screen,output_dir/f'sky_rotated_{dimension}_{width}.png')
        app.skyboxesEnabled=False
    (output_dir/'performance.json').write_text(json.dumps(measurements,indent=2))
    app.worldLoadExecutor.shutdown(wait=True)
    pygame.quit()


def render_consistency(output_dir: Path) -> None:
    """Native UI captures plus real Q/E camera checks on curated biome scenes."""
    import json
    from ui.biomes import CURATED_IDS
    output_dir.mkdir(parents=True,exist_ok=True)
    app=app_module.BlocFantome()
    app_module.DERIVED_WORLD_CACHE_DIR=str(output_dir/'scene-cache')
    assert app.assetManager.loadAllAssets()
    app.tutorialScreen.setAssets(app.assetManager.buttonNormal,app.assetManager.buttonHover,
        app.assetManager.checkboxTexture,app.assetManager.checkboxSelectedTexture,app.assetManager.clickSound,app.assetManager)
    measurements=[]
    for width,height in ((960,640),(1200,800),(1920,1080)):
        app._applyWindowSize(width,height)
        app.tutorialScreen.visible=False
        app.blocksExpanded=False
        app.experimentalExpanded=False
        app.inventoryScroll=app.inventoryScrollTarget=0
        app._openBiomeScene('plains')
        app.tooltipTimer=0
        app._render()
        save_capture(app.screen,output_dir/f'editor_{width}.png')
        for tab in app.library.TABS:
            app.library.open(app,tab)
            if app.library.entries:app.library.pending=app.library.entries[0]
            app._render()
            save_capture(app.screen,output_dir/f'library_{tab.replace(" ","_")}_{width}.png')
        app.library.visible=False
        app.settingsMenuOpen=True;app._render()
        save_capture(app.screen,output_dir/f'settings_{width}.png')
        app.settingsMenuOpen=False;app.showShortcutsPanel=True;app._render()
        save_capture(app.screen,output_dir/f'help_{width}.png')
        app.showShortcutsPanel=False
        app._beginTutorial(advanced=False)
        app._render();save_capture(app.screen,output_dir/f'tutorial_{width}.png')
        for i in range(len(app.tutorialScreen.TUTORIAL_STEPS)):
            app.tutorialScreen.selectLesson(i)
            app._render()
            save_capture(app.screen,output_dir/f'tour_{i:02}_{width}.png')
        app.tutorialScreen.hide()
        app._toggleRedstoneLab();app._render()
        save_capture(app.screen,output_dir/f'lab_{width}.png')
        app._toggleRedstoneLab()
    if '--ui-only' in sys.argv:
        app.worldLoadExecutor.shutdown(wait=True)
        pygame.quit()
        return
    app._applyWindowSize(1920,1080)
    app.tutorialScreen.visible=False
    app.library.visible=False
    for name in CURATED_IDS:
        start=time.perf_counter();app._openBiomeScene(name)
        row={'biome':name,'load_ms':round((time.perf_counter()-start)*1000,2),'views':[]}
        for turn in range(4):
            before=app.renderer.viewRotation
            pygame.event.clear()
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_e,unicode='e',mod=0))
            app._handleEvents()
            assert app.renderer.viewRotation==(before+1)%4,(name,'camera input blocked')
            times=[]
            for frame in range(8):
                start=time.perf_counter();app._update();app._render()
                times.append((time.perf_counter()-start)*1000)
            assert app.renderStats['drawn']>0,(name,'empty camera view')
            assert app._worldSurfaceBuild is None,(name,'unfinished render')
            row['views'].append({'rotation':app.renderer.viewRotation,'cold_ms':round(times[0],2),'settled_max_ms':round(max(times[3:]),2),'drawn':app.renderStats['drawn']})
            if name in ('plains','warped_forest','end_highlands'):
                save_capture(app.screen,output_dir/f'{name}_rotation_{turn}.png')
        measurements.append(row)
        print(name,row['views'],flush=True)
    (output_dir/'biome_camera_performance.json').write_text(json.dumps(measurements,indent=2))
    app.worldLoadExecutor.shutdown(wait=True)
    pygame.quit()


def render_tour(output_dir: Path):
    """Every demonstration and preview shelf, native resolutions and four camera views."""
    import json
    output_dir.mkdir(parents=True,exist_ok=True)
    app=app_module.BlocFantome()
    app_module.DERIVED_WORLD_CACHE_DIR=str(output_dir/'scene-cache')
    assert app.assetManager.loadAllAssets()
    app._generateStructurePreviews()
    app._preloadTutorialMusic()
    app.tutorialScreen.setAssets(app.assetManager.buttonNormal,app.assetManager.buttonHover,
        app.assetManager.checkboxTexture,app.assetManager.checkboxSelectedTexture,app.assetManager.clickSound,app.assetManager)
    metrics=[]
    def settle():
        frames=[];deadline=time.perf_counter()+120
        while time.perf_counter()<deadline:
            t=time.perf_counter();app._update();app._render();frames.append((time.perf_counter()-t)*1000)
            if not getattr(app,'_pendingTourLoad',None) and app._worldSurfaceBuild is None:break
            time.sleep(.001)
        assert not getattr(app,'_pendingTourLoad',None),'Tour load timed out'
        assert not app.tooltipText.startswith('Could not load tutorial scene:'),app.tooltipText
        for _ in range(3):app._render()
        return frames
    for width,height in (((1200,800),) if '--quick' in sys.argv else ((1200,800),(960,640),(1920,1080))):
        app._applyWindowSize(width,height)
        from splash import SplashScreen
        from runtime_paths import TEXTURES_DIR, FONTS_DIR, ICONS_DIR
        splash=SplashScreen(app.screen,app.clock,TEXTURES_DIR,FONTS_DIR,ICONS_DIR)
        splash.present();save_capture(app.screen,output_dir/f'splash_{width}.png')
        app._beginTutorial(advanced=False)
        for i,step in enumerate(app.tutorialScreen.TUTORIAL_STEPS):
            requested=next((arg.split('=',1)[1].split(',') for arg in sys.argv if arg.startswith('--pages=')),None)
            if requested and step['id'] not in requested:continue
            start=time.perf_counter();app.tutorialScreen.selectLesson(i)
            dispatch=(time.perf_counter()-start)*1000
            frames=settle();ready=(time.perf_counter()-start)*1000
            save_capture(app.screen,output_dir/f"tour_{step['id']}_{width}.png")
            print('Rendered',step['id'],width,round(ready),flush=True)
            if app.worldMapActive:
                app._exitWorldMap()
            if app.redstoneLabActive:
                app._toggleRedstoneLab()
            if width==1200:
                for rotation in range(1,4):
                    app._rotateViewAndRecenter(1);settle()
                    save_capture(app.screen,output_dir/f"tour_{step['id']}_view{rotation}.png")
                app._rotateViewAndRecenter(1);settle()
            stable=[]
            for _ in range(20):
                t=time.perf_counter();app._render();stable.append((time.perf_counter()-t)*1000)
            metrics.append(dict(page=step['id'],width=width,dispatch_ms=round(dispatch,2),ready_ms=round(ready,2),max_loading_frame_ms=round(max(frames),2),p95_ms=round(sorted(stable)[18],2)))
        app.tutorialScreen.optional=True;app._loadGuidedLesson(15);settle()
        save_capture(app.screen,output_dir/f'optional_chapel_{width}.png')
        app.tutorialScreen.minimized=True;app._render();save_capture(app.screen,output_dir/f'minimized_{width}.png')
        app.tutorialScreen.hide()
        app.blocksExpanded=app.experimentalExpanded=False
        for section in app.previewBrowser.SECTIONS:
            app.previewBrowser.expand(app,section);app.inventoryScroll=app.inventoryScrollTarget=0
            settle();save_capture(app.screen,output_dir/f'previews_{section}_{width}.png')
        for tab in app.library.TABS:
            app.library.open(app,tab)
            if app.library.entries:app.library.pending=app.library.entries[0]
            settle();save_capture(app.screen,output_dir/f'library_{tab.replace(" ","_")}_{width}.png')
        app.library.visible=False;app.settingsMenuOpen=True
        app._render();save_capture(app.screen,output_dir/f'settings_{width}.png')
        app.settingsMenuOpen=False;app.showShortcutsPanel=True
        app._render();save_capture(app.screen,output_dir/f'help_{width}.png');app.showShortcutsPanel=False
    (output_dir/'performance.json').write_text(json.dumps(metrics,indent=2))
    app.worldLoadExecutor.shutdown(wait=True);pygame.quit()


if __name__ == "__main__":
    destination = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "visual-checks"
    (render_tour if '--tour' in sys.argv else render_consistency if '--consistency' in sys.argv else render_guided if '--guided' in sys.argv else render_world_map_regions if '--world-map' in sys.argv else render_redstone if '--redstone' in sys.argv else render)(destination)
