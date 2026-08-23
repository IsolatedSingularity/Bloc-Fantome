from domain.block_catalog import BlockDefinition
from domain.blocks import BlockProperties, BlockType, Facing
from domain.world_catalog import WorldCatalog
from engine.redstone import RedstoneSimulator
from engine.world import World


def _definitions():
    solid = BlockDefinition("Solid", "x", "x", "x")
    detail = lambda name: BlockDefinition(name, "x", "x", "x", transparent=True, modelKind="detail")
    definitions = {block: solid for block in BlockType}
    definitions[BlockType.AIR] = BlockDefinition("Air", "x", "x", "x", transparent=True)
    for block in (
        BlockType.REDSTONE_DUST, BlockType.REDSTONE_TORCH, BlockType.LEVER,
        BlockType.REPEATER, BlockType.PISTON, BlockType.STICKY_PISTON,
        BlockType.PISTON_HEAD,
    ):
        definitions[block] = detail(block.name)
    return definitions


def _world(width=20, depth=8, height=8):
    definitions = _definitions()
    catalog = WorldCatalog(
        block_type=BlockType,
        air=BlockType.AIR,
        water=BlockType.WATER,
        lava=BlockType.LAVA,
        obsidian=BlockType.OBSIDIAN,
        cobblestone=BlockType.COBBLESTONE,
        stone=BlockType.STONE,
        definitions=definitions,
    )
    world = World(width, depth, height, catalog=catalog)
    return world, RedstoneSimulator(world, definitions)


def _place(world, position, block, **state):
    world.setBlock(*position, block)
    if state:
        world.setBlockProperties(*position, BlockProperties(**state))


def test_dust_propagates_full_strength_then_decays_to_zero():
    world, redstone = _world()
    _place(world, (1, 2, 1), BlockType.LEVER, powered=True, redstonePower=15)
    for x in range(2, 7):
        _place(world, (x, 2, 1), BlockType.REDSTONE_DUST)
    redstone.update(0)
    assert [world.getBlockProperties(x, 2, 1).redstonePower for x in range(2, 7)] == [15, 14, 13, 12, 11]

    props = world.getBlockProperties(1, 2, 1)
    props.powered = False
    props.redstonePower = 0
    world.setBlockProperties(1, 2, 1, props)
    redstone.mark_dirty()
    redstone.update(0)
    assert all(world.getBlockProperties(x, 2, 1).redstonePower == 0 for x in range(2, 7))


def test_repeater_strongly_powers_through_solid_block():
    world, redstone = _world()
    _place(world, (2, 2, 1), BlockType.REPEATER,
           facing=Facing.EAST, powered=True, redstonePower=15)
    _place(world, (3, 2, 1), BlockType.STONE)
    _place(world, (4, 2, 1), BlockType.REDSTONE_DUST)
    redstone.update(0)
    assert world.getBlockProperties(4, 2, 1).redstonePower == 15


def test_repeater_uses_selected_two_game_tick_delay():
    world, redstone = _world()
    _place(world, (1, 2, 1), BlockType.REDSTONE_BLOCK)
    _place(world, (2, 2, 1), BlockType.REPEATER,
           facing=Facing.EAST, repeaterDelay=1)
    redstone.update(0)
    redstone.update(50)
    assert not world.getBlockProperties(2, 2, 1).powered
    redstone.update(50)
    assert world.getBlockProperties(2, 2, 1).powered


def test_dust_climbs_one_block_and_continues_decaying():
    world, redstone = _world()
    _place(world, (1, 2, 1), BlockType.REDSTONE_BLOCK)
    _place(world, (2, 2, 1), BlockType.REDSTONE_DUST)
    _place(world, (3, 2, 1), BlockType.STONE)
    _place(world, (3, 2, 2), BlockType.REDSTONE_DUST)
    _place(world, (4, 2, 2), BlockType.REDSTONE_DUST)
    redstone.update(0)
    assert world.getBlockProperties(2, 2, 1).redstonePower == 15
    assert world.getBlockProperties(3, 2, 2).redstonePower == 14
    assert world.getBlockProperties(4, 2, 2).redstonePower == 13


def test_powered_side_repeater_locks_main_repeater():
    world, redstone = _world()
    _place(world, (1, 2, 1), BlockType.REDSTONE_BLOCK)
    _place(world, (2, 2, 1), BlockType.REPEATER, facing=Facing.EAST)
    _place(world, (2, 1, 1), BlockType.REPEATER,
           facing=Facing.SOUTH, powered=True, redstonePower=15)
    _place(world, (2, 0, 1), BlockType.REDSTONE_BLOCK)
    redstone.update(0)
    assert world.getBlockProperties(2, 2, 1).repeaterLocked
    redstone.update(200)
    assert not world.getBlockProperties(2, 2, 1).powered


def test_redstone_torch_inverts_power_on_supporting_block():
    world, redstone = _world()
    _place(world, (2, 2, 1), BlockType.STONE)
    _place(world, (2, 2, 2), BlockType.REDSTONE_TORCH,
           powered=True, redstonePower=15)
    _place(world, (1, 2, 1), BlockType.LEVER, powered=True, redstonePower=15)
    redstone.update(0)
    assert not world.getBlockProperties(2, 2, 2).powered

    world.setBlock(1, 2, 1, BlockType.AIR)
    redstone.mark_dirty()
    redstone.update(0)
    assert world.getBlockProperties(2, 2, 2).powered


def test_sticky_piston_pushes_and_pulls_one_block():
    world, redstone = _world()
    _place(world, (2, 2, 1), BlockType.STICKY_PISTON,
           facing=Facing.EAST, sticky=True)
    _place(world, (3, 2, 1), BlockType.STONE_BRICKS)
    _place(world, (2, 1, 1), BlockType.REDSTONE_BLOCK)
    redstone.update(50)
    assert world.getBlock(3, 2, 1) == BlockType.PISTON_HEAD
    assert world.getBlock(4, 2, 1) == BlockType.STONE_BRICKS

    world.setBlock(2, 1, 1, BlockType.AIR)
    redstone.mark_dirty()
    redstone.update(50)
    assert world.getBlock(3, 2, 1) == BlockType.STONE_BRICKS
    assert world.getBlock(4, 2, 1) == BlockType.AIR


def test_piston_accepts_quasi_power_around_block_above():
    world, redstone = _world()
    _place(world, (2, 2, 1), BlockType.PISTON, facing=Facing.EAST)
    _place(world, (2, 1, 2), BlockType.REDSTONE_BLOCK)
    redstone.update(50)
    assert world.getBlockProperties(2, 2, 1).pistonExtended


def test_piston_chain_limit_is_twelve_blocks():
    world, redstone = _world(width=20)
    _place(world, (1, 2, 1), BlockType.PISTON, facing=Facing.EAST)
    _place(world, (1, 1, 1), BlockType.REDSTONE_BLOCK)
    for x in range(2, 14):
        _place(world, (x, 2, 1), BlockType.STONE)
    redstone.update(50)
    assert world.getBlockProperties(1, 2, 1).pistonExtended
    assert world.getBlock(14, 2, 1) == BlockType.STONE

    blocked, blocked_redstone = _world(width=20)
    _place(blocked, (1, 2, 1), BlockType.PISTON, facing=Facing.EAST)
    _place(blocked, (1, 1, 1), BlockType.REDSTONE_BLOCK)
    for x in range(2, 15):
        _place(blocked, (x, 2, 1), BlockType.STONE)
    blocked_redstone.update(50)
    assert not blocked.getBlockProperties(1, 2, 1).pistonExtended
