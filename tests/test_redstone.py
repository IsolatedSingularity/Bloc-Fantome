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
           facing=Facing.WEST, powered=True, redstonePower=15)
    _place(world, (3, 2, 1), BlockType.STONE)
    _place(world, (4, 2, 1), BlockType.REDSTONE_DUST)
    redstone.update(0)
    assert world.getBlockProperties(4, 2, 1).redstonePower == 15


def test_repeater_facing_is_input_side_and_emits_from_the_opposite_side():
    world, redstone = _world()
    _place(world, (1, 2, 1), BlockType.REDSTONE_BLOCK)
    _place(world, (2, 2, 1), BlockType.REPEATER,
           facing=Facing.WEST, repeaterDelay=1)
    _place(world, (3, 2, 1), BlockType.REDSTONE_LAMP)
    redstone.update(0)

    # The source is on the repeater's FACING side. It must not be powered by
    # the lamp/output side, and the output arrives only after two game ticks.
    assert redstone._repeater_input(
        (2, 2, 1), world.getBlockProperties(2, 2, 1)
    ) == 15
    assert redstone._output_toward(
        (2, 2, 1), (3, 2, 1)
    ) == 0
    redstone.update(100)
    assert world.getBlockProperties(2, 2, 1).powered
    assert redstone._output_toward(
        (2, 2, 1), (3, 2, 1)
    ) == 15


def test_repeater_reads_loaded_wire_power_after_directional_output_fallback(monkeypatch):
    world, redstone = _world()
    _place(world, (2, 2, 1), BlockType.REPEATER, facing=Facing.WEST)
    _place(world, (1, 2, 1), BlockType.REDSTONE_DUST, redstonePower=9)

    # A loaded reference state may contain a wire whose directional arm is
    # absent. Vanilla AbstractRedstoneGateBlock still reads POWER directly.
    monkeypatch.setattr(redstone, "_output_toward", lambda *args, **kwargs: 0)
    assert redstone._repeater_input(
        (2, 2, 1), world.getBlockProperties(2, 2, 1)
    ) == 9


def test_repeater_uses_selected_two_game_tick_delay():
    world, redstone = _world()
    _place(world, (1, 2, 1), BlockType.REDSTONE_BLOCK)
    _place(world, (2, 2, 1), BlockType.REPEATER,
           facing=Facing.WEST, repeaterDelay=1)
    redstone.update(0)
    redstone.update(50)
    assert not world.getBlockProperties(2, 2, 1).powered
    redstone.update(50)
    assert world.getBlockProperties(2, 2, 1).powered


def test_repeater_extends_an_input_pulse_shorter_than_its_delay():
    world, redstone = _world()
    _place(world, (1, 2, 1), BlockType.LEVER, powered=True, redstonePower=15)
    _place(world, (2, 2, 1), BlockType.REPEATER,
           facing=Facing.WEST, repeaterDelay=4)
    redstone.update(0)

    props = world.getBlockProperties(1, 2, 1)
    props.powered = False
    props.redstonePower = 0
    world.setBlockProperties(1, 2, 1, props)
    redstone.mark_dirty()
    redstone.update(0)

    for _ in range(7):
        redstone.update(50)
        assert not world.getBlockProperties(2, 2, 1).powered
    redstone.update(50)
    assert world.getBlockProperties(2, 2, 1).powered
    for _ in range(7):
        redstone.update(50)
        assert world.getBlockProperties(2, 2, 1).powered
    redstone.update(50)
    assert not world.getBlockProperties(2, 2, 1).powered


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
    _place(world, (2, 2, 1), BlockType.REPEATER, facing=Facing.WEST)
    _place(world, (2, 1, 1), BlockType.REPEATER,
           facing=Facing.NORTH, powered=True, redstonePower=15)
    _place(world, (2, 0, 1), BlockType.REDSTONE_BLOCK)
    redstone.update(0)
    assert world.getBlockProperties(2, 2, 1).repeaterLocked
    redstone.update(200)
    assert not world.getBlockProperties(2, 2, 1).powered


def test_repeater_lock_state_change_reports_dirty_component():
    world, redstone = _world()
    _place(world, (2, 2, 1), BlockType.REPEATER, facing=Facing.WEST)
    _place(world, (2, 1, 1), BlockType.REPEATER,
           facing=Facing.NORTH, powered=True, redstonePower=15)
    _place(world, (2, 0, 1), BlockType.REDSTONE_BLOCK)
    assert redstone.update(0)
    assert world.getBlockProperties(2, 2, 1).repeaterLocked

    world.setBlock(2, 1, 1, BlockType.AIR)
    redstone.mark_dirty((2, 1, 1))
    assert redstone.update(0)
    assert not world.getBlockProperties(2, 2, 1).repeaterLocked


