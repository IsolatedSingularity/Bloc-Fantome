from pathlib import Path
p=Path('Code/domain/blocks.py');s=p.read_text();s=s.replace('    WHITE_TULIP = 663','    WHITE_TULIP = 663\n    END_ROD = 664\n    DRAGON_WALL_HEAD = 665\n    BREWING_STAND = 666');p.write_text(s)
p=Path('Code/engine/capture_materials.py');s=p.read_text();s+="\nMATERIALS.update({'END_ROD': (664, True), 'DRAGON_WALL_HEAD': (665, True), 'BREWING_STAND': (666, True)})\n";p.write_text(s)
p=Path('Code/engine/tutorial_runtime.py');s=p.read_text();s=s.replace("        if step.get('capture'):\n            return self._stageBiomeScene(step['capture'])[0]", "        if step.get('capture'):\n            return self._stageBiomeScene(step['capture'])[0]")
s=s.replace('        self._invalidateViewCaches()\n        self.lightingDirty', '''        self._invalidateViewCaches()
        import pygame
        self._worldZoomFallback=pygame.Surface((self._worldViewportRight()+self._worldSurfaceMargin*2,self.screen.get_height()+self._worldSurfaceMargin*2),pygame.SRCALPHA)
        self._worldTransitionKind='load'
        self.lightingDirty''')
p.write_text(s)
p=Path('Code/blocFantome.py');s=p.read_text(encoding='utf-8')
s=s.replace('        return snapshot, metadata\n\n    def _queueBiomeScene', '''        # Build visibility indices on the staging worker, not during the atomic
        # display-thread swap. The temporary world contains data only.
        from dataclasses import replace
        from engine.world import World as PreparedWorld
        prepared=PreparedWorld(width,depth,height,catalog=self.world.catalog)
        prepared.replace(snapshot)
        snapshot=replace(snapshot,surface_positions=frozenset(prepared.surfaceBlocks),
            view_surface_positions_by_view={r:frozenset(v) for r,v in prepared.viewSurfacePositionsByView.items()})
        return snapshot, metadata

    def _queueBiomeScene''')
s=s.replace('if (sceneMetadata or {}).get("kind") != "world":','if (sceneMetadata or {}).get("kind") not in ("world", "biome"):')
s=s.replace('transitionBatch = 5200 if self._worldTransitionKind == "rotation" else 4200', 'transitionBatch = 800 if self._worldTransitionKind == "load" else 2400 if self._worldTransitionKind == "rotation" else 4200')
p.write_text(s,encoding='utf-8')
