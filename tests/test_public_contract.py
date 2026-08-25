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
    assert len(values) == 339
    assert _digest(values) == "75eee78cf8208c8b35c066cd5b025dd892139a098b313f3063277b856d22d857"


def test_block_catalog_and_sound_contract():
    definitions = [
        (block.name, vars(definition))
        for block, definition in blocFantome.BLOCK_DEFINITIONS.items()
    ]
    sounds = [
        (block.name, vars(sound))
        for block, sound in blocFantome.BLOCK_SOUNDS.items()
    ]
    assert len(definitions) == len(sounds) == 338
    assert _digest(definitions) == "8fccdfdad67277b127e02cbe93fb3c337d41a61957b775301b8af89a38009760"
    assert _digest(sounds) == "c0326c648ad5677261707f4a7b348b03371e0db12d0f15379ac0f90a5e470e7e"


def test_category_order_and_membership_contract():
    categories = [
        (name, [block.name for block in blocks])
        for name, blocks in blocFantome.BLOCK_CATEGORIES.items()
    ]
    assert len(categories) == 12
    assert _digest(categories) == "9932d502bef84727057c3d28d12e26b5d113369d1bba97c6966bb465a8a7d4fe"


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
    assert _digest(structures) == "80c2612d4a7342e0c76e2361bd467632ed5c2755d8756228676e485205fbe8d1"
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


def test_structure_registry_composition_does_not_mutate_builtin_mapping():
    builtins = {"local": {"name": "Local", "blocks": []}}

    composed = compose_structure_registry(
        builtins,
        structure_directory=ROOT / "missing-structures",
        definitions=blocFantome.BLOCK_DEFINITIONS,
    )

    assert composed == builtins
    assert composed is not builtins
