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
from unittest.mock import patch


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
        cls.app = app_module.BlocFantome()
        if not cls.app.assetManager.loadAllAssets():
            raise RuntimeError("Integration fixture could not load application assets")

    @classmethod
    def tearDownClass(cls):
        pygame.display.quit()

    def setUp(self):
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
        self.app.undoManager.clear()

    def test_json_structures_are_cursor_placeable(self):
        for name in app_module.JSON_STRUCTURE_LIBRARY:
            structure = app_module.PREMADE_STRUCTURES[name]
            self.assertTrue(structure["blocks"], name)
            self.assertIn("source_file", structure)

    def test_app_uses_modular_world_and_renderer(self):
        self.assertEqual(self.app.world.__class__.__module__, "engine.world")
        self.assertEqual(self.app.renderer.__class__.__module__, "engine.renderer")

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

    def test_rotation_preserves_viewport_world_anchor_in_all_views(self):
        self.app.zoomLevel = 0.75
        self.app.renderer.setZoom(0.75)
        self.app.renderer.setViewRotation(0)
        self.app.renderer.offsetX = 410.5
        self.app.renderer.offsetY = 330.25
        self.app.cameraFocusZ = 3
        center = ((app_module.WINDOW_WIDTH - app_module.PANEL_WIDTH) / 2, app_module.WINDOW_HEIGHT / 2)
        anchor = self.app.renderer.screenToWorld(*center, self.app.cameraFocusZ)
        for _ in range(4):
            self.app._rotateViewAndRecenter(1)
            self.assertEqual(
                self.app.renderer.screenToWorld(*center, self.app.cameraFocusZ),
                anchor,
            )

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
        for block in (
            app_module.BlockType.OAK_DOOR,
            app_module.BlockType.IRON_DOOR,
            app_module.BlockType.OAK_STAIRS,
            app_module.BlockType.COBBLESTONE_STAIRS,
        ):
            self.assertNotIn(block, app_module.BLOCK_CATEGORIES["Experimental"])
            icon = self.app.assetManager.getIconSprite(block)
            self.assertEqual(icon.get_size(), (app_module.ICON_SIZE, app_module.ICON_SIZE))
            self.assertGreater(icon.get_bounding_rect(min_alpha=1).height, 0)

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

    def test_treasure_bastion_structure_does_not_vanish_at_overview_zoom(self):
        path = Path(app_module.WORLDS_DIR) / "bastion_treasure_1161.json.gz"
        self.assertTrue(self.app._loadBuildingFromPath(str(path), silent=True))
        self.app.zoomLevel = min(0.12, self.app.overviewZoomThreshold)
        self.app.renderer.setZoom(self.app.zoomLevel)
        self.app._invalidateViewCaches()
        drawn = {(x, y, z) for _, x, y, z, _ in self.app._visibleBlocksInDrawOrder()}
        buriedStructure = {
            pos for pos in self.app.sceneStructurePositions
            if pos[2] < self.app.world.heightIndex.get(pos[:2], pos[2])
        }
        overviewStructure = self.app.world.structureOverviewPositions()
        drawnStructure = drawn & self.app.sceneStructurePositions
        self.assertTrue(drawn & buriedStructure)
        self.assertTrue(overviewStructure <= drawnStructure)
        self.assertLess(
            len(drawnStructure),
            len(self.app.world.structureSurfacePositions(self.app.renderer.viewRotation)),
        )
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

    def test_complete_world_catalog_uses_supported_placeable_palette(self):
        from engine.world_catalog import WORLD_ENTRIES, world_catalog

        entries = world_catalog(app_module.WORLDS_DIR)
        self.assertEqual(len(entries), 13)
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

    def test_runtime_and_packaged_icons_have_padding_and_multiple_sizes(self):
        from engine.app_icon import render_app_icon_surface

        icon = render_app_icon_surface(
            self.app.assetManager.textures.get("end_stone"), 64
        )
        bounds = icon.get_bounding_rect(min_alpha=1)
        self.assertGreater(bounds.left, 0)
        self.assertGreater(bounds.top, 0)
        self.assertLess(bounds.right, 64)
        self.assertLess(bounds.bottom, 64)

        ico = ROOT / "Assets" / "Icons" / "End_Stone.ico"
        with ico.open("rb") as handle:
            reserved, kind, count = struct.unpack("<HHH", handle.read(6))
        self.assertEqual((reserved, kind), (0, 1))
        self.assertGreaterEqual(count, 7)

    def test_large_json_structure_places_at_cursor_without_clipping(self):
        self.app.selectedStructure = "end_city_tower"
        self.app.hoveredCell = (5, 5, 1)
        self.app._placeStructureAtMouse(0, 0)
        expected = len(app_module.PREMADE_STRUCTURES["end_city_tower"]["blocks"])
        self.assertEqual(len(self.app.world.blocks), expected)
        self.assertTrue(all(self.app.world.isInBounds(*pos) for pos in self.app.world.blocks))
        self.app.undoManager.undo()
        self.assertFalse(self.app.world.blocks)

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
                self.assertIn(app_module.BlockType.CHORUS_PLANT, self.app.world.blocks.values())
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
            self.assertGreater(self.app.renderer.worldToScreen(*center)[1], 380)

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

    def test_small_app_icon_keeps_a_cube_silhouette(self):
        texture = self.app.assetManager.textures["end_stone.png"]
        for size in (16, 24, 32):
            icon = app_module.render_app_icon_surface(texture, size)
            bounds = icon.get_bounding_rect(min_alpha=1)
            self.assertLessEqual(bounds.width / bounds.height, 1.6)
            self.assertLess(bounds.width, size)
            self.assertLess(bounds.height, size)


if __name__ == "__main__":
    unittest.main()
