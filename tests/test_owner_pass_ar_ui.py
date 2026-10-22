"""Approved A-R navigation, responsive galleries and non-destructive shrink."""
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


def test_shrink_refuses_occupied_bounds_without_modal_or_mutation(app):
    app.world.resize(96,96,96,preserve=False);app.world.setBlock(0,0,0,b.BlockType.DIAMOND_BLOCK)
    before=dict(app.world.blocks);dimensions=(app.world.width,app.world.depth,app.world.height)
    app.workshop.act('shrink',app)
    assert app.workshop.confirm is None
    assert app.world.blocks==before and dimensions==(app.world.width,app.world.depth,app.world.height)
    assert app.workshop.status


def test_quiet_hud_retains_no_identity_panel(app):
    shell=app.workshop;shell.visibility.last_activity=-100;shell.last_time=-100
    with patch('pygame.mouse.get_pos',return_value=(500,400)),patch('pygame.mouse.get_pressed',return_value=(False,False,False)):
        shell.render(app)
    assert not any(rect.x==24 and rect.y>400 for rect in shell.panels)
    assert not any(a in ('fill','nav:tools','half','turn') for _,a,_ in shell.hits)
