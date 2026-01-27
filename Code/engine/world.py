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

from collections import deque
from typing import Dict, List, Tuple, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from blocFantome import BlockType, BlockProperties, BlockDefinition

# These will be imported from the main module at runtime
# to avoid circular imports
BlockType = None
BlockProperties = None
BLOCK_DEFINITIONS = None


def init_world_module(block_type, block_properties, block_definitions):
    """Initialize module-level references to avoid circular imports."""
    global BlockType, BlockProperties, BLOCK_DEFINITIONS
    BlockType = block_type
    BlockProperties = block_properties
    BLOCK_DEFINITIONS = block_definitions


class World:
    """
    Manages the 3D voxel grid for the building area.
    
    Uses a dictionary-based sparse storage for efficient memory usage,
    storing only non-air blocks.
    """
    
    def __init__(self, width: int, depth: int, height: int):
        """
        Initialize the world.
        
        Args:
            width: X dimension of the world
            depth: Y dimension of the world  
            height: Z dimension (vertical) of the world
        """
        self.width = width
        self.depth = depth
        self.height = height
        self.blocks: Dict[Tuple[int, int, int], 'BlockType'] = {}
        # Block properties for special blocks (doors, slabs, stairs)
        self.blockProperties: Dict[Tuple[int, int, int], 'BlockProperties'] = {}
        # Water/lava levels (1-8, where 8 = source)
        self.liquidLevels: Dict[Tuple[int, int, int], int] = {}
        # Separate queues for water and lava flow updates
        self.waterUpdateQueue: List[Tuple[int, int, int]] = []
        self.lavaUpdateQueue: List[Tuple[int, int, int]] = []
    
    def getBlock(self, x: int, y: int, z: int) -> 'BlockType':
        """Get the block type at a position"""
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
    
    def getLiquidLevel(self, x: int, y: int, z: int) -> int:
        """Get the liquid level at a position (0 = no liquid, 8 = source)"""
        return self.liquidLevels.get((x, y, z), 0)
    
    def setBlock(self, x: int, y: int, z: int, blockType: 'BlockType') -> bool:
        """
        Set a block at a position.
        
        Args:
            x, y, z: Position coordinates
            blockType: Type of block to place
            
        Returns:
            True if block was placed successfully
        """
        if not self.isInBounds(x, y, z):
            return False
        
        if blockType == BlockType.AIR:
            # Remove block
            if (x, y, z) in self.blocks:
                del self.blocks[(x, y, z)]
            # Also remove liquid level
            if (x, y, z) in self.liquidLevels:
                del self.liquidLevels[(x, y, z)]
                # Queue neighbors for update (liquid might flow in)
                self._queueNeighborUpdates(x, y, z)
            else:
                # Solid block removed - check if there's liquid above that should fall
                self._queueLiquidAbove(x, y, z)
            # Remove block properties
            if (x, y, z) in self.blockProperties:
                del self.blockProperties[(x, y, z)]
        else:
            # Place block
            self.blocks[(x, y, z)] = blockType
            # Set liquid level for water/lava
            if blockType == BlockType.WATER:
                self.liquidLevels[(x, y, z)] = 8  # Source block
                self.waterUpdateQueue.append((x, y, z))
            elif blockType == BlockType.LAVA:
                self.liquidLevels[(x, y, z)] = 8  # Source block
                self.lavaUpdateQueue.append((x, y, z))
        
        return True
    
    def _queueNeighborUpdates(self, x: int, y: int, z: int):
        """Queue neighboring liquid blocks for update"""
        neighbors = [(x+1, y, z), (x-1, y, z), (x, y+1, z), (x, y-1, z), (x, y, z+1)]
        for nx, ny, nz in neighbors:
            block = self.getBlock(nx, ny, nz)
            if block == BlockType.WATER:
                if (nx, ny, nz) not in self.waterUpdateQueue:
                    self.waterUpdateQueue.append((nx, ny, nz))
            elif block == BlockType.LAVA:
                if (nx, ny, nz) not in self.lavaUpdateQueue:
                    self.lavaUpdateQueue.append((nx, ny, nz))
    
    def _queueLiquidAbove(self, x: int, y: int, z: int):
        """Queue liquid blocks above and adjacent for update when solid block is removed"""
        # Check block directly above
        if z + 1 < self.height:
            blockAbove = self.getBlock(x, y, z + 1)
            if blockAbove == BlockType.WATER:
                if (x, y, z + 1) not in self.waterUpdateQueue:
                    self.waterUpdateQueue.insert(0, (x, y, z + 1))
            elif blockAbove == BlockType.LAVA:
                if (x, y, z + 1) not in self.lavaUpdateQueue:
                    self.lavaUpdateQueue.insert(0, (x, y, z + 1))
        
        # Also check horizontal neighbors at same level
        for nx, ny in [(x+1, y), (x-1, y), (x, y+1), (x, y-1)]:
            if self.isInBounds(nx, ny, z):
                block = self.getBlock(nx, ny, z)
                if block == BlockType.WATER:
                    if (nx, ny, z) not in self.waterUpdateQueue:
                        self.waterUpdateQueue.append((nx, ny, z))
                elif block == BlockType.LAVA:
                    if (nx, ny, z) not in self.lavaUpdateQueue:
                        self.lavaUpdateQueue.append((nx, ny, z))
    
    def updateLiquids(self, liquidType: 'BlockType' = None, maxUpdates: int = 8) -> List[Tuple[int, int, int, 'BlockType', int]]:
        """
        Process liquid flow updates for a specific type (water or lava).
        Returns list of (x, y, z, blockType, level) for changed blocks.
        """
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
                if z > 0 and self.getBlock(x, y, z-1) == BlockType.AIR:
                    self.blocks[(x, y, z-1)] = block
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
                            self.blocks[(nx, ny, nz)] = block
                            self.liquidLevels[(nx, ny, nz)] = newLevel
                            changes.append((nx, ny, nz, block, newLevel))
                            if newLevel > 1:
                                queue.append((nx, ny, nz))
                            if nz > 0 and self.getBlock(nx, ny, nz - 1) == BlockType.AIR:
                                queue.insert(0, (nx, ny, nz))
                        elif neighborBlock == block and neighborLevel < newLevel:
                            self.liquidLevels[(nx, ny, nz)] = newLevel
                            changes.append((nx, ny, nz, block, newLevel))
                            queue.append((nx, ny, nz))
                
                chunkProcessed += 1
                updatesThisTick += 1
        
        return changes
    
    def _findHoleDirections(self, startX: int, startY: int, z: int, 
                            liquidType: 'BlockType', maxRange: int) -> List[Tuple[int, int]]:
        """Use BFS to find directions leading to holes within range."""
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
            
            if z > 0 and self.getBlock(nx, ny, z - 1) == BlockType.AIR:
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
                
                if z > 0 and self.getBlock(nx, ny, z - 1) == BlockType.AIR:
                    if (initDx, initDy) not in directionHoles:
                        directionHoles[(initDx, initDy)] = newDist
                
                bfsQueue.append((nx, ny, initDx, initDy, newDist))
        
        if not directionHoles:
            return []
        
        minDist = min(directionHoles.values())
        goodDirections = [(d, dist) for d, dist in directionHoles.items() if dist <= minDist + 2]
        goodDirections.sort(key=lambda x: x[1])
        
        return [d for d, _ in goodDirections]
    
    def isInBounds(self, x: int, y: int, z: int) -> bool:
        """Check if coordinates are within world bounds"""
        return 0 <= x < self.width and 0 <= y < self.depth and 0 <= z < self.height
    
    def clear(self):
        """Clear all blocks from the world"""
        self.blocks.clear()
        self.blockProperties.clear()
        self.liquidLevels.clear()
        self.waterUpdateQueue.clear()
        self.lavaUpdateQueue.clear()
    
    def clearLiquids(self) -> int:
        """Clear all water and lava blocks. Returns count of removed blocks."""
        removed = 0
        toRemove = []
        for pos, blockType in self.blocks.items():
            if blockType == BlockType.WATER or blockType == BlockType.LAVA:
                toRemove.append(pos)
        
        for pos in toRemove:
            del self.blocks[pos]
            if pos in self.liquidLevels:
                del self.liquidLevels[pos]
            removed += 1
        
        self.waterUpdateQueue.clear()
        self.lavaUpdateQueue.clear()
        
        return removed
    
    def hasBlockType(self, blockType: 'BlockType') -> bool:
        """Check if the world contains any blocks of the specified type"""
        for block in self.blocks.values():
            if block == blockType:
                return True
        return False
    
    def getHighestBlock(self, x: int, y: int) -> int:
        """Get the height of the highest block at (x, y)"""
        for z in range(self.height - 1, -1, -1):
            if self.getBlock(x, y, z) != BlockType.AIR:
                return z
        return -1
    
    def calculateLighting(self) -> Dict[Tuple[int, int, int], Tuple[int, Tuple[int, int, int]]]:
        """
        Calculate light levels and colors for all positions.
        Returns dict of (x, y, z) -> (light level, light color RGB).
        """
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
