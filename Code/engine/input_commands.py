"""Resolve conflicting keyboard shortcuts into editor commands.

This module is deliberately independent of Pygame. The application normalizes
events into ``KeyChord`` and a small immutable ``InputContext`` so precedence
can be tested without constructing the UI.
"""

from dataclasses import dataclass
from enum import Enum, auto


class Command(Enum):
    """Semantic actions produced by contextual keyboard input."""

    FLIP_PREVIEW_HALF = auto()
    TOGGLE_FILL = auto()
    TOGGLE_MEASUREMENT = auto()
    TOGGLE_Y_MIRROR = auto()
    TOGGLE_X_MIRROR = auto()
    START_OR_CONFIRM_SELECTION = auto()
    TOGGLE_BLUEPRINT = auto()
    HOLLOW_SELECTION = auto()
    TOGGLE_HISTORY = auto()
    TOGGLE_REPLACE = auto()
    FIT_WORLD = auto()
    CENTER_CONTEXT = auto()
    CLOSE_MODAL = auto()
    CLOSE_SEARCH = auto()
    CLOSE_HISTORY = auto()
    CLOSE_SETTINGS = auto()
    CLOSE_SHORTCUTS = auto()
    CANCEL_BLUEPRINT = auto()
    CANCEL_FILL = auto()
    CANCEL_SELECTION = auto()
    CANCEL_MEASUREMENT = auto()
    CANCEL_REPLACE = auto()
    CANCEL_STAMP = auto()
    CLOSE_TUTORIAL = auto()
    QUIT = auto()


@dataclass(frozen=True)
class KeyChord:
    """Normalized key and modifier state."""

    key: str
    ctrl: bool = False
    shift: bool = False


@dataclass(frozen=True)
class InputContext:
    """Only the editor/UI state needed to resolve conflicting commands."""

    selected_half_block: bool = False
    confirmed_selection: bool = False
    modal: bool = False
    search: bool = False
    history: bool = False
    settings: bool = False
    shortcuts: bool = False
    blueprint: bool = False
    fill: bool = False
    selection: bool = False
    measurement: bool = False
    replace: bool = False
    stamp: bool = False
    tutorial: bool = False


_ESCAPE_PRECEDENCE = (
    ("modal", Command.CLOSE_MODAL),
    ("search", Command.CLOSE_SEARCH),
    ("history", Command.CLOSE_HISTORY),
    ("settings", Command.CLOSE_SETTINGS),
    ("shortcuts", Command.CLOSE_SHORTCUTS),
    ("blueprint", Command.CANCEL_BLUEPRINT),
    ("fill", Command.CANCEL_FILL),
    ("selection", Command.CANCEL_SELECTION),
    ("measurement", Command.CANCEL_MEASUREMENT),
    ("replace", Command.CANCEL_REPLACE),
    ("stamp", Command.CANCEL_STAMP),
    ("tutorial", Command.CLOSE_TUTORIAL),
)


def resolve_command(chord: KeyChord, context: InputContext) -> Command | None:
    """Return one semantic command for a supported contextual shortcut."""

    key = chord.key.lower()
    if key == "escape":
        for field, command in _ESCAPE_PRECEDENCE:
            if getattr(context, field):
                return command
        return Command.QUIT
    if key == "f" and not chord.ctrl and not chord.shift:
        return Command.FLIP_PREVIEW_HALF if context.selected_half_block else Command.TOGGLE_FILL
    if key == "m":
        if chord.ctrl:
            return Command.TOGGLE_X_MIRROR
        if chord.shift:
            return Command.TOGGLE_Y_MIRROR
        return Command.TOGGLE_MEASUREMENT
    if key == "b" and chord.ctrl:
        return Command.TOGGLE_BLUEPRINT if chord.shift else Command.START_OR_CONFIRM_SELECTION
    if key == "h" and chord.ctrl:
        return Command.HOLLOW_SELECTION if context.confirmed_selection else Command.TOGGLE_HISTORY
    if key == "r" and chord.ctrl:
        return Command.TOGGLE_REPLACE
    if key == "home":
        return Command.CENTER_CONTEXT if chord.shift else Command.FIT_WORLD
    return None
