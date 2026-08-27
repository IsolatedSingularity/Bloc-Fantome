import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
import struct
import gzip
from types import SimpleNamespace
from unittest.mock import mock_open, patch


os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Code"))

try:
    import pygame
    import blocFantome as app_module
except ImportError:
    pygame = None
    app_module = None


@unittest.skipIf(app_module is None, "Pygame runtime is not installed")
class AppIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.font.init()
        cls.app = app_module.BlocFantome()
        if not cls.app.assetManager.loadAllAssets():
            raise RuntimeError("Integration fixture could not load application assets")

    @classmethod
    def tearDownClass(cls):
        pygame.display.quit()

    def setUp(self):
        if self.app.worldMapActive:
            self.app._exitWorldMap()
        self.app.world.resize(
            app_module.GRID_WIDTH,
            app_module.GRID_DEPTH,
            app_module.GRID_HEIGHT,
            min_y=0,
            preserve=False,
        )
        self.app.currentDimension = app_module.DIMENSION_OVERWORLD
        self.app.world.setDimension(app_module.DIMENSION_OVERWORLD)
        self.app.currentBuildPath = None
        self.app.worldCenteredRotation = False
        self.app.undoManager.clear()

    def test_world_map_session_restores_live_build_exactly(self):
        marker = (3, 4, 2)
        self.app.world.setBlock(*marker, app_module.BlockType.DIAMOND_BLOCK)
        original_blocks = dict(self.app.world.blocks)
        original_size = (self.app.world.width, self.app.world.depth, self.app.world.height)

        self.app._openWorldMap()
        self.assertTrue(self.app.worldMapActive)
        self.assertEqual(self.app.worldMapMode, "hub")
        self.assertEqual((self.app.world.width, self.app.world.depth), (48, 48))
        self.app._startWorldMapLevel()
        self.assertEqual(self.app.worldMapMode, "level")
        self.assertEqual(len(self.app.hotbar), 9)
        self.assertTrue(self.app._exitWorldMap())

        self.assertFalse(self.app.worldMapActive)
        self.assertEqual(
            (self.app.world.width, self.app.world.depth, self.app.world.height),
            original_size,
        )
        self.assertEqual(self.app.world.blocks, original_blocks)

    def test_each_world_map_objective_has_exact_completable_state(self):
        from engine.block_state import BlockProperties
        from engine.world_map import build_level, objective_progress

        for dimension in app_module.WORLD_MAP_DIMENSIONS:
            if dimension == "ocean":
                continue
            for route_index in range(2):
                with self.subTest(dimension=dimension, route=route_index):
                    objective = build_level(self.app.world, dimension, route_index)
                    self.assertTrue(objective.source_templates)
                    self.assertIsNone(objective.powered_target)
                    self.assertFalse(any("REDSTONE" in name for name in objective.hotbar))
                    self.assertFalse(any("REDSTONE" in block.name for block in self.app.world.blocks.values()))
                    current, total, done = objective_progress(self.app.world, objective)
                    self.assertFalse(done)
                    self.assertLess(current, total)
                    for position, block_name in objective.targets.items():
                        self.app.world.setBlock(*position, app_module.BlockType[block_name])
                    if objective.powered_target is not None:
                        self.app.world.setBlockProperties(
                            *objective.powered_target, BlockProperties(powered=True)
                        )
                    self.assertEqual(objective_progress(self.app.world, objective), (total, total, True))

    def test_world_map_controls_switch_tabs_start_and_return(self):
        self.app._openWorldMap()
        self.assertEqual(self.app._worldViewportRight(), app_module.WINDOW_WIDTH)
        self.app._render()
        self.app._handleWorldMapAction("dimension:end")
        self.assertEqual(self.app.currentDimension, app_module.DIMENSION_END)
        self.app._handleWorldMapAction("previous")
        self.assertEqual(self.app.currentDimension, app_module.DIMENSION_NETHER)
        self.app._handleWorldMapAction("start")
        self.assertEqual(self.app.worldMapMode, "level")
        self.app._handleWorldMapAction("hub")
        self.assertEqual(self.app.worldMapMode, "hub")
        self.assertTrue(self.app._exitWorldMap())

    def test_every_world_map_route_opens_with_a_valid_nine_slot_hotbar(self):
        self.app._openWorldMap()
        for dimension in app_module.WORLD_MAP_DIMENSIONS:
            if dimension == "ocean":
                continue
            for route_index in range(2):
                with self.subTest(dimension=dimension, route=route_index):
                    self.app._switchWorldMapHub(dimension)
                    self.app._startWorldMapLevel(route_index)
                    self.assertEqual(len(self.app.hotbar), 9)
                    self.assertTrue(all(isinstance(block, app_module.BlockType) for block in self.app.hotbar))
                    self.assertFalse(self.app.showGrid)
                    self.assertEqual(self.app._worldViewportRight(), app_module.WINDOW_WIDTH)
                    self.app._handleKeyDown(
                        pygame.event.Event(pygame.KEYDOWN, key=pygame.K_g, unicode="g")
                    )
                    self.assertFalse(self.app.showGrid)
        self.app._exitWorldMap()

    def test_ocean_world_map_is_a_locked_preview_without_objective_entry(self):
        self.app._openWorldMap()
        self.app._switchWorldMapHub("ocean")
        self.assertEqual(self.app.worldMapDimension, "ocean")
        self.assertEqual(self.app.currentDimension, app_module.DIMENSION_OVERWORLD)
        self.assertFalse(self.app.worldMapScene.playable_anchors)
        self.assertEqual(len(self.app.worldMapScene.locked_anchors), 4)
        self.app._startWorldMapLevel(0)
        self.assertEqual(self.app.worldMapMode, "hub")
        self.assertIsNone(self.app.worldMapObjective)
        self.app._exitWorldMap()

    def test_overworld_map_has_deep_skirt_but_frames_the_play_surface(self):
        self.app._openWorldMap()
        self.assertEqual(self.app.world.min_y, -40)
        self.assertLessEqual(self.app.world.occupiedBounds[0][2], -40)
        self.assertEqual(self.app.worldMapScene.framing_bounds, ((4, 5, 0), (43, 42, 12)))
        self.assertGreater(self.app.zoomLevel, 0.35)
        self.app._exitWorldMap()

    def test_middle_drag_is_direct_at_close_zoom_even_over_hotbar(self):
        self.app.zoomLevel = self.app.zoomMax
        self.app.renderer.setZoom(self.app.zoomLevel)
        self.app.smoothCameraEnabled = True
        start_x = (app_module.WINDOW_WIDTH - app_module.PANEL_WIDTH) // 2
        start_y = app_module.WINDOW_HEIGHT - 40
        before = (self.app.renderer.offsetX, self.app.renderer.offsetY)
        self.app._handleMouseDown(SimpleNamespace(button=2, pos=(start_x, start_y)))
        self.assertTrue(self.app.panning)
        self.app._handleMouseMotion(SimpleNamespace(pos=(start_x + 37, start_y - 19)))
        self.assertEqual(
            (self.app.renderer.offsetX, self.app.renderer.offsetY),
            (before[0] + 37, before[1] - 19),
        )
        self.assertEqual(
            (self.app.targetOffsetX, self.app.targetOffsetY),
            (self.app.renderer.offsetX, self.app.renderer.offsetY),
        )
        self.app._handleMouseUp(SimpleNamespace(button=2))
        self.assertFalse(self.app.panning)

    def test_world_map_progress_save_keeps_the_users_persistent_hotbar(self):
        original_hotbar = [block.name for block in self.app.hotbar]
        original_progress = {
            dimension: list(progress)
            for dimension, progress in self.app.worldMapCompleted.items()
        }
        self.app._openWorldMap()
        self.app._startWorldMapLevel()
        self.assertNotEqual([block.name for block in self.app.hotbar], original_hotbar)
        self.app.worldMapCompleted[app_module.DIMENSION_OVERWORLD][0] = True
        writer = mock_open()
        try:
            with patch("builtins.open", writer):
                self.app._saveAppConfig()
            payload = "".join(
                call.args[0] for call in writer().write.call_args_list
            )
            saved = json.loads(payload)
            self.assertEqual(saved["hotbar"], original_hotbar)
            self.assertEqual(
                saved["worldMapCompleted"][app_module.DIMENSION_OVERWORLD],
                [True, False],
            )
        finally:
            self.app.worldMapCompleted = original_progress
            self.app._exitWorldMap()

    def test_responsive_minimum_reflows_controls_and_preserves_camera_center(self):
        old_size = (app_module.WINDOW_WIDTH, app_module.WINDOW_HEIGHT)
        old_zoom = self.app.zoomLevel
        old_canvas_width = old_size[0] - app_module.PANEL_WIDTH
        old_center = self.app.renderer._screenToWorldPoint(
            old_canvas_width // 2, old_size[1] // 2, self.app.cameraFocusZ
        )
        try:
            self.app._applyWindowSize(700, 500, recreate=False)
            self.assertEqual((app_module.WINDOW_WIDTH, app_module.WINDOW_HEIGHT), (960, 640))
            canvas = pygame.Rect(0, 0, 960 - app_module.PANEL_WIDTH, 640)
            for rect in (
                self.app.worldMapButtonRect,
                self.app.terrainViewButtonRect,
                self.app.shrinkCanvasButtonRect,
                self.app.growCanvasButtonRect,
                self.app.terrainNoiseButtonRect,
                self.app.fitWorldButtonRect,
            ):
                self.assertTrue(canvas.contains(rect), rect)
            new_center = self.app.renderer._screenToWorldPoint(
                (960 - app_module.PANEL_WIDTH) // 2, 640 // 2, self.app.cameraFocusZ
            )
            self.assertAlmostEqual(new_center[0], old_center[0], delta=0.1)
            self.assertAlmostEqual(new_center[1], old_center[1], delta=0.1)
            expected_scale = min(
                (960 - app_module.PANEL_WIDTH) / old_canvas_width,
                640 / old_size[1],
            )
            self.assertAlmostEqual(self.app.zoomLevel, old_zoom * expected_scale, places=3)
            self.assertLessEqual(
                self.app.tutorialScreen.panelX + self.app.tutorialScreen.panelWidth,
                960,
            )
        finally:
            self.app._applyWindowSize(*old_size, recreate=False)

    def test_json_structures_are_cursor_placeable(self):
        for name in app_module.JSON_STRUCTURE_LIBRARY:
            structure = app_module.PREMADE_STRUCTURES[name]
            self.assertTrue(structure["blocks"], name)
            self.assertIn("source_file", structure)

    def test_app_uses_modular_world_and_renderer(self):
        self.assertEqual(self.app.world.__class__.__module__, "engine.world")
        self.assertEqual(self.app.renderer.__class__.__module__, "engine.renderer")

    def test_every_palette_block_has_loaded_place_and_break_sounds(self):
        interaction_only = {
            "chest", "enderchest", "copper_chest",
            "copper_chest_weathered", "copper_chest_oxidized",
            "enchantment_table", "end_portal",
        }
        for block_type in app_module.BlockType:
            if block_type == app_module.BlockType.AIR:
                continue
            with self.subTest(block=block_type.name):
                self.assertIn(block_type, app_module.BLOCK_SOUNDS)
                sound_def = app_module.BLOCK_SOUNDS[block_type]
                for is_place, category in (
                    (True, sound_def.placeSound),
                    (False, sound_def.breakSound),
                ):
                    if is_place and self.app.assetManager.sounds.get(f"{category}_place"):
                        category = f"{category}_place"
                    self.assertNotIn(category, interaction_only)
                    self.assertTrue(
                        self.app.assetManager.sounds.get(category),
                        f"{block_type.name} has no loaded {'place' if is_place else 'break'} pool {category}",
                    )

    def test_fire_ambient_pool_never_contains_ignition(self):
        sounds = self.app.assetManager.sounds
        self.assertEqual(len(sounds["fire_ambient"]), 1)
        self.assertEqual(len(sounds["fire_ignite"]), 1)
        self.assertIsNot(sounds["fire_ambient"][0], sounds["fire_ignite"][0])
        self.assertEqual(
            app_module.BLOCK_SOUNDS[app_module.BlockType.FIRE].placeSound,
            "fire_ignite",
        )

    def test_panel_wheel_scroll_eases_toward_target(self):
        self.app.maxScroll = 600
        self.app.inventoryScroll = 0.0
        self.app.inventoryScrollTarget = 0.0
        event = SimpleNamespace(y=-1, precise_y=-1.0)
        with patch.object(
            pygame.mouse, "get_pos",
            return_value=(app_module.WINDOW_WIDTH - 1, 100),
        ):
            self.app._handleMouseWheel(event)
        self.assertEqual(self.app.inventoryScroll, 0.0)
        self.assertEqual(self.app.inventoryScrollTarget, 72.0)
        self.app._updatePanelScroll(16)
        self.assertGreater(self.app.inventoryScroll, 0.0)
        self.assertLess(self.app.inventoryScroll, self.app.inventoryScrollTarget)
        self.app._updatePanelScroll(1000)
        self.assertAlmostEqual(self.app.inventoryScroll, 72.0, delta=0.1)

    def test_settings_controls_share_one_bounded_minecraft_panel(self):
        panel = self.app._settingsMenuRect()
        self.assertTrue(pygame.Rect(0, 0, app_module.WINDOW_WIDTH, app_module.WINDOW_HEIGHT).contains(panel))
        slider = pygame.Rect(panel.x + 28, panel.y + 68 + 22, panel.width - 56, 12)
        self.assertTrue(panel.contains(slider))
        last_toggle = pygame.Rect(panel.x + 28, panel.y + 242 + 5 * 36, panel.width - 56, 30)
        self.assertTrue(panel.contains(last_toggle))

        old_value = self.app.showBlockTooltip
        self.app.settingsMenuOpen = True
        self.app._handleSettingsClick(last_toggle.centerx, last_toggle.centery)
        self.assertNotEqual(self.app.showBlockTooltip, old_value)
        self.app.showBlockTooltip = old_value

        world_rotation_toggle = pygame.Rect(
            panel.x + 28,
            panel.y + 242 + 6 * 36,
            panel.width - 56,
            30,
        )
        self.assertTrue(panel.contains(world_rotation_toggle))
        self.app.worldCenteredRotation = False
        self.app._handleSettingsClick(*world_rotation_toggle.center)
        self.assertTrue(self.app.worldCenteredRotation)

    def test_block_and_toggle_submenus_share_rows_and_preview_icons(self):
        self.assertEqual(app_module.PANEL_SUBMENU_ROW_HEIGHT, 30)
        self.assertEqual(app_module.PANEL_SUBMENU_ROW_STRIDE, 35)
        self.assertEqual(
            set(app_module.CATEGORY_PREVIEW_BLOCKS),
            set(app_module.CATEGORY_ORDER),
        )
        for category, block_type in app_module.CATEGORY_PREVIEW_BLOCKS.items():
            with self.subTest(category=category):
                self.assertIn(block_type, app_module.BLOCK_CATEGORIES[category])
                self.assertIsNotNone(
                    self.app.assetManager.getIconSprite(block_type)
                )

    def test_rain_button_animation_covers_button_and_keeps_icon_on_top(self):
        rect = pygame.Rect(10, 10, 210, app_module.PANEL_SUBMENU_ROW_HEIGHT)
        icon = self.app.assetManager.getIconSprite(app_module.BlockType.WATER)
        plain = pygame.Surface((230, 50), pygame.SRCALPHA)
        animated = pygame.Surface((230, 50), pygame.SRCALPHA)
        self.app.assetManager.drawPanelRow(
            plain, rect, "Rain: ON", self.app.smallFont, icon=icon
        )
        # Pin the animation phase so at least one drop crosses the icon area;
        # an arbitrary real clock can legitimately place all eight drops to
        # its left and make this foreground-order assertion intermittent.
        with patch.object(pygame.time, "get_ticks", return_value=1000):
            self.app.assetManager.drawPanelRow(
                animated,
                rect,
                "Rain: ON",
                self.app.smallFont,
                icon=icon,
                effectStyle="rain",
                effectColors=((100, 140, 220, 220),),
            )
        icon_area = pygame.Rect(rect.right - rect.height, rect.top, rect.height, rect.height)
        self.assertNotEqual(
            pygame.image.tobytes(plain.subsurface(icon_area), "RGBA"),
            pygame.image.tobytes(animated.subsurface(icon_area), "RGBA"),
        )
        self.assertEqual(
            plain.get_at((icon_area.centerx, icon_area.centery)),
            animated.get_at((icon_area.centerx, icon_area.centery)),
        )
        self.assertNotEqual(
            pygame.image.tobytes(plain.subsurface(rect), "RGBA"),
            pygame.image.tobytes(animated.subsurface(rect), "RGBA"),
        )

    def test_all_toggle_effect_styles_cover_button_and_keep_preview_foreground(self):
        rect = pygame.Rect(10, 10, 210, app_module.PANEL_SUBMENU_ROW_HEIGHT)
        icon = self.app.assetManager.getPanelPreviewIcon(app_module.BlockType.WATER)
        initial_effect_surfaces = len(self.app.assetManager.uiEffectSurfaces)
        plain = pygame.Surface((230, 50), pygame.SRCALPHA)
        self.app.assetManager.drawPanelRow(
            plain, rect, "Toggle", self.app.smallFont, icon=icon
        )
        icon_area = pygame.Rect(rect.right - rect.height, rect.top, rect.height, rect.height)
        plain_icon = pygame.image.tobytes(plain.subsurface(icon_area), "RGBA")
        styles = (
            "rain", "embers", "void", "snow", "souls", "shards",
            "clouds", "celestial", "lighting", "overworld", "pulse",
        )
        for style in styles:
            with self.subTest(style=style):
                animated = pygame.Surface((230, 50), pygame.SRCALPHA)
                self.app.assetManager.drawPanelRow(
                    animated,
                    rect,
                    "Toggle",
                    self.app.smallFont,
                    active=True,
                    icon=icon,
                    effectStyle=style,
                    effectColors=((130, 180, 230, 170),),
                    effectTint=(80, 120, 170),
                )
                self.assertNotEqual(
                    pygame.image.tobytes(animated.subsurface(icon_area), "RGBA"),
                    plain_icon,
                )
                effect_only = pygame.Surface((230, 50), pygame.SRCALPHA)
                self.app.assetManager.drawPanelRow(
                    effect_only, rect, "Toggle", self.app.smallFont,
                    active=True, effectStyle=style,
                    effectColors=((130, 180, 230, 170),),
                    effectTint=(80, 120, 170),
                )
                self.assertNotEqual(
                    pygame.image.tobytes(animated.subsurface(icon_area), "RGBA"),
                    pygame.image.tobytes(effect_only.subsurface(icon_area), "RGBA"),
                )
                self.assertNotEqual(
                    pygame.image.tobytes(animated.subsurface(rect), "RGBA"),
                    pygame.image.tobytes(plain.subsurface(rect), "RGBA"),
                )
        self.assertLessEqual(
            len(self.app.assetManager.uiEffectSurfaces),
            initial_effect_surfaces + 1,
        )

    def test_toggle_effect_motion_advances_between_60_fps_frames(self):
        rect = pygame.Rect(10, 10, 210, app_module.PANEL_SUBMENU_ROW_HEIGHT)
        frames = []
        for ticks in (1000, 1017):
            surface = pygame.Surface((230, 50), pygame.SRCALPHA)
            with patch.object(pygame.time, "get_ticks", return_value=ticks):
                self.app.assetManager.drawPanelRow(
                    surface, rect, "Rain", self.app.smallFont,
                    effectStyle="rain",
                    effectColors=((130, 180, 230, 220),),
                )
            frames.append(pygame.image.tobytes(surface.subsurface(rect), "RGBA"))
        self.assertNotEqual(frames[0], frames[1])

    def test_volume_controls_fit_panel_and_muted_button_keeps_speaker(self):
        self.app.volumeControlRects.clear()
        x = app_module.WINDOW_WIDTH - app_module.PANEL_WIDTH + app_module.ICON_MARGIN + 10
        for index, (label, value) in enumerate((
            ("Music", 0.8), ("Ambient", 0.6), ("Effects", 0.4),
        )):
            self.app._renderVolumeSlider(x, 120 + index * 28, label, value, -1, -1)
        panel = pygame.Rect(
            app_module.WINDOW_WIDTH - app_module.PANEL_WIDTH, 0,
            app_module.PANEL_WIDTH, app_module.WINDOW_HEIGHT,
        )
        for control in self.app.volumeControlRects.values():
            self.assertTrue(panel.contains(control["track"]))
            self.assertTrue(panel.contains(control["mute"]))
            self.assertLess(control["track"].right, control["mute"].left)

    def test_open_library_buttons_play_click_audio(self):
        event_factory = lambda pos: pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": pos}
        )
        with patch.object(self.app.assetManager, "playClickSound") as click:
            self.app.buildLibrary.open([])
            self.app.buildLibrary.render(self.app.screen)
            action = self.app.buildLibrary.handle_event(
                event_factory(self.app.buildLibrary._browse_rect.center)
            )
            self.assertEqual(action[0], "browse")
            self.app.worldLibrary.open([])
            self.app.worldLibrary.render(self.app.screen)
            action = self.app.worldLibrary.handle_event(
                event_factory(self.app.worldLibrary._import_rect.center)
            )
            self.assertEqual(action[0], "import")
            self.assertEqual(click.call_count, 2)
        self.app.buildLibrary.close()
        self.app.worldLibrary.close()

    def test_panel_preview_icons_stay_stable_while_world_icons_animate(self):
        animated_blocks = (
            app_module.BlockType.WATER,
            app_module.BlockType.FIRE,
            app_module.BlockType.END_PORTAL,
        )
        previews = {
            block: self.app.assetManager.getPanelPreviewIcon(block)
            for block in animated_blocks
        }
        preview_bytes = {
            block: pygame.image.tobytes(preview, "RGBA")
            for block, preview in previews.items()
        }
        for _ in range(12):
            self.app.assetManager.updateAnimation(100)
        for block in animated_blocks:
            self.assertIs(
                self.app.assetManager.getPanelPreviewIcon(block), previews[block]
            )
            self.assertEqual(
                pygame.image.tobytes(previews[block], "RGBA"), preview_bytes[block]
            )

    def test_side_targets_work_at_every_zoom_and_rotation(self):
        source = (5, 5, 4)
        self.app.world.setBlock(*source, app_module.BlockType.STONE)
        leftDirections = ((0, 1), (1, 0), (0, -1), (-1, 0))
        rightDirections = ((1, 0), (0, -1), (-1, 0), (0, 1))
        for zoom in (0.5, 1.0, 1.4, 2.0):
            self.app.renderer.setZoom(zoom)
            self.app.zoomLevel = zoom
            for rotation in range(4):
                self.app.renderer.setViewRotation(rotation)
                polygons = self.app.renderer.getBlockFacePolygons(*source)
                for face, directions in (("left", leftDirections), ("right", rightDirections)):
                    polygon = polygons[face]
                    point = (
                        sum(vertex[0] for vertex in polygon) // len(polygon),
                        sum(vertex[1] for vertex in polygon) // len(polygon),
                    )
                    self.app._updateHoveredCell(*point)
                    dx, dy = directions[rotation]
                    self.assertEqual(self.app.hoveredCell, (source[0] + dx, source[1] + dy, source[2]))

    def test_overlapping_depth_tie_picks_the_last_visible_model(self):
        first = (5, 5, 1)
        second = (5, 5, 2)
        self.app.renderer.setZoom(1.0)
        self.app.zoomLevel = 1.0
        self.app.renderer.setViewRotation(0)
        self.app.world.setBlock(*first, app_module.BlockType.STONE)
        self.app.world.setBlock(*second, app_module.BlockType.OAK_PLANKS)
        first_sprite = self.app.assetManager.getBlockSprite(app_module.BlockType.STONE)
        second_sprite = self.app.assetManager.getBlockSprite(app_module.BlockType.OAK_PLANKS)

        def rect_for(position, sprite):
            sx, sy = self.app.renderer.worldToScreen(*position)
            return pygame.Rect(sx - app_module.TILE_WIDTH // 2, sy, *sprite.get_size())

        first_rect = rect_for(first, first_sprite)
        second_rect = rect_for(second, second_sprite)
        overlap = first_rect.clip(second_rect)
        point = None
        for screen_y in range(overlap.top, overlap.bottom):
            for screen_x in range(overlap.left, overlap.right):
                a = first_sprite.get_at((screen_x - first_rect.x, screen_y - first_rect.y)).a
                b = second_sprite.get_at((screen_x - second_rect.x, screen_y - second_rect.y)).a
                if a and b and self.app.renderer.detectBlockFace(
                    screen_x, screen_y, *second
                ):
                    point = (screen_x, screen_y)
                    break
            if point:
                break
        self.assertIsNotNone(point, "fixture blocks should overlap on screen")
        self.app._updateHoveredCell(*point)
        self.assertEqual(self.app.hoveredSourceBlock, second)

    def test_rotation_preserves_cursor_world_anchor_in_all_views(self):
        self.app.zoomLevel = 0.75
        self.app.renderer.setZoom(0.75)
        self.app.renderer.setViewRotation(0)
        self.app.renderer.offsetX = 410.5
        self.app.renderer.offsetY = 330.25
        self.app.cameraFocusZ = 3
        self.app.hoveredSourceBlock = (8, 9, 17)
        cursor = (287, 463)
        anchor_z = self.app.hoveredSourceBlock[2]
        anchor = self.app.renderer._screenToWorldPoint(
            *cursor, anchor_z
        )
        with patch.object(pygame.mouse, "get_pos", return_value=cursor):
            for _ in range(4):
                self.app._rotateViewAndRecenter(1)
                projected = self.app.renderer.worldToScreen(
                    *anchor, anchor_z
                )
                self.assertLessEqual(abs(projected[0] - cursor[0]), 1)
                self.assertLessEqual(abs(projected[1] - cursor[1]), 1)
        self.app.hoveredSourceBlock = None

    def test_world_centered_rotation_preserves_world_axis_in_all_views(self):
        self.app.world.resize(80, 64, 32, min_y=0, preserve=False)
        self.app.worldCenteredRotation = True
        self.app.cameraFocusZ = 7
        center = (39.5, 31.5, 7)
        projected = self.app.renderer.worldToScreen(*center)
        with patch.object(pygame.mouse, "get_pos", return_value=(50, 50)):
            for _ in range(4):
                self.app._rotateViewAndRecenter(1)
                self.assertEqual(
                    self.app.renderer.worldToScreen(*center), projected
                )

    def test_magic_wand_overlay_uses_display_size(self):
        """A retained selection must remain renderable after placing a block."""
        self.app.magicWandSelection = {(5, 5, 1)}
        self.app.world.setBlock(5, 5, 1, app_module.BlockType.STONE)
        self.app._renderMagicWandSelection()

    def test_occlusion_uses_camera_facing_neighbors_in_every_view(self):
        center = (5, 5, 2)
        directions = (
            ((0, 1), (1, 0)),
            ((1, 0), (0, -1)),
            ((0, -1), (-1, 0)),
            ((-1, 0), (0, 1)),
        )
        for rotation, sides in enumerate(directions):
            self.app.world.clear()
            self.app.renderer.setViewRotation(rotation)
            self.app.world.setBlock(*center, app_module.BlockType.STONE)
            self.app.world.setBlock(5, 5, 3, app_module.BlockType.STONE)
            for dx, dy in sides:
                self.app.world.setBlock(5 + dx, 5 + dy, 2, app_module.BlockType.STONE)
            self.assertTrue(self.app._isFullyOccluded(*center, app_module.BlockType.STONE))

    def test_zoom_keeps_projected_world_point_under_cursor(self):
        self.app.zoomLevel = 0.5
        self.app.renderer.setZoom(0.5)
        self.app.renderer.setViewRotation(0)
        point = (4, 6, 2)
        cursor = self.app.renderer.worldToScreen(*point)
        self.app._handleZoom(0.1, *cursor)
        projected = self.app.renderer.worldToScreen(*point)
        self.assertLessEqual(abs(projected[0] - cursor[0]), 1)
        self.assertLessEqual(abs(projected[1] - cursor[1]), 1)

    def test_large_zoom_uses_complete_fallback_then_finishes_exact_surface(self):
        self.app.world.resize(80, 80, 16, min_y=0, preserve=False)
        with self.app.world.bulkUpdate():
            for x in range(80):
                for y in range(80):
                    self.app.world.setBlock(x, y, 0, app_module.BlockType.STONE)
        self.app.zoomLevel = 0.2
        self.app.renderer.setZoom(self.app.zoomLevel)
        self.app._centerOnCell(40, 40, 0)
        self.app.renderer.offsetX = self.app.targetOffsetX
        self.app.renderer.offsetY = self.app.targetOffsetY
        self.app._invalidateViewCaches()
        self.app._renderWorld()
        exactSize = self.app._worldSurfaceCache.get_size()

        cursor = ((app_module.WINDOW_WIDTH - app_module.PANEL_WIDTH) // 2, 400)
        self.app._handleZoom(0.025, *cursor)
        self.assertIsNotNone(self.app._worldZoomFallback)
        self.assertEqual(self.app._worldZoomFallback.get_size(), exactSize)
        self.app._renderWorld()
        self.assertGreater(self.app._worldSurfaceBuildIndex, 0)

        for _ in range(8):
            self.app._renderWorld()
            if self.app._worldZoomFallback is None:
                break
        self.assertIsNone(self.app._worldZoomFallback)
        self.assertIsNotNone(self.app._worldSurfaceCache)

    def test_large_rotation_keeps_complete_frame_while_exact_surface_rebuilds(self):
        self.app.world.resize(80, 80, 16, min_y=0, preserve=False)
        with self.app.world.bulkUpdate():
            for x in range(80):
                for y in range(80):
                    self.app.world.setBlock(x, y, 0, app_module.BlockType.STONE)
        self.app.zoomLevel = 0.2
        self.app.renderer.setZoom(self.app.zoomLevel)
        self.app._centerOnCell(40, 40, 0)
        self.app.renderer.offsetX = self.app.targetOffsetX
        self.app.renderer.offsetY = self.app.targetOffsetY
        self.app._invalidateViewCaches()
        self.app._renderWorld()

        cursor = (
            (app_module.WINDOW_WIDTH - app_module.PANEL_WIDTH) // 2,
            app_module.WINDOW_HEIGHT // 2,
        )
        with patch.object(pygame.mouse, "get_pos", return_value=cursor):
            self.app._rotateViewAndRecenter(1)
        self.assertIsNotNone(self.app._worldZoomFallback)
        self.app._renderWorld()
        self.assertGreater(self.app._worldSurfaceBuildIndex, 0)

        for _ in range(8):
            self.app._renderWorld()
            if self.app._worldZoomFallback is None:
                break
        self.assertIsNone(self.app._worldZoomFallback)
        self.assertIsNotNone(self.app._worldSurfaceCache)

    def test_fit_world_uses_precomputed_occupied_bounds(self):
        self.app.world.setBlock(2, 3, 1, app_module.BlockType.STONE)
        self.app.world.setBlock(10, 8, 6, app_module.BlockType.DEEPSLATE)

        with patch.object(
            self.app,
            "_fitPositionsToViewport",
            side_effect=AssertionError("fit should not rescan world positions"),
        ):
            self.app._fitWorldToViewport(notify=False)

        self.assertGreaterEqual(self.app.zoomLevel, self.app.zoomMin)
        self.assertLessEqual(self.app.zoomLevel, self.app.zoomMax)

    def test_exposed_blocks_receive_brighter_skylight_than_enclosed_blocks(self):
        with self.app.world.bulkUpdate():
            for x in range(3, 6):
                for y in range(3, 6):
                    for z in range(0, 3):
                        self.app.world.setBlock(x, y, z, app_module.BlockType.STONE)
        self.app.lightMap = {}
        self.app.currentDimension = app_module.DIMENSION_OVERWORLD
        sprite = self.app.assetManager.getBlockSprite(app_module.BlockType.STONE)
        enclosed = self.app._applyLighting(sprite, 4, 4, 1, app_module.BlockType.STONE)
        exposed = self.app._applyLighting(sprite, 4, 4, 2, app_module.BlockType.STONE)
        self.assertGreater(
            sum(pygame.transform.average_color(exposed)[:3]),
            sum(pygame.transform.average_color(enclosed)[:3]),
        )

    def test_finished_doors_and_stairs_use_model_icons_and_regular_categories(self):
        self.assertIn(app_module.BlockType.OAK_DOOR, app_module.BLOCK_CATEGORIES["Wood"])
        self.assertIn(app_module.BlockType.OAK_STAIRS, app_module.BLOCK_CATEGORIES["Wood"])
        self.assertIn(app_module.BlockType.COBBLESTONE_STAIRS, app_module.BLOCK_CATEGORIES["Stone & Brick"])
        self.assertIn(app_module.BlockType.IRON_DOOR, app_module.BLOCK_CATEGORIES["Functional"])
        self.assertNotIn("Experimental", app_module.BLOCK_CATEGORIES)
        for block in (
            app_module.BlockType.OAK_DOOR,
            app_module.BlockType.IRON_DOOR,
            app_module.BlockType.OAK_STAIRS,
            app_module.BlockType.COBBLESTONE_STAIRS,
        ):
            icon = self.app.assetManager.getIconSprite(block)
            self.assertEqual(icon.get_size(), (app_module.ICON_SIZE, app_module.ICON_SIZE))
            self.assertGreater(icon.get_bounding_rect(min_alpha=1).height, 0)

    def test_finished_special_blocks_use_regular_categories_and_model_sprites(self):
        expected = {
            app_module.BlockType.OXIDIZING_COPPER: "Ores & Minerals",
            app_module.BlockType.ENCHANTING_TABLE: "Functional",
            app_module.BlockType.SCULK_SENSOR: "Functional",
            app_module.BlockType.FIRE: "Light Sources",
            app_module.BlockType.SOUL_FIRE: "Nether",
            app_module.BlockType.MATRIX: "End",
        }
        for block, category in expected.items():
            self.assertIn(block, app_module.BLOCK_CATEGORIES[category])
            sprite = self.app.assetManager.getBlockSprite(block)
            icon = self.app.assetManager.getIconSprite(block)
            self.assertGreater(sprite.get_bounding_rect(min_alpha=1).height, 0)
            self.assertEqual(icon.get_size(), (app_module.ICON_SIZE, app_module.ICON_SIZE))
        self.assertEqual(
            app_module.BLOCK_DEFINITIONS[app_module.BlockType.MATRIX].name,
            "Matrix",
        )
        self.assertNotEqual(
            pygame.image.tostring(
                self.app.assetManager.sculkSensorSprites[False], "RGBA"
            ),
            pygame.image.tostring(
                self.app.assetManager.sculkSensorSprites[True], "RGBA"
            ),
        )

    def test_water_and_lava_interpolate_at_sixty_fps_without_speeding_cycles(self):
        assets = self.app.assetManager
        assets.liquidAnimationElapsed = 0.0
        assets.currentWaterVisualFrame = 0
        assets.currentLavaVisualFrame = 0
        assets.currentWaterFrame = 0
        assets.currentLavaFrame = 0
        assets.blockSprites[app_module.BlockType.WATER] = assets._liquidAnimationSprite(
            True, 8, 0
        )
        assets.blockSprites[app_module.BlockType.LAVA] = assets._liquidAnimationSprite(
            False, 8, 0
        )
        water_before = pygame.image.tostring(
            assets.getBlockSprite(app_module.BlockType.WATER), "RGBA"
        )
        lava_before = pygame.image.tostring(
            assets.getBlockSprite(app_module.BlockType.LAVA), "RGBA"
        )
        assets.updateAnimation(17)
        self.assertEqual(assets.currentWaterVisualFrame, 1)
        self.assertEqual(assets.currentLavaVisualFrame, 1)
        self.assertEqual(assets.currentWaterFrame, 0)
        self.assertEqual(assets.currentLavaFrame, 0)
        self.assertNotEqual(
            water_before,
            pygame.image.tostring(assets.getBlockSprite(app_module.BlockType.WATER), "RGBA"),
        )
        self.assertNotEqual(
            lava_before,
            pygame.image.tostring(assets.getBlockSprite(app_module.BlockType.LAVA), "RGBA"),
        )
        assets.updateAnimation(33)
        self.assertEqual(assets.currentWaterVisualFrame, 3)
        self.assertEqual(assets.currentWaterFrame, 1)
        self.assertEqual(assets.currentLavaFrame, 0)
        self.assertLessEqual(len(assets.liquidAnimationTextureCache), 192)

    def test_special_detail_models_use_source_shaped_geometry(self):
        renderer = self.app.assetManager.blockModelRenderer
        self.assertEqual(
            renderer.detail_boxes("ladder", app_module.Facing.SOUTH),
            ((0, 15, 0, 16, 16, 16),),
        )
        self.assertEqual(
            renderer.detail_boxes("chain"), ((6, 6, 0, 10, 10, 16),)
        )
        floorLantern = renderer.detail_boxes("lantern", is_open=False)
        hangingLantern = renderer.detail_boxes("lantern", is_open=True)
        self.assertEqual(max(box[5] for box in floorLantern), 11)
        self.assertEqual(max(box[5] for box in hangingLantern), 16)
        self.assertEqual(
            renderer.detail_boxes(
                "piston", app_module.Facing.EAST, is_open=True
            ),
            ((0, 0, 0, 12, 16, 16),),
        )
        eastHead = renderer.detail_boxes("piston_head", app_module.Facing.EAST)
        northHead = renderer.detail_boxes("piston_head", app_module.Facing.NORTH)
        self.assertEqual(eastHead[1], (0, 6, 6, 12, 10, 10))
        self.assertEqual(northHead[1], (6, 4, 6, 10, 16, 10))
        for block in (
            app_module.BlockType.LADDER,
            app_module.BlockType.CHAIN,
            app_module.BlockType.LANTERN,
            app_module.BlockType.SOUL_LANTERN,
        ):
            sprite = self.app.assetManager.getBlockSprite(block)
            self.assertGreater(sprite.get_bounding_rect(min_alpha=1).height, 0)

    def test_end_portal_frame_and_effects_have_source_heights(self):
        frame = self.app.assetManager.getBlockSprite(app_module.BlockType.END_PORTAL_FRAME)
        portal = self.app.assetManager.getBlockSprite(app_module.BlockType.END_PORTAL)
        gateway = self.app.assetManager.getBlockSprite(app_module.BlockType.END_GATEWAY)
        self.assertLess(frame.get_bounding_rect(min_alpha=1).height,
                        gateway.get_bounding_rect(min_alpha=1).height)
        self.assertLess(portal.get_bounding_rect(min_alpha=1).height,
                        gateway.get_bounding_rect(min_alpha=1).height)

    def test_end_gateway_effect_uses_java_1161_layer_math(self):
        parameters = self.app.assetManager._endPortalLayerParameters(2, 0.25)
        self.assertAlmostEqual(parameters[0], 8.5)
        self.assertAlmostEqual(parameters[1], 5.0 / 6.0)
        self.assertAlmostEqual(parameters[2], 34604.0)
        self.assertAlmostEqual(parameters[3], 2.0)
        self.assertEqual(len(tuple(
            self.app.assetManager._javaRandomPortalColors(16)
        )), 16)

    def test_fire_and_chest_models_have_depth_and_inset_geometry(self):
        fire = self.app.assetManager.getBlockSprite(app_module.BlockType.FIRE)
        chest = self.app.assetManager.getBlockSprite(app_module.BlockType.CHEST)
        fireBounds = fire.get_bounding_rect(min_alpha=1)
        chestBounds = chest.get_bounding_rect(min_alpha=1)
        self.assertGreater(fireBounds.width, app_module.TILE_WIDTH // 2)
        self.assertLess(chestBounds.width, app_module.TILE_WIDTH)
        self.assertIsNotNone(
            self.app.assetManager.textures.get("chest_normal_latch.png")
        )

    def test_stair_variants_are_connected_transforms_of_canonical_volume(self):
        renderer = self.app.assetManager.blockModelRenderer
        expectedCounts = {
            app_module.StairShape.STRAIGHT: 6,
            app_module.StairShape.INNER_LEFT: 7,
            app_module.StairShape.INNER_RIGHT: 7,
            app_module.StairShape.OUTER_LEFT: 5,
            app_module.StairShape.OUTER_RIGHT: 5,
        }
        for facing in app_module.Facing:
            for shape, expectedCount in expectedCounts.items():
                bottom = renderer.stair_occupancy(
                    facing, shape, app_module.SlabPosition.BOTTOM
                )
                top = renderer.stair_occupancy(
                    facing, shape, app_module.SlabPosition.TOP
                )
                self.assertEqual(len(bottom), expectedCount)
                self.assertEqual(top, {(x, y, 1 - z) for x, y, z in bottom})
                pending = {next(iter(bottom))}
                reached = set()
                while pending:
                    cell = pending.pop()
                    if cell in reached:
                        continue
                    reached.add(cell)
                    x, y, z = cell
                    pending.update({
                        neighbor for neighbor in (
                            (x + 1, y, z), (x - 1, y, z),
                            (x, y + 1, z), (x, y - 1, z),
                            (x, y, z + 1), (x, y, z - 1),
                        ) if neighbor in bottom and neighbor not in reached
                    })
                self.assertEqual(reached, set(bottom))

        north = renderer.stair_occupancy(
            app_module.Facing.NORTH,
            app_module.StairShape.STRAIGHT,
            app_module.SlabPosition.BOTTOM,
        )
        north_upper = {(x, y) for x, y, z in north if z == 1}
        self.assertEqual(north_upper, {(0, 0), (1, 0)})
        east = renderer.stair_occupancy(
            app_module.Facing.EAST,
            app_module.StairShape.STRAIGHT,
            app_module.SlabPosition.BOTTOM,
        )
        east_upper = {(x, y) for x, y, z in east if z == 1}
        self.assertEqual(east_upper, {(1, 0), (1, 1)})

    def test_copper_stage_round_trips_and_nearby_sculk_sensor_pulses(self):
        copper = (3, 3, 1)
        sensor = (5, 3, 1)
        self.app.world.setBlock(*copper, app_module.BlockType.OXIDIZING_COPPER)
        props = app_module.BlockProperties(oxidationStage=2)
        self.app.world.setBlockProperties(*copper, props)
        self.app.world.setBlock(*sensor, app_module.BlockType.SCULK_SENSOR)
        self.app._updateSpecialBlocks(self.app.assetManager.oxidizingCopperSpeed)
        self.assertEqual(
            self.app.world.getBlockProperties(*copper).oxidationStage, 3
        )
        self.app._triggerSculkSensors(4, 3, 1)
        self.assertIn(sensor, self.app._sculkSensorActiveUntil)

        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "special.json.gz")
            self.assertTrue(self.app._saveBuilding(filepath=path, silent=True))
            self.app.world.clear()
            self.assertTrue(self.app._loadBuildingFromPath(path, silent=True))
        self.assertEqual(
            self.app.world.getBlockProperties(*copper).oxidationStage, 3
        )

    def test_tutorial_rooms_match_the_supplied_open_builds(self):
        caveBlocks = {
            (x, y, z): block for x, y, z, block, *_ in app_module.STRUCTURE_DARK_CAVE["blocks"]
        }
        courtyardBlocks = {
            (x, y, z): block
            for x, y, z, block, *_ in app_module.STRUCTURE_RAIN_COURTYARD["blocks"]
        }

        # Lighting is a concave shell: both camera-facing walls and the centre
        # of the roof are absent, while the back/side shell remains solid.
        self.assertIn((0, 6, 3), caveBlocks)
        self.assertIn((6, 0, 3), caveBlocks)
        self.assertNotIn((11, 6, 3), caveBlocks)
        self.assertNotIn((6, 11, 3), caveBlocks)
        self.assertNotIn((6, 6, 6), caveBlocks)

        # Weather contains four pillars and only partial roof sections; there
        # are no perimeter walls closing the courtyard.
        for pillar in ((2, 2), (11, 2), (2, 11), (11, 11)):
            self.assertIn((*pillar, 4), courtyardBlocks)
        self.assertNotIn((0, 6, 2), courtyardBlocks)
        self.assertNotIn((13, 6, 2), courtyardBlocks)
        self.assertNotIn((6, 0, 2), courtyardBlocks)
        self.assertNotIn((6, 13, 2), courtyardBlocks)
        self.assertIn((6, 2, 5), courtyardBlocks)
        self.assertNotIn((6, 6, 5), courtyardBlocks)

    def test_build_load_is_transactional(self):
        self.app.world.setBlock(2, 3, 1, app_module.BlockType.STONE)
        with tempfile.TemporaryDirectory() as tempDir:
            goodPath = os.path.join(tempDir, "good.json.gz")
            self.assertTrue(self.app._saveBuilding(filepath=goodPath, silent=True))
            self.app.world.clear()
            self.assertTrue(self.app._loadBuildingFromPath(goodPath, silent=True))
            self.assertEqual(self.app.world.getBlock(2, 3, 1), app_module.BlockType.STONE)

            badPath = os.path.join(tempDir, "bad.json")
            with open(badPath, "w", encoding="utf-8") as handle:
                json.dump({"not_blocks": []}, handle)
            self.assertFalse(self.app._loadBuildingFromPath(badPath, silent=True))
            self.assertEqual(self.app.world.getBlock(2, 3, 1), app_module.BlockType.STONE)

    def test_v5_save_round_trips_large_bounds_and_provenance(self):
        self.app.world.resize(64, 80, 96, min_y=-32, preserve=False)
        self.app.sceneMetadata = {
            "kind": "world", "provider": "test", "version": "1.21"
        }
        self.app.world.setBlock(63, 79, -32, app_module.BlockType.DEEPSLATE)
        with tempfile.TemporaryDirectory() as tempDir:
            path = os.path.join(tempDir, "large.json.gz")
            self.assertTrue(self.app._saveBuilding(filepath=path, silent=True))
            self.app.world.resize(12, 12, 12, preserve=False)
            self.assertTrue(self.app._loadBuildingFromPath(path, silent=True))
        self.assertEqual(
            (self.app.world.width, self.app.world.depth, self.app.world.height, self.app.world.min_y),
            (64, 80, 96, -32),
        )
        self.assertEqual(self.app.world.getBlock(63, 79, -32), app_module.BlockType.DEEPSLATE)
        self.assertEqual(self.app.sceneMetadata["provider"], "test")

    def test_world_scene_preserves_nested_java_state_and_structure_role(self):
        payload = {
            "version": 5,
            "dimension": "end",
            "bounds": {"width": 16, "depth": 16, "height": 32, "min_y": 0},
            "scene": {"kind": "world", "default_terrain_view": "transparent"},
            "blocks": [{
                "x": 3, "y": 4, "z": 5, "type": "PURPUR_STAIRS",
                "state": {"facing": "west", "half": "top", "shape": "outer_left"},
                "role": "structure",
            }],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "state.json.gz")
            with gzip.open(path, "wt", encoding="utf-8") as handle:
                json.dump(payload, handle)
            self.assertTrue(self.app._loadBuildingFromPath(path, silent=True))
        props = self.app.world.getBlockProperties(3, 4, 5)
        self.assertEqual(props.facing, app_module.Facing.WEST)
        self.assertEqual(props.slabPosition, app_module.SlabPosition.TOP)
        self.assertEqual(props.stairShape, app_module.StairShape.OUTER_LEFT)
        self.assertIn((3, 4, 5), self.app.sceneStructurePositions)
        self.assertEqual(self.app.sceneTerrainMode, "transparent")

    def test_curated_ancient_city_opens_on_256_canvas(self):
        path = Path(app_module.WORLDS_DIR) / "ancient_city_121.json.gz"
        self.assertTrue(self.app._loadBuildingFromPath(str(path), silent=True))
        self.assertEqual((self.app.world.width, self.app.world.depth), (256, 256))
        self.assertEqual(self.app.world.min_y, -64)
        self.assertGreater(len(self.app.world.blocks), 100000)
        self.assertEqual(self.app.sceneMetadata["version"], "1.21")
        self.assertIn(app_module.BlockType.REINFORCED_DEEPSLATE, self.app.world.blocks.values())
        self.assertLessEqual(self.app.zoomLevel, self.app.overviewZoomThreshold)

    def test_treasure_bastion_surface_does_not_vanish_at_overview_zoom(self):
        path = Path(app_module.WORLDS_DIR) / "bastion_treasure_1161.json.gz"
        self.assertTrue(self.app._loadBuildingFromPath(str(path), silent=True))
        self.app.zoomLevel = min(0.12, self.app.overviewZoomThreshold)
        self.app.renderer.setZoom(self.app.zoomLevel)
        self.app._invalidateViewCaches()
        drawn = {(x, y, z) for _, x, y, z, _ in self.app._visibleBlocksInDrawOrder()}
        drawnStructure = drawn & self.app.sceneStructurePositions
        visibleStructureSurface = {
            pos for pos in self.app.world.surfaceBlocks
            if pos in self.app.sceneStructurePositions
            if not self.app._isFullyOccluded(
                *pos, self.app.world.blocks[pos]
            )
            if self.app._blockIsOnScreen(*pos, self.app._worldSurfaceMargin)
        }
        self.assertTrue(visibleStructureSurface)
        self.assertTrue(visibleStructureSurface <= drawnStructure)
        self.assertIn(
            max(self.app.sceneStructurePositions, key=lambda pos: pos[2]), drawn
        )

    def test_trial_chamber_exterior_masonry_uses_visual_glass_without_data_changes(self):
        path = Path(app_module.WORLDS_DIR) / "trial_chamber_121.json.gz"
        self.assertTrue(self.app._loadBuildingFromPath(str(path), silent=True))
        self.assertEqual(self.app.sceneMetadata["exterior_shell_view"], "glass")
        masonry = {
            app_module.BlockType.TUFF_BRICKS,
            app_module.BlockType.POLISHED_TUFF,
            app_module.BlockType.CHISELED_TUFF,
            app_module.BlockType.CHISELED_TUFF_BRICKS,
        }
        exterior = next(
            pos for pos in self.app.sceneStructurePositions
            if self.app.world.getBlock(*pos) in masonry
            and self.app._usesExteriorShellGlass(
                *pos, self.app.world.getBlock(*pos)
            )
        )
        originalType = self.app.world.getBlock(*exterior)
        self.assertIn(originalType, masonry)
        self.assertTrue(self.app._usesExteriorShellGlass(*exterior, originalType))
        self.assertEqual(self.app.world.getBlock(*exterior), originalType)
        interior = next(
            pos for pos in self.app.sceneStructurePositions
            if self.app.world.getBlock(*pos) in masonry
            and pos not in self.app.sceneExteriorGlassPositions
        )
        interiorType = self.app.world.getBlock(*interior)
        self.assertFalse(self.app._usesExteriorShellGlass(*interior, interiorType))
        self.assertEqual(self.app.world.getBlock(*interior), interiorType)

    def test_canvas_resize_reports_clipping_and_extends_the_floor(self):
        self.app.world.resize(32, 32, 32, preserve=False)
        self.app.world.setBlock(31, 31, 31, app_module.BlockType.DIAMOND_BLOCK)
        dimensions, clipped = self.app._canvasResizeImpact(-16)
        self.assertEqual(dimensions, (16, 16, 16))
        self.assertEqual(clipped, 1)
        self.app._resizeCanvas(-16)
        self.assertEqual((self.app.world.width, self.app.world.depth, self.app.world.height), dimensions)
        self.assertNotIn((31, 31, 31), self.app.world.blocks)
        self.app._resizeCanvas(16)
        self.assertEqual(self.app.world.getBlock(31, 31, 0), app_module.BlockType.GRASS)

    def test_canvas_growth_is_centered_and_preserves_relative_world_state(self):
        self.app.world.setBlock(1, 2, 3, app_module.BlockType.WATER)
        self.app.world.liquidLevels[(1, 2, 3)] = 6
        self.app.world.liquidSources.add((1, 2, 3))
        self.app.sceneStructurePositions = {(4, 5, 1)}
        self.app.world.sceneStructurePositions = self.app.sceneStructurePositions
        self.app.world.setBlock(4, 5, 1, app_module.BlockType.STONE_BRICKS)

        self.app._resizeCanvas(16)

        self.assertEqual((self.app.world.width, self.app.world.depth), (28, 28))
        self.assertEqual(self.app.world.getBlock(9, 10, 3), app_module.BlockType.WATER)
        self.assertEqual(self.app.world.liquidLevels[(9, 10, 3)], 6)
        self.assertIn((9, 10, 3), self.app.world.liquidSources)
        self.assertIn((12, 13, 1), self.app.sceneStructurePositions)
        self.assertEqual(
            self.app.world.getBlock(12, 13, 1), app_module.BlockType.STONE_BRICKS
        )
        self.assertEqual(self.app.world.getBlock(0, 0, 0), app_module.BlockType.GRASS)
        self.assertEqual(self.app.world.getBlock(27, 27, 0), app_module.BlockType.GRASS)

    def test_local_terrain_noise_protects_build_columns_and_is_undoable(self):
        self.app._createInitialFloor()
        self.app.world.setBlock(5, 5, 1, app_module.BlockType.DIAMOND_BLOCK)
        before = dict(self.app.world.blocks)

        with patch.object(app_module.random, "randint", return_value=8731):
            self.assertTrue(self.app._applyLocalTerrainNoise())

        self.assertEqual(
            self.app.world.getBlock(5, 5, 1), app_module.BlockType.DIAMOND_BLOCK
        )
        self.assertEqual(self.app.world.getHighestBlock(5, 5), 1)
        self.assertTrue(any(z > 1 for _x, _y, z in self.app.world.blocks))
        command = self.app.undoManager.undo()
        self.assertIsNotNone(command)
        self.assertEqual(self.app.world.blocks, before)

    def test_terrain_hover_preview_holds_the_seed_used_on_click(self):
        self.app._createInitialFloor()
        self.app._clearTerrainNoisePreview()
        seed = 421337
        with (
            patch.object(pygame.mouse, "get_pos", return_value=self.app.terrainNoiseButtonRect.center),
            patch.object(app_module.random, "randint", return_value=seed),
        ):
            self.app._renderTerrainNoiseButton()
        self.assertEqual(self.app._terrainNoisePreviewSeed, seed)
        preview_columns = tuple(self.app._terrainNoisePreviewPlan["columns"])
        self.assertTrue(preview_columns)
        self.assertTrue(self.app._applyLocalTerrainNoise())
        self.assertEqual(self.app.sceneMetadata["terrain_noise_seed"], seed)
        self.assertEqual(
            {(x, y, elevation) for x, y, elevation in preview_columns},
            {
                (x, y, self.app.world.getHighestBlock(x, y) - self.app.world.min_y)
                for x, y, elevation in preview_columns
            },
        )

    def test_persistent_tome_starts_the_advanced_tutorial(self):
        self.app._renderTutorialTomeButton(
            pygame.Rect(app_module.WINDOW_WIDTH - 42, app_module.WINDOW_HEIGHT - 42, 32, 32)
        )
        tutorial = self.app.tutorialScreen
        old_callback = tutorial.onStepChange
        tutorial.onStepChange = None
        try:
            tutorial.currentStep = 9
            tutorial.visible = False
            self.app._handlePanelClick(*self.app.tutorialTomeRect.center)
            self.assertTrue(tutorial.visible)
            self.assertTrue(self.app.tutorialAdvancedMode)
            self.assertEqual(tutorial.currentStep, 0)
            self.assertEqual(len(tutorial.TUTORIAL_STEPS), 17)
        finally:
            tutorial.onStepChange = old_callback
            tutorial.hide()

    def test_basic_tutorial_restores_the_existing_build_and_editor_state(self):
        self.app.world.setBlock(2, 3, 1, app_module.BlockType.DIAMOND_BLOCK)
        self.app.hotbar[0] = app_module.BlockType.OBSIDIAN
        self.app.selectedBlock = app_module.BlockType.OBSIDIAN
        original_blocks = dict(self.app.world.blocks)
        original_dimensions = (
            self.app.world.width, self.app.world.depth, self.app.world.height,
            self.app.world.min_y,
        )

        self.app._beginTutorial(advanced=False)
        self.assertTrue(self.app.tutorialScreen.visible)
        self.assertNotEqual(dict(self.app.world.blocks), original_blocks)
        self.app.tutorialScreen.hide()

        self.assertEqual(dict(self.app.world.blocks), original_blocks)
        self.assertEqual((
            self.app.world.width, self.app.world.depth, self.app.world.height,
            self.app.world.min_y,
        ), original_dimensions)
        self.assertEqual(self.app.hotbar[0], app_module.BlockType.OBSIDIAN)
        self.assertEqual(self.app.selectedBlock, app_module.BlockType.OBSIDIAN)
        self.assertIsNone(self.app._tutorialSessionSnapshot)

    def test_advanced_tutorial_uses_dedicated_32x32_showcases_and_restores(self):
        self.app.world.setBlock(2, 3, 1, app_module.BlockType.EMERALD_BLOCK)
        original_blocks = dict(self.app.world.blocks)
        basic_count = len(app_module.STRUCTURE_WELCOME_SHOWCASE["blocks"])

        self.app._beginTutorial(advanced=True)
        self.assertEqual(
            (self.app.world.width, self.app.world.depth, self.app.world.height),
            (32, 32, 32),
        )
        non_floor = sum(1 for (x, y, z) in self.app.world.blocks if z > 0)
        self.assertGreater(non_floor, basic_count)
        self.app.tutorialScreen.hide()
        self.assertEqual(dict(self.app.world.blocks), original_blocks)

    def test_every_advanced_lesson_has_a_fitted_scene_and_matching_hotbar(self):
        self.app._beginTutorial(advanced=True)
        tutorial = self.app.tutorialScreen
        try:
            for index, names in enumerate(tutorial.ADVANCED_HOTBARS):
                self.app._onTutorialStepChange(index)
                self.assertEqual((self.app.world.width, self.app.world.depth), (32, 32))
                title = tutorial.TUTORIAL_STEPS[index]["title"]
                expected_dimension = (
                    app_module.DIMENSION_NETHER if "Nether" in title else
                    app_module.DIMENSION_END if "End" in title else
                    app_module.DIMENSION_OVERWORLD
                )
                self.assertEqual(self.app.currentDimension, expected_dimension)
                self.assertEqual(self.app.world.dimension, expected_dimension)
                self.assertIsNotNone(self.app.world.occupiedBounds)
                self.assertGreater(len(self.app.world.blocks), 250)
                expected = [tutorial._iconNameToBlockType(name) for name in names]
                self.assertNotIn(None, expected)
                self.assertEqual(self.app.hotbar, expected)
                self.assertGreater(self.app.zoomLevel, 0)
                self.assertLessEqual(self.app.zoomLevel, 1)

            # The advanced liquid lesson contains both controlled reservoirs,
            # and the End lesson has non-flat terrain beneath its tower.
            self.app._onTutorialStepChange(8)
            self.assertIn(app_module.BlockType.WATER, self.app.world.blocks.values())
            self.assertIn(app_module.BlockType.LAVA, self.app.world.blocks.values())
            self.app._onTutorialStepChange(11)
            endHeights = {
                self.app.world.getHighestBlock(x, y)
                for x in range(10, 22) for y in range(10, 22)
            }
            self.assertGreater(len(endHeights), 3)
        finally:
            tutorial.hide()

    def test_tutorial_window_drags_minimizes_and_restores(self):
        tutorial = app_module.TutorialScreen(
            app_module.WINDOW_WIDTH, app_module.WINDOW_HEIGHT
        )
        tutorial.visible = True
        start = (tutorial.panelX, tutorial.panelY)
        dragStart = (tutorial.panelX + 80, tutorial.panelY + 20)
        self.assertTrue(tutorial.handleEvent(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": dragStart}
        )))
        self.assertTrue(tutorial.dragging)
        dragEnd = (dragStart[0] - 140, dragStart[1] + 90)
        self.assertTrue(tutorial.handleEvent(pygame.event.Event(
            pygame.MOUSEMOTION, {"pos": dragEnd}
        )))
        tutorial.handleEvent(pygame.event.Event(
            pygame.MOUSEBUTTONUP, {"button": 1, "pos": dragEnd}
        ))
        self.assertNotEqual((tutorial.panelX, tutorial.panelY), start)
        self.assertFalse(tutorial.dragging)

        self.assertTrue(tutorial.handleEvent(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {"button": 1, "pos": tutorial.minimizeButtonRect.center},
        )))
        self.assertTrue(tutorial.minimized)
        self.assertFalse(tutorial.handleEvent(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": (100, 100)}
        )))
        self.assertTrue(tutorial.handleEvent(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {"button": 1, "pos": tutorial._restoreTileRect().center},
        )))
        self.assertFalse(tutorial.minimized)

    def test_fit_world_button_label_has_no_percentage(self):
        self.app.sceneStructurePositions.clear()
        with patch.object(pygame.mouse, "get_pos", return_value=(0, 0)), patch.object(
            self.app.assetManager, "drawButton"
        ) as drawButton, patch.object(self.app, "_renderTerrainNoiseButton"):
            self.app._renderFitWorldButton()
        labels = [call.args[2] for call in drawButton.call_args_list]
        self.assertIn("Fit World", labels)
        self.assertFalse(any("%" in label for label in labels))

    def test_complete_world_catalog_uses_supported_placeable_palette(self):
        from engine.world_catalog import WORLD_ENTRIES, world_catalog

        entries = world_catalog(app_module.WORLDS_DIR)
        self.assertEqual(len(entries), 15)
        self.assertEqual({entry.category for entry in entries}, {"Overworld", "Nether", "The End"})
        for entry in WORLD_ENTRIES:
            path = Path(app_module.WORLDS_DIR) / entry.filename
            with gzip.open(path, "rt", encoding="utf-8") as handle:
                scene = json.load(handle)
            expectedTerrain = (
                "transparent"
                if entry.scene_id in {"ancient_city_121", "trial_chamber_121"}
                else "all"
            )
            self.assertEqual(scene["scene"]["default_terrain_view"], expectedTerrain)
            self.assertGreater(len(scene["blocks"]), 50000, entry.name)
            for block in scene["blocks"]:
                self.assertIn(block["type"], app_module.BlockType.__members__, (entry.name, block))
                self.assertNotIn(
                    block.get("minecraft"),
                    {"minecraft:jigsaw", "minecraft:structure_block", "minecraft:structure_void"},
                )

    def test_new_dimension_worlds_expose_source_backed_scene_contracts(self):
        expected = {
            "nether_fortress_biomes_1161.json.gz": ("nether", False),
            "ocean_monument_1161.json.gz": ("overworld", True),
        }
        for filename, (dimension, underwater) in expected.items():
            with self.subTest(filename=filename):
                path = Path(app_module.WORLDS_DIR) / filename
                with gzip.open(path, "rt", encoding="utf-8") as handle:
                    data = json.load(handle)
                self.assertEqual(data["dimension"], dimension)
                self.assertEqual(bool(data["scene"].get("underwater")), underwater)
                self.assertGreater(data["scene"]["structure_blocks"], 1000)
                self.assertGreater(len(data["blocks"]), 250000)
        with gzip.open(
            Path(app_module.WORLDS_DIR) / "nether_fortress_biomes_1161.json.gz",
            "rt", encoding="utf-8",
        ) as handle:
            nether = json.load(handle)
        self.assertEqual(len(nether["scene"]["biome_regions"]), 5)
        with gzip.open(
            Path(app_module.WORLDS_DIR) / "ocean_monument_1161.json.gz",
            "rt", encoding="utf-8",
        ) as handle:
            ocean = json.load(handle)
        self.assertEqual(len(ocean["scene"]["decorations"]), 4)
        self.assertIn("elder_guardian", {item["type"] for item in ocean["scene"]["decorations"]})

    def test_end_city_world_structure_sits_above_terrain(self):
        path = Path(app_module.WORLDS_DIR) / "end_city_1161.json.gz"
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            scene = json.load(handle)
        structure = [block for block in scene["blocks"] if block.get("role") == "structure"]
        terrain = [block for block in scene["blocks"] if block.get("role") != "structure"]
        terrainTop = {}
        for block in terrain:
            column = (block["x"], block["y"])
            terrainTop[column] = max(terrainTop.get(column, -999), block["z"])
        structureBase = {}
        for block in structure:
            column = (block["x"], block["y"])
            structureBase[column] = min(
                structureBase.get(column, 999), block["z"]
            )
        shared = set(terrainTop) & set(structureBase)
        self.assertTrue(shared)
        self.assertTrue(all(
            terrainTop[column] < structureBase[column] for column in shared
        ))
        padHeights = {
            terrainTop[(x, y)]
            for x in range(99, 156) for y in range(105, 151)
        }
        self.assertGreaterEqual(len(padHeights), 5)
        groundContacts = {
            column for column, base in structureBase.items() if base == 19
        }
        self.assertTrue(groundContacts)
        self.assertTrue(all(terrainTop[column] == 18 for column in groundContacts))

    def test_small_canvas_resets_camera_after_large_world(self):
        path = Path(app_module.WORLDS_DIR) / "ancient_city_121.json.gz"
        self.assertTrue(self.app._loadBuildingFromPath(str(path), silent=True))
        self.app.world.resize(
            app_module.GRID_WIDTH, app_module.GRID_DEPTH, app_module.GRID_HEIGHT,
            min_y=0, preserve=False,
        )
        self.app._createInitialFloor()
        self.app._frameCurrentCanvas()
        self.assertEqual(self.app.zoomLevel, 1.0)
        self.assertEqual(self.app.cameraFocusZ, 0)

    def test_dimension_change_from_world_resets_minimum_canvas(self):
        path = Path(app_module.WORLDS_DIR) / "bastion_bridge_1161.json.gz"
        self.assertTrue(self.app._loadBuildingFromPath(str(path), silent=True))
        self.assertGreater(self.app.world.width, app_module.GRID_WIDTH)
        self.app._switchDimension(app_module.DIMENSION_OVERWORLD)
        self.assertEqual(
            (self.app.world.width, self.app.world.depth, self.app.world.height),
            (app_module.GRID_WIDTH, app_module.GRID_DEPTH, app_module.GRID_HEIGHT),
        )
        self.assertEqual(len(self.app.world.blocks), app_module.GRID_WIDTH * app_module.GRID_DEPTH)
        self.assertEqual(
            set(self.app.world.blocks.values()), {app_module.BlockType.GRASS}
        )

    def test_clicking_active_dimension_does_not_reset_canvas(self):
        self.app.world.resize(32, 32, 32, preserve=False)
        self.app.world.setBlock(20, 20, 5, app_module.BlockType.DIAMOND_BLOCK)
        self.app.currentDimension = app_module.DIMENSION_OVERWORLD
        self.app._switchDimension(app_module.DIMENSION_OVERWORLD)
        self.assertEqual((self.app.world.width, self.app.world.depth), (32, 32))
        self.assertEqual(
            self.app.world.getBlock(20, 20, 5), app_module.BlockType.DIAMOND_BLOCK
        )

    def test_runtime_and_packaged_icons_have_padding_and_multiple_sizes(self):
        from engine.app_icon import (
            render_explorer_icon_surface,
            render_runtime_icon_surface,
        )

        artwork = pygame.image.load(ROOT / "Assets" / "Icons" / "Respawn_Anchor.png")
        icon = render_runtime_icon_surface(artwork, 64)
        bounds = icon.get_bounding_rect(min_alpha=1)
        self.assertGreater(bounds.left, 0)
        self.assertGreater(bounds.top, 0)
        self.assertLess(bounds.right, 64)
        self.assertLess(bounds.bottom, 64)

        ico = ROOT / "Assets" / "Icons" / "Respawn_Anchor.ico"
        with ico.open("rb") as handle:
            reserved, kind, count = struct.unpack("<HHH", handle.read(6))
            entries = [struct.unpack("<BBBBHHII", handle.read(16)) for _ in range(count)]
        self.assertEqual((reserved, kind), (0, 1))
        self.assertEqual(
            {256 if entry[0] == 0 else entry[0] for entry in entries},
            {16, 32, 48, 64, 128, 256},
        )
        for size in (16, 32, 48, 256):
            explorer = render_explorer_icon_surface(artwork, size)
            explorer_artwork = explorer.get_bounding_rect(min_alpha=1)
            runtime_artwork = render_runtime_icon_surface(
                artwork, size
            ).get_bounding_rect(min_alpha=1)
            self.assertGreater(explorer_artwork.left, 0)
            self.assertLess(explorer_artwork.right, size)
            self.assertLessEqual(abs(explorer_artwork.width - runtime_artwork.width), 1)
            self.assertLessEqual(abs(explorer_artwork.height - runtime_artwork.height), 1)

    def test_optional_native_sort_matches_python_painter_order(self):
        from engine import build_io, native_acceleration

        positions = {
            (x, y, z)
            for x in range(-7, 9)
            for y in range(-5, 6)
            for z in range(-2, 5)
            if (x * 3 + y * 5 + z * 7) % 4
        }
        if native_acceleration.backend_name() != "rust":
            self.skipTest("optional Rust accelerator is not built")
        for rotation in range(4):
            native = native_acceleration.sort_positions(positions, rotation)
            self.assertIsNotNone(native)
            native_positions, native_indices, native_depths = native
            native_rows = tuple(
                (native_depths[output], *native_positions[index])
                for output, index in enumerate(native_indices)
            )
            expected_positions = sorted(
                positions,
                key=lambda position: (
                    build_io._depth_key(rotation, position),
                    position[2],
                    position[0],
                    position[1],
                ),
            )
            expected = tuple(
                (build_io._depth_key(rotation, position), *position)
                for position in expected_positions
            )
            self.assertEqual(native_rows, expected)

    def test_large_json_structure_places_at_cursor_without_clipping(self):
        self.app.selectedStructure = "end_city_tower"
        self.app.hoveredCell = (5, 5, 1)
        self.app._placeStructureAtMouse(0, 0)
        expected = len(app_module.PREMADE_STRUCTURES["end_city_tower"]["blocks"])
        self.assertEqual(len(self.app.world.blocks), expected)
        self.assertTrue(all(self.app.world.isInBounds(*pos) for pos in self.app.world.blocks))
        self.app.undoManager.undo()
        self.assertFalse(self.app.world.blocks)

    def test_large_world_accepts_an_edit_and_keeps_rotations_prepared(self):
        path = Path(app_module.WORLDS_DIR) / "bastion_bridge_1161.json.gz"
        self.assertTrue(self.app._loadBuildingFromPath(str(path), silent=True))
        x = self.app.world.width // 2
        y = self.app.world.depth // 2
        z = min(
            self.app.world.max_y_exclusive - 1,
            self.app.world.getHighestBlock(x, y) + 1,
        )
        self.assertTrue(
            self.app._placeBlockWithUndo(x, y, z, app_module.BlockType.STONE)
        )
        self.assertEqual(
            self.app.world.drawOrdersRevision, self.app.world.revision
        )
        self.app._fitWorldToViewport(notify=False)
        for _ in range(4):
            self.app._rotateViewAndRecenter(1)
            self.app._renderWorld()

    def test_structure_door_generation_is_part_of_the_same_undo(self):
        key = "_door_undo_fixture"
        app_module.PREMADE_STRUCTURES[key] = {
            "name": "Door Undo Fixture",
            "blocks": [(0, 0, 0, app_module.BlockType.OAK_DOOR)],
        }
        try:
            self.app.selectedStructure = key
            self.app.hoveredCell = (4, 4, 1)
            self.app._placeStructureAtMouse(0, 0)
            self.assertEqual(len(self.app.world.blocks), 2)
            self.app.undoManager.undo()
            self.assertFalse(self.app.world.blocks)
        finally:
            app_module.PREMADE_STRUCTURES.pop(key, None)

    def test_quick_swap_uses_transactional_door_state(self):
        self.app.world.setBlock(4, 4, 1, app_module.BlockType.STONE)
        self.app.hoveredCell = (4, 4, 1)
        self.app.selectedBlock = app_module.BlockType.OAK_DOOR
        self.assertTrue(self.app._quickSwapBlock(0, 0))
        self.assertEqual(self.app.world.getBlock(4, 4, 1), app_module.BlockType.OAK_DOOR)
        self.assertEqual(self.app.world.getBlock(4, 4, 2), app_module.BlockType.OAK_DOOR)
        self.app.undoManager.undo()
        self.assertEqual(self.app.world.getBlock(4, 4, 1), app_module.BlockType.STONE)
        self.assertEqual(self.app.world.getBlock(4, 4, 2), app_module.BlockType.AIR)

    def test_replace_all_is_one_undoable_bulk_edit(self):
        for x in range(4):
            self.app.world.setBlock(x, 1, 1, app_module.BlockType.STONE)
        revision = self.app.world.revision

        replaced = self.app._replaceAllBlocks(
            app_module.BlockType.STONE, app_module.BlockType.DIRT
        )

        self.assertEqual(replaced, 4)
        self.assertEqual(len(self.app.undoManager.undo_stack), 1)
        self.assertEqual(self.app.world.revision, revision + 1)
        self.app.undoManager.undo()
        self.assertTrue(all(
            self.app.world.getBlock(x, 1, 1) == app_module.BlockType.STONE
            for x in range(4)
        ))

    def test_magic_wand_delete_is_one_undoable_bulk_edit(self):
        positions = {(2, 2, 1), (3, 2, 1), (3, 3, 1)}
        for pos in positions:
            self.app.world.setBlock(*pos, app_module.BlockType.BRICKS)
        self.app.magicWandSelection = set(positions)

        self.app._deleteMagicWandSelection()

        self.assertEqual(len(self.app.undoManager.undo_stack), 1)
        self.assertTrue(all(
            self.app.world.getBlock(*pos) == app_module.BlockType.AIR
            for pos in positions
        ))
        self.app.undoManager.undo()
        self.assertTrue(all(
            self.app.world.getBlock(*pos) == app_module.BlockType.BRICKS
            for pos in positions
        ))

    def test_stamp_is_one_undoable_bulk_edit(self):
        self.app.hoveredCell = (2, 2, 1)
        self.app.stampData = {
            (0, 0, 0): app_module.BlockType.STONE,
            (1, 0, 0): app_module.BlockType.DIRT,
        }

        self.app._handleStampClick()

        self.assertEqual(len(self.app.undoManager.undo_stack), 1)
        self.assertEqual(self.app.world.getBlock(2, 2, 1), app_module.BlockType.STONE)
        self.assertEqual(self.app.world.getBlock(3, 2, 1), app_module.BlockType.DIRT)
        self.app.undoManager.undo()
        self.assertEqual(self.app.world.getBlock(2, 2, 1), app_module.BlockType.AIR)
        self.assertEqual(self.app.world.getBlock(3, 2, 1), app_module.BlockType.AIR)

    def test_contextual_shortcuts_reach_the_intended_app_actions(self):
        def press(key, mods=0):
            event = SimpleNamespace(key=key, unicode="")
            with patch.object(pygame.key, "get_mods", return_value=mods):
                self.app._handleKeyDown(event)

        self.app.fillToolActive = False
        self.app.selectedBlock = app_module.BlockType.STONE
        press(pygame.K_f)
        self.assertTrue(self.app.fillToolActive)

        self.app.selectedBlock = app_module.BlockType.OAK_SLAB
        old_half = self.app.previewSlabPosition
        press(pygame.K_f)
        self.assertNotEqual(self.app.previewSlabPosition, old_half)
        self.assertTrue(self.app.fillToolActive)

        self.app.measurementMode = False
        self.app.mirrorModeX = False
        self.app.mirrorModeY = False
        press(pygame.K_m)
        press(pygame.K_m, pygame.KMOD_SHIFT)
        press(pygame.K_m, pygame.KMOD_CTRL)
        self.assertTrue(self.app.measurementMode)
        self.assertTrue(self.app.mirrorModeX)
        self.assertTrue(self.app.mirrorModeY)

    def test_camera_w_never_steals_normal_block_placement(self):
        def press_w(mods=0):
            event = SimpleNamespace(key=pygame.K_w, unicode="w")
            with patch.object(pygame.key, "get_mods", return_value=mods):
                self.app._handleKeyDown(event)

        self.app.magicWandMode = False
        self.app.magicWandSelection.clear()
        self.app.measurementMode = False
        self.app.replaceMode = False
        self.app.stampMode = False
        self.app.fillToolActive = False
        self.app.selectionActive = False
        self.app.structurePlacementMode = False
        self.app.selectedStructure = None

        press_w()
        self.assertFalse(self.app.magicWandMode)

        self.app.hoveredCell = (5, 5, 1)
        self.app.selectedBlock = app_module.BlockType.STONE
        with patch.object(pygame.key, "get_mods", return_value=0):
            self.app._handleMouseDown(SimpleNamespace(button=1, pos=(300, 300)))
        self.assertEqual(self.app.world.getBlock(5, 5, 1), app_module.BlockType.STONE)

        press_w(pygame.KMOD_CTRL | pygame.KMOD_SHIFT)
        self.assertTrue(self.app.magicWandMode)
        self.app.magicWandSelection = {(5, 5, 1)}
        self.app._selectBlockForPlacement(app_module.BlockType.DIRT)
        self.assertFalse(self.app.magicWandMode)
        self.assertFalse(self.app.magicWandSelection)

    def test_escape_cancels_editor_modes_before_quitting(self):
        def press_escape():
            event = SimpleNamespace(key=pygame.K_ESCAPE, unicode="")
            with patch.object(pygame.key, "get_mods", return_value=0):
                self.app._handleKeyDown(event)

        self.app.running = True
        self.app.historyPanelOpen = False
        self.app.settingsMenuOpen = False
        self.app.showShortcutsPanel = False
        self.app.blueprintMode = False
        self.app.fillToolActive = False
        self.app.measurementMode = False
        self.app.replaceMode = False
        self.app.stampMode = False
        self.app.selectionActive = True
        self.app.selectionStart = (1, 1, 1)
        self.app.selectionEnd = (2, 2, 2)
        press_escape()
        self.assertFalse(self.app.selectionActive)
        self.assertTrue(self.app.running)

        self.app.measurementMode = True
        press_escape()
        self.assertFalse(self.app.measurementMode)
        self.assertTrue(self.app.running)

        press_escape()
        self.assertFalse(self.app.running)

    def test_tutorial_loads_nether_and_end_showcases(self):
        for title, dimension, minimumBlocks in (
            ("The Nether", app_module.DIMENSION_NETHER, 500),
            ("The End", app_module.DIMENSION_END, 300),
        ):
            index = next(
                stepIndex
                for stepIndex, step in enumerate(app_module.TutorialScreen.TUTORIAL_STEPS)
                if step["title"] == title
            )
            self.app._onTutorialStepChange(index)
            self.assertEqual(self.app.currentDimension, dimension)
            self.assertGreaterEqual(len(self.app.world.blocks), minimumBlocks)
            if title == "The End":
                self.assertEqual((self.app.world.width, self.app.world.depth), (16, 16))
                self.assertIn(app_module.BlockType.END_STONE, self.app.world.blocks.values())
                self.assertIn(app_module.BlockType.END_STONE_BRICKS, self.app.world.blocks.values())
                self.assertIn(app_module.BlockType.MAGENTA_STAINED_GLASS, self.app.world.blocks.values())
                self.assertGreaterEqual(
                    max(z for (x, y, z), block in self.app.world.blocks.items()
                        if block == app_module.BlockType.PURPUR_BLOCK),
                    3,
                )
            occupied = self.app.world.blocks
            center = (
                (min(pos[0] for pos in occupied) + max(pos[0] for pos in occupied)) / 2,
                (min(pos[1] for pos in occupied) + max(pos[1] for pos in occupied)) / 2,
                (min(pos[2] for pos in occupied) + max(pos[2] for pos in occupied)) / 2,
            )
            self.assertGreater(self.app.zoomLevel, 0.0)
            self.assertLessEqual(self.app.zoomLevel, 1.0)
            centerScreen = self.app.renderer.worldToScreen(*center)
            self.assertAlmostEqual(
                centerScreen[0],
                (app_module.WINDOW_WIDTH - app_module.PANEL_WIDTH) / 2,
                delta=2,
            )
            self.assertAlmostEqual(centerScreen[1], 400, delta=2)

    def test_door_uses_two_synchronized_cells_and_undo(self):
        self.assertTrue(self.app._placeDoorWithUndo(
            3, 3, 1, app_module.BlockType.OAK_DOOR, app_module.Facing.SOUTH
        ))
        self.assertEqual(self.app.world.getBlock(3, 3, 1), app_module.BlockType.OAK_DOOR)
        self.assertEqual(self.app.world.getBlock(3, 3, 2), app_module.BlockType.OAK_DOOR)
        self.assertEqual(
            self.app.world.getBlockProperties(3, 3, 1).doorHalf,
            app_module.DoorHalf.LOWER,
        )
        self.assertEqual(
            self.app.world.getBlockProperties(3, 3, 2).doorHalf,
            app_module.DoorHalf.UPPER,
        )
        self.assertTrue(self.app._toggleDoor(3, 3, 2))
        self.assertTrue(self.app.world.getBlockProperties(3, 3, 1).isOpen)
        self.assertTrue(self.app.world.getBlockProperties(3, 3, 2).isOpen)
        self.assertTrue(self.app._removeBlockWithUndo(3, 3, 2))
        self.assertEqual(self.app.world.getBlock(3, 3, 1), app_module.BlockType.AIR)
        self.assertEqual(self.app.world.getBlock(3, 3, 2), app_module.BlockType.AIR)
        self.app.undoManager.undo()
        self.assertEqual(self.app.world.getBlock(3, 3, 1), app_module.BlockType.OAK_DOOR)
        self.assertEqual(self.app.world.getBlock(3, 3, 2), app_module.BlockType.OAK_DOOR)

    def test_stairs_derive_outer_corner_and_render_distinct_model(self):
        stair = app_module.BlockType.OAK_STAIRS
        self.app.world.setBlock(3, 3, 1, stair)
        self.app.world.setBlockProperties(
            3, 3, 1, app_module.BlockProperties(facing=app_module.Facing.EAST)
        )
        self.app.world.setBlock(4, 3, 1, stair)
        self.app.world.setBlockProperties(
            4, 3, 1, app_module.BlockProperties(facing=app_module.Facing.NORTH)
        )
        self.app._refreshStairTopologyAround(3, 3, 1)
        props = self.app.world.getBlockProperties(3, 3, 1)
        self.assertEqual(props.stairShape, app_module.StairShape.OUTER_LEFT)
        straight = self.app.assetManager.getStairSprite(
            stair, app_module.Facing.EAST, app_module.StairShape.STRAIGHT,
            app_module.SlabPosition.BOTTOM,
        )
        corner = self.app.assetManager.getStairSprite(
            stair, app_module.Facing.EAST, app_module.StairShape.OUTER_LEFT,
            app_module.SlabPosition.BOTTOM,
        )
        self.assertNotEqual(pygame.image.tostring(straight, "RGBA"), pygame.image.tostring(corner, "RGBA"))

    def test_legacy_single_cell_door_migrates_on_load(self):
        with tempfile.TemporaryDirectory() as tempDir:
            path = os.path.join(tempDir, "legacy.json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump({
                    "version": 3,
                    "dimension": "overworld",
                    "blocks": [{"x": 2, "y": 2, "z": 1, "type": "OAK_DOOR"}],
                }, handle)
            self.assertTrue(self.app._loadBuildingFromPath(path, silent=True))
            self.assertEqual(self.app.world.getBlock(2, 2, 1), app_module.BlockType.OAK_DOOR)
            self.assertEqual(self.app.world.getBlock(2, 2, 2), app_module.BlockType.OAK_DOOR)

    def test_first_lit_frame_after_glowstone_stays_interactive(self):
        for x in range(app_module.GRID_WIDTH):
            for y in range(app_module.GRID_DEPTH):
                self.app.world.setBlock(x, y, 0, app_module.BlockType.STONE)
        self.app.world.setBlock(6, 6, 1, app_module.BlockType.GLOWSTONE)
        self.app.lightingEnabled = True
        self.app.lightingDirty = True
        self.app.litBlockCache.clear()
        self.app.litBlockCacheOrder.clear()
        started = time.perf_counter()
        self.app._renderWorld()
        elapsed = time.perf_counter() - started
        self.app.lightingEnabled = False
        self.assertLess(elapsed, 0.20, f"first lit frame took {elapsed:.3f}s")

    def test_empty_overworld_does_not_enable_hidden_horror_audio(self):
        self.assertFalse(self.app.horrorEnabled)

    def test_dimension_music_playlists_do_not_leak_between_dimensions(self):
        overworld = self.app._dimensionMusicFiles(app_module.DIMENSION_OVERWORLD)
        nether = self.app._dimensionMusicFiles(app_module.DIMENSION_NETHER)
        end = self.app._dimensionMusicFiles(app_module.DIMENSION_END)
        self.assertTrue(overworld)
        self.assertTrue(nether)
        self.assertTrue(end)
        self.assertFalse(any("nether" in Path(track).parts for track in overworld))
        self.assertFalse(any("end" in Path(track).parts for track in overworld))
        self.assertTrue(all("nether" in Path(track).parts for track in nether))
        self.assertTrue(all("end" in Path(track).parts for track in end))

    def test_dimension_music_replacement_starts_immediately(self):
        self.app._playMenuMusic(app_module.DIMENSION_OVERWORLD)
        self.assertTrue(self.app.musicController.get_busy())
        self.app._playMenuMusic(app_module.DIMENSION_NETHER)
        self.assertTrue(self.app.musicController.get_busy())
        self.assertIn("nether", Path(self.app.musicController.last_track).parts)
        self.assertFalse(self.app.musicController.fading_out)
        self.assertIsNone(self.app.musicController.pending_tracks)

    def test_java_import_preserves_supported_models_and_material_fallbacks(self):
        from engine.anvil import JavaBlock

        blocks = [
            JavaBlock(1, 70, 2, "minecraft:oak_stairs", {"facing": "east", "half": "top"}),
            JavaBlock(2, 70, 2, "minecraft:nether_brick_wall", {}),
        ]
        staged, skipped = self.app._stageJavaBlocks(blocks)
        self.assertEqual(skipped, 0)
        self.assertEqual(staged[0][3], app_module.BlockType.OAK_STAIRS)
        self.assertEqual(staged[0][4].facing, app_module.Facing.EAST)
        self.assertEqual(staged[0][4].slabPosition, app_module.SlabPosition.TOP)
        self.assertEqual(staged[1][3], app_module.BlockType.NETHER_BRICKS)

    def test_identical_regular_blocks_share_sprite_and_mipmaps(self):
        glowstone = self.app.assetManager.blockSprites[app_module.BlockType.GLOWSTONE]
        alias = self.app.assetManager.blockSprites[app_module.BlockType.GLOWSTONE_BLOCK]
        self.assertIs(glowstone, alias)
        self.assertEqual(set(self.app.assetManager._mipmaps[glowstone]), {0.5, 0.25})

    def test_nearby_zoom_values_share_a_cached_variant(self):
        sprite = self.app.assetManager.blockSprites[app_module.BlockType.STONE]
        first = self.app.assetManager.getScaledSprite(sprite, 0.31)
        second = self.app.assetManager.getScaledSprite(sprite, 0.32)
        self.assertIs(first, second)

    def test_transparent_sprite_variants_are_cached(self):
        sprite = self.app.assetManager.blockSprites[app_module.BlockType.STONE]
        first = self.app.assetManager.getAlphaSprite(sprite, 40)
        second = self.app.assetManager.getAlphaSprite(sprite, 40)
        self.assertIs(first, second)
        self.assertEqual(first.get_alpha(), 40)

    def test_dimension_weather_configs_and_particles(self):
        expected = {
            app_module.DIMENSION_OVERWORLD: ("Rain", "Snow"),
            app_module.DIMENSION_NETHER: ("Ember Fall", "Soul Drift"),
            app_module.DIMENSION_END: ("Void Rain", "End Shards"),
        }
        for dimension, names in expected.items():
            self.app.currentDimension = dimension
            config = self.app._getDimensionWeatherConfig()
            self.assertEqual((config["rain"]["name"], config["snow"]["name"]), names)
            self.app._startRain()
            self.app._startSnow()
            self.assertTrue(self.app.rainDrops)
            self.assertTrue(self.app.snowFlakes)
            self.assertIn(self.app.rainDrops[0]["color"], config["rain"]["colors"])
            self.assertIn(self.app.snowFlakes[0]["color"], config["snow"]["colors"])
            self.app.rainEnabled = True
            self.app.snowEnabled = True
            self.app._updateRain(16)
            self.app._updateSnow(16)
            self.app._renderRain()
            self.app._renderSnow()
            self.app.rainEnabled = False
            self.app.snowEnabled = False
            self.app._stopRain()
            self.app._stopSnow()

        self.assertEqual(
            app_module.DIMENSION_WEATHER[app_module.DIMENSION_END]["snow"]["particles"],
            84,
        )
        self.assertTrue(
            app_module.DIMENSION_WEATHER[app_module.DIMENSION_END]["snow"]["screenwide"]
        )
        self.assertGreaterEqual(
            app_module.DIMENSION_WEATHER[app_module.DIMENSION_END]["snow"]["size"][0], 4
        )

    def test_nether_and_end_weather_reuse_particle_surfaces(self):
        for dimension in (app_module.DIMENSION_NETHER, app_module.DIMENSION_END):
            with self.subTest(dimension=dimension):
                self.app.currentDimension = dimension
                self.app._startRain()
                self.app._startSnow()
                self.app.rainEnabled = True
                self.app.snowEnabled = True
                self.app._renderRain()
                self.app._renderSnow()
                with patch.object(pygame, "Surface", wraps=pygame.Surface) as surface_factory:
                    self.app._renderRain()
                    self.app._renderSnow()
                surface_factory.assert_not_called()
                self.app.rainEnabled = False
                self.app.snowEnabled = False
                self.app._stopRain()
                self.app._stopSnow()

    def test_weather_impacts_and_sounds_run_in_every_dimension(self):
        for dimension in (
            app_module.DIMENSION_OVERWORLD,
            app_module.DIMENSION_NETHER,
            app_module.DIMENSION_END,
        ):
            with self.subTest(dimension=dimension):
                self.app.currentDimension = dimension
                self.app.world.setDimension(dimension)
                self.app._createInitialFloor()
                self.app._frameCurrentCanvas()

                with patch.object(self.app.assetManager, "playSound") as play_sound:
                    self.app.rainEnabled = True
                    self.app._startRain()
                    self.app.splashSpawnTimer = 1000
                    self.app._updateRain(16)
                    self.assertTrue(self.app.rainSplashes)
                    play_sound.assert_called()
                    self.app.rainEnabled = False
                    self.app._stopRain()

                    play_sound.reset_mock()
                    self.app.snowEnabled = True
                    self.app._startSnow()
                    self.app.snowImpactTimer = 1000
                    self.app._updateSnow(16)
                    self.assertTrue(self.app.snowImpacts)
                    play_sound.assert_called()
                    self.app.snowEnabled = False
                    self.app._stopSnow()

                self.app.world.resize(
                    app_module.GRID_WIDTH,
                    app_module.GRID_DEPTH,
                    app_module.GRID_HEIGHT,
                    min_y=0,
                    preserve=False,
                )

    def test_weather_surface_candidates_refresh_only_after_world_edit(self):
        self.app._createInitialFloor()
        first = self.app._weatherSurfaceCandidates()
        self.assertIs(self.app._weatherSurfaceCandidates(), first)
        self.app.world.setBlock(2, 2, 1, app_module.BlockType.STONE)
        refreshed = self.app._weatherSurfaceCandidates()
        self.assertIsNot(refreshed, first)
        self.assertIn(((2, 2), 1), refreshed)

    def test_rain_extinguishes_only_dimension_appropriate_fire_and_undoes(self):
        scenarios = (
            (
                app_module.DIMENSION_OVERWORLD,
                app_module.BlockType.FIRE,
                True,
            ),
            (
                app_module.DIMENSION_NETHER,
                app_module.BlockType.SOUL_FIRE,
                True,
            ),
            (
                app_module.DIMENSION_END,
                app_module.BlockType.FIRE,
                False,
            ),
        )
        for dimension, fire_type, should_extinguish in scenarios:
            with self.subTest(dimension=dimension):
                self.app.world.resize(
                    app_module.GRID_WIDTH,
                    app_module.GRID_DEPTH,
                    app_module.GRID_HEIGHT,
                    min_y=0,
                    preserve=False,
                )
                self.app.currentDimension = dimension
                self.app.world.setDimension(dimension)
                self.app.undoManager.clear()
                self.app.world.setBlock(4, 4, 0, app_module.BlockType.STONE)
                self.app.world.setBlock(4, 4, 1, fire_type)
                self.app.weatherInteractionTimer = 0

                with patch.object(self.app.assetManager, "playSound") as play_sound:
                    self.app._updateWeatherFireInteractions(650)

                expected = (
                    app_module.BlockType.AIR if should_extinguish else fire_type
                )
                self.assertEqual(self.app.world.getBlock(4, 4, 1), expected)
                if should_extinguish:
                    self.assertEqual(len(self.app.undoManager.undo_stack), 1)
                    play_sound.assert_called_once()
                    self.assertTrue(self.app.undoManager.undo())
                    self.assertEqual(
                        self.app.world.getBlock(4, 4, 1), fire_type
                    )
                else:
                    self.assertFalse(self.app.undoManager.undo_stack)
                    play_sound.assert_not_called()

    def test_small_app_icon_preserves_respawn_anchor_aspect_ratio(self):
        artwork = pygame.image.load(ROOT / "Assets" / "Icons" / "Respawn_Anchor.png")
        for size in (16, 24, 32):
            icon = app_module.render_app_icon_surface(artwork, size)
            bounds = icon.get_bounding_rect(min_alpha=1)
            self.assertLessEqual(bounds.width / bounds.height, 1.6)
            self.assertLess(bounds.width, size)
            self.assertLess(bounds.height, size)
            colors = {
                icon.get_at((x, y))[:3]
                for x in range(size)
                for y in range(size)
                if icon.get_at((x, y)).a
            }
            self.assertGreater(len(colors), 8)

    def test_both_piston_doors_are_natural_and_survive_repeated_cycles(self):
        self.assertEqual(next(iter(app_module.PREMADE_STRUCTURES)), "piston_door")
        for key, expected_name in (
            ("piston_door", "2x2 Exposed Piston Door"),
            ("flush_piston_door", "2x2 Flush Piston Door"),
        ):
            structure = app_module.PREMADE_STRUCTURES[key]
            self.assertEqual(structure["name"], expected_name)
            self.assertEqual(sum(
                1 for block in structure["blocks"]
                if block[3] == app_module.BlockType.STICKY_PISTON
            ), 4)
            self.assertFalse(any(
                block[3] == app_module.BlockType.PISTON_HEAD
                for block in structure["blocks"]
            ))

            self.app.world.resize(12, 12, 12, min_y=0, preserve=False)
            self.app.redstone.active_motions.clear()
            with self.app.world.bulkUpdate():
                for block in structure["blocks"]:
                    x, y, z, block_type, props = app_module._structureBlockParts(block)
                    self.app.world.setBlock(x, y, z, block_type)
                    if props is not None:
                        self.app.world.setBlockProperties(x, y, z, props.copy())
            self.app.redstone.mark_dirty()
            self.app.redstone.update(50)

            for _cycle in range(3):
                # Lever starts off: the two halves are parked beside the opening.
                self.assertTrue(all(
                    self.app.world.getBlock(x, 3, z) == app_module.BlockType.AIR
                    for x in (5, 6) for z in (1, 2)
                ))
                self.assertTrue(self.app._interactBlock(0, 2, 1))
                self.app.redstone.update(50)
                self.assertTrue(all(
                    self.app.world.getBlock(x, 3, z) == app_module.BlockType.STONE_BRICKS
                    for x in (5, 6) for z in (1, 2)
                ))
                self.assertTrue(self.app._interactBlock(0, 2, 1))
                self.app.redstone.update(50)
                self.assertTrue(all(
                    self.app.world.getBlock(x, 3, z) == app_module.BlockType.STONE_BRICKS
                    for x in (4, 7) for z in (1, 2)
                ))

    def test_redstone_lab_is_interact_only_and_restores_the_live_build(self):
        marker = (2, 2, 2)
        self.app.world.setBlock(*marker, app_module.BlockType.DIAMOND_BLOCK)
        self.app.showGrid = False
        original_bounds = (
            self.app.world.width, self.app.world.depth, self.app.world.height
        )

        self.app._toggleRedstoneLab()
        self.assertTrue(self.app.redstoneLabActive)
        self.assertTrue(self.app.interactionMode)
        self.assertTrue(self.app.showGrid)
        self.assertEqual((self.app.world.width, self.app.world.depth), (32, 32))
        self.assertEqual(self.app.sceneMetadata["mode"], "redstone_lab")
        self.assertIn(app_module.BlockType.STONE_BUTTON, self.app.hotbar)
        self.assertEqual(
            self.app.world.getBlock(3, 14, 1), app_module.BlockType.STONE_BUTTON
        )
        self.assertTrue(self.app._interactBlock(14, 9, 1))
        self.app.redstone.update(50)
        self.assertTrue(all(
            self.app.world.getBlock(x, 10, z) == app_module.BlockType.STONE_BRICKS
            for x in (19, 20) for z in (1, 2)
        ))

        # Moving the pointer in hand mode must never read the click-only
        # ``button`` field from a MOUSEMOTION event.
        self.app._handleMouseMotion(SimpleNamespace(pos=(300, 300)))
        lever = (3, 9, 1)
        before = self.app.world.getBlockProperties(*lever).powered
        self.app.hoveredSourceBlock = lever
        self.app._handleMouseDown(SimpleNamespace(button=1, pos=(300, 300)))
        self.assertNotEqual(self.app.world.getBlockProperties(*lever).powered, before)

        self.app._toggleRedstoneLab()
        self.assertFalse(self.app.redstoneLabActive)
        self.assertFalse(self.app.interactionMode)
        self.assertFalse(self.app.showGrid)
        self.assertEqual(
            (self.app.world.width, self.app.world.depth, self.app.world.height),
            original_bounds,
        )
        self.assertEqual(self.app.world.getBlock(*marker), app_module.BlockType.DIAMOND_BLOCK)

    def test_connected_clear_glass_culls_internal_faces_and_reuses_variants(self):
        self.app.world.resize(12, 12, 12, min_y=0, preserve=False)
        with self.app.world.bulkUpdate():
            for x in range(2, 10):
                for y in range(2, 10):
                    for z in range(1, 9):
                        self.app.world.setBlock(x, y, z, app_module.BlockType.GLASS)

        visibleMasks = [
            self.app._clearGlassFaceMask(x, y, z)
            for x in range(2, 10) for y in range(2, 10) for z in range(1, 9)
        ]
        self.assertIn(0, visibleMasks)
        self.assertLess(sum(mask != 0 for mask in visibleMasks), len(visibleMasks) // 2)
        self.assertEqual(self.app._clearGlassFaceMask(9, 9, 8), 0b111)

        first = self.app.assetManager.getConnectedGlassSprite(0b111)
        second = self.app.assetManager.getConnectedGlassSprite(0b111)
        self.assertIs(first, second)
        self.assertGreater(first.get_bounding_rect(min_alpha=1).width, 0)

    def test_music_starts_lower_while_ambient_and_effects_retain_headroom(self):
        self.assertEqual(
            (self.app.musicVolume, self.app.ambientVolume, self.app.effectsVolume),
            (0.4, 0.8, 0.8),
        )
        self.assertEqual(app_module.BLOCK_ACTION_GAIN_SCALE, 0.875)


if __name__ == "__main__":
    unittest.main()
