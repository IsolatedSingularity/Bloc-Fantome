"""An owned save transaction. Workers never read the live editor world."""
from copy import deepcopy
from dataclasses import dataclass, fields
from collections import namedtuple
from operator import attrgetter
from time import perf_counter

from engine.world_snapshot import WorldSnapshot
from domain.blocks import BlockProperties

_property_fields = tuple(field.name for field in fields(BlockProperties))
_property_values = attrgetter(*_property_fields)
SavedProperties = namedtuple('SavedProperties', _property_fields)


def capture_save(world, dimension, metadata, structures, progress=None):
    """Own every mutable value; equal primitive property states may share a tuple.

    Capture stays on the owner thread. The optional callback pumps/presents only,
    never dispatches edits, so queued input cannot change this transaction.
    """
    blocks = dict(world.blocks)
    properties = {}
    states = {}
    total = len(world.blockProperties)
    for index, (position, value) in enumerate(world.blockProperties.items()):
        values = _property_values(value)
        owned = states.get(values)
        if owned is None:
            owned = states[values] = SavedProperties(*values)
        properties[position] = owned
        if progress and index % 4096 == 0:
            progress(index, total)
    return WorldSnapshot(width=world.width, depth=world.depth, height=world.height,
        min_y=world.min_y, dimension=dimension, blocks=blocks,
        properties=properties,
        liquid_levels=dict(world.liquidLevels), liquid_sources=frozenset(world.liquidSources),
        liquid_falling=frozenset(world.liquidFalling), scene_metadata=deepcopy(metadata),
        structure_positions=frozenset(structures))


@dataclass
class SaveJob:
    future: object
    world: object
    revision: int
    path: str
    track_path: bool
    silent: bool
    started: float
    capture_ms: float
    generation: int = 0
    autosave: bool = False

    def belongs_to(self, world, generation):
        """Edits may advance revision; replacing the document invalidates ownership."""
        return self.world is world and self.generation == generation


class SaveCoordinator:
    """Single owner of the save worker and its one in-flight transaction.

    The UI owns capture, dialogs and presentation. This service receives an
    already-owned snapshot and returns completion exactly once on the UI thread.
    It has no application/SDL dependency and never reads the live world on a worker.
    """
    def __init__(self, executor=None):
        self.executor = executor
        self.pending = None

    def start(self, snapshot, definitions, *, world, revision, generation, path,
              track_path, silent, started, capture_ms, autosave=False, backup=None):
        if self.pending is not None:
            raise RuntimeError("A save transaction is already pending")
        if self.executor is None:
            from concurrent.futures import ThreadPoolExecutor
            self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='build-save')
        future = self.executor.submit(write_timed, path, snapshot, definitions, backup)
        self.pending = SaveJob(future, world, revision, str(path), track_path,
                               silent, started, capture_ms, generation, autosave)
        return self.pending

    def take_completed(self):
        job = self.pending
        if job is None or not job.future.done():
            return None
        self.pending = None
        return job

    def shutdown(self):
        if self.executor is not None:
            self.executor.shutdown(wait=True)


def write_timed(path, snapshot, definitions, backup=None):
    from engine.build_io import write_build
    from pathlib import Path
    from datetime import datetime
    start = perf_counter()
    warning = ''
    if backup:
        directory, count = backup
        try:
            directory = Path(directory)
            previous = sorted(directory.glob('backup_*.json*'), key=lambda p: p.stat().st_mtime)
            write_build(directory / ('backup_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '.json.gz'),
                        snapshot, definitions)
            for old in previous[:max(0, len(previous) - max(1, count) + 1)]:
                old.unlink()
        except OSError as error:
            warning = f'Recovery backup failed: {error}'
    result = write_build(path, snapshot, definitions)
    return result, (perf_counter() - start) * 1000, warning
