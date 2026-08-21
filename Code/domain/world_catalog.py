"""Minimal immutable block semantics required by the editable world."""

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping


@dataclass(frozen=True)
class WorldCatalog:
    """Inject block identities and light/opacity definitions into ``World``."""

    block_type: type
    air: Any
    water: Any
    lava: Any
    obsidian: Any
    cobblestone: Any
    stone: Any
    definitions: Mapping[Any, Any]

    def __post_init__(self) -> None:
        object.__setattr__(self, "definitions", MappingProxyType(dict(self.definitions)))