def test_redstone_torch_inverts_power_on_supporting_block():
    world, redstone = _world()
    _place(world, (2, 2, 1), BlockType.STONE)
    _place(world, (2, 2, 2), BlockType.REDSTONE_TORCH,
           powered=True, redstonePower=15)
    # A redstone block is a directional-independent strong source.  A
    # floor-mounted lever on the support's side would only provide weak power
    # in vanilla and must not be used as a shortcut here.
    _place(world, (1, 2, 1), BlockType.REDSTONE_BLOCK)
    redstone.update(0)
    assert not world.getBlockProperties(2, 2, 2).powered

    world.setBlock(1, 2, 1, BlockType.AIR)
    redstone.mark_dirty()
    redstone.update(0)
    assert world.getBlockProperties(2, 2, 2).powered


def test_redstone_torch_does_not_count_its_own_support_as_input():
    world, redstone = _world()
    _place(world, (2, 2, 1), BlockType.STONE)
    _place(world, (2, 2, 2), BlockType.REDSTONE_TORCH,
           powered=True, redstonePower=15)
    redstone.update(0)
    assert world.getBlockProperties(2, 2, 2).powered
    for _ in range(3):
        redstone.mark_dirty()
        redstone.update(0)
        assert world.getBlockProperties(2, 2, 2).powered


def test_redstone_torch_only_checks_power_emitted_by_its_support_face():
    """A weak-only side signal must not unpower a floor-mounted torch."""
    world, redstone = _world()
    _place(world, (2, 2, 0), BlockType.STONE)
    _place(world, (2, 2, 1), BlockType.REDSTONE_TORCH,
           powered=True, redstonePower=15)
    # The floor lever weakly powers adjacent cells, but its strong output is
    # only sent into its own support below.  Java's torch checks the support's
    # downward emitted face, so this side signal must not turn it off.
    _place(world, (1, 2, 0), BlockType.LEVER,
           powered=True, redstonePower=15)

    redstone.update(0)

    assert world.getBlockProperties(2, 2, 1).powered


def test_torch_inverter_chain_converges_when_downstream_is_visited_first():
    world, redstone = _world()
    # The second torch is mounted one block higher, so the first torch powers
    # its support. Set insertion order is intentionally not relied upon: a
    # single pass can otherwise leave the downstream state stale.
    _place(world, (2, 2, 1), BlockType.STONE)
    # The second support is above the first torch.  RedstoneTorchBlock's
    # strong output reaches the block above it; a side support would receive
    # only weak power and would not relay it to the next torch in vanilla.
    _place(world, (2, 2, 3), BlockType.STONE)
    _place(world, (2, 2, 2), BlockType.REDSTONE_TORCH,
           powered=False, redstonePower=0)
    _place(world, (2, 2, 4), BlockType.REDSTONE_TORCH,
           powered=True, redstonePower=15)
    _place(world, (1, 2, 1), BlockType.REDSTONE_BLOCK)
    redstone.update(0)
    assert not world.getBlockProperties(2, 2, 2).powered
    assert world.getBlockProperties(2, 2, 4).powered

    world.setBlock(1, 2, 1, BlockType.AIR)
    redstone.mark_dirty()
    redstone.update(0)
    assert world.getBlockProperties(2, 2, 2).powered
    assert not world.getBlockProperties(2, 2, 4).powered


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


def test_piston_accepts_java_quasi_power_around_block_above():
    world, redstone = _world()
    _place(world, (2, 2, 1), BlockType.PISTON, facing=Facing.EAST)
    _place(world, (2, 1, 2), BlockType.REDSTONE_BLOCK)
    redstone.update(50)
    assert world.getBlockProperties(2, 2, 1).pistonExtended


def test_slime_moves_side_neighbors_but_does_not_stick_to_honey():
    world, redstone = _world()
    _place(world, (2, 3, 1), BlockType.STICKY_PISTON,
           facing=Facing.EAST, sticky=True)
    _place(world, (3, 3, 1), BlockType.SLIME_BLOCK)
    _place(world, (3, 2, 1), BlockType.STONE)
    _place(world, (3, 4, 1), BlockType.HONEY_BLOCK)
    _place(world, (2, 2, 1), BlockType.REDSTONE_BLOCK)
    redstone.update(50)

    assert world.getBlock(4, 3, 1) == BlockType.SLIME_BLOCK
    assert world.getBlock(4, 2, 1) == BlockType.STONE
    assert world.getBlock(3, 4, 1) == BlockType.HONEY_BLOCK

    world.setBlock(2, 2, 1, BlockType.AIR)
    redstone.mark_dirty()
    redstone.update(50)
    assert world.getBlock(3, 3, 1) == BlockType.SLIME_BLOCK
    assert world.getBlock(3, 2, 1) == BlockType.STONE
    assert world.getBlock(3, 4, 1) == BlockType.HONEY_BLOCK


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


