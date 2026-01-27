# Contributing to Bloc Fantôme

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to the project.

## Table of Contents
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Code Style Guidelines](#code-style-guidelines)
- [Adding New Blocks](#adding-new-blocks)
- [Adding New Structures](#adding-new-structures)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)

---

## Getting Started

### Prerequisites
- Python 3.8 or higher
- pygame library
- Git
- Minecraft Java Edition 1.21.1+ (for assets)

### Clone the Repository
```bash
git clone https://github.com/IsolatedSingularity/Bloc-Fantome.git
cd Bloc-Fantome
```

### Install Dependencies
```bash
pip install pygame
```

### Setup Assets
```bash
cd Code
python setup_assets.py
```

### Run from Source
```bash
python minecraftBuilder.py
```

---

## Development Setup

### Project Structure
```
Bloc-Fantome/
├── Code/
│   ├── minecraftBuilder.py   # Main application (entry point)
│   ├── setup_assets.py       # Asset extraction script
│   ├── splash.py             # Splash screen module
│   ├── horror.py             # Horror system manager
│   ├── constants.py          # Shared constants and enums
│   └── engine/               # Core engine modules
│       ├── undo.py           # Undo/redo system
│       ├── world.py          # World voxel grid
│       ├── renderer.py       # Isometric renderer
│       └── performance.py    # Performance utilities
├── Assets/
│   ├── Texture Hub/          # Block and UI textures (user-provided)
│   ├── Sound Hub/            # Sound effects and music (user-provided)
│   └── Icons/                # Application icons
└── References/               # Reference materials
```

### Running Tests
Currently, manual testing is required. See the [Testing](#testing) section.

### Building the Executable
```bash
cd Code
python build_exe.py
```

---

## Code Style Guidelines

### Python Style
- Follow PEP 8 guidelines
- Use 4 spaces for indentation (no tabs)
- Maximum line length: 120 characters
- Use type hints for function parameters and return types

### Naming Conventions
- Classes: `PascalCase` (e.g., `MinecraftBuilder`, `AssetManager`)
- Functions/Methods: `camelCase` with underscore prefix for private (e.g., `_renderWorld`, `loadAssets`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `TILE_WIDTH`, `GRID_HEIGHT`)
- Variables: `camelCase` (e.g., `blockType`, `currentDimension`)

### Docstrings
Use docstrings for all public functions and classes:
```python
def myFunction(param1: int, param2: str) -> bool:
    """
    Brief description of what the function does.
    
    Args:
        param1: Description of param1
        param2: Description of param2
        
    Returns:
        Description of return value
    """
    pass
```

### Exception Handling
- **DO NOT** use bare `except:` clauses
- Always catch specific exceptions:
```python
# Bad
try:
    something()
except:
    pass

# Good
try:
    something()
except (ValueError, KeyError) as e:
    print(f"Warning: {e}")
```

### File Operations
- Use atomic writes for save files (write to temp, then rename)
- Always use context managers (`with` statements)

---

## Adding New Blocks

### Step 1: Add to BlockType Enum
In `minecraftBuilder.py`, find the `BlockType` enum and add your block:
```python
class BlockType(Enum):
    # ... existing blocks ...
    MY_NEW_BLOCK = auto()
```

### Step 2: Define Block Properties
Add an entry to `BLOCK_DEFINITIONS`:
```python
BlockType.MY_NEW_BLOCK: BlockDefinition(
    textureTop="my_block_top.png",
    textureSide="my_block.png",
    textureBottom="my_block_bottom.png",
    transparent=False,
    solid=True,
    lightLevel=0,
    animated=False,
    category="Building"
),
```

### Step 3: Add Texture Files
Place your 16x16 PNG textures in `Assets/Texture Hub/blocks/`:
- `my_block.png` (side texture)
- `my_block_top.png` (top texture, optional)
- `my_block_bottom.png` (bottom texture, optional)

### Step 4: Add to Category
Ensure your block's category exists in `BLOCK_CATEGORIES`:
```python
BLOCK_CATEGORIES = {
    "Building": [BlockType.STONE, ..., BlockType.MY_NEW_BLOCK],
    # ...
}
```

### Step 5: Add Sound (Optional)
If your block has a unique sound category, add it to `BLOCK_SOUNDS`:
```python
BLOCK_SOUNDS = {
    BlockType.MY_NEW_BLOCK: "stone",  # Use existing sound category
}
```

---

## Adding New Structures

### Step 1: Create Structure JSON
Create a new JSON file in `Code/saves/`:
```json
{
    "version": 3,
    "dimension": "overworld",
    "blocks": [
        {"x": 0, "y": 0, "z": 0, "type": "STONE"},
        {"x": 1, "y": 0, "z": 0, "type": "OAK_PLANKS"},
        ...
    ]
}
```

### Step 2: Register as Predefined Structure
In `minecraftBuilder.py`, find `PREDEFINED_STRUCTURES` and add:
```python
PREDEFINED_STRUCTURES = {
    # ... existing structures ...
    "my_structure": "my_structure.json",
}
```

### Step 3: Add Preview (Optional)
Structure previews are auto-generated at startup from the JSON files.

---

## Testing

### Manual Testing Checklist
Before submitting changes, verify:

- [ ] **Fresh install** - Delete `.app_config.json` and test startup
- [ ] **Save/Load** - Create a build, save it, reload it
- [ ] **All dimensions** - Test in Overworld, Nether, and End
- [ ] **Block placement** - Test placing and removing blocks
- [ ] **Special blocks** - Test doors, slabs, stairs, liquids
- [ ] **Undo/Redo** - Test Ctrl+Z and Ctrl+Y
- [ ] **Tutorial** - Complete full tutorial flow
- [ ] **Hotkeys** - Verify all keyboard shortcuts work
- [ ] **No errors** - Check console for error messages
- [ ] **Memory** - Run for 10+ minutes, check for leaks

### Performance Testing
For large builds (1000+ blocks):
- FPS should stay above 30
- Memory should stabilize after initial load
- No stuttering during placement

---

## Pull Request Process

### Before Submitting
1. Test your changes thoroughly (see Testing section)
2. Update documentation if adding features
3. Add comments for complex logic
4. Ensure no bare `except:` clauses

### PR Title Format
```
[TYPE] Brief description

Types:
- [FIX] Bug fixes
- [FEAT] New features
- [PERF] Performance improvements
- [DOCS] Documentation changes
- [REFACTOR] Code refactoring
```

### PR Description Template
```markdown
## What does this PR do?
Brief description of changes.

## How to test?
Steps to verify the changes work.

## Screenshots (if applicable)
Add screenshots for UI changes.

## Checklist
- [ ] Tested manually
- [ ] No new bare except clauses
- [ ] Documentation updated
```

---

## Questions?

If you have questions about contributing, please open an issue with the `question` label.

---

*Happy building!*
