"""Editable circuit exhibits. Every action operates actual simulated blocks.

These spacious teaching layouts adapt ordinary Java mechanisms; they are not
claimed to be cell-for-cell copies of a creator's compact schematic. Sources
and operational contracts live alongside the blocks for review and tests.
"""
from dataclasses import dataclass, field
from domain.blocks import BlockType as B, BlockProperties as State, Facing as F


@dataclass
class Circuit:
    key: str
    name: str
    description: str
    instruction: str
    source: str
    cells: dict = field(default_factory=dict)
    controls: list = field(default_factory=list)
    outputs: list = field(default_factory=list)
    shell: set = field(default_factory=set)

    def put(self, pos, block, **state):
        self.cells[pos] = (block, State(**state) if state else None)

    def supported(self, pos, block, **state):
        x, y, z = pos
        self.cells.setdefault((x, y, z-1), (B.SMOOTH_STONE, None))
        self.put(pos, block, **state)

    def control(self, pos, label, block=B.LEVER, **state):
        state.setdefault("powered", False)
        self.supported(pos, block, **state)
        self.controls.append((label, pos))


def door(concealed=False):
    c = Circuit('hidden_entrance' if concealed else 'piston_door',
                'Concealed entrance' if concealed else '2 x 2 piston door',
                'Four sticky pistons retract a full two-wide, two-high doorway.',
                'Toggle the lever. Cutaway reveals the wiring above the doorway.',
                'Java 1.16.1 PistonBlock / RedstoneWireBlock; opposed piston-door adaptation')
    for x, facing, panel in ((3,F.EAST,4),(8,F.WEST,7)):
        for z in (2,3):
            c.put((x,5,z),B.STICKY_PISTON,facing=facing)
            c.put((panel,5,z),B.STONE_BRICKS if concealed else B.QUARTZ_BLOCK)
        for y in (3,4,5):
            c.supported((x,y,4),B.REDSTONE_DUST)
    for x in range(2,10):
        c.supported((x,2,4),B.REDSTONE_DUST)
    c.control((1,2,4),'Close / open',powered=True,redstonePower=15)
    for x in range(2,10):
        for z in range(1,6):
            if x in (2,9) or z == 5:
                pos=(x,5,z)
                c.put(pos,B.STONE_BRICKS if concealed else B.DEEPSLATE_TILES)
                c.shell.add(pos)
    if concealed:
        for x in range(2,10):
            for y in (3,4):
                pos=(x,y,5); c.put(pos,B.STONE_BRICKS); c.shell.add(pos)
    c.outputs=[(x,5,z) for x in (5,6) for z in (2,3)]
    return c