def test_sticky_retraction_does_not_pull_fragile_block_at_initial_cell():
    world, redstone = _world(width=10)
    _place(world, (2, 2, 1), BlockType.STICKY_PISTON,
           facing=Facing.EAST, sticky=True)
    _place(world, (3, 2, 1), BlockType.STONE_BRICKS)
    _place(world, (2, 1, 1), BlockType.REDSTONE_BLOCK)
    redstone.update(50)

    # A fragile block in the pull cell is not movable during Java's initial
    # retraction check, so the head retracts without breaking or moving it.
    world.setBlock(4, 2, 1, BlockType.REDSTONE_DUST)
    world.setBlock(2, 1, 1, BlockType.AIR)
    redstone.mark_dirty()
    redstone.update(50)

    assert world.getBlock(3, 2, 1) == BlockType.AIR
    assert world.getBlock(4, 2, 1) == BlockType.REDSTONE_DUST


def test_piston_world_writes_trigger_a_follow_up_topology_pass():
    """Moving a powered block must not leave adjacent dust latched forever."""
    world, redstone = _world(width=10, depth=8, height=6)
    _place(world, (2, 2, 1), BlockType.PISTON, facing=Facing.EAST)
    _place(world, (3, 2, 1), BlockType.REDSTONE_DUST)
    _place(world, (4, 2, 1), BlockType.REDSTONE_DUST)
    _place(world, (3, 3, 1), BlockType.REDSTONE_DUST)
    _place(world, (3, 4, 1), BlockType.REDSTONE_BLOCK)
    _place(world, (2, 1, 1), BlockType.REDSTONE_BLOCK)
    redstone.update(0)
    assert world.getBlockProperties(4, 2, 1).redstonePower > 0

    redstone.update(50)
    assert world.getBlock(3, 2, 1) == BlockType.PISTON_HEAD
    # The first tick performs the piston event; the next tick consumes the
    # world revision generated by that event and recalculates the dust.
    redstone.update(50)
    assert world.getBlockProperties(4, 2, 1).redstonePower == 0


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


def test_component_tick_reports_lamp_powered_by_repeater_transition():
    world, redstone = _world()
    _place(world, (1, 2, 1), BlockType.REDSTONE_BLOCK)
    _place(world, (2, 2, 1), BlockType.REPEATER,
           facing=Facing.WEST, repeaterDelay=1)
    _place(world, (3, 2, 1), BlockType.REDSTONE_LAMP)
    redstone.update(0)
    assert not world.getBlockProperties(3, 2, 1).powered

    redstone.update(50)
    assert not world.getBlockProperties(3, 2, 1).powered
    assert redstone.update(50)
    assert world.getBlockProperties(3, 2, 1).powered


def test_wire_connection_mask_encodes_north_east_south_west():
    world, redstone = _world()
    center = (3, 3, 1)
    _place(world, center, BlockType.REDSTONE_DUST)
    _place(world, (3, 2, 1), BlockType.REDSTONE_DUST)  # north, bit 0
    _place(world, (3, 4, 1), BlockType.LEVER)          # south, bit 2
    assert redstone.wire_connection_mask(center) == 0b0101


def test_wire_connection_mask_requires_vanilla_step_geometry():
    world, redstone = _world()
    center = (3, 3, 1)
    _place(world, center, BlockType.REDSTONE_DUST)

    # An upper wire over an air side is not a valid step connection.
    _place(world, (4, 3, 2), BlockType.REDSTONE_DUST)
    # A lower wire behind a solid side cannot be reached from this cell.
    _place(world, (3, 2, 1), BlockType.STONE)
    _place(world, (3, 2, 0), BlockType.REDSTONE_DUST)
    assert redstone.wire_connection_mask(center) == 0

    # The same upper wire becomes valid once the side is a solid support and
    # the current cell's upper space is open, matching WireConnection.UP.
    world.setBlock(4, 3, 1, BlockType.STONE)
    assert redstone.wire_connection_mask(center) == 0b0010

    # Filling the current cell's upper space suppresses all stepped arms.
    _place(world, (3, 3, 2), BlockType.STONE)
    assert redstone.wire_connection_mask(center) == 0


