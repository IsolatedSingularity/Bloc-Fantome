"""Shared test path setup; individual test order must not affect imports."""

from pathlib import Path
import sys
import tempfile
import pytest


CODE_DIR = Path(__file__).resolve().parents[1] / "Code"
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))


# Default collection retains every release check. Select this explicit subset
# for a tracked-source checkout without private media or ignored lesson bundles.
CORE_MODULES={
    'test_build_catalog','test_build_io','test_capture_records','test_cleanup_tool','test_engine',
    'test_fonts','test_input_commands','test_lighting','test_maintenance',
    'test_public_contract','test_redstone','test_redstone_lab','test_scene_cache',
    'test_settings_io','test_terrain','test_tutorial_bundle_core','test_undo',
    'test_world_indexes','test_visibility_contract',
}


def pytest_collection_modifyitems(items):
    for item in items:
        if Path(item.path).stem in CORE_MODULES:item.add_marker(pytest.mark.core)


@pytest.fixture(scope='session',autouse=True)
def stdlib_temp_inside_test_workspace(tmp_path_factory):
    """Keep stdlib fixtures inside pytest's explicitly writable workspace."""
    previous=tempfile.tempdir
    tempfile.tempdir=str(tmp_path_factory.mktemp('stdlib'))
    try:yield
    finally:tempfile.tempdir=previous
