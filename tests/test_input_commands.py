"""Pure keyboard-command precedence and contextual shortcut tests."""

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Code"))

from engine.input_commands import Command, InputContext, KeyChord, resolve_command


def command(key, *, ctrl=False, shift=False, **context):
    return resolve_command(KeyChord(key, ctrl=ctrl, shift=shift), InputContext(**context))


def test_f_flips_half_only_for_selected_stairs_or_slabs():
    assert command("f", selected_half_block=True) is Command.FLIP_PREVIEW_HALF
    assert command("f") is Command.TOGGLE_FILL


def test_measurement_and_mirror_chords_are_distinct():
    assert command("m") is Command.TOGGLE_MEASUREMENT
    assert command("m", shift=True) is Command.TOGGLE_Y_MIRROR
    assert command("m", ctrl=True) is Command.TOGGLE_X_MIRROR


def test_selection_and_blueprint_chords_are_distinct():
    assert command("b", ctrl=True) is Command.START_OR_CONFIRM_SELECTION
    assert command("b", ctrl=True, shift=True) is Command.TOGGLE_BLUEPRINT


def test_hollow_requires_an_active_confirmed_selection():
    assert command("h", ctrl=True, confirmed_selection=True) is Command.HOLLOW_SELECTION
    assert command("h", ctrl=True) is Command.TOGGLE_HISTORY


def test_replace_and_home_chords_are_distinct():
    assert command("r", ctrl=True) is Command.TOGGLE_REPLACE
    assert command("home") is Command.FIT_WORLD
    assert command("home", shift=True) is Command.CENTER_CONTEXT


def test_escape_closes_only_the_highest_priority_context():
    ordered = (
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
    active = {name: True for name, _ in ordered}
    for name, expected in ordered:
        assert command("escape", **active) is expected
        active[name] = False
    assert command("escape") is Command.QUIT