def test_wire_up_mask_marks_only_supported_step_connections():
    world, redstone = _world()
    center = (3, 3, 1)
    _place(world, center, BlockType.REDSTONE_DUST)
    _place(world, (4, 3, 1), BlockType.STONE)
    _place(world, (4, 3, 2), BlockType.REDSTONE_DUST)
    _place(world, (3, 2, 1), BlockType.REDSTONE_DUST)
    assert redstone.wire_up_connection_mask(center) == 0b0010

    _place(world, (3, 3, 2), BlockType.STONE)
    assert redstone.wire_up_connection_mask(center) == 0


def test_piston_base_is_solid_for_redstone_support_and_wire_climb():
    world, redstone = _world(width=12, depth=8, height=8)
    _place(world, (4, 3, 1), BlockType.PISTON, facing=Facing.EAST)
    _place(world, (3, 3, 1), BlockType.REDSTONE_DUST)
    _place(world, (4, 3, 2), BlockType.REDSTONE_DUST)
    redstone.update(0)
    assert redstone._is_solid((4, 3, 1))
    assert redstone.wire_up_connection_mask((3, 3, 1)) == 0b0010


def test_slime_and_honey_remain_solid_redstone_supports_even_with_translucent_art():
    world, redstone = _world(width=12, depth=8, height=8)
    # The application texture catalog deliberately renders these blocks with
    # translucent-looking pixels; that visual flag must not remove their
    # vanilla solid support behavior.
    redstone.definitions[BlockType.SLIME_BLOCK] = BlockDefinition(
        "Slime", "x", "x", "x", transparent=True
    )
    redstone.definitions[BlockType.HONEY_BLOCK] = BlockDefinition(
        "Honey", "x", "x", "x", transparent=True
    )
    _place(world, (3, 3, 1), BlockType.REDSTONE_DUST)
    _place(world, (4, 3, 1), BlockType.SLIME_BLOCK)
    _place(world, (4, 3, 2), BlockType.REDSTONE_DUST)
    _place(world, (3, 1, 1), BlockType.REDSTONE_DUST)
    _place(world, (4, 1, 1), BlockType.HONEY_BLOCK)
    _place(world, (4, 1, 2), BlockType.REDSTONE_DUST)

    assert redstone._is_solid((4, 3, 1))
    assert redstone._is_solid((4, 1, 1))
    assert redstone.wire_up_connection_mask((3, 3, 1)) == 0b0010
    assert redstone.wire_up_connection_mask((3, 1, 1)) == 0b0010


def test_sticky_piston_leaves_immovable_side_branch_blocks_in_place():
    world, redstone = _world()
    _place(world, (2, 2, 1), BlockType.STICKY_PISTON,
           facing=Facing.EAST, sticky=True)
    _place(world, (3, 2, 1), BlockType.SLIME_BLOCK)
    _place(world, (3, 1, 1), BlockType.OBSIDIAN)
    _place(world, (2, 1, 1), BlockType.REDSTONE_BLOCK)

    redstone.update(50)

    assert world.getBlock(4, 2, 1) == BlockType.SLIME_BLOCK
    assert world.getBlock(3, 1, 1) == BlockType.OBSIDIAN


def test_sticky_side_chain_skips_immovable_block_behind_the_branch():
    world, redstone = _world()
    _place(world, (2, 2, 1), BlockType.STICKY_PISTON,
           facing=Facing.EAST, sticky=True)
    _place(world, (3, 2, 1), BlockType.SLIME_BLOCK)
    _place(world, (3, 3, 1), BlockType.SLIME_BLOCK)
    _place(world, (2, 3, 1), BlockType.OBSIDIAN)
    _place(world, (2, 1, 1), BlockType.REDSTONE_BLOCK)

    redstone.update(50)

    assert world.getBlock(4, 2, 1) == BlockType.SLIME_BLOCK
    assert world.getBlock(4, 3, 1) == BlockType.SLIME_BLOCK
    assert world.getBlock(2, 3, 1) == BlockType.OBSIDIAN


def test_repeater_can_strong_power_through_a_piston_base():
    world, redstone = _world(width=12, depth=8, height=8)
    _place(world, (2, 3, 1), BlockType.REPEATER,
           facing=Facing.WEST, powered=True, redstonePower=15)
    _place(world, (3, 3, 1), BlockType.PISTON, facing=Facing.EAST)
    _place(world, (4, 3, 1), BlockType.REDSTONE_DUST)
    redstone.update(0)
    assert world.getBlockProperties(4, 3, 1).redstonePower == 15


