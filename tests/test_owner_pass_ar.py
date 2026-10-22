"""Owner-reproduced underwater edits and exact camera/picking regressions."""
import pygame
import pytest
from unittest.mock import patch
import blocFantome as b
from engine.draw_order import DrawOrder
from test_workshop_production import app, reset


def test_cutaway_water_target_roundtrips_through_undo(app, tmp_path):
    app.sceneMetadata = {'water_cutaway': True}
    app.world.sceneMetadata = app.sceneMetadata
    app.world.setBlock(4, 4, 2, b.BlockType.STONE)
    app.world.setBlock(4, 4, 3, b.BlockType.WATER)
    props = b.BlockProperties(sourceCapture='_scene_ocean_monument_1161', sourcePalette=0)
    app.world.setBlockProperties(4, 4, 3, props)
    prior = app.world.getBlockProperties(4, 4, 3).copy()
    target = app._targetForBlockFace(4, 4, 2, 'top')
    assert target == (4, 4, 3), 'Hidden source water must not block a visible placement'
    app.hoveredCell = target
    app.selectedBlock = b.BlockType.GOLD_BLOCK
    app._placeBlockAtMouse(600, 400)
    assert app.world.getBlock(*target) == b.BlockType.GOLD_BLOCK
    assert not app.world.getBlockProperties(*target).sourceCapture if app.world.getBlockProperties(*target) else True
    assert app.undoManager.undo()
    assert app.world.getBlock(*target) == b.BlockType.WATER
    assert vars(app.world.getBlockProperties(*target)) == vars(prior)
    assert app.undoManager.redo()
    path = tmp_path/'underwater.json.gz'
    assert app._saveBuilding(filepath=str(path), silent=True)
    assert app._loadBuildingFromPath(str(path), silent=True)
    assert app.world.getBlock(*target) == b.BlockType.GOLD_BLOCK


def test_reverse_painter_pages_does_not_perform_random_access():
    rows = tuple((i, i, 0, 0, 'stone') for i in range(10000))
    order = DrawOrder(rows)
    with patch.object(DrawOrder, '__getitem__', side_effect=AssertionError('linear page lookup')):
        assert tuple(reversed(order)) == rows[::-1]


@pytest.mark.parametrize('rotation', range(4))
def test_screen_pick_candidates_match_exhaustive_owner(app, rotation):
    app.sceneMetadata = {};app.renderer.viewRotation=rotation
    for x in range(6):
        for y in range(6):
            for z in range((x+y)%4+1): app.world.setBlock(x,y,z,b.BlockType.STONE)
    app._fitWorldToViewport(notify=False)
    for x in range(400,801,45):
        for y in range(200,601,45):
            expected=None
            for _,bx,by,bz,block in reversed(app._visibleBlocksInDrawOrder()):
                if app._pickRenderedBlockFace(x,y,bx,by,bz,block):
                    expected=(bx,by,bz);break
            app._updateHoveredCell(x,y)
            assert app.hoveredSourceBlock==expected