def staircase():
    c=Circuit('staircase','Retractable staircase',
              'Two banks of sticky pistons bring six steps together into a two-wide staircase.',
              'Toggle to extend the steps; rotate the view to inspect the rising signal bus.',
              'Java 1.16.1 PistonHandler; supported wire ascent and direct repeater power')
    for piston_y, panel_y, output_y, wire_y, facing in (
            (3,4,5,1,F.SOUTH), (8,7,6,10,F.NORTH)):
        for x,z in ((4,1),(5,2),(6,3)):
            c.put((x,piston_y,z),B.STICKY_PISTON,facing=facing)
            c.put((x,panel_y,z),B.STONE_BRICK_STAIRS,facing=F.EAST)
            c.supported((x,(piston_y+wire_y)//2,z),B.REPEATER,facing=facing.opposite())
            c.supported((x,wire_y,z),B.REDSTONE_DUST)
            c.outputs.append((x,output_y,z))
        c.supported((3,wire_y,1),B.REDSTONE_DUST)
        for x in range(4,7):
            for z in range(1,x-3):
                pos=(x,panel_y,z)
                if pos not in c.cells:
                    c.put(pos,B.DEEPSLATE_TILES);c.shell.add(pos)
    for y in range(1,11):
        c.supported((2,y,1),B.REDSTONE_DUST)
    for y in (5,6):
        for z in range(1,4):
            c.put((7,y,z),B.DEEPSLATE_TILES)
    c.control((1,1,1),'Extend / retract')
    return c


def clock(slow=False):
    c=Circuit('slow_clock' if slow else 'clock',
              'Slow toggle clock' if slow else 'Toggle clock',
              'A delayed inverter loop produces a repeating signal; the lever holds it stopped.',
              'Lever ON stops the clock. Switch it OFF to run. Click repeaters to change the period.',
              'Java RedstoneTorchBlock.scheduledTick / RepeaterBlock; delayed torch-feedback clock')
    c.put((4,4,1),B.SMOOTH_STONE)
    c.control((4,4,2),'Stop / run',powered=True,redstonePower=15)
    c.put((5,4,1),B.REDSTONE_WALL_TORCH,facing=F.EAST,powered=False)
    for pos in ((6,4,1),(6,5,1),(6,6,1),(5,6,1),(4,6,1)):
        c.supported(pos,B.REDSTONE_DUST)
    c.supported((4,5,1),B.REPEATER,facing=F.SOUTH,repeaterDelay=4 if slow else 2)
    if slow:
        c.supported((5,6,1),B.REPEATER,facing=F.EAST,repeaterDelay=4)
    c.supported((7,4,1),B.REDSTONE_DUST)
    c.put((8,4,1),B.REDSTONE_LAMP)
    c.outputs=[(8,4,1)]
    return c


def feed_tape():
    c=Circuit('feed_tape','Piston feed tape',
              'Four pistons circulate thirteen blocks around a square track.',
              'Press 1, 2, 3, 4 in order. Let each button release before repeating.',
              'Redstone Reference piston_feedtape family; Java PistonHandler; four-phase ring adaptation')
    for x in range(4,8):c.put((x,4,2),B.QUARTZ_BLOCK)
    for y in range(5,8):c.put((8,y,2),B.QUARTZ_BLOCK)
    for x in range(5,8):c.put((x,8,2),B.QUARTZ_BLOCK)
    for y in range(5,8):c.put((4,y,2),B.QUARTZ_BLOCK)
    c.put((4,4,2),B.GOLD_BLOCK)
    for pos,facing,control,label in (
        ((3,4,2),F.EAST,(2,4,2),'1 - east'),
        ((8,3,2),F.SOUTH,(8,2,2),'2 - south'),
        ((9,8,2),F.WEST,(10,8,2),'3 - west'),
        ((4,9,2),F.NORTH,(4,10,2),'4 - north')):
        c.put(pos,B.PISTON,facing=facing)
        c.control(control,label,B.STONE_BUTTON,facing=facing.opposite())
    return c


def circuits():
    return {c.key:c for c in (door(),door(True),staircase(),feed_tape(),clock(),clock(True))}


def counter():
    import json
    from pathlib import Path
    import sys
    base=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parents[1]))
    data=json.loads((base/'data/redstone/counter4.json').read_text(encoding='utf-8'))
    c=Circuit('counter','4-bit counter',
              'A real four-bit register and adder count clock pulses from 0 to 15.',
              'Pulse +1 sends a timed clock cycle. The display reads the four real output wires. Reset returns to zero.',
              data['source'])
    for row in data['blocks']:
        name=row['block'].split(':')[-1]
        block=B['REDSTONE_DUST' if name=='redstone_wire' else name.upper().replace('_CONCRETE','_WOOL')]
        p=row['properties'];state={}
        if p:
            state=dict(facing=F[p.get('facing','south').upper()],
                       powered=p.get('powered',p.get('lit','false'))=='true',
                       redstonePower=int(p.get('power',0)),
                       repeaterDelay=int(p.get('delay',1)),
                       repeaterLocked=p.get('locked','false')=='true',
                       comparatorSubtract=p.get('mode')=='subtract')
            if state['powered'] and block in (B.REDSTONE_TORCH,B.REDSTONE_WALL_TORCH,B.REPEATER):
                state['redstonePower']=15
        c.put((row['x']+2,row['z']+2,row['y']+1),block,**state)
    c.controls=[('Clock',p) for p,(b,s) in c.cells.items() if b==B.LEVER]
    c.outputs=[(50,12+13*k,2) for k in range(4)]
    return c


def load_circuit(world, simulator, circuit):
    """Fit every cell, clear all old tick queues, and start without QC."""
    max_x=max(p[0] for p in circuit.cells);max_y=max(p[1] for p in circuit.cells)
    max_z=max(p[2] for p in circuit.cells)
    world.resize(max_x+3,max_y+3,max_z+4,min_y=0,preserve=False)
    with world.bulkUpdate():
        for x in range(world.width):
            for y in range(world.depth):
                world.setBlock(x,y,0,B.POLISHED_DEEPSLATE)
        for pos,(block,state) in circuit.cells.items():
            world.setBlock(*pos,block)
            if state:world.setBlockProperties(*pos,state.copy())
    simulator.reset()
    simulator.quasi_connectivity=False
    simulator.update(0)


LAB_CIRCUITS=circuits()
LAB_CIRCUITS["counter"]=counter()
