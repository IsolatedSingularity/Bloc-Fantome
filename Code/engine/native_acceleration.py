"""Lazy, optional access to Bloc Fantome's native painter-order sorter."""

from __future__ import annotations

from array import array
import ctypes
import os
from pathlib import Path
import sys
from typing import Iterable, Optional


_DLL_NAME = "bloc_fantome_native.dll"
_library = None
_load_attempted = False


def _disabled() -> bool:
    return os.environ.get("BLOC_FANTOME_DISABLE_NATIVE", "").casefold() in {
        "1", "true", "yes", "on",
    }


def _candidate_paths() -> tuple[Path, ...]:
    configured = os.environ.get("BLOC_FANTOME_NATIVE_LIBRARY")
    source = Path(__file__).resolve().parents[1] / "native" / "bin" / _DLL_NAME
    bundled = Path(getattr(sys, "_MEIPASS", source.parent)) / "native" / _DLL_NAME
    candidates = [Path(configured)] if configured else []
    candidates.extend((bundled, source))
    return tuple(dict.fromkeys(candidates))


def _load_library():
    global _library, _load_attempted
    if _load_attempted or _disabled():
        return _library
    _load_attempted = True
    for path in _candidate_paths():
        if not path.is_file():
            continue
        try:
            library = ctypes.CDLL(str(path))
            function = library.bf_sort_positions
            function.argtypes = (
                ctypes.POINTER(ctypes.c_int32),
                ctypes.c_size_t,
                ctypes.c_int32,
                ctypes.POINTER(ctypes.c_uint32),
                ctypes.POINTER(ctypes.c_int32),
            )
            function.restype = ctypes.c_int32
            _library = library
            break
        except (AttributeError, OSError):
            continue
    return _library


def backend_name() -> str:
    """Return the active sorting backend without making it mandatory."""
    return "rust" if _load_library() is not None else "python"


def sort_positions(
    positions: Iterable[tuple[int, int, int]], rotation: int
) -> Optional[tuple[list[tuple[int, int, int]], array, array]]:
    """Return source positions plus sorted indices/depths, or None for fallback."""
    library = _load_library()
    if library is None or rotation not in range(4):
        return None
    position_list = list(positions)
    count = len(position_list)
    if not count:
        return (position_list, array("I"), array("i"))

    coordinates = array(
        "i", (coordinate for position in position_list for coordinate in position)
    )
    if coordinates.itemsize != ctypes.sizeof(ctypes.c_int32):
        return None
    indices = array("I", [0]) * count
    depths = array("i", [0]) * count
    result = library.bf_sort_positions(
        (ctypes.c_int32 * (count * 3)).from_buffer(coordinates),
        count,
        rotation,
        (ctypes.c_uint32 * count).from_buffer(indices),
        (ctypes.c_int32 * count).from_buffer(depths),
    )
    if result != 0:
        return None
    return position_list, indices, depths
