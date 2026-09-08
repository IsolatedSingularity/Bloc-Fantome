import pytest
from domain.blocks import BlockType as B, Facing as F
from engine.redstone_lab import LAB_CIRCUITS, load_circuit
from test_redstone import _world, _place


def advance(sim, ticks=40):
    for _ in range(ticks):sim.update(50)


def toggle(world,sim,pos):
    props=world.getBlockProperties(*pos).copy()
    props.powered=not props.powered
    props.redstonePower=15 if props.powered else 0
    world.setBlockProperties(*pos,props)
    sim.mark_dirty(pos)


@pytest.mark.parametrize('key',['piston_door','hidden_entrance','staircase'])
def test_mechanism_completes_twenty_cycles_without_qc(key):
    world,sim=_world();c=LAB_CIRCUITS[key];load_circuit(world,sim,c)
    assert not sim.quasi_connectivity
    lever=c.controls[0][1]
    for _ in range(40):
        advance(sim)
        on=world.getBlockProperties(*lever).powered
        assert all((world.getBlock(*p)!=B.AIR)==on for p in c.outputs)
        toggle(world,sim,lever)


@pytest.mark.parametrize('key',['clock','slow_clock'])
def test_clock_runs_stops_and_restarts_without_burnout(key):
    world,sim=_world();c=LAB_CIRCUITS[key];load_circuit(world,sim,c)
    lever=c.controls[0][1];lamp=c.outputs[0]
    advance(sim)
    assert not world.getBlockProperties(*lamp).powered
    for _ in range(3):
        toggle(world,sim,lever)
        states=[]
        for _ in range(200):
            sim.update(50);states.append(world.getBlockProperties(*lamp).powered)
        assert sum(a!=b for a,b in zip(states,states[1:]))>=8
        assert not sim._torch_cooldown
        toggle(world,sim,lever);advance(sim)
        assert not world.getBlockProperties(*lamp).powered


def test_feed_tape_moves_marker_and_conserves_every_block():
    world,sim=_world();c=LAB_CIRCUITS['feed_tape'];load_circuit(world,sim,c)
    starts=set(world.blockTypePositions[B.GOLD_BLOCK])
    for _ in range(4):
        for _,pos in c.controls:
            assert sim.press_button(pos)
            advance(sim,24)
        assert len(world.blockTypePositions[B.GOLD_BLOCK])==1
        assert len(world.blockTypePositions[B.QUARTZ_BLOCK])==12
    assert set(world.blockTypePositions[B.GOLD_BLOCK])!=starts


@pytest.mark.parametrize('facing,dz',[(F.UP,1),(F.DOWN,-1)])
def test_vertical_sticky_piston_pushes_and_pulls(facing,dz):
    world,sim=_world();sim.quasi_connectivity=False
    _place(world,(3,3,3),B.STICKY_PISTON,facing=facing)
    _place(world,(3,3,3+dz),B.GOLD_BLOCK)
    _place(world,(2,3,3),B.REDSTONE_BLOCK)
    advance(sim,4)
    assert world.getBlock(3,3,3+2*dz)==B.GOLD_BLOCK
    world.setBlock(2,3,3,B.AIR);sim.mark_dirty();advance(sim,4)
    assert world.getBlock(3,3,3+dz)==B.GOLD_BLOCK


def test_reset_discards_pending_clock_and_button_work():
    world,sim=_world();load_circuit(world,sim,LAB_CIRCUITS['clock'])
    sim._button_updates[(1,1,1)]=20
    sim._torch_updates[(1,1,1)]=50
    load_circuit(world,sim,LAB_CIRCUITS['staircase'])
    assert not sim._button_updates
    assert (1,1,1) not in sim._torch_updates


def test_torch_waits_two_game_ticks_before_inverting():
    world,sim=_world()
    _place(world,(2,2,1),B.STONE)
    _place(world,(2,2,2),B.REDSTONE_TORCH,powered=True,redstonePower=15)
    _place(world,(1,2,1),B.REDSTONE_BLOCK)
    sim.update(0);sim.update(50)
    assert world.getBlockProperties(2,2,2).powered
    sim.update(50)
    assert not world.getBlockProperties(2,2,2).powered


