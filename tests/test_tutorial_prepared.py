"""Prepared lessons preserve exact cells and transfer independent state once."""
import os,sys
from pathlib import Path
os.environ.setdefault('SDL_VIDEODRIVER','dummy');os.environ.setdefault('SDL_AUDIODRIVER','dummy')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Code'))
from blocFantome import BlocFantome
from engine.tutorial_lessons import TOUR
from engine.tutorial_prepared import load_lesson
from domain.blocks import BlockType


def test_prepared_lesson_matches_source_and_never_reuses_live_state():
    app=BlocFantome()
    try:
        step=next(s for s in TOUR if s['id']=='blocks')
        packed=load_lesson('blocks',app.world.catalog)
        assert packed is not None
        app._buildingTutorialBundle=True
        source=app._stageTourScene(step)
        assert packed.blocks==source.blocks
        assert packed.properties==source.properties
        assert packed.liquid_levels==source.liquid_levels
        assert packed.scene_metadata==source.scene_metadata
        assert packed._prepared[0].drawOrdersByMode==source._prepared[0].drawOrdersByMode
        assert packed._prepared[0].viewSurfacePositionsByView==source._prepared[0].viewSurfacePositionsByView
        before=dict(packed.blocks)
        app.world.replace(packed)
        assert not packed._prepared
        app.world.clear()
        fresh=load_lesson('blocks',app.world.catalog)
        assert fresh.blocks==before and fresh._prepared
    finally:app.worldLoadExecutor.shutdown(wait=True)


def test_prepared_lighting_matches_live_calculation_and_invalidates_after_edit():
    app=BlocFantome()
    try:
        step=next(s for s in TOUR if s['id']=='lighting')
        packed=load_lesson('lighting',app.world.catalog)
        assert packed is not None and packed._lighting
        assert packed._lighting==packed._prepared[0].calculateLighting()
        app.tutorialScreen.visible=True
        app._applyTourScene(packed,step)
        assert not app.lightingDirty
        assert app.lightMap==packed._lighting
        # The source Nether ceiling stays editable but must not obscure the
        # lesson. Use the existing terrain toggle and frame the actual ruin.
        assert app.sceneTerrainMode=='hidden'
        assert app.renderer.viewRotation==1
        assert app.sceneStructurePositions
        assert len(app.world.blocks)==len(packed.blocks)
        assert any(b==BlockType.NETHERRACK for b in app.world.blocks.values())
        low,high=app.sceneStructureBounds
        center=app.renderer.worldToScreen(*[(a+b)/2 for a,b in zip(low,high)])
        assert abs(center[0]-app.screen.get_width()/2)<1
        assert abs(center[1]-app.screen.get_height()*.445)<1
        original=dict(app.lightMap)
        position=next(p for p,b in app.world.blocks.items() if b==BlockType.GLOWSTONE)
        app._placeBlockWithUndo(*position,BlockType.AIR)
        app._afterWorldEdit((position,))
        assert app.lightingDirty
        assert app.world.calculateLighting()!=original
        assert packed._lighting==original
        fresh=load_lesson('lighting',app.world.catalog)
        assert fresh._lighting==original and fresh._lighting is not packed._lighting
    finally:app.worldLoadExecutor.shutdown(wait=True)
