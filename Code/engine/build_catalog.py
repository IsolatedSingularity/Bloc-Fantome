"""Catalog user builds and bundled showcases for the Open Build experience."""

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Mapping


CATEGORIES = ("My Builds", "Tutorials", "Nether", "End")


@dataclass(frozen=True)
class BuildEntry:
    """One loadable build or tutorial lesson."""

    key: str
    label: str
    category: str
    kind: str
    path: str = ""
    tutorial_index: int = -1


def _friendly_name(stem: str) -> str:
    if stem == "_autosave":
        return "Autosave Recovery"
    if stem.startswith("build_"):
        return "Build " + stem.removeprefix("build_").replace("_", " ")
    return stem.replace("_", " ").title()


def build_catalog(
    saves_dir: str,
    bundled_dir: str,
    tutorial_steps: Iterable[Mapping[str, object]],
) -> List[BuildEntry]:
    """Return stable, categorized entries without copying bundled content."""

    entries: List[BuildEntry] = []
    saves = Path(saves_dir)
    bundled = Path(bundled_dir)
    bundled_paths = {
        path.resolve() for path in bundled.glob("*.json")
    } if bundled.exists() else set()
    if saves.exists():
        files = set(saves.glob("*.json")) | set(saves.glob("*.json.gz"))
        for path in sorted(files, key=lambda item: item.stat().st_mtime, reverse=True):
            if path.resolve() in bundled_paths:
                continue
            stem = path.name.removesuffix(".gz").removesuffix(".json")
            entries.append(BuildEntry(
                key=f"user:{path.resolve()}",
                label=_friendly_name(stem),
                category="My Builds",
                kind="file",
                path=str(path),
            ))

    for index, step in enumerate(tutorial_steps):
        title = str(step.get("title", f"Tutorial {index + 1}"))
        entries.append(BuildEntry(
            key=f"tutorial:{index}",
            label=f"{index + 1}. {title}",
            category="Tutorials",
            kind="tutorial",
            tutorial_index=index,
        ))

    if bundled.exists():
        for path in sorted(bundled.glob("*.json")):
            stem = path.stem
            lowered = stem.lower()
            if "end_city" in lowered:
                category = "End"
            elif any(token in lowered for token in ("bastion", "nether", "warped", "portal")):
                category = "Nether"
            else:
                continue
            entries.append(BuildEntry(
                key=f"bundled:{stem}",
                label=_friendly_name(stem),
                category=category,
                kind="file",
                path=str(path),
            ))

    return entries
