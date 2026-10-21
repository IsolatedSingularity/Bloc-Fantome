"""Pinned Java constant emitters must illuminate neighbors through real undo."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import pytest
import pygame
from collections import OrderedDict
from blocFantome import BlocFantome,BlockType as B,BLOCK_DEFINITIONS,BLOCK_SOUNDS,DIMENSION_OVERWORLD
from domain.world_catalog import WorldCatalog
from engine.world import World
from engine.undo import UndoManager,PlaceBlockCommand


@pytest.mark.parametrize('block,level',[(B.ENDER_CHEST,7),(B.FIRE,15),(B.SOUL_FIRE,10),(B.END_PORTAL,15)])
def test_constant_source_illuminates_neighbor_and_undo_removes_light(block,level):
    catalog=WorldCatalog(B,B.AIR,B.WATER,B.LAVA,B.OBSIDIAN,B.COBBLESTONE,B.STONE,BLOCK_DEFINITIONS)
    world=World(12,12,12,catalog=catalog);undo=UndoManager()
    assert undo.execute(PlaceBlockCommand(world,5,5,5,block))
    lights=world.calculateLighting()
    assert lights[(5,5,5)][0]==level
    assert lights[(5,5,6)][0]==level-1
    assert undo.undo()
    assert not world.calculateLighting()
    assert undo.redo()
    assert world.calculateLighting()==lights


def test_final_resolved_sound_groups_match_local_java_events():
    for block,group in ((B.RED_SAND,'sand'),(B.BAMBOO,'bamboo_place'),
                        (B.BRAIN_CORAL_BLOCK,'coral'),(B.FIRE_CORAL_BLOCK,'coral'),(B.TUBE_CORAL_BLOCK,'coral')):
        assert BLOCK_SOUNDS[block].placeSound==BLOCK_SOUNDS[block].breakSound==group


@pytest.mark.parametrize('block',[B.ENDER_CHEST,B.FIRE,B.SOUL_FIRE,B.END_PORTAL])
def test_rendered_neighbor_changes_with_source_and_restores_after_undo(block):
    catalog=WorldCatalog(B,B.AIR,B.WATER,B.LAVA,B.OBSIDIAN,B.COBBLESTONE,B.STONE,BLOCK_DEFINITIONS)
    app=BlocFantome.__new__(BlocFantome)
    app.world=World(12,12,12,catalog=catalog)
    app.currentDimension=DIMENSION_OVERWORLD;app.dayBrightness=0
    app.litBlockCache=OrderedDict();app.litBlockCacheMaxSize=64
    app.world.setBlock(5,5,6,B.STONE)
    for x in range(4,7):
        for y in range(4,7):app.world.setBlock(x,y,8,B.STONE)
    sprite=pygame.Surface((8,8),pygame.SRCALPHA);sprite.fill((170,170,170,255))
    def render_neighbor():
        app.lightMap=app.world.calculateLighting()
        return pygame.image.tostring(app._applyLighting(sprite,5,5,6,B.STONE),'RGBA')
    dark=render_neighbor();undo=UndoManager()
    assert undo.execute(PlaceBlockCommand(app.world,5,5,5,block))
    lit=render_neighbor();assert lit!=dark
    assert undo.undo();assert render_neighbor()==dark
    assert undo.redo();assert render_neighbor()==lit