def test_wire_strongly_powers_a_solid_block_and_relays_to_a_lamp():
    """A wire on a block can power a component on that block's side."""
    world, redstone = _world()
    _place(world, (1, 2, 1), BlockType.REDSTONE_BLOCK)
    _place(world, (2, 2, 1), BlockType.REDSTONE_DUST)
    _place(world, (2, 2, 0), BlockType.STONE)
    _place(world, (3, 2, 0), BlockType.REDSTONE_LAMP)

    redstone.update(0)

    assert world.getBlockProperties(2, 2, 1).redstonePower == 15
    assert world.getBlockProperties(3, 2, 0).powered


def test_dust_recalculation_does_not_seed_through_a_wire_only_solid_relay():
    world, redstone = _world(width=12, depth=8, height=8)
    # The left wire component is powered by a redstone block and points into a
    # stone relay. The right wire is a separate component behind that relay.
    # During Java wire recalculation, getReceivedRedstonePower temporarily
    # disables wire output, so the right component must not be seeded directly
    # through the stone; only an actual source can seed it.
    _place(world, (1, 2, 2), BlockType.REDSTONE_BLOCK)
    _place(world, (2, 2, 2), BlockType.REDSTONE_DUST)
    _place(world, (2, 2, 1), BlockType.STONE)
    _place(world, (3, 2, 2), BlockType.STONE)
    _place(world, (3, 2, 0), BlockType.STONE)
    _place(world, (3, 2, 1), BlockType.REDSTONE_DUST)

    redstone.update(0)

    assert world.getBlockProperties(2, 2, 2).redstonePower == 15
    assert world.getBlockProperties(3, 2, 1).redstonePower == 0


def test_strong_power_respects_floor_lever_mount_when_crossing_a_solid():
    world, redstone = _world()
    # The lever is floor-mounted on (1, 2, 0).  Its weak power is
    # omnidirectional, but Java's strong power only reaches that support cell.
    _place(world, (1, 2, 0), BlockType.STONE)
    _place(world, (1, 2, 1), BlockType.LEVER, powered=True, redstonePower=15)
    _place(world, (2, 2, 1), BlockType.STONE)
    _place(world, (3, 2, 1), BlockType.PISTON, facing=Facing.EAST)

    redstone.update(50)

    # A side-adjacent solid must not relay a floor lever's strong power into
    # the piston.  The old omnidirectional shortcut extended it incorrectly.
    assert not world.getBlockProperties(3, 2, 1).pistonExtended


def test_wire_does_not_connect_visually_to_consumers_that_cannot_emit_power():
    world, redstone = _world()
    center = (3, 3, 1)
    _place(world, center, BlockType.REDSTONE_DUST)
    _place(world, (3, 2, 1), BlockType.REDSTONE_LAMP)
    _place(world, (4, 3, 1), BlockType.PISTON, facing=Facing.EAST)
    assert redstone.wire_connection_mask(center) == 0


def test_isolated_dust_does_not_emit_side_power_to_a_lamp():
    world, redstone = _world()
    _place(world, (2, 2, 0), BlockType.REDSTONE_BLOCK)
    _place(world, (2, 2, 1), BlockType.REDSTONE_DUST)
    _place(world, (3, 2, 1), BlockType.REDSTONE_LAMP)
    redstone.update(0)
    assert redstone._dust_output_toward(
        (2, 2, 1), (3, 2, 1), world.getBlockProperties(2, 2, 1)
    ) == 0
    assert not world.getBlockProperties(3, 2, 1).powered


def test_local_dirty_update_recalculates_only_the_touched_wire_component():
    world, redstone = _world(width=40)
    for start in (2, 24):
        _place(world, (start, 2, 1), BlockType.LEVER, powered=True, redstonePower=15)
        for x in range(start + 1, start + 8):
            _place(world, (x, 2, 1), BlockType.REDSTONE_DUST)
    redstone.update(0)

    untouched = {
        (x, 2, 1): world.getBlockProperties(x, 2, 1).redstonePower
        for x in range(25, 32)
    }
    source = (2, 2, 1)
    props = world.getBlockProperties(*source)
    props.powered = False
    props.redstonePower = 0
    world.setBlockProperties(*source, props)
    redstone.mark_dirty(source)
    redstone.update(0)

    assert all(world.getBlockProperties(x, 2, 1).redstonePower == 0 for x in range(3, 10))
    assert {
        pos: world.getBlockProperties(*pos).redstonePower for pos in untouched
    } == untouched


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
