"""Convert the licensed 3x2 OptiFine cube atlases to crisp panoramas.

The generated files stay beside the local, Git-ignored licensed assets. Runtime
rendering only loads and scrolls these projections; NumPy and Pillow are build
tools, not application dependencies.
"""

from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
SKY_ROOT = (
    ROOT / "Assets" / "Skyboxes" / "Black Mesa" / "assets" / "minecraft"
    / "optifine" / "sky"
)
OUTPUT_ROOT = SKY_ROOT / "panoramas"
WIDTH = 2400
HEIGHT = 1200

# OptiFine's 3x2 layout and orientation, as rendered by SkyPart: bottom, top,
# east / south, west, north. The source faces are individually rotated; merely
# concatenating the four horizon tiles exposes cube seams.
FACES = {
    "bottom": (0, 0), "top": (1, 0), "east": (2, 0),
    "south": (0, 1), "west": (1, 1), "north": (2, 1),
}


def _face(atlas: np.ndarray, column: int, row: int) -> np.ndarray:
    face_h = atlas.shape[0] // 2
    face_w = atlas.shape[1] // 3
    return atlas[row * face_h:(row + 1) * face_h,
                 column * face_w:(column + 1) * face_w]


def _sample(face: np.ndarray, u: np.ndarray, v: np.ndarray) -> np.ndarray:
    x = np.clip(np.rint(u * (face.shape[1] - 1)), 0, face.shape[1] - 1).astype(np.int32)
    y = np.clip(np.rint(v * (face.shape[0] - 1)), 0, face.shape[0] - 1).astype(np.int32)
    return face[y, x]


def project(source: Path, destination: Path) -> None:
    atlas = np.asarray(Image.open(source).convert("RGB"))
    longitudes = np.linspace(-np.pi, np.pi, WIDTH, endpoint=False, dtype=np.float32)
    latitudes = np.linspace(np.pi / 2, -np.pi / 2, HEIGHT, dtype=np.float32)
    lon, lat = np.meshgrid(longitudes, latitudes)

    dx = np.cos(lat) * np.sin(lon)
    dy = np.sin(lat)
    dz = np.cos(lat) * np.cos(lon)
    dominant = np.maximum.reduce((np.abs(dx), np.abs(dy), np.abs(dz)))
    result = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)

    # Inverse-transform each direction through the exact cube-face rotations.
    # Local face coordinates use y=-1, u=(x+1)/2, v=(z+1)/2.
    face_maps = (
        ("bottom", (np.abs(dy) == dominant) & (dy < 0), -dz, dx),
        ("top", (np.abs(dy) == dominant) & (dy >= 0), -dz, -dx),
        ("east", (np.abs(dx) == dominant) & (dx >= 0), dz, -dy),
        ("south", (np.abs(dz) == dominant) & (dz >= 0), -dx, -dy),
        ("west", (np.abs(dx) == dominant) & (dx < 0), -dz, -dy),
        ("north", (np.abs(dz) == dominant) & (dz < 0), dx, -dy),
    )
    claimed = np.zeros((HEIGHT, WIDTH), dtype=bool)
    for name, candidate, local_x, local_z in face_maps:
        mask = candidate & ~claimed
        u = 0.5 + 0.5 * local_x / dominant
        v = 0.5 + 0.5 * local_z / dominant
        sampled = _sample(_face(atlas, *FACES[name]), u, v)
        result[mask] = sampled[mask]
        claimed |= mask

    destination.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(result, "RGB").save(destination, optimize=True)
    print(f"{source.relative_to(SKY_ROOT)} -> {destination.relative_to(SKY_ROOT)}")


def main() -> int:
    sources = sorted(
        path for world in (SKY_ROOT / "world0", SKY_ROOT / "world1")
        for path in world.glob("*.png")
    )
    if len(sources) != 7:
        print(f"Expected seven sky atlases, found {len(sources)}", file=sys.stderr)
        return 1
    for source in sources:
        destination = OUTPUT_ROOT / source.parent.name / source.name
        project(source, destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
