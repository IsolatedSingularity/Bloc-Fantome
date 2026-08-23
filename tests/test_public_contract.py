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
    assert _digest(definitions) == "6e88a4525a52282733ee74afacda33cf32343335637fd900f6ae314622933133"
    assert _digest(sounds) == "ce0c571ea2dd8d437b22869d3af04a7d736a534b9e994d64421fc3b9d63e3dac"


def test_category_order_and_membership_contract():
    categories = [
        (name, [block.name for block in blocks])
        for name, blocks in blocFantome.BLOCK_CATEGORIES.items()
    ]
    assert len(categories) == 11
    assert _digest(categories) == "2c1096a50e9a7ee9baae2273186ce19b1a251dd7ba71ade230b5069568b02b9d"


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
    assert _digest(structures) == "ac6d210f4e3a24c91f23f14ba87a8214ef35bd38efe5c9c75898a15d534aeb2f"
    assert len(tutorial) == 17
    assert _digest(tutorial) == "feb5ea23a90ee8d142e7ef811203e624a657cf21d29d503fd2d05abc8e43c0ae"
    assert _digest(blocFantome.DIMENSION_WEATHER) == "bffbbbf2ed9ea82422dd95c8da6b3ec694ff4f99aaf53d8bf84e50858b121988"


def test_runtime_paths_are_absolute_and_keep_assets_external():
    for name in ("BASE_DIR", "ASSETS_DIR", "SAVES_DIR", "WORLDS_DIR"):
        assert Path(getattr(blocFantome, name)).is_absolute(), name
    assert Path(blocFantome.ASSETS_DIR).name == "Assets"


def test_visible_product_name_is_accented_while_executable_name_stays_compatible():
    build_script = (ROOT / "Code" / "build_exe.py").read_text(encoding="utf-8")
    installer = (ROOT / "Code" / "installer.iss").read_text(encoding="utf-8")

    assert blocFantome.TITLE == "Bloc Fantôme"
    assert 'PRODUCT = "Bloc Fantôme"' in build_script
    assert '#define MyAppName "Bloc Fantôme"' in installer
    assert '#define MyAppExeName "BlocFantome.exe"' in installer
    assert 'Name: "{group}\\Miette"' in installer


def test_structure_registry_composition_does_not_mutate_builtin_mapping():
    builtins = {"local": {"name": "Local", "blocks": []}}

    composed = compose_structure_registry(
        builtins,
        structure_directory=ROOT / "missing-structures",
        definitions=blocFantome.BLOCK_DEFINITIONS,
    )

    assert composed == builtins
    assert composed is not builtins
