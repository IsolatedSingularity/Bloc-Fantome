"""Build Bloc Fantome's optional, dependency-free Rust accelerator."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess


SCRIPT_DIR = Path(__file__).resolve().parent
MANIFEST = SCRIPT_DIR / "native" / "depth_sort" / "Cargo.toml"
OUTPUT = SCRIPT_DIR / "native" / "bin" / "bloc_fantome_native.dll"


def build(*, required: bool = False) -> bool:
    cargo = shutil.which("cargo")
    if cargo is None:
        if OUTPUT.is_file():
            print(f"Rust toolchain unavailable; using existing accelerator: {OUTPUT}")
            return True
        message = "Rust toolchain unavailable; packaged app will use the Python fallback"
        if required:
            raise RuntimeError(message)
        print(message)
        return False

    target_dir = SCRIPT_DIR / "build" / "native-target"
    environment = os.environ.copy()
    environment["CARGO_TARGET_DIR"] = str(target_dir)
    result = subprocess.run(
        [cargo, "build", "--release", "--manifest-path", str(MANIFEST)],
        cwd=SCRIPT_DIR,
        env=environment,
        check=False,
    )
    if result.returncode:
        message = "Optional Rust accelerator build failed; Python fallback remains available"
        if required:
            raise RuntimeError(message)
        print(message)
        return False

    compiled = target_dir / "release" / "bloc_fantome_native.dll"
    if not compiled.is_file():
        raise FileNotFoundError(f"Cargo did not produce {compiled}")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(compiled, OUTPUT)
    print(f"Built optional native accelerator: {OUTPUT}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--required", action="store_true")
    args = parser.parse_args()
    return 0 if build(required=args.required) else 2


if __name__ == "__main__":
    raise SystemExit(main())
