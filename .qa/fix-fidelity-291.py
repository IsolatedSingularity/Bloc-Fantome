from pathlib import Path
p=Path('Code/engine/biome_capture.py');s=p.read_text()
s=s.replace("    row=manifest()[name]", "    row={'file':'tutorial_end_city.json.gz'} if name=='_tutorial_end_city' else manifest()[name]")
s=s.replace("    if name not in manifest():return None", "    if name!='_tutorial_end_city' and name not in manifest():return None")
p.write_text(s)
p=Path('Code/engine/tutorial_runtime.py');s=p.read_text()
s=s.replace("            return self._readBuildFile(os.path.join(WORLDS_DIR,step['world']+'.json.gz'))[3]", "            if step['world']=='end_city_1161':return self._stageBiomeScene('_tutorial_end_city')[0]\n            return self._readBuildFile(os.path.join(WORLDS_DIR,step['world']+'.json.gz'))[3]")
s=s.replace("dict(snapshot.scene_metadata),snapshot,None,silent=True)", "dict(snapshot.scene_metadata),snapshot,None,silent=True,preferredMusic=self.tutorialMusicPaths.get(snapshot.dimension))")
s=s.replace("        self.tutorialScreen.observe(self)", "        if hasattr(self,'previewBrowser') and self.previewBrowser.expanded in ('Worlds','Biomes'):\n            self.previewBrowser.catalog.dimension=snapshot.dimension\n            self.previewBrowser.catalog.refresh(self)\n        self.tutorialScreen.observe(self)")
p.write_text(s)
p=Path('Code/engine/tutorial_lessons.py');s=p.read_text(encoding='utf-8-sig').replace('This is the bundled canonical city assembly.','This complete city was captured from the Java 1.16.1 reference world.')
p.write_text(s,encoding='utf-8')
p=Path('Code/blocFantome.py');s=p.read_text(encoding='utf-8')
s=s.replace('for dimension in (DIMENSION_NETHER, DIMENSION_END):','for dimension in (DIMENSION_OVERWORLD, DIMENSION_NETHER, DIMENSION_END):',1)
s=s.replace('bestScale = min(mipmapLevels, key=lambda level: abs(level - zoom))','bestScale = min((level for level in mipmapLevels if level >= zoom), default=max(mipmapLevels))')
# Only downsample mipmaps; the full source is used if no adequately sized mip exists.
s=s.replace('if mipmapLevels and zoom < 0.9:', 'if mipmapLevels and zoom < 0.9 and max(mipmapLevels) >= zoom:')
needle='                # Apply X-Ray transparency for solid blocks\n'
s=s.replace(needle,'''                # Seal subpixel raster cracks only on opaque full cubes. Thin,
                # transparent and modelled blocks retain their original silhouette.
                if self.zoomLevel < 0.65 and self._isOpaqueCubeDefinition(blockDef):
                    cache = getattr(self, '_opaqueZoomSprites', None)
                    if cache is None:cache = self._opaqueZoomSprites = {}
                    sealed = cache.get(sprite)
                    if sealed is None:
                        sealed = pygame.Surface((sprite.get_width()+2,sprite.get_height()+2),pygame.SRCALPHA)
                        sealed.blits([(sprite,p) for p in ((0,1),(2,1),(1,0),(1,2),(1,1))],doreturn=False)
                        if len(cache)>=512:cache.clear()
                        cache[sprite]=sealed
                    sprite=sealed;drawX-=1;drawY-=1

'''+needle)
p.write_text(s,encoding='utf-8')
