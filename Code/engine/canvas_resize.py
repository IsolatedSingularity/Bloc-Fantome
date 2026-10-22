"""Undo ownership for centered canvas changes, including cropped cells."""
from copy import deepcopy
from dataclasses import replace

from engine.undo import Command


class CanvasResizeCommand(Command):
    # These are the persistent coordinates translated by _shiftAppWorldState.
    fields = ('selectionStart', 'selectionEnd', 'fillStart', 'measurePoint1',
              'measurePoint2', 'stampOrigin', 'magicWandSelection',
              '_copperAgeTimers', '_sculkSensorActiveUntil', 'snowLayers',
              'blueprintBlocks')

    def __init__(self, app, delta):
        self.app = app
        self.delta = delta
        self.before = None

    def execute(self):
        app = self.app
        if self.before is None:
            dimensions = (app.world.width, app.world.depth, app.world.height)
            self.before, _ = app._centeredWorldSnapshot(dimensions, 0, 0)
            self.before = replace(self.before,
                properties=deepcopy(self.before.properties),
                scene_metadata=deepcopy(self.before.scene_metadata))
            self.coordinates = {name: deepcopy(getattr(app, name)) for name in self.fields}
        app._resizeCanvasNow(self.delta)
        return True

    def undo(self):
        if self.before is None:
            return False
        app = self.app
        # World.replace consumes its dictionaries. Keep this undo record owned
        # independently so editing after undo cannot corrupt the next cycle.
        app.world.replace(replace(self.before, blocks=dict(self.before.blocks),
            properties=deepcopy(self.before.properties),
            liquid_levels=dict(self.before.liquid_levels),
            scene_metadata=deepcopy(self.before.scene_metadata)))
        app.sceneMetadata = deepcopy(self.before.scene_metadata)
        app.sceneStructurePositions = app.world.sceneStructurePositions
        app.sceneStructureBounds = app.world.sceneStructureBounds
        app.sceneExteriorGlassPositions = set(self.before.exterior_glass_positions)
        for name, value in self.coordinates.items():
            setattr(app, name, deepcopy(value))
        app._shiftAppWorldState(0, 0)
        app._clearTerrainNoisePreview()
        app.lightingDirty = True
        app._frameCurrentCanvas()
        return True

    def get_description(self):
        return 'Grow canvas' if self.delta > 0 else 'Shrink canvas'
