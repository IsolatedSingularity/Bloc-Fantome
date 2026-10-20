"""Four camera sides must retain every exposed source face, including cutaways."""
from itertools import product
import blocFantome as app
from domain.world_catalog import WorldCatalog
from engine.world import World


def test_every_side_combination_and_transparent_neighbor():
    bt=app.BlockType
    catalog=WorldCatalog(bt,bt.AIR,bt.WATER,bt.LAVA,bt.OBSIDIAN,bt.COBBLESTONE,bt.STONE,app.BLOCK_DEFINITIONS)
    sides=((3,2,2),(1,2,2),(2,3,2),(2,1,2)) # east, west, north, south
    camera_faces=((0,2),(0,3),(1,3),(1,2))
    for transparent in (bt.AIR,bt.GLASS,bt.WATER):
        for open_faces in product((False,True),repeat=4):
            world=World(5,5,5,catalog=catalog)
            world.setBlock(2,2,2,bt.STONE);world.setBlock(2,2,3,bt.STONE)
            for position,exposed in zip(sides,open_faces):
                world.setBlock(*position,transparent if exposed else bt.STONE)
            expected=tuple(r for r,faces in enumerate(camera_faces) if any(open_faces[f] for f in faces))
            assert tuple(world._surfaceViewsForPosition((2,2,2)))==expected
            world.setBlock(2,2,3,bt.AIR)
            assert tuple(world._surfaceViewsForPosition((2,2,2)))==(0,1,2,3)
