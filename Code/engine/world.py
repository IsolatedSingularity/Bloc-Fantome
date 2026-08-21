"""
World Module for Bloc Fantome

This module contains the World class which manages the 3D voxel grid
for the building area. It uses dictionary-based sparse storage for
efficient memory usage, storing only non-air blocks.

Features:
- Block placement and removal
- Liquid flow simulation (water and lava)
- Lighting system (experimental)
- Ambient occlusion calculation
- Structure placement
"""

from collections import defaultdict, deque
from contextlib import contextmanager
from typing import Any, Deque, Dict, List, Optional, Set, Tuple

from domain.world_catalog import WorldCatalog
from engine.block_state import BlockProperties
from engine.performance import ChunkStorage, DirtyRegionTracker


class World:
    """
    Manages the 3D voxel grid for the building area.
    
    Uses a dictionary-based sparse storage for efficient memory usage,
    storing only non-air blocks.
    """
    
    def __init__(self, width: int, depth: int, height: int, *,
                 catalog: WorldCatalog, min_y: int = 0, chunk_size: int = 16):
        """
        Initialize the world.
        
        Args:
            width: X dimension of the world
            depth: Y dimension of the world  
            height: Z dimension (vertical) of the world
        """
        self.catalog = catalog
        self.width = width
        self.depth = depth
        self.height = height
        self.min_y = int(min_y)
        self.max_y_exclusive = self.min_y + self.height
        self.blocks: Dict[Tuple[int, int, int], Any] = {}
        self.chunkStorage = ChunkStorage(chunk_size)
        self.dirtyRegions = DirtyRegionTracker(chunk_size)
        self._columnLevels: Dict[Tuple[int, int], Set[int]] = {}
        self.heightIndex: Dict[Tuple[int, int], int] = {}
        self.blockTypePositions: Dict[Any, Set[Tuple[int, int, int]]] = {}
        self.blockTypeCounts: Dict[Any, int] = {}
        self._axisCounts = ({}, {}, {})
        self.occupiedBounds: Optional[
            Tuple[Tuple[int, int, int], Tuple[int, int, int]]
        ] = None
        # Conservative render index: blocks with at least one air neighbor.
        # It removes buried terrain cells from large-world candidate scans
        # without changing the editable sparse world representation.
        self.surfaceBlocks: Set[Tuple[int, int, int]] = set()
        self.surfaceChunks: Dict[Tuple[int, int, int], Set[Tuple[int, int, int]]] = {}
        self.sceneStructurePositions: Set[Tuple[int, int, int]] = set()
        self.sceneStructureBounds: Optional[
            Tuple[Tuple[int, int, int], Tuple[int, int, int]]
        ] = None
        self.sceneStructureChunks: Dict[Tuple[int, int, int], Set[Tuple[int, int, int]]] = {}
        self.sceneStructureSurfacesByView = {rotation: set() for rotation in range(4)}
        self.sceneStructureSurfaceChunksByView = {rotation: {} for rotation in range(4)}
        self._sceneStructureOverviewPositions = None
        self.revision = 0
        self._bulkDepth = 0
        self._bulkChanged = False
        # Block properties for special blocks (doors, slabs, stairs)
        self.blockProperties: Dict[Tuple[int, int, int], 'BlockProperties'] = {}
        # Fluid state mirrors the 1.16.1 source model: level, still/source,
        # and falling are separate properties.
        self.liquidLevels: Dict[Tuple[int, int, int], int] = {}
        self.liquidSources: Set[Tuple[int, int, int]] = set()
        self.liquidFalling: Set[Tuple[int, int, int]] = set()
        self.waterUpdateQueue: Deque[Tuple[int, int, int]] = deque()
        self.lavaUpdateQueue: Deque[Tuple[int, int, int]] = deque()
        self._waterQueued: Set[Tuple[int, int, int]] = set()
        self._lavaQueued: Set[Tuple[int, int, int]] = set()
        self.dimension = "overworld"

    def setDimension(self, dimension: str) -> None:
        """Set the dimension used by Nether-specific lava rules."""
        self.dimension = dimension
    
    def getBlock(self, x: int, y: int, z: int) -> 'BlockType':
        """Get the block type at a position"""
        BlockType = self.catalog.block_type
        if not self.isInBounds(x, y, z):
            return BlockType.AIR
        return self.blocks.get((x, y, z), BlockType.AIR)
    
    def getBlockProperties(self, x: int, y: int, z: int) -> Optional['BlockProperties']:
        """Get the properties for a block at a position (None if no special properties)"""
        return self.blockProperties.get((x, y, z))
    
    def setBlockProperties(self, x: int, y: int, z: int, props: 'BlockProperties'):
        """Set properties for a block at a position"""
        if self.isInBounds(x, y, z):
            self.blockProperties[(x, y, z)] = props
            if self._bulkDepth:
                self._bulkChanged = True
            else:
                self.revision += 1
                self.dirtyRegions.mark_block_and_neighbors(x, y, z)

    def _storeBlock(self, pos: Tuple[int, int, int], blockType: 'BlockType') -> bool:
        """Synchronize sparse, chunk, height, and dirty indexes for one edit."""
        BlockType = self.catalog.block_type
        oldBlock = self.blocks.get(pos, BlockType.AIR)
        if oldBlock == blockType:
            return False
        x, y, z = pos
        column = (x, y)
        levels = self._columnLevels.get(column)
        if oldBlock != BlockType.AIR:
            self.blocks.pop(pos, None)
            self.chunkStorage.set_block(x, y, z, None)
            self._removePositionIndexes(pos, oldBlock)
            if levels is not None:
                levels.discard(z)
                if not levels:
                    self._columnLevels.pop(column, None)
                    self.heightIndex.pop(column, None)
                elif self.heightIndex.get(column) == z:
                    self.heightIndex[column] = max(levels)
        if blockType != BlockType.AIR:
            self.blocks[pos] = blockType
            self.chunkStorage.set_block(x, y, z, blockType)
            self._addPositionIndexes(pos, blockType)
            levels = self._columnLevels.setdefault(column, set())
            levels.add(z)
            if z > self.heightIndex.get(column, self.min_y - 1):
                self.heightIndex[column] = z
        if self._bulkDepth:
            self._bulkChanged = True
        else:
            self._refreshSurfaceNeighborhood(pos)
            self.revision += 1
            self.dirtyRegions.mark_block_and_neighbors(x, y, z)
        return True

    def _addPositionIndexes(self, pos, blockType) -> None:
        positions = self.blockTypePositions.setdefault(blockType, set())
        positions.add(pos)
        self.blockTypeCounts[blockType] = len(positions)
        for axis, value in enumerate(pos):
            counts = self._axisCounts[axis]
            counts[value] = counts.get(value, 0) + 1
        self._refreshOccupiedBounds()

    def _removePositionIndexes(self, pos, blockType) -> None:
        positions = self.blockTypePositions.get(blockType)
        if positions is not None:
            positions.discard(pos)
            if positions:
                self.blockTypeCounts[blockType] = len(positions)
            else:
                self.blockTypePositions.pop(blockType, None)
                self.blockTypeCounts.pop(blockType, None)
        for axis, value in enumerate(pos):
            counts = self._axisCounts[axis]
            remaining = counts.get(value, 0) - 1
            if remaining > 0:
                counts[value] = remaining
            else:
                counts.pop(value, None)
        self._refreshOccupiedBounds()

    def _refreshOccupiedBounds(self) -> None:
        if not self.blocks:
            self.occupiedBounds = None
            return
        self.occupiedBounds = (
            tuple(min(counts) for counts in self._axisCounts),
            tuple(max(counts) for counts in self._axisCounts),
        )

    @staticmethod
    def _neighborPositions(pos: Tuple[int, int, int]):
        x, y, z = pos
        for dx, dy, dz in (
            (1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0),
            (0, 0, 1), (0, 0, -1),
        ):
            yield (x + dx, y + dy, z + dz)

    def _isSurfaceBlock(self, pos: Tuple[int, int, int]) -> bool:
        BlockType = self.catalog.block_type
        if self.blocks.get(pos, BlockType.AIR) == BlockType.AIR:
            return False
        return any(self.getBlock(*neighbor) == BlockType.AIR for neighbor in self._neighborPositions(pos))

    def _refreshSurfaceNeighborhood(self, pos: Tuple[int, int, int]) -> None:
        for candidate in (pos, *self._neighborPositions(pos)):
            if self._isSurfaceBlock(candidate):
                if candidate not in self.surfaceBlocks:
                    self.surfaceBlocks.add(candidate)
                    chunk = tuple(value // self.chunkStorage.chunk_size for value in candidate)
                    self.surfaceChunks.setdefault(chunk, set()).add(candidate)
            else:
                if candidate in self.surfaceBlocks:
                    self.surfaceBlocks.discard(candidate)
                    chunk = tuple(value // self.chunkStorage.chunk_size for value in candidate)
                    cells = self.surfaceChunks.get(chunk)
                    if cells is not None:
                        cells.discard(candidate)
                        if not cells:
                            self.surfaceChunks.pop(chunk, None)

    def _rebuildSurfaceIndex(self) -> None:
        blocks = self.blocks
        self.surfaceBlocks = {
            pos for pos in blocks
            if any(neighbor not in blocks for neighbor in self._neighborPositions(pos))
        }
        self.surfaceChunks.clear()
        size = self.chunkStorage.chunk_size
        for pos in self.surfaceBlocks:
            chunk = tuple(value // size for value in pos)
            self.surfaceChunks.setdefault(chunk, set()).add(pos)

    def replace(self, snapshot) -> None:
        """Atomically replace live state from a validated immutable snapshot."""
        BlockType = self.catalog.block_type
        width = int(snapshot.width)
        depth = int(snapshot.depth)
        height = int(snapshot.height)
        min_y = int(snapshot.min_y)
        max_y = min_y + height
        blocks = snapshot.blocks if isinstance(snapshot.blocks, dict) else dict(snapshot.blocks)

        chunkStorage = ChunkStorage(self.chunkStorage.chunk_size)
        size = chunkStorage.chunk_size
        chunks = defaultdict(dict)
        columnLevels = defaultdict(set)
        typePositions = defaultdict(set)
        axisCounts = ({}, {}, {})
        xCounts, yCounts, zCounts = axisCounts
        for (x, y, z), blockType in blocks.items():
            chunk = (x // size, y // size, z // size)
            local = (x % size, y % size, z % size)
            chunks[chunk][local] = blockType
            columnLevels[(x, y)].add(z)
            typePositions[blockType].add((x, y, z))
            xCounts[x] = xCounts.get(x, 0) + 1
            yCounts[y] = yCounts.get(y, 0) + 1
            zCounts[z] = zCounts.get(z, 0) + 1

        chunkStorage.chunks = dict(chunks)
        columnLevels = dict(columnLevels)
        typePositions = dict(typePositions)

        surfaceBlocks = (
            snapshot.surface_positions
            if isinstance(snapshot.surface_positions, set)
            else set(snapshot.surface_positions)
        )
        if not surfaceBlocks and blocks:
            surfaceBlocks = {
                pos for pos in blocks
                if any(neighbor not in blocks for neighbor in self._neighborPositions(pos))
            }
        surfaceChunks = defaultdict(set)
        for pos in surfaceBlocks:
            chunk = (pos[0] // size, pos[1] // size, pos[2] // size)
            surfaceChunks[chunk].add(pos)
        surfaceChunks = dict(surfaceChunks)

        structurePositions = (
            snapshot.structure_positions
            if isinstance(snapshot.structure_positions, set)
            else set(snapshot.structure_positions)
        )
        suppliedSurfaces = snapshot.structure_surfaces_by_view
        if all(rotation in suppliedSurfaces for rotation in range(4)):
            structureSurfacesByView = {
                rotation: (
                    suppliedSurfaces[rotation]
                    if isinstance(suppliedSurfaces[rotation], set)
                    else set(suppliedSurfaces[rotation])
                )
                for rotation in range(4)
            }
        else:
            sideDirections = (
                ((0, 1), (1, 0)),
                ((1, 0), (0, -1)),
                ((0, -1), (-1, 0)),
                ((-1, 0), (0, 1)),
            )
            exteriorShell = snapshot.scene_metadata.get("exterior_shell_view") == "glass"
            structureSurfacesByView = {rotation: set() for rotation in range(4)}
            if exteriorShell:
                visible = {
                    position for position in structurePositions
                    if any(
                        neighbor not in structurePositions
                        for neighbor in self._neighborPositions(position)
                    )
                }
                structureSurfacesByView = {rotation: visible for rotation in range(4)}
            else:
                for x, y, z in structurePositions:
                    position = (x, y, z)
                    definition = self.catalog.definitions.get(blocks[position])
                    opaqueCube = bool(
                        definition
                        and not getattr(definition, "transparent", False)
                        and not getattr(definition, "isLiquid", False)
                        and not getattr(definition, "isThin", False)
                        and not getattr(definition, "isSlab", False)
                        and not getattr(definition, "isStair", False)
                        and not getattr(definition, "isPortal", False)
                        and not getattr(definition, "modelKind", None)
                    )
                    if not opaqueCube:
                        for visible in structureSurfacesByView.values():
                            visible.add(position)
                        continue
                    for rotation, directions in enumerate(sideDirections):
                        neighbors = ((x, y, z + 1),) + tuple(
                            (x + dx, y + dy, z) for dx, dy in directions
                        )
                        if any(neighbor not in structurePositions for neighbor in neighbors):
                            structureSurfacesByView[rotation].add(position)
        self.width = width
        self.depth = depth
        self.height = height
        self.min_y = min_y
        self.max_y_exclusive = max_y
        self.dimension = snapshot.dimension
        self.blocks = blocks
        self.chunkStorage = chunkStorage
        self._columnLevels = columnLevels
        self.heightIndex = {
            column: max(levels) for column, levels in columnLevels.items()
        }
        self.blockTypePositions = typePositions
        self.blockTypeCounts = {
            blockType: len(positions)
            for blockType, positions in typePositions.items()
        }
        self._axisCounts = axisCounts
        self.occupiedBounds = (
            tuple(min(counts) for counts in axisCounts),
            tuple(max(counts) for counts in axisCounts),
        ) if blocks else None
        self.surfaceBlocks = surfaceBlocks
        self.surfaceChunks = surfaceChunks
        self.sceneStructurePositions = structurePositions
        self.sceneStructureBounds = (
            tuple(min(position[axis] for position in structurePositions) for axis in range(3)),
            tuple(max(position[axis] for position in structurePositions) for axis in range(3)),
        ) if structurePositions else None
        self.sceneStructureChunks = {}
        self.sceneStructureSurfacesByView = structureSurfacesByView
        self.sceneStructureSurfaceChunksByView = {rotation: {} for rotation in range(4)}
        self._sceneStructureOverviewPositions = None
        self.blockProperties = dict(snapshot.properties)
        self.liquidLevels = dict(snapshot.liquid_levels)
        self.liquidSources = set(snapshot.liquid_sources) & blocks.keys()
        self.liquidFalling = set(snapshot.liquid_falling) & blocks.keys()
        self.waterUpdateQueue.clear()
        self.lavaUpdateQueue.clear()
        self._waterQueued.clear()
        self._lavaQueued.clear()
        self._bulkDepth = 0
        self._bulkChanged = False
        self.revision += 1
        self.dirtyRegions.request_full_redraw()

    @contextmanager
    def bulkUpdate(self):
        """Coalesce revision and redraw work for scene imports/generation."""
        self._bulkDepth += 1
        try:
            yield self
        finally:
            self._bulkDepth -= 1
            if self._bulkDepth == 0 and self._bulkChanged:
                self._bulkChanged = False
                self._rebuildSurfaceIndex()
                self.revision += 1
                self.dirtyRegions.request_full_redraw()
    
    def getLiquidLevel(self, x: int, y: int, z: int) -> int:
        """Get the liquid level at a position (0 = no liquid, 8 = source)"""
        return self.liquidLevels.get((x, y, z), 0)
    
    def setBlock(self, x: int, y: int, z: int, blockType: 'BlockType') -> bool:
        """Set a block and schedule any affected fluid cells."""
        BlockType = self.catalog.block_type
        if not self.isInBounds(x, y, z):
            return False
        pos = (x, y, z)
        oldBlock = self.blocks.get(pos, BlockType.AIR)
        if blockType == BlockType.AIR:
            self._storeBlock(pos, BlockType.AIR)
            self.blockProperties.pop(pos, None)
            self._clearLiquidState(pos)
            self._queueNeighborUpdates(x, y, z)
            self._queueLiquidAbove(x, y, z)
        else:
            self._storeBlock(pos, blockType)
            self.blockProperties.pop(pos, None)
            self._clearLiquidState(pos)
            if blockType in (BlockType.WATER, BlockType.LAVA):
                self.liquidLevels[pos] = 8
                self.liquidSources.add(pos)
                self._enqueueLiquid(pos, blockType)
                self._queueNeighborUpdates(x, y, z)
            elif oldBlock in (BlockType.WATER, BlockType.LAVA):
                self._queueNeighborUpdates(x, y, z)
        return True

    def _queueFor(self, liquidType: 'BlockType'):
        BlockType = self.catalog.block_type
        if liquidType == BlockType.WATER:
            return self.waterUpdateQueue, self._waterQueued
        return self.lavaUpdateQueue, self._lavaQueued

    def _enqueueLiquid(self, pos: Tuple[int, int, int], liquidType: 'BlockType', front: bool = False) -> None:
        if not self.isInBounds(*pos):
            return
        queue, queued = self._queueFor(liquidType)
        if pos in queued:
            return
        queued.add(pos)
        if front:
            queue.appendleft(pos)
        else:
            queue.append(pos)

    def _clearLiquidState(self, pos: Tuple[int, int, int]) -> None:
        self.liquidLevels.pop(pos, None)
        self.liquidSources.discard(pos)
        self.liquidFalling.discard(pos)

    def _setFlowingLiquid(
        self,
        pos: Tuple[int, int, int],
        liquidType: 'BlockType',
        level: int,
        falling: bool,
    ) -> bool:
        BlockType = self.catalog.block_type
        if not self.isInBounds(*pos) or level <= 0:
            return False
        oldBlock = self.blocks.get(pos, BlockType.AIR)
        oldLevel = self.liquidLevels.get(pos, 0)
        oldFalling = pos in self.liquidFalling
        if oldBlock not in (BlockType.AIR, liquidType):
            return False
        if oldBlock == liquidType and oldLevel > level:
            return False
        self._storeBlock(pos, liquidType)
        self.liquidLevels[pos] = max(1, min(8, level))
        self.liquidSources.discard(pos)
        if falling:
            self.liquidFalling.add(pos)
        else:
            self.liquidFalling.discard(pos)
        changed = oldBlock != liquidType or oldLevel != level or oldFalling != falling
        if changed:
            self._enqueueLiquid(pos, liquidType)
        return changed
    
    def _queueNeighborUpdates(self, x: int, y: int, z: int):
        """Queue neighboring liquid blocks for update"""
        BlockType = self.catalog.block_type
        neighbors = [
            (x + 1, y, z), (x - 1, y, z),
            (x, y + 1, z), (x, y - 1, z),
            (x, y, z + 1), (x, y, z - 1),
        ]
        for nx, ny, nz in neighbors:
            block = self.getBlock(nx, ny, nz)
            if block == BlockType.WATER:
                self._enqueueLiquid((nx, ny, nz), block)
            elif block == BlockType.LAVA:
                self._enqueueLiquid((nx, ny, nz), block)
    
    def _queueLiquidAbove(self, x: int, y: int, z: int):
        """Queue liquid blocks above and adjacent for update when solid block is removed"""
        BlockType = self.catalog.block_type
        # Check block directly above
        if z + 1 < self.max_y_exclusive:
            blockAbove = self.getBlock(x, y, z + 1)
            if blockAbove == BlockType.WATER:
                self._enqueueLiquid((x, y, z + 1), blockAbove, front=True)
            elif blockAbove == BlockType.LAVA:
                self._enqueueLiquid((x, y, z + 1), blockAbove, front=True)
        
        # Also check horizontal neighbors at same level
        for nx, ny in [(x+1, y), (x-1, y), (x, y+1), (x, y-1)]:
            if self.isInBounds(nx, ny, z):
                block = self.getBlock(nx, ny, z)
                if block == BlockType.WATER:
                    self._enqueueLiquid((nx, ny, z), block)
                elif block == BlockType.LAVA:
                    self._enqueueLiquid((nx, ny, z), block)
    
    def _legacyUpdateLiquids(self, liquidType: 'BlockType' = None, maxUpdates: int = 8) -> List[Tuple[int, int, int, 'BlockType', int]]:
        """
        Process liquid flow updates for a specific type (water or lava).
        Returns list of (x, y, z, blockType, level) for changed blocks.
        """
        BlockType = self.catalog.block_type
        # Select the appropriate queue
        if liquidType == BlockType.WATER:
            queue = self.waterUpdateQueue
        elif liquidType == BlockType.LAVA:
            queue = self.lavaUpdateQueue
        else:
            return []
        
        if not queue:
            return []
        
        changes = []
        processed = set()
        
        # Chunk-based optimization
        CHUNK_SIZE = 4
        chunkUpdates = {}
        
        for pos in queue:
            x, y, z = pos
            chunkKey = (x // CHUNK_SIZE, y // CHUNK_SIZE)
            if chunkKey not in chunkUpdates:
                chunkUpdates[chunkKey] = []
            chunkUpdates[chunkKey].append(pos)
        
        updatesThisTick = 0
        maxUpdatesPerChunk = max(2, maxUpdates // max(1, len(chunkUpdates)))
        sortedChunks = sorted(chunkUpdates.items(), key=lambda x: len(x[1]), reverse=True)
        
        for chunkKey, chunkPositions in sortedChunks:
            if updatesThisTick >= maxUpdates:
                break
            
            chunkProcessed = 0
            for pos in chunkPositions:
                if chunkProcessed >= maxUpdatesPerChunk or updatesThisTick >= maxUpdates:
                    break
                    
                if pos in processed:
                    if pos in queue:
                        queue.remove(pos)
                    continue
                    
                processed.add(pos)
                if pos in queue:
                    queue.remove(pos)
                
                x, y, z = pos
                block = self.getBlock(x, y, z)
                level = self.getLiquidLevel(x, y, z)
                
                if block != liquidType or level <= 0:
                    chunkProcessed += 1
                    updatesThisTick += 1
                    continue
                
                # PRIORITY 1: Flow down first
                if z > self.min_y and self.getBlock(x, y, z-1) == BlockType.AIR:
                    self._storeBlock((x, y, z - 1), block)
                    self.liquidLevels[(x, y, z-1)] = 8
                    changes.append((x, y, z-1, block, 8))
                    queue.append((x, y, z-1))
                    chunkProcessed += 1
                    updatesThisTick += 1
                    continue
                
                # PRIORITY 2: Horizontal spread with pathfinding
                if level > 1:
                    newLevel = level - 1
                    searchRadius = 5 if block == BlockType.WATER else 3
                    holeDirections = self._findHoleDirections(x, y, z, block, searchRadius)
                    allDirections = [(1, 0), (-1, 0), (0, 1), (0, -1)]
                    flowDirections = holeDirections if holeDirections else allDirections
                    
                    for dx, dy in flowDirections:
                        nx, ny, nz = x + dx, y + dy, z
                        
                        if not self.isInBounds(nx, ny, nz):
                            continue
                        
                        neighborBlock = self.getBlock(nx, ny, nz)
                        neighborLevel = self.getLiquidLevel(nx, ny, nz)
                        
                        if neighborBlock == BlockType.AIR:
                            self._storeBlock((nx, ny, nz), block)
                            self.liquidLevels[(nx, ny, nz)] = newLevel
                            changes.append((nx, ny, nz, block, newLevel))
                            if newLevel > 1:
                                queue.append((nx, ny, nz))
                            if nz > self.min_y and self.getBlock(nx, ny, nz - 1) == BlockType.AIR:
                                queue.insert(0, (nx, ny, nz))
                        elif neighborBlock == block and neighborLevel < newLevel:
                            self.liquidLevels[(nx, ny, nz)] = newLevel
                            changes.append((nx, ny, nz, block, newLevel))
                            queue.append((nx, ny, nz))
                
                chunkProcessed += 1
                updatesThisTick += 1
        
        return changes
    
    def _legacyFindHoleDirections(self, startX: int, startY: int, z: int,
                            liquidType: 'BlockType', maxRange: int) -> List[Tuple[int, int]]:
        """Use BFS to find directions leading to holes within range."""
        BlockType = self.catalog.block_type
        directionHoles = {}
        visited = {(startX, startY)}
        bfsQueue = deque()
        
        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            nx, ny = startX + dx, startY + dy
            if not self.isInBounds(nx, ny, z):
                continue
            
            neighborBlock = self.getBlock(nx, ny, z)
            if neighborBlock != BlockType.AIR and neighborBlock != liquidType:
                continue
            
            visited.add((nx, ny))
            
            if z > self.min_y and self.getBlock(nx, ny, z - 1) == BlockType.AIR:
                directionHoles[(dx, dy)] = 1
            
            bfsQueue.append((nx, ny, dx, dy, 1))
        
        while bfsQueue:
            cx, cy, initDx, initDy, dist = bfsQueue.popleft()
            
            if dist >= maxRange:
                continue
            
            for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                nx, ny = cx + dx, cy + dy
                
                if (nx, ny) in visited:
                    continue
                
                if not self.isInBounds(nx, ny, z):
                    continue
                
                neighborBlock = self.getBlock(nx, ny, z)
                if neighborBlock != BlockType.AIR and neighborBlock != liquidType:
                    continue
                
                visited.add((nx, ny))
                newDist = dist + 1
                
                if z > self.min_y and self.getBlock(nx, ny, z - 1) == BlockType.AIR:
                    if (initDx, initDy) not in directionHoles:
                        directionHoles[(initDx, initDy)] = newDist
                
                bfsQueue.append((nx, ny, initDx, initDy, newDist))
        
        if not directionHoles:
            return []
        
        minDist = min(directionHoles.values())
        goodDirections = [(d, dist) for d, dist in directionHoles.items() if dist <= minDist + 2]
        goodDirections.sort(key=lambda x: x[1])
        
        return [d for d, _ in goodDirections]

    def updateLiquids(self, liquidType: 'BlockType' = None, maxUpdates: int = 32) -> List[Tuple[int, int, int, 'BlockType', int]]:
        """Process a deduplicated batch of source-style scheduled fluid updates."""
        BlockType = self.catalog.block_type
        if liquidType not in (BlockType.WATER, BlockType.LAVA):
            return []
        queue, queued = self._queueFor(liquidType)
        changes: List[Tuple[int, int, int, 'BlockType', int]] = []
        updatesThisTick = 0

        while queue and updatesThisTick < maxUpdates:
            pos = queue.popleft()
            queued.discard(pos)
            updatesThisTick += 1
            if self.getBlock(*pos) != liquidType:
                continue

            reaction = self._reactLavaWithWater(pos)
            if reaction is not None:
                changes.append(reaction)
                continue

            stabilized = self._stabilizeLiquid(pos, liquidType)
            if stabilized is not None:
                changes.append(stabilized)
            if self.getBlock(*pos) != liquidType:
                continue

            x, y, z = pos
            level = self.getLiquidLevel(x, y, z)
            falling = pos in self.liquidFalling
            flowedDown = False
            if z > self.min_y:
                below = (x, y, z - 1)
                belowBlock = self.getBlock(*below)
                if liquidType == BlockType.LAVA and belowBlock == BlockType.WATER:
                    self._replaceLiquidWithSolid(below, BlockType.STONE)
                    changes.append((*below, BlockType.STONE, 0))
                    flowedDown = True
                elif belowBlock in (BlockType.AIR, liquidType):
                    if self._setFlowingLiquid(below, liquidType, 8, True):
                        changes.append((*below, liquidType, 8))
                        self._queueNeighborUpdates(*below)
                    flowedDown = True

            # Vanilla only spreads sideways while falling when surrounded by
            # at least three still neighbors.
            if flowedDown and self._sourceNeighborCount(pos, liquidType) < 3:
                continue

            spreadLevel = 7 if falling else level - self._levelDecrease(liquidType)
            if spreadLevel <= 0:
                continue
            for dx, dy in self._bestSpreadDirections(pos, liquidType):
                target = (x + dx, y + dy, z)
                if self._setFlowingLiquid(target, liquidType, spreadLevel, False):
                    changes.append((*target, liquidType, spreadLevel))
                    self._queueNeighborUpdates(*target)

        return changes

    def _sourceNeighborCount(self, pos: Tuple[int, int, int], liquidType: 'BlockType') -> int:
        x, y, z = pos
        return sum(
            (x + dx, y + dy, z) in self.liquidSources
            and self.getBlock(x + dx, y + dy, z) == liquidType
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
        )

    def _levelDecrease(self, liquidType: 'BlockType') -> int:
        BlockType = self.catalog.block_type
        if liquidType == BlockType.WATER:
            return 1
        return 1 if self.dimension == "nether" else 2

    def _flowSearchDepth(self, liquidType: 'BlockType') -> int:
        BlockType = self.catalog.block_type
        if liquidType == BlockType.WATER or self.dimension == "nether":
            return 4
        return 2

    def _stabilizeLiquid(self, pos: Tuple[int, int, int], liquidType: 'BlockType'):
        BlockType = self.catalog.block_type
        if pos in self.liquidSources:
            self.liquidLevels[pos] = 8
            self.liquidFalling.discard(pos)
            return None

        x, y, z = pos
        above = (x, y, z + 1)
        if z + 1 < self.max_y_exclusive and self.getBlock(*above) == liquidType:
            desiredLevel, falling = 8, True
        else:
            neighborLevels = []
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                neighbor = (x + dx, y + dy, z)
                if self.getBlock(*neighbor) == liquidType:
                    neighborLevels.append(self.getLiquidLevel(*neighbor))

            if liquidType == BlockType.WATER and self._sourceNeighborCount(pos, liquidType) >= 2:
                below = self.getBlock(x, y, z - 1) if z > self.min_y else BlockType.AIR
                if below not in (BlockType.AIR, BlockType.LAVA):
                    self.liquidSources.add(pos)
                    self.liquidLevels[pos] = 8
                    self.liquidFalling.discard(pos)
                    return (*pos, liquidType, 8)

            desiredLevel = (max(neighborLevels) if neighborLevels else 0) - self._levelDecrease(liquidType)
            falling = False

        if desiredLevel <= 0:
            self._storeBlock(pos, BlockType.AIR)
            self._clearLiquidState(pos)
            self._queueNeighborUpdates(*pos)
            return (*pos, BlockType.AIR, 0)

        oldLevel = self.liquidLevels.get(pos, 0)
        oldFalling = pos in self.liquidFalling
        self.liquidLevels[pos] = desiredLevel
        if falling:
            self.liquidFalling.add(pos)
        else:
            self.liquidFalling.discard(pos)
        if oldLevel != desiredLevel or oldFalling != falling:
            self._queueNeighborUpdates(*pos)
            return (*pos, liquidType, desiredLevel)
        return None

    def _canFlowHorizontally(self, pos: Tuple[int, int, int], liquidType: 'BlockType') -> bool:
        BlockType = self.catalog.block_type
        block = self.getBlock(*pos)
        return block == BlockType.AIR or (block == liquidType and pos not in self.liquidSources)

    def _dropDistance(
        self,
        start: Tuple[int, int, int],
        liquidType: 'BlockType',
        blockedDirection: Tuple[int, int],
    ) -> int:
        BlockType = self.catalog.block_type
        maxDepth = self._flowSearchDepth(liquidType)
        queue = deque([(start[0], start[1], 1)])
        visited = {(start[0], start[1])}
        while queue:
            x, y, distance = queue.popleft()
            if start[2] > 0 and self.getBlock(x, y, start[2] - 1) == BlockType.AIR:
                return distance
            if distance >= maxDepth:
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                if distance == 1 and (dx, dy) == blockedDirection:
                    continue
                target = (x + dx, y + dy, start[2])
                key = (target[0], target[1])
                if key in visited or not self.isInBounds(*target):
                    continue
                if not self._canFlowHorizontally(target, liquidType):
                    continue
                visited.add(key)
                queue.append((target[0], target[1], distance + 1))
        return 1000

    def _bestSpreadDirections(self, pos: Tuple[int, int, int], liquidType: 'BlockType') -> List[Tuple[int, int]]:
        BlockType = self.catalog.block_type
        x, y, z = pos
        candidates = []
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            target = (x + dx, y + dy, z)
            if not self.isInBounds(*target) or not self._canFlowHorizontally(target, liquidType):
                continue
            distance = (
                0
                if z > self.min_y and self.getBlock(target[0], target[1], z - 1) == BlockType.AIR
                else self._dropDistance(target, liquidType, (-dx, -dy))
            )
            candidates.append((distance, dx, dy))
        if not candidates:
            return []
        best = min(item[0] for item in candidates)
        return [(dx, dy) for distance, dx, dy in candidates if distance == best]

    def _replaceLiquidWithSolid(self, pos: Tuple[int, int, int], blockType: 'BlockType') -> None:
        self._storeBlock(pos, blockType)
        self._clearLiquidState(pos)
        self._queueNeighborUpdates(*pos)

    def _reactLavaWithWater(self, pos: Tuple[int, int, int]):
        BlockType = self.catalog.block_type
        if self.getBlock(*pos) != BlockType.LAVA:
            return None
        x, y, z = pos
        neighbors = (
            (x + 1, y, z), (x - 1, y, z),
            (x, y + 1, z), (x, y - 1, z),
            (x, y, z + 1),
        )
        if any(
            self.isInBounds(*neighbor) and self.getBlock(*neighbor) == BlockType.WATER
            for neighbor in neighbors
        ):
            result = BlockType.OBSIDIAN if pos in self.liquidSources else BlockType.COBBLESTONE
            self._replaceLiquidWithSolid(pos, result)
            return (*pos, result, 0)
        return None

    def _findHoleDirections(self, startX: int, startY: int, z: int,
                            liquidType: 'BlockType', maxRange: int) -> List[Tuple[int, int]]:
        """Compatibility wrapper around the source-style slope search."""
        return self._bestSpreadDirections((startX, startY, z), liquidType)
    
    def isInBounds(self, x: int, y: int, z: int) -> bool:
        """Check if coordinates are within world bounds"""
        return (
            0 <= x < self.width
            and 0 <= y < self.depth
            and self.min_y <= z < self.max_y_exclusive
        )

    def iterBlocks(self):
        """Iterate all blocks without materializing a compatibility dictionary."""
        return self.chunkStorage.iter_blocks()

    def iterSurfaceBlocks(self):
        """Iterate conservative visible candidates for large-world rendering."""
        for pos in self.surfaceBlocks:
            block = self.blocks.get(pos)
            if block is not None:
                yield pos, block

    def iterSurfaceChunks(self):
        """Iterate chunk keys and their conservative surface positions."""
        return self.surfaceChunks.items()

    def iterSurfaceChunksInHorizontalRadius(self, centerX: int, centerY: int, chunkRadius: int):
        """Iterate surface chunks by direct key lookup in a horizontal square."""
        size = self.chunkStorage.chunk_size
        centerChunkX = centerX // size
        centerChunkY = centerY // size
        radius = max(0, int(chunkRadius))
        if self.occupiedBounds is None:
            return
        minChunkZ = self.occupiedBounds[0][2] // size
        maxChunkZ = self.occupiedBounds[1][2] // size
        for chunkX in range(centerChunkX - radius, centerChunkX + radius + 1):
            for chunkY in range(centerChunkY - radius, centerChunkY + radius + 1):
                for chunkZ in range(minChunkZ, maxChunkZ + 1):
                    key = (chunkX, chunkY, chunkZ)
                    positions = self.surfaceChunks.get(key)
                    if positions:
                        yield key, positions

    def iterStructurePositionsInChunkRadius(self, centerX: int, centerY: int, chunkRadius: int):
        """Iterate structure-role positions by direct chunk lookup."""
        size = self.chunkStorage.chunk_size
        if not self.sceneStructureChunks and self.sceneStructurePositions:
            for pos in self.sceneStructurePositions:
                chunk = tuple(value // size for value in pos)
                self.sceneStructureChunks.setdefault(chunk, set()).add(pos)
        centerChunkX = centerX // size
        centerChunkY = centerY // size
        radius = max(0, int(chunkRadius))
        if self.occupiedBounds is None:
            return
        minChunkZ = self.occupiedBounds[0][2] // size
        maxChunkZ = self.occupiedBounds[1][2] // size
        for chunkX in range(centerChunkX - radius, centerChunkX + radius + 1):
            for chunkY in range(centerChunkY - radius, centerChunkY + radius + 1):
                for chunkZ in range(minChunkZ, maxChunkZ + 1):
                    yield from self.sceneStructureChunks.get((chunkX, chunkY, chunkZ), ())

    def structureSurfacePositions(self, viewRotation: int):
        """Return precomputed structure cells visible from one view."""
        return self.sceneStructureSurfacesByView[viewRotation % 4]

    def structureOverviewPositions(self):
        """Return the top structure cell per column for subpixel overview LOD."""
        if self._sceneStructureOverviewPositions is None:
            columns = {}
            for x, y, z in self.sceneStructurePositions:
                key = (x, y)
                if z > columns.get(key, self.min_y - 1):
                    columns[key] = z
            self._sceneStructureOverviewPositions = {
                (x, y, z) for (x, y), z in columns.items()
            }
        return self._sceneStructureOverviewPositions

    def prepareStructureSurfaceChunks(self, viewRotation: int) -> None:
        """Build one rotation's chunk lookup before latency-sensitive rendering."""
        rotation = viewRotation % 4
        chunks = self.sceneStructureSurfaceChunksByView[rotation]
        if chunks or not self.sceneStructureSurfacesByView[rotation]:
            return
        size = self.chunkStorage.chunk_size
        for pos in self.sceneStructureSurfacesByView[rotation]:
            chunk = (pos[0] // size, pos[1] // size, pos[2] // size)
            chunks.setdefault(chunk, set()).add(pos)

    def iterStructureSurfaceChunksInHorizontalRadius(
        self, viewRotation: int, centerX: int, centerY: int, chunkRadius: int
    ):
        """Iterate precomputed view-facing structure surfaces by direct lookup."""
        size = self.chunkStorage.chunk_size
        centerChunkX = centerX // size
        centerChunkY = centerY // size
        radius = max(0, int(chunkRadius))
        if self.occupiedBounds is None:
            return
        chunks = self.sceneStructureSurfaceChunksByView[viewRotation % 4]
        self.prepareStructureSurfaceChunks(viewRotation)
        minChunkZ = self.occupiedBounds[0][2] // size
        maxChunkZ = self.occupiedBounds[1][2] // size
        for chunkX in range(centerChunkX - radius, centerChunkX + radius + 1):
            for chunkY in range(centerChunkY - radius, centerChunkY + radius + 1):
                for chunkZ in range(minChunkZ, maxChunkZ + 1):
                    key = (chunkX, chunkY, chunkZ)
                    positions = chunks.get(key)
                    if positions:
                        yield key, positions

    def iterBlocksInChunkRadius(self, centerX: int, centerY: int, chunkRadius: int):
        """Iterate blocks inside the horizontal render distance."""
        return self.chunkStorage.iter_horizontal_radius(centerX, centerY, chunkRadius)

    def resize(self, width: int, depth: int, height: int, *, min_y: int = 0,
               preserve: bool = True) -> None:
        """Change world bounds while preserving in-range state when requested."""
        oldBlocks = dict(self.blocks) if preserve else {}
        oldProperties = dict(self.blockProperties) if preserve else {}
        oldLiquidLevels = dict(self.liquidLevels) if preserve else {}
        oldLiquidSources = set(self.liquidSources) if preserve else set()
        oldLiquidFalling = set(self.liquidFalling) if preserve else set()
        self.clear()
        self.width = max(1, int(width))
        self.depth = max(1, int(depth))
        self.height = max(1, int(height))
        self.min_y = int(min_y)
        self.max_y_exclusive = self.min_y + self.height
        for pos, blockType in oldBlocks.items():
            if self.isInBounds(*pos):
                self._storeBlock(pos, blockType)
                if pos in oldProperties:
                    self.blockProperties[pos] = oldProperties[pos]
                if pos in oldLiquidLevels:
                    self.liquidLevels[pos] = oldLiquidLevels[pos]
                if pos in oldLiquidSources:
                    self.liquidSources.add(pos)
                if pos in oldLiquidFalling:
                    self.liquidFalling.add(pos)
        self.dirtyRegions.request_full_redraw()
    
    def clear(self):
        """Clear all blocks from the world"""
        self.blocks.clear()
        self.chunkStorage.clear()
        self._columnLevels.clear()
        self.heightIndex.clear()
        self.blockTypePositions.clear()
        self.blockTypeCounts.clear()
        for counts in self._axisCounts:
            counts.clear()
        self.occupiedBounds = None
        self.surfaceBlocks.clear()
        self.surfaceChunks.clear()
        self.sceneStructurePositions.clear()
        self.sceneStructureBounds = None
        self.sceneStructureChunks.clear()
        for positions in self.sceneStructureSurfacesByView.values():
            positions.clear()
        for chunks in self.sceneStructureSurfaceChunksByView.values():
            chunks.clear()
        self._sceneStructureOverviewPositions = None
        self.blockProperties.clear()
        self.liquidLevels.clear()
        self.liquidSources.clear()
        self.liquidFalling.clear()
        self.waterUpdateQueue.clear()
        self.lavaUpdateQueue.clear()
        self._waterQueued.clear()
        self._lavaQueued.clear()
        self.revision += 1
        self.dirtyRegions.request_full_redraw()
    
    def clearLiquids(self) -> int:
        """Clear all water and lava blocks. Returns count of removed blocks."""
        BlockType = self.catalog.block_type
        removed = 0
        toRemove = []
        for pos, blockType in self.blocks.items():
            if blockType == BlockType.WATER or blockType == BlockType.LAVA:
                toRemove.append(pos)
        
        for pos in toRemove:
            self._storeBlock(pos, BlockType.AIR)
            self._clearLiquidState(pos)
            removed += 1
        
        self.waterUpdateQueue.clear()
        self.lavaUpdateQueue.clear()
        self._waterQueued.clear()
        self._lavaQueued.clear()
        
        return removed
    
    def hasBlockType(self, blockType: 'BlockType') -> bool:
        """Check if the world contains any blocks of the specified type"""
        return bool(self.blockTypeCounts.get(blockType))

    def positionsOfType(self, blockType: 'BlockType') -> Set[Tuple[int, int, int]]:
        """Return a defensive copy of positions occupied by one block type."""
        return set(self.blockTypePositions.get(blockType, ()))
    
    def getHighestBlock(self, x: int, y: int) -> int:
        """Get the height of the highest block at (x, y)"""
        return self.heightIndex.get((x, y), self.min_y - 1)
    
    def calculateLighting(self) -> Dict[Tuple[int, int, int], Tuple[int, Tuple[int, int, int]]]:
        """
        Calculate light levels and colors for all positions.
        Returns dict of (x, y, z) -> (light level, light color RGB).
        """
        BlockType = self.catalog.block_type
        BLOCK_DEFINITIONS = self.catalog.definitions
        lightMap = {}
        
        lightSources = []
        for (x, y, z), blockType in self.blocks.items():
            if BLOCK_DEFINITIONS is None:
                continue
            blockDef = BLOCK_DEFINITIONS.get(blockType)
            if blockDef and blockDef.lightLevel > 0:
                lightColor = getattr(blockDef, 'lightColor', (255, 200, 150))
                lightSources.append((x, y, z, blockDef.lightLevel, lightColor))
                lightMap[(x, y, z)] = (blockDef.lightLevel, lightColor)
        
        if not lightSources:
            return lightMap
        
        visited = {}
        queue = deque()
        
        for x, y, z, level, color in lightSources:
            visited[(x, y, z)] = level
            if level > 1:
                for dx, dy, dz in [(1,0,0), (-1,0,0), (0,1,0), (0,-1,0), (0,0,1), (0,0,-1)]:
                    nx, ny, nz = x + dx, y + dy, z + dz
                    if self.isInBounds(nx, ny, nz):
                        queue.append((nx, ny, nz, level - 1, color))
        
        while queue:
            x, y, z, level, color = queue.popleft()
            
            if level <= 0:
                continue
            
            if (x, y, z) in visited and visited[(x, y, z)] >= level:
                continue
            
            block = self.getBlock(x, y, z)
            if block != BlockType.AIR:
                if BLOCK_DEFINITIONS is not None:
                    blockDef = BLOCK_DEFINITIONS.get(block)
                    if blockDef and not blockDef.transparent and not blockDef.isLiquid:
                        continue
            
            visited[(x, y, z)] = level
            
            if (x, y, z) in lightMap:
                oldLevel, oldColor = lightMap[(x, y, z)]
                if level > oldLevel:
                    lightMap[(x, y, z)] = (level, color)
                elif level == oldLevel:
                    blendedColor = (
                        (oldColor[0] + color[0]) // 2,
                        (oldColor[1] + color[1]) // 2,
                        (oldColor[2] + color[2]) // 2
                    )
                    lightMap[(x, y, z)] = (level, blendedColor)
            else:
                lightMap[(x, y, z)] = (level, color)
            
            if level > 1:
                newLevel = level - 1
                for dx, dy, dz in [(1,0,0), (-1,0,0), (0,1,0), (0,-1,0), (0,0,1), (0,0,-1)]:
                    nx, ny, nz = x + dx, y + dy, z + dz
                    if self.isInBounds(nx, ny, nz):
                        if (nx, ny, nz) not in visited or visited[(nx, ny, nz)] < newLevel:
                            queue.append((nx, ny, nz, newLevel, color))
        
        return lightMap
    
    def calculateAmbientOcclusion(self, x: int, y: int, z: int) -> Tuple[float, float, float]:
        """
        Calculate ambient occlusion factors for a block's 3 visible faces.
        Returns (topAO, leftAO, rightAO) where each is 0.0 (dark) to 1.0 (bright).
        """
        BlockType = self.catalog.block_type
        topAO = 1.0
        leftAO = 1.0
        rightAO = 1.0
        
        # Top face
        aboveBlocks = 0
        for dx, dy in [(1,0), (-1,0), (0,1), (0,-1), (1,1), (-1,1), (1,-1), (-1,-1)]:
            if self.getBlock(x + dx, y + dy, z + 1) != BlockType.AIR:
                aboveBlocks += 1
        topAO = max(0.5, 1.0 - aboveBlocks * 0.06)
        
        # Left face
        leftBlocks = 0
        for dy, dz in [(1,0), (-1,0), (0,1), (0,-1), (1,1), (-1,1), (1,-1), (-1,-1)]:
            if self.getBlock(x - 1, y + dy, z + dz) != BlockType.AIR:
                leftBlocks += 1
        leftAO = max(0.4, 1.0 - leftBlocks * 0.075)
        
        # Right face
        rightBlocks = 0
        for dx, dz in [(1,0), (-1,0), (0,1), (0,-1), (1,1), (-1,1), (1,-1), (-1,-1)]:
            if self.getBlock(x + dx, y + 1, z + dz) != BlockType.AIR:
                rightBlocks += 1
        rightAO = max(0.4, 1.0 - rightBlocks * 0.075)
        
        return (topAO, leftAO, rightAO)
    
    def placeStructure(self, structure: Dict, offsetX: int, offsetY: int, offsetZ: int):
        """Place a premade structure at an offset position."""
        for block in structure["blocks"]:
            x, y, z, blockType = block
            newX = x + offsetX
            newY = y + offsetY
            newZ = z + offsetZ
            
            if self.isInBounds(newX, newY, newZ):
                self.setBlock(newX, newY, newZ, blockType)
