from pathlib import Path
p=Path('Code/blocFantome.py');s=p.read_text(encoding='utf-8')
a=s.index('    def _saveBackup(');b=s.index('    def _getBackupFiles',a)
s=s[:a]+'''    def _saveBackup(self, filepath: str):
        """Use the same atomic v5 serializer as ordinary saves."""
        return self._saveBuilding(filepath=filepath, silent=True)

'''+s[b:]
a=s.index('            # Delete oldest backups');b=s.index('        except Exception as e:',a)
s=s[:a]+'''            # Commit the replacement before retiring any recovery point.
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            backupPath = os.path.join(self.backupDir, f"backup_{timestamp}.json.gz")
            if not self._saveBackup(backupPath):
                return False
            while len(backups) >= max(1, self.maxBackups):
                oldest = backups.pop(0)
                os.remove(oldest[0])
            return True

'''+s[b:]
s=s.replace('            print(f"Backup error: {e}")','            print(f"Backup error: {e}")\n            return False')
s=s.replace('            self._saveBuilding(os.path.basename(self.autoSavePath), silent=True)','''            if not self._saveBuilding(os.path.basename(self.autoSavePath), silent=True):
                self.autoSaveFlashTimer = 0
                self.tooltipText = "Autosave failed; your world is still open"
                self.tooltipTimer = 3000
                return''')
s=s.replace('        except (OSError, ValueError, json.JSONDecodeError) as error:', '        except (OSError, ValueError, EOFError) as error:')
s=s.replace('        self.pendingWorldLoad = (future, entry, path)','''        self.pendingWorldLoad = (future, entry, path)
        self._worldLoadOwner = (self.world, self.world.revision, self.currentDimension,
                                self.worldMapActive, self.redstoneLabActive,
                                self._tutorialSessionSnapshot)
        self.panning = False''')
s=s.replace('        self.pendingWorldLoad = None\n        try:\n            dimension, bounds, metadata, staged, skipped = future.result()', '''        self.pendingWorldLoad = None
        owner = (self.world, self.world.revision, self.currentDimension,
                 self.worldMapActive, self.redstoneLabActive, self._tutorialSessionSnapshot)
        if owner != self._worldLoadOwner:
            self.tooltipText = "World load cancelled because the canvas changed"
            self.tooltipTimer = 3000
            return
        try:
            dimension, bounds, metadata, staged, skipped = future.result()''')
s=s.replace('            if self.worldMapActive:\n                action = self.worldMapView.handle_event(event)', '''            if self.pendingWorldLoad is not None:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.pendingWorldLoad[0].cancel()
                    self.pendingWorldLoad = None
                    self.tooltipText = "World load cancelled"
                    self.tooltipTimer = 1800
                continue
            if self.worldMapActive:
                action = self.worldMapView.handle_event(event)''')
p.write_text(s,encoding='utf-8')
p=Path('Code/engine/build_io.py');s=p.read_text();s=s.replace('    save_version = int(save_data.get("version", 1))','''    try:
        save_version = int(save_data.get("version", 1))
    except (TypeError, ValueError) as error:
        raise ValueError("Invalid build version") from error
    if save_version not in range(1, 6):
        raise ValueError(f"Unsupported build version: {save_version}")''')
s=s.replace('    staged = []\n    structure_positions', '    staged = {}\n    structure_positions')
s=s.replace('            staged.append((x, y, z, parsed_type, block_properties, liquid_state))','''            # Last valid row wins, including removal of earlier state and role.
            staged[(x, y, z)] = (x, y, z, parsed_type, block_properties, liquid_state)
            structure_positions.discard((x, y, z))''')
s=s.replace('    if save_version < 4:', '''    if save_data["blocks"] and not staged:
        raise ValueError("Build contains no valid blocks")
    staged = list(staged.values())
    if save_version < 4:''')
p.write_text(s)
p=Path('Code/engine/undo.py');s=p.read_text();a=s.index('        success = True',s.index('class BatchCommand'));b=s.index('    def undo(',a)
s=s[:a]+'''        self._executed = False
        completed = []
        with ExitStack() as stack:
            for world in self._worlds():
                bulk_update = getattr(world, "bulkUpdate", None)
                if bulk_update is not None:
                    stack.enter_context(bulk_update())
            try:
                for cmd in self.commands:
                    if not cmd.execute():
                        for previous in reversed(completed):
                            if not previous.undo():
                                raise RuntimeError("Batch rollback failed")
                        return False
                    completed.append(cmd)
            except Exception:
                for previous in reversed(completed):
                    previous.undo()
                raise
        self._executed = True
        return True

'''+s[b:];p.write_text(s)
