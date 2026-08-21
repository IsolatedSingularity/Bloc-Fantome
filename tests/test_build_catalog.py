import importlib.util
import pathlib
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("build_catalog", ROOT / "Code" / "engine" / "build_catalog.py")
CATALOG = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CATALOG)


class BuildCatalogTests(unittest.TestCase):
    def test_catalog_separates_user_tutorial_nether_and_end_content(self):
        with tempfile.TemporaryDirectory() as saves, tempfile.TemporaryDirectory() as bundled:
            pathlib.Path(saves, "_autosave.json.gz").touch()
            pathlib.Path(saves, "castle.json.gz").touch()
            pathlib.Path(bundled, "warped_forest.json").touch()
            pathlib.Path(bundled, "end_city_tower.json").touch()
            entries = CATALOG.build_catalog(
                saves,
                bundled,
                [{"title": "Welcome", "demo": "welcome_showcase"}],
            )
            categories = {entry.category for entry in entries}
            self.assertEqual(categories, {"My Builds", "Tutorials", "Nether", "End"})
            tutorial = next(entry for entry in entries if entry.kind == "tutorial")
            self.assertEqual(tutorial.tutorial_index, 0)

    def test_bundled_files_are_not_duplicated_as_user_builds_in_source_mode(self):
        with tempfile.TemporaryDirectory() as shared:
            pathlib.Path(shared, "_autosave.json.gz").touch()
            pathlib.Path(shared, "warped_forest.json").touch()
            entries = CATALOG.build_catalog(shared, shared, [])
            my_builds = [entry.label for entry in entries if entry.category == "My Builds"]
            self.assertEqual(my_builds, ["Autosave Recovery"])


if __name__ == "__main__":
    unittest.main()
