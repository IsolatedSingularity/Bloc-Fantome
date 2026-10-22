"""Event semantics and effects level on real editable world interactions."""
from unittest.mock import patch
import blocFantome as b
from test_workshop_production import app, reset


def test_fluid_edit_pools_exclude_continuous_ambience(app):
    for block,material in ((b.BlockType.WATER,'water'),(b.BlockType.LAVA,'lava')):
        for placed,event in ((True,'place'),(False,'break')):
            with patch.object(app.assetManager,'playSound') as play:
                app.assetManager.playBlockSound(block,isPlace=placed,worldPos=(2,3,4),effectsVolume=.25)
            assert play.call_args.args==(material+'_'+event,(2,3,4),.25)
            assert app.assetManager.sounds[material+'_'+event]
            assert not set(app.assetManager.sounds[material+'_'+event]).intersection(app.assetManager.sounds[material])


def test_comparator_change_clicks_once_and_failed_button_stays_silent(app):
    app.world.setBlock(2,3,1,b.BlockType.COMPARATOR)
    with patch.object(app,'_playRedstoneSound') as play:
        assert app._interactBlock(2,3,1)
        play.assert_called_once_with('redstone_click',(2,3,1))
    app.world.setBlock(2,3,1,b.BlockType.STONE_BUTTON)
    with patch.object(app.redstone,'press_button',return_value=False),patch.object(app,'_playRedstoneSound') as play:
        assert not app._interactBlock(2,3,1)
        play.assert_not_called()


def test_door_interaction_uses_effects_gain(app):
    app.effectsVolume=.2
    with patch.object(app.assetManager,'playOneShot') as play:
        app.assetManager.playDoorSound(True,b.BlockType.OAK_DOOR,effectsVolume=app.effectsVolume)
    assert abs(play.call_args.kwargs['volume']-.16)<1e-8
    app.effectsVolume=.8
