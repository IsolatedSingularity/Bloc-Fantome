"""Repeatable headless render benchmark for the three bundled Worlds."""

import os
from pathlib import Path
import statistics
import sys
import time


os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Code"))

import pygame
import blocFantome


def main() -> int:
    app = blocFantome.BlocFantome()
    if not app.assetManager.loadAllAssets():
        raise RuntimeError("assets unavailable")
    print(f"viewport={app.screen.get_width()}x{app.screen.get_height()} distance={app.renderDistanceChunks} chunks")
    requested = set(sys.argv[1:])
    paths = sorted(Path(blocFantome.WORLDS_DIR).glob("*.json.gz"))
    if requested:
        paths = [path for path in paths if path.stem.replace(".json", "") in requested]
    for path in paths:
        started = time.perf_counter()
        if not app._loadBuildingFromPath(str(path), silent=True):
            raise RuntimeError(f"could not load {path}")
        load_ms = (time.perf_counter() - started) * 1000.0
        app.zoomLevel = 0.5
        app.renderer.setZoom(0.5)
        app._invalidateViewCaches()
        cold_started = time.perf_counter()
        app._renderWorld()
        cold_ms = (time.perf_counter() - cold_started) * 1000.0
        for _ in range(3):
            app._renderWorld()
        samples = []
        for _ in range(90):
            tick = time.perf_counter()
            app._renderWorld()
            samples.append((time.perf_counter() - tick) * 1000.0)
        samples.sort()
        mean = statistics.fmean(samples)
        p95 = samples[int(len(samples) * 0.95) - 1]
        full_samples = []
        for _ in range(60):
            tick = time.perf_counter()
            app._render()
            full_samples.append((time.perf_counter() - tick) * 1000.0)
        full_samples.sort()
        full_mean = statistics.fmean(full_samples)
        full_p95 = full_samples[int(len(full_samples) * 0.95) - 1]
        pan_samples = []
        original_offset = (app.renderer.offsetX, app.renderer.offsetY)
        for frame in range(30):
            app.renderer.offsetX += 2.0
            app.renderer.offsetY += 1.0 if frame % 2 else -1.0
            tick = time.perf_counter()
            app._render()
            pan_samples.append((time.perf_counter() - tick) * 1000.0)
        app.renderer.offsetX, app.renderer.offsetY = original_offset
        app.renderer.offsetX += app._worldSurfaceMargin + 80
        rebuild_started = time.perf_counter()
        app._renderWorld()
        pan_rebuild_ms = (time.perf_counter() - rebuild_started) * 1000.0
        app.renderer.offsetX, app.renderer.offsetY = original_offset
        pan_samples.sort()
        pan_mean = statistics.fmean(pan_samples)
        pan_p95 = pan_samples[int(len(pan_samples) * 0.95) - 1]
        fit_started = time.perf_counter()
        app._fitWorldToViewport()
        app._render()
        fit_ms = (time.perf_counter() - fit_started) * 1000.0
        overview_samples = []
        for frame in range(30):
            app.renderer.offsetX += 1.5
            app.renderer.offsetY += 0.5 if frame % 2 else -0.5
            tick = time.perf_counter()
            app._render()
            overview_samples.append((time.perf_counter() - tick) * 1000.0)
        overview_mean = statistics.fmean(overview_samples)
        overview_p95 = sorted(overview_samples)[int(len(overview_samples) * 0.95) - 1]
        print(
            f"{path.stem}: blocks={len(app.world.blocks)} load={load_ms:.1f}ms "
            f"cold={cold_ms:.1f}ms pan_rebuild={pan_rebuild_ms:.1f}ms "
            f"mean={mean:.2f}ms p95={p95:.2f}ms fps={1000.0 / mean:.1f} "
            f"full={full_mean:.2f}ms full_p95={full_p95:.2f}ms full_fps={1000.0 / full_mean:.1f} "
            f"pan={pan_mean:.2f}ms pan_p95={pan_p95:.2f}ms pan_fps={1000.0 / pan_mean:.1f} "
            f"fit={fit_ms:.2f}ms overview={overview_mean:.2f}ms "
            f"overview_p95={overview_p95:.2f}ms overview_fps={1000.0 / overview_mean:.1f} "
            f"zoom={app.zoomLevel:.3f} "
            f"drawn={app.renderStats['drawn']} candidates={app.renderStats['candidates']}"
        )
    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
