"""Main-thread ownership and completion of staged world/biome loads."""
import os
from runtime_paths import WORLDS_DIR


class WorldLoadingAppMixin:
    def _captureLoadOwner(self):
        return (self.world, self.world.revision, self.currentDimension,
                self.worldMapActive, self.redstoneLabActive, self._tutorialSessionSnapshot)

    def _queueBiomeScene(self, biome_id):
        if self.pendingBiomeLoad is not None or self.pendingWorldLoad is not None:
            return
        self._biomeLoadOwner = self._captureLoadOwner()
        self.pendingBiomeLoad = (self.worldLoadExecutor.submit(self._stageBiomeScene, biome_id, library=True), biome_id)


    def _pollBiomeLoad(self):
        if self.pendingBiomeLoad is None:
            self._biomeLoadOwner = None
            return
        if not self.pendingBiomeLoad[0].done():
            return
        if self._captureLoadOwner() != self._biomeLoadOwner:
            self.pendingBiomeLoad = self.pendingBiomeWarmup = None
            self._biomeLoadOwner = None
            self.tooltipText = "Biome load cancelled because the canvas changed"
            self.tooltipTimer = 3000
            return
        if self.pendingBiomeWarmup is not None:
            if self._worldSurfaceCache is None:
                return
            self.pendingBiomeWarmup += 1
            self._rotateViewAndRecenter(1)
            if self.pendingBiomeWarmup >= 4:
                self.pendingBiomeLoad = None
                self.pendingBiomeWarmup = None
                self._biomeLoadOwner = None
            return
        future, name = self.pendingBiomeLoad
        try:
            self._applyBiomeScene(*future.result())
            self._biomeLoadOwner = self._captureLoadOwner()
            if not self.horrorEnabled and not self.redstone.active_motions:
                self.pendingBiomeWarmup = 0
            else:
                self.pendingBiomeLoad = None
                self._biomeLoadOwner = None
        except Exception as error:
            self.pendingBiomeLoad = None
            self._biomeLoadOwner = None
            self.tooltipText = f"Could not open biome: {error}"
            self.tooltipTimer = 5000
            if getattr(self,'workshop',None):self.workshop.error=self.tooltipText


    def _handleWorldLibraryAction(self, action) -> None:
        if not action:
            return
        actionName, entry = action
        if actionName == "import":
            self.worldLibrary.close()
            self._openJavaWorldDialog()
            return
        if actionName != "open" or entry is None:
            return
        if self.pendingWorldLoad is not None:
            self.tooltipText = "A world is already loading"
            self.tooltipTimer = 1800
            return
        path = os.path.join(WORLDS_DIR, entry.filename)
        future = self.worldLoadExecutor.submit(self._readBuildFile, path)
        self.pendingWorldLoad = (future, entry, path)
        self._worldLoadOwner = self._captureLoadOwner()
        self.panning = False
        self.tooltipText = f"Loading {entry.name}..."
        self.tooltipTimer = 60000


    def _pollWorldLoad(self) -> None:
        if self.pendingWorldLoad is None:
            self._worldLoadOwner = None
            return
        future, entry, path = self.pendingWorldLoad
        if not future.done():
            return
        self.pendingWorldLoad = None
        expected = self._worldLoadOwner
        self._worldLoadOwner = None
        owner = self._captureLoadOwner()
        if owner != expected:
            self.tooltipText = "World load cancelled because the canvas changed"
            self.tooltipTimer = 3000
            return
        try:
            dimension, bounds, metadata, staged, skipped = future.result()
            opened = self._applyStagedBuild(
                dimension, bounds, metadata, staged, path, silent=True
            )
        except Exception as error:
            print(f"World load failed: {error}")
            opened = False
            skipped = 0
        if opened:
            self.currentBuildPath = None
            self.undoManager.undo_stack.clear()
            self.undoManager.redo_stack.clear()
            self.tooltipText = f"Opened {entry.name} | {entry.subtitle}"
            self.tooltipTimer = 3500
            print(
                f"World opened: {entry.name} ({len(self.world.blocks)} cells, "
                f"{skipped} skipped)"
            )
        else:
            self.tooltipText = f"Could not open {entry.name}"
            self.tooltipTimer = 3000
            if getattr(self,'workshop',None):self.workshop.error=self.tooltipText+'. Your current build stays open.'
