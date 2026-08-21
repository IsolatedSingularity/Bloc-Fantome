"""Compatibility contract for data exported by ``blocFantome``."""

import hashlib
import json
import os
from pathlib import Path
import sys


os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Code"))

import blocFantome
from domain.structures import compose_structure_registry
from engine.renderer import IsometricRenderer as EngineRenderer
from engine.world import World as EngineWorld


def _digest(value) -> str:
    encoded = json.dumps(value, separators=(",", ":"), sort_keys=True).encode()
    return hashlib.sha256(encoded).hexdigest()


def test_required_public_exports_remain_available():
    required = {
        "BlocFantome", "BlockType", "BlockDefinition", "SoundDefinition",
        "BLOCK_DEFINITIONS", "BLOCK_SOUNDS", "BLOCK_CATEGORIES",
        "PREMADE_STRUCTURES", "DIMENSION_OVERWORLD", "DIMENSION_NETHER",
        "DIMENSION_END", "DIMENSION_WEATHER", "BASE_DIR", "ASSETS_DIR",
        "SAVES_DIR", "WORLDS_DIR",
    }
    assert required <= set(vars(blocFantome))


def test_dead_duplicate_types_are_not_exported():
    assert not hasattr(blocFantome, "_LegacyBlockType")
    assert not hasattr(blocFantome, "Renderer3D")
    assert blocFantome.World is EngineWorld
    assert blocFantome.IsometricRenderer is EngineRenderer


def test_block_enum_name_and_value_contract():
    values = [(member.name, member.value) for member in blocFantome.BlockType]
    assert len(values) == 332
    assert _digest(values) == "3d059ca60e85642d913905b696e00b831e614bcacdf05b2c68dda18f2cb0a114"


def test_block_catalog_and_sound_contract():
    definitions = [
        (block.name, vars(definition))
        for block, definition in blocFantome.BLOCK_DEFINITIONS.items()
    ]
    sounds = [
        (block.name, vars(sound))
        for block, sound in blocFantome.BLOCK_SOUNDS.items()
    ]
    assert len(definitions) == len(sounds) == 331
    assert _digest(definitions) == "640f558c42b98ddb2b08c81b0f760c6a8ae9dfd4d6015637abe89d22d8a6260e"
    assert _digest(sounds) == "24990291718c08140d421f57d9467a5462a4a8c7d15b12110c8a56395ecbde5a"


def test_category_order_and_membership_contract():
    categories = [
        (name, [block.name for block in blocks])
        for name, blocks in blocFantome.BLOCK_CATEGORIES.items()
    ]
    assert len(categories) == 12
    assert _digest(categories) == "1f062c839487ba2a933160925d9a74b37ef64fc2f198df2b1ad5c23dfd4a30b1"


def test_structure_tutorial_and_weather_summary_contract():
    structures = [
        (
            key,
            value.get("name"),
            len(value.get("blocks", ())),
            value.get("source_file"),
            value.get("source_version"),
        )
        for key, value in blocFantome.PREMADE_STRUCTURES.items()
    ]
    tutorial = [
        (step.get("title"), step.get("demo"), step.get("icon"))
        for step in blocFantome.TutorialScreen.TUTORIAL_STEPS
    ]
    assert len(structures) == 38
    assert _digest(structures) == "ba9b0af1ccf40414eafcadf399f0beb7426c3edb45baaa7e7099e59729f42c50"
    assert len(tutorial) == 17
    assert _digest(tutorial) == "885c2e6f58c548cfa745553038925c3081150af240b3d053f7c17025b9e9f577"
    assert _digest(blocFantome.DIMENSION_WEATHER) == "bffbbbf2ed9ea82422dd95c8da6b3ec694ff4f99aaf53d8bf84e50858b121988"


def test_runtime_paths_are_absolute_and_keep_assets_external():
    for name in ("BASE_DIR", "ASSETS_DIR", "SAVES_DIR", "WORLDS_DIR"):
        assert Path(getattr(blocFantome, name)).is_absolute(), name
    assert Path(blocFantome.ASSETS_DIR).name == "Assets"


def test_structure_registry_composition_does_not_mutate_builtin_mapping():
    builtins = {"local": {"name": "Local", "blocks": []}}

    composed = compose_structure_registry(
        builtins,
        structure_directory=ROOT / "missing-structures",
        definitions=blocFantome.BLOCK_DEFINITIONS,
    )

    assert composed == builtins
    assert composed is not builtins
