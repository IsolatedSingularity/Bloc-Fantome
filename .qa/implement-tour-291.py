from pathlib import Path
p=Path('Code/engine/tutorial_runtime.py')
s=p.read_text();a=s.index('    def _loadGuidedLesson(');b=s.index('    def _recordTutorialPlacement',a)
s=s[:a]+'''    def _cancelTourLoad(self):
        pending=getattr(self,'_pendingTourLoad',None)
        if pending:pending[0].cancel()
        self._pendingTourLoad=None
        for name in ('pendingBiomeLoad','pendingWorldLoad'):
            pending=getattr(self,name,None)
            if pending:pending[0].cancel();setattr(self,name,None)
        self.pendingBiomeWarmup=None

    def _stageTourScene(self,step):
        if step.get('capture'):
            return self._stageBiomeScene(step['capture'])[0]
        if step.get('world'):
            import os
            from runtime_paths import WORLDS_DIR
            return self._readBuildFile(os.path.join(WORLDS_DIR,step['world']+'.json.gz'))[3]
        from engine.tutorial_scenes import scene_snapshot
        return scene_snapshot(step['id'])

    def _loadGuidedLesson(self,index):
        self._cancelTourLoad()
        step=self.tutorialScreen.lesson
        self._guidedActiveLesson=step['id']
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
        cache=getattr(self,'_tourSnapshots',{})
        self._tourSnapshots=cache
        if step['id'] in cache:self._applyTourScene(cache[step['id']],step)
        elif step.get('capture') or step.get('world'):
            self._pendingTourLoad=(self.worldLoadExecutor.submit(self._stageTourScene,dict(step)),step['id'])
        else:
            snapshot=self._stageTourScene(step)
            cache[step['id']]=snapshot
            self._applyTourScene(snapshot,step)

    def _pollTourLoad(self):
        pending=getattr(self,'_pendingTourLoad',None)
        if not pending or not pending[0].done():return
        self._pendingTourLoad=None
        if not self.tutorialScreen.visible or pending[1]!=self.tutorialScreen.lesson['id']:return
        try:
            snapshot=pending[0].result()
            self._tourSnapshots[pending[1]]=snapshot
            self._applyTourScene(snapshot,self.tutorialScreen.lesson)
        except Exception as error:
            self.tooltipText=f'Could not load tutorial scene: {error}';self.tooltipTimer=6000

    def _applyTourScene(self,snapshot,step):
        self._applyStagedBuild(snapshot.dimension,(snapshot.width,snapshot.depth,snapshot.height,snapshot.min_y),
            dict(snapshot.scene_metadata),snapshot,None,silent=True)
        self.undoManager.clear();self.currentBuildPath=None
        self.rainEnabled=self.snowEnabled=self.horrorRainEnabled=False
        self.skyboxesEnabled=step['id']=='skies'
        self.cloudsEnabled=self.celestialEnabled=False
        self.lightingEnabled=step['id']=='lighting'
        self.showGrid=False
        self.hotbar=[BlockType[name.upper()] for name in step['icons']]
        self.hotbarSelectedSlot=0;self.selectedBlock=self.hotbar[0];self.previewFacing=Facing.SOUTH
        self.renderer.setViewRotation(0)
        self._fitWorldToViewport(notify=False)
        self._biomeViewSurfaces.clear();self._capturedRenderTiles.clear()
        self._invalidateViewCaches()
        self.lightingDirty=True;self.redstone.mark_dirty();self.tooltipTimer=0
        # Authored demo liquids are settled until the visitor edits them.
        self.world.waterUpdateQueue.clear();self.world.lavaUpdateQueue.clear()
        self.world._waterQueued.clear();self.world._lavaQueued.clear()
        self.tutorialScreen.observe(self)

'''+s[b:];p.write_text(s)
p=Path('Code/blocFantome.py');s=p.read_text()
s=s.replace('        self._pollBiomeLoad()','        self._pollBiomeLoad()\n        self._pollTourLoad()')
s=s.replace('        state = self._tutorialSessionSnapshot\n        if state is None:', '        self._cancelTourLoad()\n        state = self._tutorialSessionSnapshot\n        if state is None:',1)
s=s.replace('        elif self.tutorialScreen.visible:\n            self.tutorialScreen.hide()\n            self._restoreTutorialSession()','        elif self.tutorialScreen.visible:\n            self._cancelTourLoad()\n            self._tourMapReturn = True\n            self.tutorialScreen.visible = False',1)
a=s.index('    def _exitWorldMap(');b=s.index('    def _handleWorldMapAction',a)
part=s[a:b].replace('        return True','        if getattr(self, "_tourMapReturn", False):\n            self._tourMapReturn = False\n            self.tutorialScreen.visible = True\n        return True')
s=s[:a]+part+s[b:]
# Let tutorial navigation cancel a pending import before the loading shield handles editor input.
needle='            if self.pendingBiomeLoad is not None and event.type in'
s=s.replace(needle,'            if getattr(self, "_pendingTourLoad", None) is not None:\n                if self.tutorialScreen.handleEvent(event):continue\n                if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEWHEEL):\n                    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:self.tutorialScreen.hide()\n                    continue\n'+needle)
p.write_text(s)
