"""Repeatable headless benchmark for bundled large editable worlds."""

import argparse
import json
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


def measure(operation, repetitions=5, warmup=0, sample_setup=None):
    for _ in range(warmup):
        if sample_setup is not None:
            sample_setup()
        operation()
    samples = []
    for _ in range(repetitions):
        if sample_setup is not None:
            sample_setup()
        started = time.perf_counter()
        operation()
        samples.append((time.perf_counter() - started) * 1000.0)
    ordered = sorted(samples)
    return {
        "median_ms": statistics.median(ordered),
        "p95_ms": ordered[max(0, int(len(ordered) * 0.95) - 1)],
        "max_ms": ordered[-1],
        "samples_ms": samples,
    }


def surface_bytes(surface):
    if surface is None:
        return 0
    return surface.get_width() * surface.get_height() * surface.get_bytesize()


def benchmark_scene(app, path, repetitions):
    load = measure(
        lambda: app._loadBuildingFromPath(str(path), silent=True),
        repetitions=repetitions,
    )

    def cold_render():
        app.zoomLevel = 0.5
        app.renderer.setZoom(0.5)
        app._invalidateViewCaches()
        app._renderWorld()

    cold = measure(cold_render, repetitions=repetitions)
    stable = measure(app._render, repetitions=90, warmup=3)

    def forced_pan():
        app.renderer.offsetX += app._worldSurfaceMargin + 80
        app._invalidateViewCaches()
        app._renderWorld()

    pan_rebuild = measure(forced_pan, repetitions=repetitions)

    def rotate():
        app._rotateViewAndRecenter(1)
        app._renderWorld()

    rotation = measure(rotate, repetitions=repetitions)

    def fit_and_render():
        app._fitWorldToViewport()
        app._render()

    fit = measure(fit_and_render, repetitions=repetitions)
    overview = measure(app._render, repetitions=30, warmup=3)

    def zoom_exact():
        center = ((blocFantome.WINDOW_WIDTH - blocFantome.PANEL_WIDTH) // 2,
                  blocFantome.WINDOW_HEIGHT // 2)
        app._handleZoom(app.zoomStep, *center)
        app._zoomPreviewUntil = 0
        app._renderWorld()

    def prepare_zoom_exact():
        app._fitWorldToViewport(notify=False)
        app._zoomPreviewSurface = None
        app._zoomPreviewSource = None
        app._zoomPreviewUntil = 0
        app._renderWorld()

    zoom = measure(
        zoom_exact,
        repetitions=repetitions,
        sample_setup=prepare_zoom_exact,
    )

    world_surface_bytes = surface_bytes(app._worldSurfaceCache)
    zoom_stats = app.assetManager.zoomSpriteCache.get_stats()
    alpha_stats = app.assetManager.alphaSpriteCache.get_stats()
    return {
        "scene": path.stem.replace(".json", ""),
        "blocks": len(app.world.blocks),
        "load": load,
        "cold_render": cold,
        "forced_pan_rebuild": pan_rebuild,
        "stable_full_frame": stable,
        "rotation": rotation,
        "fit_first_frame": fit,
        "overview": overview,
        "first_exact_zoom_frame": zoom,
        "render": dict(app.renderStats),
        "memory": {
            "world_surface_bytes": world_surface_bytes,
            "zoom_sprites": zoom_stats,
            "alpha_sprites": alpha_stats,
        },
    }


def parse_args(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("scenes", nargs="*", help="scene ids without .json.gz")
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument("--json-output", type=Path)
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    if args.repetitions < 5:
        raise ValueError("cold-operation benchmarks require at least five repetitions")
    app = blocFantome.BlocFantome()
    if not app.assetManager.loadAllAssets():
        raise RuntimeError("assets unavailable")
    print(
        f"viewport={app.screen.get_width()}x{app.screen.get_height()} "
        f"distance={app.renderDistanceChunks} chunks repetitions={args.repetitions}"
    )
    requested = set(args.scenes)
    paths = sorted(Path(blocFantome.WORLDS_DIR).glob("*.json.gz"))
    if requested:
        paths = [path for path in paths if path.stem.replace(".json", "") in requested]
    results = []
    for path in paths:
        result = benchmark_scene(app, path, args.repetitions)
        results.append(result)
        print(
            f"{result['scene']}: blocks={result['blocks']} "
            f"load_median={result['load']['median_ms']:.1f}ms "
            f"load_p95={result['load']['p95_ms']:.1f}ms "
            f"cold_median={result['cold_render']['median_ms']:.1f}ms "
            f"cold_p95={result['cold_render']['p95_ms']:.1f}ms "
            f"pan_median={result['forced_pan_rebuild']['median_ms']:.1f}ms "
            f"full_p95={result['stable_full_frame']['p95_ms']:.2f}ms "
            f"fit_median={result['fit_first_frame']['median_ms']:.1f}ms "
            f"zoom_exact_p95={result['first_exact_zoom_frame']['p95_ms']:.1f}ms "
            f"drawn={result['render']['drawn']} candidates={result['render']['candidates']}"
        )
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(
            json.dumps({"environment": {"python": sys.version, "pygame": pygame.version.ver},
                        "results": results}, indent=2),
            encoding="utf-8",
        )
    app.worldLoadExecutor.shutdown(wait=False, cancel_futures=True)
    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
