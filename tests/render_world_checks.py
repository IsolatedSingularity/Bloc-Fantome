"""Render deterministic problem-scene checks without changing repository art."""

import os
from pathlib import Path
import sys
import tempfile


os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Code"))

import pygame
import blocFantome


SCENES = (
    "ancient_city_121",
    "trial_chamber_121",
    "bastion_treasure_1161",
    "bastion_hoglin_stable_1161",
    "end_city_1161",
    "village_plains_1161",
)


def render(output_dir: Path, scenes=SCENES) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    app = blocFantome.BlocFantome()
    if not app.assetManager.loadAllAssets():
        raise RuntimeError("Could not load visual-check assets")
    app.blocksExpanded = False
    app.problemsExpanded = False
    app.experimentalExpanded = False
    app.structuresExpanded = False
    app.worldsExpanded = False

    for scene_id in scenes:
        if scene_id == "tutorial_end":
            step = next(
                index for index, data in enumerate(blocFantome.TutorialScreen.TUTORIAL_STEPS)
                if data["title"] == "The End"
            )
            app._onTutorialStepChange(step)
            app._render()
            pygame.image.save(app.screen, output_dir / "tutorial_end.png")
            continue
        path = Path(blocFantome.WORLDS_DIR) / f"{scene_id}.json.gz"
        if not app._loadBuildingFromPath(str(path), silent=True):
            raise RuntimeError(f"Could not load {scene_id}")
        app._render()
        pygame.image.save(app.screen, output_dir / f"{scene_id}_overview.png")

        if app.sceneStructurePositions:
            positions = app.sceneStructurePositions
            center = tuple(
                round((min(pos[axis] for pos in positions) + max(pos[axis] for pos in positions)) / 2)
                for axis in range(3)
            )
            app.zoomLevel = 0.22
            app.renderer.setZoom(app.zoomLevel)
            app._centerOnCell(*center)
            app.renderer.offsetX = app.targetOffsetX
            app.renderer.offsetY = app.targetOffsetY
            app._invalidateViewCaches()
            app._render()
            pygame.image.save(app.screen, output_dir / f"{scene_id}_detail.png")

    app.worldLoadExecutor.shutdown(wait=False, cancel_futures=True)
    pygame.quit()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        output = Path(sys.argv[1])
        selected = tuple(sys.argv[2:]) or SCENES
        render(output, selected)
    else:
        render(Path(tempfile.gettempdir()) / "kilo" / "bloc-fantome-world-checks")
