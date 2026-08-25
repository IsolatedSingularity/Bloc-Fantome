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
    definitions[BlockType.OAK_DOOR] = BlockDefinition(
        "Door", "x", "x", "x", transparent=True, isDoor=True
    )
    for block in (
        BlockType.REDSTONE_DUST, BlockType.REDSTONE_TORCH,
        BlockType.REDSTONE_WALL_TORCH, BlockType.LEVER,
        BlockType.REPEATER, BlockType.PISTON, BlockType.STICKY_PISTON,
        BlockType.PISTON_HEAD, BlockType.REDSTONE_LAMP,
        BlockType.STONE_BUTTON,
    ):
        definitions[block] = detail(block.name)
    return definitions


def _world(width=20, depth=8, height=8, sound=None):
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
    return world, RedstoneSimulator(world, definitions, sound=sound)


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


def test_piston_extension_and_retraction_emit_their_real_sound_routes():
    events = []
    world, redstone = _world(sound=lambda category, pos: events.append((category, pos)))
    _place(world, (2, 2, 1), BlockType.STICKY_PISTON,
           facing=Facing.EAST, sticky=True)
    _place(world, (3, 2, 1), BlockType.STONE_BRICKS)
    _place(world, (2, 1, 1), BlockType.REDSTONE_BLOCK)
    redstone.update(50)
    world.setBlock(2, 1, 1, BlockType.AIR)
    redstone.mark_dirty()
    redstone.update(50)
    assert events == [
        ("piston_out", (2, 2, 1)),
        ("piston_in", (2, 2, 1)),
    ]


def test_piston_rejects_quasi_power_around_block_above():
    world, redstone = _world()
    _place(world, (2, 2, 1), BlockType.PISTON, facing=Facing.EAST)
    _place(world, (2, 1, 2), BlockType.REDSTONE_BLOCK)
    redstone.update(50)
    assert not world.getBlockProperties(2, 2, 1).pistonExtended


def test_piston_motion_is_time_based_and_completes_after_six_sixty_fps_frames():
    world, redstone = _world()
    _place(world, (2, 2, 1), BlockType.STICKY_PISTON,
           facing=Facing.EAST, sticky=True)
    _place(world, (3, 2, 1), BlockType.STONE_BRICKS)
    _place(world, (2, 1, 1), BlockType.REDSTONE_BLOCK)
    redstone.update(50)

    assert len(redstone.active_motions) == 1
    assert redstone.active_motions[0].progress == 0.0
    assert (4, 2, 1) in redstone.moving_final_targets
    for frame in range(5):
        redstone.update(16)
        assert redstone.active_motions
        assert redstone.active_motions[0].progress == (frame + 1) * 0.16
    redstone.update(20)
    assert not redstone.active_motions


def test_piston_breaks_fragile_redstone_instead_of_moving_it():
    world, redstone = _world()
    _place(world, (2, 2, 1), BlockType.PISTON, facing=Facing.EAST)
    _place(world, (3, 2, 1), BlockType.REDSTONE_DUST)
    _place(world, (2, 1, 1), BlockType.REDSTONE_BLOCK)
    redstone.update(50)
    assert world.getBlock(3, 2, 1) == BlockType.PISTON_HEAD
    assert world.getBlock(4, 2, 1) == BlockType.AIR


def test_piston_breaks_both_fragile_door_cells_and_cannot_move_block_entities():
    world, redstone = _world()
    _place(world, (2, 2, 1), BlockType.PISTON, facing=Facing.EAST)
    _place(world, (3, 2, 1), BlockType.OAK_DOOR)
    _place(world, (3, 2, 2), BlockType.OAK_DOOR)
    _place(world, (2, 1, 1), BlockType.REDSTONE_BLOCK)
    redstone.update(50)
    assert world.getBlock(3, 2, 1) == BlockType.PISTON_HEAD
    assert world.getBlock(3, 2, 2) == BlockType.AIR

    blocked, blocked_redstone = _world()
    _place(blocked, (2, 2, 1), BlockType.PISTON, facing=Facing.EAST)
    _place(blocked, (3, 2, 1), BlockType.CHEST)
    _place(blocked, (2, 1, 1), BlockType.REDSTONE_BLOCK)
    blocked_redstone.update(50)
    assert not blocked.getBlockProperties(2, 2, 1).pistonExtended
    assert blocked.getBlock(3, 2, 1) == BlockType.CHEST


def test_redstone_lamp_uses_four_game_tick_off_delay():
    world, redstone = _world()
    _place(world, (2, 2, 1), BlockType.REDSTONE_LAMP)
    _place(world, (1, 2, 1), BlockType.REDSTONE_BLOCK)
    redstone.update(0)
    assert world.getBlockProperties(2, 2, 1).powered

    world.setBlock(1, 2, 1, BlockType.AIR)
    redstone.mark_dirty()
    redstone.update(0)
    for _ in range(3):
        redstone.update(50)
        assert world.getBlockProperties(2, 2, 1).powered
    redstone.update(50)
    assert not world.getBlockProperties(2, 2, 1).powered


def test_wire_connection_mask_encodes_north_east_south_west():
    world, redstone = _world()
    center = (3, 3, 1)
    _place(world, center, BlockType.REDSTONE_DUST)
    _place(world, (3, 2, 1), BlockType.REDSTONE_DUST)  # north, bit 0
    _place(world, (3, 4, 1), BlockType.LEVER)          # south, bit 2
    assert redstone.wire_connection_mask(center) == 0b0101


def test_wire_does_not_connect_visually_to_consumers_that_cannot_emit_power():
    world, redstone = _world()
    center = (3, 3, 1)
    _place(world, center, BlockType.REDSTONE_DUST)
    _place(world, (3, 2, 1), BlockType.REDSTONE_LAMP)
    _place(world, (4, 3, 1), BlockType.PISTON, facing=Facing.EAST)
    assert redstone.wire_connection_mask(center) == 0


def test_stone_button_powers_for_twenty_game_ticks_then_releases():
    world, redstone = _world()
    position = (2, 2, 1)
    _place(world, position, BlockType.STONE_BUTTON, facing=Facing.SOUTH)
    _place(world, (3, 2, 1), BlockType.REDSTONE_DUST)

    assert redstone.press_button(position)
    redstone.update(0)
    assert world.getBlockProperties(*position).powered
    assert world.getBlockProperties(3, 2, 1).redstonePower == 15

    for _ in range(19):
        redstone.update(50)
        assert world.getBlockProperties(*position).powered
    redstone.update(50)
    assert not world.getBlockProperties(*position).powered
    assert world.getBlockProperties(3, 2, 1).redstonePower == 0


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
