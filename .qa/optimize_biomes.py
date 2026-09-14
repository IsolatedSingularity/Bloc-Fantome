from pathlib import Path
p=Path('Code/blocFantome.py');s=p.read_text(encoding='utf-8')
s=s.replace('        self._worldSurfaceMargin = 640','        self._biomeViewSurfaces = {}\n        self._capturedRenderTiles = {}\n        self._worldSurfaceMargin = 640')
s=s.replace('            anchorZ = self.cameraFocusZ\n            anchorScreenX', '''            anchorZ = self.cameraFocusZ
            if self.sceneMetadata.get('kind') == 'biome' and self.world.occupiedBounds:
                low, high = self.world.occupiedBounds
                anchorX = (low[0]+high[0])/2
                anchorY = (low[1]+high[1])/2
                anchorZ = (low[2]+high[2])/2
            anchorScreenX''',1)
s=s.replace("        self.searchQuery = ''\n        self.searchResults = []", "        self.searchQuery = ''\n        self.searchResults = []\n        self.hoveredSourceBlock = None\n        self._biomeViewSurfaces.clear()\n        self._capturedRenderTiles.clear()",1)
# Do not build the generic material model only to immediately replace it with
# the captured source sprite. Captured palette states already contain it.
start=s.index('            # Check if this is a liquid with a specific level',s.index('    def _renderWorld'))
end=s.index('            if sprite:\n',start)
chunk=s[start:end]
lookup=chunk.index('            sourceDisplay=False')
normal=chunk[:lookup]
captured=chunk[lookup:]
captured=captured.replace('            sourceDisplay=False','            sprite=None\n            sourceDisplay=False')
s=s[:start]+captured+'            if not sourceDisplay:\n'+''.join('    '+line if line.strip() else line for line in normal.splitlines(keepends=True))+s[end:]
# Captured liquid appearance is baked; animating generic liquid keys cannot
# change those sprites and invalidates otherwise stable landscape frames.
s=s.replace('            and any(item[4] in animatedTypes for item in blocksToDraw)','''            and any(item[4] in animatedTypes and not (
                (props := self.world.getBlockProperties(*item[1:4])) and props.sourceCapture
            ) for item in blocksToDraw)''')
needle='        targetSurface = self.screen\n        incrementalZoomBuild = bool('
assert needle in s
s=s.replace(needle,'''        biomeView = self.sceneMetadata.get('kind') == 'biome' and canCacheSurface
        if biomeView and surfaceKey in self._biomeViewSurfaces:
            surface, offset = self._biomeViewSurfaces[surfaceKey]
            self._worldSurfaceCache = surface
            self._worldSurfaceCacheKey = surfaceKey
            self._worldSurfaceCacheOffset = offset
            self._worldZoomFallback = None
            self._worldSurfaceBuild = None
            self._worldSurfaceBuildIndex = 0
            self.screen.blit(surface,(self.renderer.offsetX-offset[0]-self._worldSurfaceMargin,self.renderer.offsetY-offset[1]-self._worldSurfaceMargin))
            self.renderStats = {'candidates':allCandidateCount,'screen_candidates':len(blocksToDraw),'drawn':len(blocksToDraw),'occluded':occludedCount}
            return

        targetSurface = self.screen
        incrementalZoomBuild = bool(''')
needle='                drawY = screenY - round(96*self.zoomLevel) if sourceDisplay else screenY\n'
assert needle in s
s=s.replace(needle,needle+'''                if sourceDisplay:
                    cropped = self._capturedRenderTiles.get(sprite)
                    if cropped is None:
                        bounds = sprite.get_bounding_rect()
                        cropped = (sprite.subsurface(bounds), bounds.topleft)
                        if len(self._capturedRenderTiles) >= 1024:self._capturedRenderTiles.clear()
                        self._capturedRenderTiles[sprite] = cropped
                    sprite, (cx, cy) = cropped
                    drawX += cx
                    drawY += cy
''')
needle='            self._worldSurfaceCache = targetSurface\n'
assert needle in s
s=s.replace(needle,needle+'''            if biomeView:
                if len(self._biomeViewSurfaces) >= 4:
                    self._biomeViewSurfaces.pop(next(iter(self._biomeViewSurfaces)))
                self._biomeViewSurfaces[surfaceKey] = (targetSurface,(self.renderer.offsetX,self.renderer.offsetY))
''')
p.write_text(s,encoding='utf-8')
p=Path('Code/engine/tutorial_lessons.py');s=p.read_text(encoding='utf-8').replace('Open Structures in the right panel, select a preview, and click in the scene to place it.','Open Library, then Structures. Select a structure, choose Place structure, and click in the scene.').replace('Every Java 1.16.1 biome has an editable showcase. The list follows your current dimension.','Explore a curated set of Java 1.16.1 landscapes. Each biome family has one or two distinctive examples.').replace('select a large card','select a landscape').replace('Open Settings with the gear for volume sliders. The gear opens Settings; F11 toggles fullscreen.','Open Settings with the gear for volume and mute controls. F11 toggles fullscreen.');p.write_text(s,encoding='utf-8')