def rotated(circuit, turns):
    from copy import deepcopy
    c=deepcopy(circuit)
    for _ in range(turns):
        edge=max(p[1] for p in c.cells)+2
        transform=lambda p:(edge-p[1],p[0],p[2])
        c.cells={transform(p):(block,state) for p,(block,state) in c.cells.items()}
        for block,state in c.cells.values():
            if state:state.facing=state.facing.clockwise()
        c.controls=[(name,transform(p)) for name,p in c.controls]
        c.outputs=[transform(p) for p in c.outputs]
        c.shell={transform(p) for p in c.shell}
    return c


@pytest.mark.parametrize('turns',range(4))
def test_source_counter_counts_through_overflow_in_all_rotations(turns):
    c=rotated(LAB_CIRCUITS['counter'],turns)
    world,sim=_world();load_circuit(world,sim,c)
    advance(sim,160)
    def read():
        return sum(int(world.getBlockProperties(*p).redstonePower>0)<<i for i,p in enumerate(c.outputs))
    assert read()==0
    for count in range(1,25):
        toggle(world,sim,c.controls[0][1]);advance(sim,30)
        toggle(world,sim,c.controls[0][1]);advance(sim,110)
        assert read()==count%16


@pytest.mark.parametrize('key',['piston_door','staircase','clock','slow_clock'])
@pytest.mark.parametrize('turns',[1,2,3])
def test_exhibits_keep_operating_after_physical_rotation(key,turns):
    c=rotated(LAB_CIRCUITS[key],turns)
    world,sim=_world();load_circuit(world,sim,c)
    for _ in range(4):
        advance(sim,40)
        if key in ('piston_door','staircase'):
            on=world.getBlockProperties(*c.controls[0][1]).powered
            assert all((world.getBlock(*p)!=B.AIR)==on for p in c.outputs)
        toggle(world,sim,c.controls[0][1])
        if 'clock' in key and not world.getBlockProperties(*c.controls[0][1]).powered:
            levels=[]
            for _ in range(100):
                sim.update(50);levels.append(world.getBlockProperties(*c.outputs[0]).powered)
            assert any(levels) and not all(levels)


def test_comparator_compare_subtract_delay_and_strong_output():
    world,sim=_world()
    _place(world,(3,3,1),B.COMPARATOR,facing=F.WEST)
    _place(world,(2,3,1),B.REDSTONE_BLOCK)
    _place(world,(3,2,1),B.REDSTONE_BLOCK)
    _place(world,(4,3,1),B.STONE)
    _place(world,(5,3,1),B.REDSTONE_LAMP)
    sim.update(0);sim.update(50)
    assert not world.getBlockProperties(3,3,1).powered
    sim.update(50)
    assert world.getBlockProperties(5,3,1).powered
    props=world.getBlockProperties(3,3,1).copy();props.comparatorSubtract=True
    world.setBlockProperties(3,3,1,props);sim.mark_dirty();advance(sim,6)
    assert world.getBlockProperties(3,3,1).redstonePower==0
    assert not world.getBlockProperties(5,3,1).powered


def test_staircase_forms_two_adjacent_treads_at_each_rise():
    c = LAB_CIRCUITS['staircase']
    world, sim = _world()
    load_circuit(world, sim, c)
    toggle(world, sim, c.controls[0][1])
    advance(sim)
    assert set(c.outputs) == {(x, y, x-3) for x in (4,5,6) for y in (5,6)}
    for pos in c.outputs:
        assert world.getBlock(*pos) == B.STONE_BRICK_STAIRS
        assert world.getBlockProperties(*pos).facing == F.EAST


def test_bundled_models_and_counter_match_local_reference_cells():
    import json
    from pathlib import Path
    from engine.piston_models import PISTON_ELEMENTS
    root = Path(__file__).resolve().parents[1]
    reference = root / 'Game Reference/02_jar_extracted/client/assets/minecraft/models/block'
    if not reference.exists():
        pytest.skip('Optional local Java reference corpus is unavailable')
    names = dict(body='template_piston', extended='piston_extended',
                 head='template_piston_head', wall_torch='template_torch_wall')
    for key, elements in PISTON_ELEMENTS.items():
        assert elements == json.loads((reference / (names.get(key,key)+'.json')).read_text())['elements']
    data = json.loads((root / 'Code/data/redstone/counter4.json').read_text())
    dump = root / data['source']
    if dump.exists():
        assert data['blocks'] == [json.loads(line) for line in dump.read_text().splitlines()]
