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
python blocFantome.py
```

---

## Development Setup

### Project Structure
```
Bloc-Fantome/
├── Code/
│   ├── blocFantome.py         # Composition root and application orchestration
│   ├── runtime_paths.py       # Source/frozen paths and user-data locations
│   ├── constants.py           # Compatibility re-exports
│   ├── domain/                # Stable data and identities; no UI dependencies
│   │   ├── blocks.py          # BlockType and serializable block state
│   │   ├── block_catalog.py   # Definition value objects
│   │   ├── dimensions.py      # Dimension and weather presentation data
│   │   ├── structures.py      # JSON structure loading and registry composition
│   │   └── world_catalog.py   # Narrow dependency required by World
│   ├── engine/
│   │   ├── build_io.py        # Transactional build parsing and migration
│   │   ├── input_commands.py  # Context-aware keyboard command resolution
│   │   ├── renderer.py        # Instance-owned projection and picking geometry
│   │   ├── scene_cache.py     # Validated derived large-world cache
│   │   ├── undo.py            # Undoable editor commands
│   │   ├── world.py           # Sparse world and spatial indexes
│   │   └── world_snapshot.py  # Immutable staged replacement data
│   ├── ui/                    # Existing modal interfaces
│   ├── setup_assets.py        # Asset extraction script
│   └── splash.py              # Splash screen module
├── Assets/
│   ├── Texture Hub/          # Block and UI textures (user-provided)
│   ├── Sound Hub/            # Sound effects and music (user-provided)
│   └── Icons/                # Application icons
└── References/               # Reference materials
```

### Running Tests
Run the automated and deterministic checks from the repository root:

```bash
python -m pytest -q
python tests/render_visual_checks.py
python tests/render_world_checks.py
python tests/benchmark_large_world.py ancient_city_121 trial_chamber_121
```

### Building the Executable
```bash
python Code/build_exe.py --diagnostic
python Code/build_exe.py
```

---

## Code Style Guidelines

### Python Style
- Follow PEP 8 guidelines
- Use 4 spaces for indentation (no tabs)
- Maximum line length: 120 characters
- Use type hints for function parameters and return types

### Naming Conventions
- Classes: `PascalCase` (e.g., `BlocFantome`, `AssetManager`)
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
Add the stable serialized identity to `Code/domain/blocks.py`. Never create a
second enum with equivalent values:
```python
class BlockType(Enum):
    # ... existing blocks ...
    MY_NEW_BLOCK = auto()
```

### Step 2: Define Block Properties
Add the corresponding compatibility catalog entry to `BLOCK_DEFINITIONS` in
`Code/blocFantome.py`. `Code/domain/block_catalog.py` owns the immutable value
types used by this map:
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
Add the JSON filename and display name to `JSON_STRUCTURE_LIBRARY` in
`Code/domain/structures.py`:
```python
JSON_STRUCTURE_LIBRARY = {
    # ... existing structures ...
    "my_structure": "My Structure",
}
```

### Step 3: Add Preview (Optional)
Structure previews are auto-generated at startup from the JSON files.

---

## Testing

### Automated Gates

Every behavioral change starts with a focused failing test. Run that focused
test after the implementation, then run the complete suite before moving to a
different subsystem. Rendering, projection, sprites, ordering, lighting,
weather, and UI changes also require both deterministic visual scripts.

Large-world changes must retain these Trial Chamber medians over at least five
runs:

- Cached load at or below 1,000 ms.
- Stable full-frame p95 below 16.7 ms.
- Cold view rebuild below 100 ms.
- Fit plus first exact frame below 250 ms.
- Bounded world-surface and sprite-cache memory reported by the benchmark.

The software Pygame renderer currently meets these practical budgets. NumPy is
not a dependency and a GPU backend is intentionally not maintained: neither is
accepted without an isolated benchmark showing the gains defined by the
refactor plan, equivalent deterministic output, a tested one-file build, and an
automatic Pygame fallback.

### Architecture Invariants

- Dependencies point from `blocFantome.py` toward `domain`, `engine`, and `ui`;
  extracted modules never import the application module.
- `BlockType` and block-state classes have one canonical identity in
  `Code/domain/blocks.py`.
- `World` receives its immutable catalog dependency through its constructor.
- Build readers return a `WorldSnapshot`; only the main thread replaces the live
  world or creates and mutates Pygame surfaces.
- Source and frozen path lookup stays in `Code/runtime_paths.py`.
- Render and sprite caches are byte-bounded. Invalidation must preserve source
  sprites when only projection, camera, or composition state changes.
- Painter order is global. Never concatenate independently sorted chunks unless
  an equivalence test proves the resulting order.

### Save Compatibility

Save-format work must preserve versions 1 through 5, gzip and plain JSON input,
v3 single-cell door migration, nested and legacy block-state fields, liquid
level/source/falling state, scene roles, v5 bounds/provenance, and atomic writes.
Malformed loads must leave the current live world unchanged.

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
