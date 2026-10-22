"""Practice-session setup kept separate from input and rendering code."""
from copy import deepcopy

from domain.blocks import BlockType, BlockProperties, Facing
from engine.tutorial_lessons import tour_scene
from engine.world_snapshot import WorldSnapshot


PRACTICE_TOOLS = ('brushSize','mirrorModeX','mirrorModeY','radialSymmetry','fillToolActive',
                  'fillStart','measurementMode','measurePoint1','measurePoint2','selectionActive',
                  'selectionStart','selectionEnd','selectionConfirmed','clipboard','clipboardSize',
                  'structurePlacementMode','selectedStructure','stampMode','blueprintMode',
                  'replaceMode','magicWandMode','previewFacing','previewSlabPosition',
                  'blocksExpanded','experimentalExpanded','structuresExpanded')


class GuidedTutorialAppMixin:
    def _practiceCheckpoint(self):
        world=self.world
        return WorldSnapshot(world.width,world.depth,world.height,world.min_y,self.currentDimension,
            blocks=dict(world.blocks),properties={p:v.copy() for p,v in world.blockProperties.items()},
            liquid_levels=dict(world.liquidLevels),liquid_sources=frozenset(world.liquidSources),
            liquid_falling=frozenset(world.liquidFalling),scene_metadata=dict(self.sceneMetadata))

    def _cancelTourLoad(self, *, navigating=False):
        pending=getattr(self,'_pendingTourLoad',None)
        if pending:pending[0].cancel()
        self._pendingTourLoad=None
        if not navigating:
            for future in getattr(self,'_tourWarmLoads',{}).values():future.cancel()
            self._tourWarmLoads={}
        for name in ('pendingBiomeLoad','pendingWorldLoad'):
            pending=getattr(self,name,None)
            if pending:pending[0].cancel();setattr(self,name,None)
        self.pendingBiomeWarmup=None

    def _stageTourScene(self,step):
        snapshot=self._readTourScene(step)
        if step['id']=='lighting' and snapshot._lighting is None and snapshot._prepared:
            from dataclasses import replace
            snapshot=replace(snapshot,_lighting=snapshot._prepared[0].calculateLighting())
        return snapshot

    def _readTourScene(self,step):
        if not getattr(self,'_buildingTutorialBundle',False):
            from engine.tutorial_prepared import load_lesson
            prepared=load_lesson(step['id'],self.world.catalog)
            if prepared is not None:return prepared
        if step['id']=='redstone':
            from engine.redstone_lab import counter
            from engine.world_snapshot import prepare_snapshot
            circuit=counter()
            cells={p:b for p,(b,_) in circuit.cells.items()}
            props={p:s.copy() for p,(_,s) in circuit.cells.items() if s}
            snapshot=WorldSnapshot(max(p[0] for p in cells)+3,max(p[1] for p in cells)+3,
                max(p[2] for p in cells)+4,0,'overworld',blocks=cells,properties=props,
                scene_metadata={'kind':'tutorial','id':'redstone','source':circuit.source})
            return prepare_snapshot(snapshot,self.world.catalog,reusable=False)
        if step.get('capture'):
            return self._stageBiomeScene(step['capture'])[0]
        if step.get('world'):
            import os
            from runtime_paths import WORLDS_DIR
            if step['world']=='end_city_1161':return self._stageBiomeScene('_tutorial_end_city')[0]
            return self._readBuildFile(os.path.join(WORLDS_DIR,step['world']+'.json.gz'))[3]
        from engine.tutorial_scenes import scene_snapshot
        from engine.world_snapshot import prepare_snapshot
        return prepare_snapshot(scene_snapshot(step['id']), self.world.catalog)

    def _loadGuidedLesson(self,index):
        if self.worldMapActive:
            self._exitWorldMap()
        if self.redstoneLabActive:
            self._toggleRedstoneLab()
        self._cancelTourLoad(navigating=True)
        step=self.tutorialScreen.lesson
        self._guidedActiveLesson=step['id']
        self.currentBuildPath=None
        self.panning=False
        self.layerViewEnabled=False
        self.library.visible=False
        for name,value in dict(brushSize=1,mirrorModeX=False,mirrorModeY=False,radialSymmetry=0,
            fillToolActive=False,fillStart=None,measurementMode=False,measurePoint1=None,measurePoint2=None,
            selectionActive=False,selectionStart=None,selectionEnd=None,selectionConfirmed=False,
            structurePlacementMode=False,stampMode=False,blueprintMode=False,replaceMode=False,magicWandMode=False).items():
            setattr(self,name,value)
        self._setInteractionMode(False)
        self.blocksExpanded=step.get('focus')=='blocks'
        self.experimentalExpanded=step.get('focus') in ('toggles','terrain')
        self.biomePanel.expanded=False
        self.inventoryScroll=self.inventoryScrollTarget=0
        if hasattr(self,'previewBrowser'):
            focus=step.get('focus')
            self.previewBrowser.expand(self,{'worlds':'Worlds','biomes':'Biomes','structures':'Structures'}.get(focus))
        warmed=getattr(self,'_tourWarmLoads',{}).pop(step['id'],None)
        for future in getattr(self,'_tourWarmLoads',{}).values():future.cancel()
        self._tourWarmLoads={}
        if warmed is None or warmed.cancelled():
            warmed=self.worldLoadExecutor.submit(self._stageTourScene,dict(step))
        self._pendingTourLoad=(warmed,step['id'])
        self.tutorialScreen.loading=True

    def _pollTourLoad(self):
        pending=getattr(self,'_pendingTourLoad',None)
        if not pending or not pending[0].done():return
        self._pendingTourLoad=None
        if not self.tutorialScreen.visible or pending[1]!=self.tutorialScreen.lesson['id']:return
        try:
            snapshot=pending[0].result()
            self._applyTourScene(snapshot,self.tutorialScreen.lesson)
            # Stage only the next page while the current one is being explored.
            # A prepared snapshot transfers ownership exactly once; never cache
            # the live world's dictionaries or reuse a consumed holder.
            from engine.tutorial_lessons import TOUR
            index=self.tutorialScreen.currentStep+1
            if index<len(TOUR) and not self.tutorialScreen.optional:
                step=TOUR[index]
                self._tourWarmLoads={step['id']:self.worldLoadExecutor.submit(self._stageTourScene,dict(step))}
        except Exception as error:
            self.tooltipText=f'Could not load tutorial scene: {error}';self.tooltipTimer=6000
        finally:
            self.tutorialScreen.loading=False

    def _applyTourScene(self,snapshot,step):
        from dataclasses import replace
        if not snapshot._prepared:
            snapshot=replace(snapshot,blocks=dict(snapshot.blocks),
            properties={p:v.copy() for p,v in snapshot.properties.items()},
            surface_positions=frozenset(snapshot.surface_positions),
            structure_positions=frozenset(snapshot.structure_positions),
            structure_surfaces_by_view={r:frozenset(v) for r,v in snapshot.structure_surfaces_by_view.items()},
            view_surface_positions_by_view={r:frozenset(v) for r,v in snapshot.view_surface_positions_by_view.items()})
        self._applyStagedBuild(snapshot.dimension,(snapshot.width,snapshot.depth,snapshot.height,snapshot.min_y),
            dict(snapshot.scene_metadata),snapshot,None,silent=True,preferredMusic=self.tutorialMusicPaths.get(snapshot.dimension))
        self.undoManager.clear();self.currentBuildPath=None
        self._stopRain();self._stopSnow();self._stopHorrorRain()
        self.rainEnabled=step['id']=='rain'
        self.snowEnabled=step['id']=='snow'
        self.horrorRainEnabled=False
        self.skyboxesEnabled=step['id'] in ('welcome','skies')
        self.cloudsEnabled=self.celestialEnabled=False
        self.lightingEnabled=step['id'] in ('welcome','lighting')
        self.showGrid=False
        self.hotbar=[BlockType[name.upper()] for name in step['icons']]
        self.hotbarSelectedSlot=0;self.selectedBlock=self.hotbar[0];self.previewFacing=Facing.SOUTH
        # The bastion's open vault faces southeast; its rear wall otherwise
        # hides the very surfaces used to demonstrate lighting.
        self.renderer.setViewRotation(1 if step['id']=='lighting' else 0)
        self._frameGuidedLesson(step)
        self._biomeViewSurfaces.clear();self._capturedRenderTiles.clear()
        self._invalidateViewCaches()
        import pygame
        self._worldZoomFallback=pygame.Surface((self._worldViewportRight()+self._worldSurfaceMargin*2,self.screen.get_height()+self._worldSurfaceMargin*2),pygame.SRCALPHA)
        self._worldTransitionKind='load'
        self.lightingDirty=True;self.redstone.mark_dirty();self.tooltipTimer=0
        if self.lightingEnabled and snapshot._lighting is not None:
            self.lightMap=snapshot._lighting
            self.lightingDirty=False
            self.litBlockCache.clear();self.litBlockCacheOrder.clear()
        # Authored demo liquids are settled until the visitor edits them.
        self.world.waterUpdateQueue.clear();self.world.lavaUpdateQueue.clear()
        self.world._waterQueued.clear();self.world._lavaQueued.clear()
        if hasattr(self,'previewBrowser') and self.previewBrowser.expanded in ('Worlds','Biomes'):
            self.previewBrowser.catalog.dimension=snapshot.dimension
            self.previewBrowser.catalog.refresh(self)
        self.tutorialScreen.observe(self)
        if self.rainEnabled:self._startRain()
        if self.snowEnabled:self._startSnow()
        if step['id']=='worldmap':
            self._openWorldMap()
        elif step['id']=='redstone':
            self._toggleRedstoneLab()

    def _frameGuidedLesson(self, step):
        """Frame the teaching subject, retaining the full surrounding world."""
        # Small lessons have authored subject bounds. Terrain and neighbouring
        # buildings remain editable, but no longer determine the teaching zoom.
        if step.get('frame') is not None:
            self._fitBoundsToViewport(step['frame'],notify=False)
            return
        if step['id']=='lighting' and self.sceneStructureBounds:
            self._fitBoundsToViewport(self.sceneStructureBounds,notify=False)
            return
        bounds = self.world.occupiedBounds
        if bounds is None:
            return
        low, high = bounds
        # Large source captures include context far beyond the demonstrated object.
        radius = {'welcome':18, 'blocks':14, 'camera':17, 'history':30,
                  'structures':32, 'dimensions':24, 'lighting':24}.get(step['id'], 32)
        cx, cy = (low[0]+high[0])/2, (low[1]+high[1])/2
        x0, x1 = max(low[0],round(cx-radius)), min(high[0],round(cx+radius))
        y0, y1 = max(low[1],round(cy-radius)), min(high[1],round(cy+radius))
        tops = [self.world.getHighestBlock(x,y) for x in range(x0,x1+1) for y in range(y0,y1+1)]
        z1 = max(tops) if tops else high[2]
        z0 = max(low[2], sorted(tops)[len(tops)//2]-4) if tops else low[2]
        if step['id']=='history':
            z0,z1=48,82
        self._fitBoundsToViewport(((x0,y0,z0),(x1,y1,z1)),notify=False)

    def _recordTutorialPlacement(self,block):
        tutorial=self.tutorialScreen
        tutorial.record('place')
        if block in (BlockType.WATER,BlockType.LAVA): tutorial.record('liquid')
        if block in (BlockType.POPPY,BlockType.DANDELION,BlockType.SUNFLOWER): tutorial.record('flower')
        if self._isStairType(block) or block.name.endswith('_SLAB'): tutorial.record('shape')
        if block in (BlockType.GLOWSTONE,BlockType.LANTERN,BlockType.SOUL_LANTERN,
                     BlockType.SEA_LANTERN,BlockType.SHROOMLIGHT,BlockType.JACK_O_LANTERN):
            tutorial.record('light')

    def _capturePracticeTools(self):
        return {name:deepcopy(getattr(self,name)) for name in PRACTICE_TOOLS if hasattr(self,name)}

    def _revealGuidedAnomaly(self):
        """One quiet, bounded change in the optional room, never a running effect."""
        x,y = ((25,9),(9,25),(25,22),(22,25))[self.renderer.viewRotation%4]
        for z in range(2,7):
            if self.world.getBlock(x,y,z)==BlockType.AIR:
                self.world.setBlock(x,y,z,BlockType.BLACK_WOOL)
        for dx in (-1,1):
            if self.world.getBlock(x+dx,y,5)==BlockType.AIR:
                self.world.setBlock(x+dx,y,5,BlockType.BONE_BLOCK)
        self.lightingDirty=True
