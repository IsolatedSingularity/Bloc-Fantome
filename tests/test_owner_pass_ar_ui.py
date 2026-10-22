"""Approved A-R navigation, responsive galleries and reversible shrink."""
import pygame
from unittest.mock import patch
from test_workshop_production import app, reset
from ui.fonts import set_text_scale
import blocFantome as b


def test_build_has_vertical_rail_and_compact_category_step(app):
    shell=app.workshop;shell.page='build';shell.render(app)
    categories=[r for r,a,e in shell.hits if a.startswith('category:')]
    assert len(categories)>2 and len({r.x for r in categories})==1
    assert not any(a=='category_next' for _,a,_ in shell.hits)
    app._applyWindowSize(960,640);set_text_scale(1.5);shell.text_scale=1.5
    shell.render(app)
    assert any(a=='categories' for _,a,_ in shell.hits)
    shell.act('categories',app);shell.render(app)
    assert any(a=='category:Favorites' for _,a,_ in shell.hits)
    assert not any(a.startswith('block:') for _,a,_ in shell.hits)


def test_library_home_and_back_never_mutate_world(app):
    library=app.library;before=dict(app.world.blocks);library.open(app);library.render(app)
    assert library.home and len(library.tab_rects)==4 and not library.rows
    rect=library.tab_rects['Structures']
    library.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=rect.center),app)
    assert not library.home and library.tab=='Structures'
    library.render(app)
    library.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=library.back_rect.center),app)
    assert library.home and app.world.blocks==before


def test_shrink_is_immediate_without_warning_and_restorable(app):
    app.world.resize(96,96,96,preserve=False);app.world.setBlock(0,0,0,b.BlockType.DIAMOND_BLOCK)
    before=dict(app.world.blocks);dimensions=(app.world.width,app.world.depth,app.world.height)
    app.workshop.act('shrink',app)
    assert app.workshop.confirm is None
    assert (app.world.width,app.world.depth,app.world.height)==(80,80,80)
    assert not app.workshop.status and not app.tooltipText
    assert app.undoManager.undo() is not None
    assert app.world.blocks==before and dimensions==(app.world.width,app.world.depth,app.world.height)


def test_library_close_never_overlaps_hovered_saved_tile(app):
    for size,scale in (((1200,800),1),((960,640),1.5),((1920,1080),1.25)):
        app._applyWindowSize(*size);set_text_scale(scale);app.workshop.text_scale=scale
        app.library.open(app);app.library._morph_from=None;app.library.render(app)
        close=app.library.close_rect.copy()
        assert all(not close.colliderect(r) for r in app.library.tab_rects.values())
        with patch('pygame.mouse.get_pos',return_value=app.library.tab_rects['Saved Builds'].center):
            app.library.render(app)
        assert app.library.close_rect==close


def test_canvas_previews_use_real_renderers_and_noise_click_uses_preview(app):
    app._createInitialFloor();shell=app.workshop
    for rect,action in shell.canvas_controls(app.screen.get_size()):
        method='_renderTerrainNoisePreview' if action=='noise' else '_renderCanvasResizePreview'
        with patch('pygame.mouse.get_pos',return_value=rect.center),patch.object(app,method,wraps=getattr(app,method)) as preview:
            shell.render(app);shell.render(app)
            assert preview.call_count==1  # Stationary previews reuse their transparent surface.
        if action=='noise':
            plan=app._terrainNoisePreviewPlan;seed=app._terrainNoisePreviewSeed
            shell.act('noise',app)
            assert app.sceneMetadata['terrain_noise_seed']==seed
            assert all(app.world.getHighestBlock(x,y)==plan['base_z']+z for x,y,z in plan['columns'])
    with patch('pygame.mouse.get_pos',return_value=(500,400)):
        shell.render(app)
    assert app._terrainNoisePreviewSeed is None


def test_held_block_is_visible_with_awake_hud_and_nav_spacing_is_even(app):
    shell=app.workshop;shell.visibility.pinned=True;shell.render(app)
    assert shell.context in shell.panels and shell.context.width>100
    right=[r for r,a,e in shell.hits if a in ('nav:tools','save','nav:menu')]
    assert right[1].left-right[0].right==right[2].left-right[1].right==4
    assert len({r.centery for r in right})==1


