"""Compatibility contract for data exported by ``blocFantome``."""

import hashlib
import json
import os
from pathlib import Path
import re
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
    assert len(values) == 340
    assert _digest(values) == "8ef8365c6f45454d4a1ecb022164e8263c90e8ed759dd6462d8a95015019697a"


def test_block_catalog_and_sound_contract():
    definitions = [
        (block.name, vars(definition))
        for block, definition in blocFantome.BLOCK_DEFINITIONS.items()
    ]
    sounds = [
        (block.name, vars(sound))
        for block, sound in blocFantome.BLOCK_SOUNDS.items()
    ]
    assert len(definitions) == len(sounds) == 339
    assert _digest(definitions) == "e85e4cb9105c7192f255cf9c1e3fcfc85c5c0be437aa465303a0a02944fddfa2"
    assert _digest(sounds) == "b58593730d6308e173fb5166ecfe348ebf5c3776db569a00f55eb9bbd6ba5f98"


def test_category_order_and_membership_contract():
    categories = [
        (name, [block.name for block in blocks])
        for name, blocks in blocFantome.BLOCK_CATEGORIES.items()
    ]
    assert len(categories) == 12
    assert _digest(categories) == "255a0e711c48419d87e741957fe81bf23d7c6ebf0ffbd63f1b2d1ce94a6a7f92"


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
    assert len(structures) == 40
    assert _digest(structures) == "55cdfbe04bbc91497d5c2b185d9ce7d2f7f1bdeedf7bc23b6be23b812232f678"
    assert len(tutorial) == 17
    assert _digest(tutorial) == "feb5ea23a90ee8d142e7ef811203e624a657cf21d29d503fd2d05abc8e43c0ae"
    assert _digest(blocFantome.DIMENSION_WEATHER) == "ba1a097351944d2a2aa27be50da2a101866f25f4b52f952fb757e0beb3f5da65"


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
    assert 'Name: "{group}\\{#MyAppName}"' in installer
    build_version = re.search(r'^VERSION = "([^"]+)"', build_script, re.MULTILINE).group(1)
    installer_version = re.search(
        r'^#define MyAppVersion "([^"]+)"', installer, re.MULTILINE
    ).group(1)
    runtime_version = re.search(
        r"blocfantome\.builder\.([0-9.]+)",
        (ROOT / "Code" / "blocFantome.py").read_text(encoding="utf-8"),
    ).group(1)
    assert build_version == installer_version == runtime_version


def test_structure_registry_composition_does_not_mutate_builtin_mapping():
    builtins = {"local": {"name": "Local", "blocks": []}}

    composed = compose_structure_registry(
        builtins,
        structure_directory=ROOT / "missing-structures",
        definitions=blocFantome.BLOCK_DEFINITIONS,
    )

    assert composed == builtins
    assert composed is not builtins
