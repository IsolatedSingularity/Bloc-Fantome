"""
Undo/Redo system for Bite Sized Minecraft.

Implements the Command pattern for reversible block operations.
Uses duck typing to avoid import issues with BlockType enum.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Any, Tuple


class Command(ABC):
    """Abstract base class for undoable commands"""
    
    @abstractmethod
    def execute(self) -> bool:
        """Execute the command. Returns True if successful."""
        pass
    
    @abstractmethod
    def undo(self) -> bool:
        """Undo the command. Returns True if successful."""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """Get a human-readable description of the command"""
        pass


@dataclass
class PlaceBlockCommand(Command):
    """Command to place a block at a position"""
    world: Any  # World object - uses duck typing to avoid import issues
    x: int
    y: int
    z: int
    block_type: Any  # BlockType enum value
    properties: Any = None  # BlockProperties or None
    # State saved for undo
    previous_block: Any = None
    previous_properties: Any = None
    _executed: bool = False
    
    def execute(self) -> bool:
        """Place the block, saving the previous state"""
        if not self.world.isInBounds(self.x, self.y, self.z):
            return False
        
        # Save previous state for undo
        self.previous_block = self.world.getBlock(self.x, self.y, self.z)
        self.previous_properties = self.world.getBlockProperties(self.x, self.y, self.z)
        if self.previous_properties and hasattr(self.previous_properties, 'copy'):
            self.previous_properties = self.previous_properties.copy()
        
        # Place the new block
        self.world.setBlock(self.x, self.y, self.z, self.block_type)
        if self.properties:
            self.world.setBlockProperties(self.x, self.y, self.z, self.properties)
        
        self._executed = True
        return True
    
    def undo(self) -> bool:
        """Restore the previous block state"""
        if not self._executed:
            return False
        
        # Check if previous block was AIR (value 0 or name 'AIR')
        is_air = (self.previous_block is None or 
                  (hasattr(self.previous_block, 'value') and self.previous_block.value == 0) or
                  (hasattr(self.previous_block, 'name') and self.previous_block.name == 'AIR'))
        
        if is_air:
            # Get AIR block type from the same enum class as block_type
            if hasattr(self.block_type, '__class__'):
                air_type = self.block_type.__class__(0)  # Create AIR enum value
                self.world.setBlock(self.x, self.y, self.z, air_type)
        else:
            self.world.setBlock(self.x, self.y, self.z, self.previous_block)
            if self.previous_properties:
                self.world.setBlockProperties(self.x, self.y, self.z, self.previous_properties)
        
        return True
    
    def get_description(self) -> str:
        name = getattr(self.block_type, 'name', str(self.block_type))
        return f"Place {name} at ({self.x}, {self.y}, {self.z})"


@dataclass
class RemoveBlockCommand(Command):
    """Command to remove a block at a position"""
    world: Any  # World object
    x: int
    y: int
    z: int
    # State saved for undo
    previous_block: Any = None
    previous_properties: Any = None
    _executed: bool = False
    
    def execute(self) -> bool:
        """Remove the block, saving the previous state"""
        if not self.world.isInBounds(self.x, self.y, self.z):
            return False
        
        # Save previous state for undo
        self.previous_block = self.world.getBlock(self.x, self.y, self.z)
        
        # Check if already air
        is_air = (self.previous_block is None or 
                  (hasattr(self.previous_block, 'value') and self.previous_block.value == 0) or
                  (hasattr(self.previous_block, 'name') and self.previous_block.name == 'AIR'))
        
        if is_air:
            return False  # Nothing to remove
        
        self.previous_properties = self.world.getBlockProperties(self.x, self.y, self.z)
        if self.previous_properties and hasattr(self.previous_properties, 'copy'):
            self.previous_properties = self.previous_properties.copy()
        
        # Remove the block - create AIR from the same enum class
        air_type = self.previous_block.__class__(0)
        self.world.setBlock(self.x, self.y, self.z, air_type)
        
        self._executed = True
        return True
    
    def undo(self) -> bool:
        """Restore the removed block"""
        if not self._executed or self.previous_block is None:
            return False
        
        self.world.setBlock(self.x, self.y, self.z, self.previous_block)
        if self.previous_properties:
            self.world.setBlockProperties(self.x, self.y, self.z, self.previous_properties)
        
        return True
    
    def get_description(self) -> str:
        block_name = getattr(self.previous_block, 'name', 'block') if self.previous_block else "block"
        return f"Remove {block_name} at ({self.x}, {self.y}, {self.z})"


@dataclass
class BatchCommand(Command):
    """Command that groups multiple commands together"""
    commands: List[Command] = field(default_factory=list)
    description: str = "Batch operation"
    _executed: bool = False
    
    def add(self, command: Command) -> None:
        """Add a command to the batch"""
        self.commands.append(command)
    
    def execute(self) -> bool:
        """Execute all commands in order"""
        if not self.commands:
            return False
        
        success = True
        for cmd in self.commands:
            if not cmd.execute():
                success = False
        
        self._executed = True
        return success
    
    def undo(self) -> bool:
        """Undo all commands in reverse order"""
        if not self._executed:
            return False
        
        success = True
        for cmd in reversed(self.commands):
            if not cmd.undo():
                success = False
        
        return success
    
    def get_description(self) -> str:
        if len(self.commands) == 1:
            return self.commands[0].get_description()
        return f"{self.description} ({len(self.commands)} blocks)"


class UndoManager:
    """
    Manages undo/redo history for the application.
    
    Maintains two stacks:
    - undo_stack: Commands that can be undone
    - redo_stack: Commands that have been undone and can be redone
    """
    
    def __init__(self, max_history: int = 100):
        """
        Initialize the undo manager.
        
        Args:
            max_history: Maximum number of commands to keep in history
        """
        self.max_history = max_history
        self.undo_stack: List[Command] = []
        self.redo_stack: List[Command] = []
    
    def execute(self, command: Command) -> bool:
        """
        Execute a command and add it to the undo stack.
        
        Args:
            command: The command to execute
            
        Returns:
            True if command executed successfully
        """
        if command.execute():
            self.undo_stack.append(command)
            
            # Clear redo stack when new command is executed
            self.redo_stack.clear()
            
            # Trim history if exceeds max
            while len(self.undo_stack) > self.max_history:
                self.undo_stack.pop(0)
            
            return True
        return False
    
    def undo(self) -> Optional[Command]:
        """
        Undo the most recent command.
        
        Returns:
            The undone command, or None if nothing to undo
        """
        if not self.undo_stack:
            return None
        
        command = self.undo_stack.pop()
        if command.undo():
            self.redo_stack.append(command)
            return command
        else:
            # If undo failed, put command back
            self.undo_stack.append(command)
            return None
    
    def redo(self) -> Optional[Command]:
        """
        Redo the most recently undone command.
        
        Returns:
            The redone command, or None if nothing to redo
        """
        if not self.redo_stack:
            return None
        
        command = self.redo_stack.pop()
        if command.execute():
            self.undo_stack.append(command)
            return command
        else:
            # If redo failed, put command back
            self.redo_stack.append(command)
            return None
    
    def can_undo(self) -> bool:
        """Check if there are commands to undo"""
        return len(self.undo_stack) > 0
    
    def can_redo(self) -> bool:
        """Check if there are commands to redo"""
        return len(self.redo_stack) > 0
    
    def get_undo_description(self) -> Optional[str]:
        """Get description of the command that would be undone"""
        if self.undo_stack:
            return self.undo_stack[-1].get_description()
        return None
    
    def get_redo_description(self) -> Optional[str]:
        """Get description of the command that would be redone"""
        if self.redo_stack:
            return self.redo_stack[-1].get_description()
        return None
    
    def clear(self) -> None:
        """Clear all undo/redo history"""
        self.undo_stack.clear()
        self.redo_stack.clear()
    
    def get_history_count(self) -> Tuple[int, int]:
        """Get count of (undo, redo) items"""
        return (len(self.undo_stack), len(self.redo_stack))
    
    def get_undo_history(self, max_items: int = 20) -> List[Tuple[int, str]]:
        """
        Get list of undo history items with index and description.
        
        Args:
            max_items: Maximum number of items to return
            
        Returns:
            List of (index, description) tuples, most recent first
        """
        history = []
        start = max(0, len(self.undo_stack) - max_items)
        for i in range(len(self.undo_stack) - 1, start - 1, -1):
            cmd = self.undo_stack[i]
            history.append((i, cmd.get_description()))
        return history
    
    def get_redo_history(self, max_items: int = 20) -> List[Tuple[int, str]]:
        """
        Get list of redo history items with index and description.
        
        Args:
            max_items: Maximum number of items to return
            
        Returns:
            List of (index, description) tuples, most recent first
        """
        history = []
        start = max(0, len(self.redo_stack) - max_items)
        for i in range(len(self.redo_stack) - 1, start - 1, -1):
            cmd = self.redo_stack[i]
            history.append((i, cmd.get_description()))
        return history
    
    def undo_to_index(self, target_index: int) -> int:
        """
        Undo all commands down to target index.
        
        Args:
            target_index: The index to undo to (this command will remain in undo stack)
            
        Returns:
            Number of commands undone
        """
        count = 0
        while len(self.undo_stack) > target_index + 1:
            if self.undo():
                count += 1
            else:
                break
        return count
    
    def redo_to_index(self, target_index: int) -> int:
        """
        Redo all commands up to target index.
        
        Args:
            target_index: The index to redo to
            
        Returns:
            Number of commands redone
        """
        count = 0
        # Redo stack is reversed, so we redo until we've processed enough
        while len(self.redo_stack) > 0 and count <= target_index:
            if self.redo():
                count += 1
            else:
                break
        return count