def test_held_block_is_anchored_without_overlapping_hotbar_at_large_text(app):
    app.selectedBlock=b.BlockType.OAK_STAIRS
    for size,scale in (((1200,800),1),((960,640),1.5)):
        app._applyWindowSize(*size);set_text_scale(scale);app.workshop.text_scale=scale
        shell=app.workshop;shell.visibility.pinned=True;shell.page='world';shell.render(app)
        assert shell.context.bottom==size[1]-10 and shell.context.left==24
        assert not shell.context.colliderect(shell.hotbar_bounds)
        assert app.screen.get_rect().contains(shell.context)


def test_floating_grid_is_archived_outside_current_editor(app):
    app.showGrid=True;app.screen.fill((11,17,23))
    before=pygame.image.tostring(app.screen,'RGBA')
    app._renderGrid()
    assert pygame.image.tostring(app.screen,'RGBA')==before
    assert not any(field=='showGrid' for _,field,_ in app._settingsLayout()[2])
    assert 'grid' not in {row[0] for row in __import__('ui.workshop_actions',fromlist=['TOOLS']).TOOLS}
    app.workshop.legacy=True;app._renderGrid()
    assert pygame.image.tostring(app.screen,'RGBA')!=before


def test_rounded_controls_keep_uniform_rgb_through_antialiased_corners():
    import numpy as np
    from ui import chrome
    for alpha in (225,255):
        surface=pygame.Surface((180,60),pygame.SRCALPHA)
        chrome.rounded(surface,(*chrome.CONTROL,alpha),surface.get_rect(),12)
        pixels=pygame.surfarray.array3d(surface);coverage=pygame.surfarray.array_alpha(surface)
        assert np.all(pixels[coverage>0]==chrome.CONTROL)
        assert coverage[90,30]==alpha and 0<coverage.min()+coverage.max()


def test_resize_undo_retains_fluids_properties_metadata_coordinates_and_history(app):
    from copy import deepcopy
    from engine.undo import PlaceBlockCommand
    edge=(31,31,2);inside=(16,16,2)
    app.world.setBlock(*edge,b.BlockType.WATER)
    app.world.liquidLevels[edge]=6;app.world.liquidSources.add(edge);app.world.liquidFalling.add(edge)
    app.sceneStructurePositions={edge};app.sceneExteriorGlassPositions={edge}
    app.sceneMetadata={'name':'Resize specimen','nested':{'kept':True}}
    app.selectionStart=edge;app.snowLayers={edge:2}
    assert app.undoManager.execute(PlaceBlockCommand(app.world,*inside,b.BlockType.OAK_STAIRS,b.BlockProperties()))
    before=dict(app.world.blocks);properties=deepcopy(app.world.blockProperties)
    app._resizeCanvas(-16)
    after=dict(app.world.blocks)
    assert app.selectionStart is None and not app.snowLayers
    for _ in range(2):
        assert app.undoManager.undo()
        assert app.world.blocks==before and app.world.blockProperties==properties
        assert app.world.liquidLevels[edge]==6
        assert edge in app.world.liquidSources and edge in app.world.liquidFalling
        assert app.sceneStructurePositions==app.sceneExteriorGlassPositions=={edge}
        assert app.selectionStart==edge and app.snowLayers=={edge:2}
        assert app.sceneMetadata=={'name':'Resize specimen','nested':{'kept':True}}
        assert app.undoManager.redo() and app.world.blocks==after
    assert app.undoManager.undo() and app.undoManager.undo()
    assert app.world.getBlock(*inside)==b.BlockType.AIR


def test_quiet_hud_retains_no_identity_panel(app):
    shell=app.workshop;shell.visibility.last_activity=-100;shell.last_time=-100
    with patch('pygame.mouse.get_pos',return_value=(500,400)),patch('pygame.mouse.get_pressed',return_value=(False,False,False)):
        shell.render(app)
    assert not any(rect.x==24 and rect.y>400 for rect in shell.panels)
    assert not any(a in ('fill','nav:tools','half','turn') for _,a,_ in shell.hits)
