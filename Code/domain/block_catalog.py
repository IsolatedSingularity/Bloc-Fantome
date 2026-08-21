"""Block and sound definition value objects for the canonical catalog."""

from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class BlockDefinition:
    name: str
    textureTop: str
    textureSide: str
    textureBottom: str
    tintTop: bool = False
    tintSide: bool = False
    textureFront: Optional[str] = None
    transparent: bool = False
    isThin: bool = False
    isDoor: bool = False
    isLiquid: bool = False
    isStair: bool = False
    isSlab: bool = False
    isPortal: bool = False
    lightLevel: int = 0
    lightColor: Tuple[int, int, int] = (255, 200, 150)
    modelKind: Optional[str] = None


@dataclass(frozen=True)
class SoundDefinition:
    placeSound: str
    breakSound: str
