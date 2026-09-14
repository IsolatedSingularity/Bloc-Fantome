from pathlib import Path
p=Path('Code/blocFantome.py');s=p.read_text(encoding='utf-8');a=s.index('        from engine.biome_catalog import BY_ID\n',s.index('    def _openBiomeScene'));b=s.index('\n    def _generateTerrainSlice',a)
s=s[:a]+'''        from engine.biome_capture import capture
        from engine.anvil import JavaBlock
        from engine.world_snapshot import WorldSnapshot
        data=capture(biome_id)
        palette=data['palette']
        source=[JavaBlock(x,z,y,palette[p]['Name'],palette[p].get('Properties',{})) for x,y,z,p in data['blocks']]
        staged,skipped=self._stageJavaBlocks(source)
        if skipped:raise ValueError(f'Capture has {skipped} unsupported blocks')
        indices={(x,y,z):p for x,y,z,p in data['blocks']}
        blocks={};properties={};liquid={};sources=set();falling=set()
        for x,y,z,block,props,fluid in staged:
            pos=(x,y,z);blocks[pos]=block
            props=props or BlockProperties()
            props.sourceCapture=biome_id;props.sourcePalette=indices[pos]
            properties[pos]=props
            if fluid:
                level=int(palette[indices[pos]].get('Properties',{}).get('level','0'))
                liquid[pos]=8 if level==0 or level>=8 else 8-level
                if level==0:sources.add(pos)
                if level>=8:falling.add(pos)
        metadata={'kind':'biome','name':biome_id.replace('_',' ').title(),'biome':biome_id,
                  'version':'Java 1.16.1','seed':data['seed'],'origin':data['origin'],
                  'capture_kind':data['capture_kind'],'accuracy':data['presentation']}
        width,depth,height=data['size']
        snapshot=WorldSnapshot(width,depth,height,dimension=data['dimension'],blocks=blocks,
                               properties=properties,liquid_levels=liquid,liquid_sources=frozenset(sources),
                               liquid_falling=frozenset(falling),scene_metadata=metadata)
        self._applyStagedBuild(data['dimension'],(width,depth,height,0),metadata,snapshot,None,silent=True)
        self.currentBuildPath=None
        self.undoManager.clear()
        self._fitWorldToViewport(notify=False)
        self.tooltipText=metadata['name']+' | Java 1.16.1 capture'
        self.tooltipTimer=3500
''' +s[b:];p.write_text(s,encoding='utf-8')
