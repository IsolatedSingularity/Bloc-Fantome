from pathlib import Path
p=Path('Code/blocFantome.py');s=p.read_text(encoding='utf-8')
a=s.index('    def _updateLiquidAnimation60(');b=s.index('        # Update spawner particles',a)
part=s[a:b]
part=part.replace('if self.waterFrames and visualFrame != self.currentWaterVisualFrame:', 'if self._animationWanted(BlockType.WATER) and self.waterFrames and visualFrame != self.currentWaterVisualFrame:')
part=part.replace('if self.lavaFrames and visualFrame != self.currentLavaVisualFrame:', 'if self._animationWanted(BlockType.LAVA) and self.lavaFrames and visualFrame != self.currentLavaVisualFrame:')
part=part.replace('if self.portalFrames:', 'if self.portalFrames and self._animationWanted(BlockType.NETHER_PORTAL):')
part=part.replace('if self.endPortalTexture:', 'if self.endPortalTexture and (self._animationWanted(BlockType.END_PORTAL) or self._animationWanted(BlockType.END_GATEWAY)):')
part=part.replace('if self.fireFrames:', 'if self.fireFrames and self._animationWanted(BlockType.FIRE):')
part=part.replace('if self.soulFireFrames:', 'if self.soulFireFrames and self._animationWanted(BlockType.SOUL_FIRE):')
part=part.replace('if self.matrixAnimationTimer >= self.matrixAnimationSpeed:', 'if self.matrixAnimationTimer >= self.matrixAnimationSpeed and self._animationWanted(BlockType.MATRIX):')
part=part.replace('if self.enchantingAnimationTimer >= self.enchantingAnimationSpeed:', 'if self.enchantingAnimationTimer >= self.enchantingAnimationSpeed and self._animationWanted(BlockType.ENCHANTING_TABLE):')
s=s[:a]+'''    def _animationWanted(self, blockType):
        demand = getattr(self, '_animationDemand', None)
        return demand is None or blockType in demand

'''+part+s[b:]
needle='        self.assetManager.updateAnimation(dt)'
assert needle in s
s=s.replace(needle,'''        # Keep every visible inventory/world animation, without rasterizing
        # expensive fire, portal and enchanting models absent from the scene.
        demand = set(self.world.blockTypePositions) | set(self.hotbar) | set(self.hotbar2)
        demand.add(self.selectedBlock)
        if self.blocksExpanded:
            for category, expanded in self.expandedCategories.items():
                if expanded: demand.update(BLOCK_CATEGORIES.get(category, ()))
        self.assetManager._animationDemand = demand
        self.assetManager.updateAnimation(dt)''')
p.write_text(s,encoding='utf-8')
