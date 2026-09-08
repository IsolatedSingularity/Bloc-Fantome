import math
import os

import pygame

from runtime_paths import WORLD_MAP_DIR
from ui.world_map import MISSION_MARKER_SCALE, QUESTION_REGISTRATION, WorldMapView


def setup_module():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.display.init()
    pygame.font.init()
    pygame.display.set_mode((1, 1))


def teardown_module():
    pygame.font.quit()
    pygame.display.quit()


def _view():
    return WorldMapView(
        WORLD_MAP_DIR,
        pygame.font.Font(None, 28),
        pygame.font.Font(None, 18),
    )


def test_director_edge_key_restores_transparency_and_visible_arrows():
    view = _view()
    for name in ("prev_world_arrow", "next_world_arrow"):
        arrow = view._scaled(name, 1)
        alphas = [
            arrow.get_at((x, y)).a
            for y in range(arrow.get_height())
            for x in range(arrow.get_width())
        ]
        assert min(alphas) == 0
        assert max(alphas) == 255
        assert 0 < sum(alpha > 0 for alpha in alphas) < len(alphas)


def test_question_marker_composes_the_exact_recovered_worldbuilder_layers():
    view = _view()
    marker = view._question(1)
    assert view._surfaces["question_mark"].get_size() == (20, 27)
    assert view._surfaces["question_mark_shadow"].get_size() == (15, 8)
    assert view._surfaces["question_mark_blink"].get_size() == (48, 42)
    assert marker.get_size() == (20, 27)
    assert marker.get_at((0, 0)).a == 0
    colors = {
        tuple(marker.get_at((x, y))[:3])
        for y in range(marker.get_height())
        for x in range(marker.get_width())
        if marker.get_at((x, y)).a
    }
    assert (207, 246, 239) in colors
    assert (109, 173, 162) in colors
    assert (0, 0, 0) in colors
    shadow_colors = {
        tuple(view._surfaces["question_mark_shadow"].get_at((x, y))[:3])
        for y in range(view._surfaces["question_mark_shadow"].get_height())
        for x in range(view._surfaces["question_mark_shadow"].get_width())
        if view._surfaces["question_mark_shadow"].get_at((x, y)).a
    }
    assert (3, 170, 12) in shadow_colors
    assert QUESTION_REGISTRATION == {
        "question_mark": (18, 12),
        "question_mark_blink": (32, 27),
        "question_mark_shadow": (15, -17),
    }
    assert any(
        marker.get_at((x, y)).a
        for y in range(marker.get_height())
        for x in range(marker.get_width())
    )
    assert view.worldbuilder_font is not None
    title = view._text("WORLD MAP?", (255, 255, 255), scale=2)
    assert title.get_height() == 10


def test_question_marker_uses_director_registration_idle_orbit_and_hover_clock(monkeypatch):
    view = _view()
    screen = pygame.Surface((220, 180), pygame.SRCALPHA)

    monkeypatch.setattr(pygame.time, "get_ticks", lambda: 0)
    normal = view._draw_marker(
        screen, (100, 100), completed=False, active=True, phase=0
    )
    assert normal == pygame.Rect(80, 85, 25, 46)

    screen.fill((0, 0, 0, 0))
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: 200)
    blink = view._draw_marker(
        screen, (100, 100), completed=False, active=True, hovered=True, phase=0
    )
    assert blink == pygame.Rect(62, 67, 60, 64)
    assert blink.width > normal.width


def test_displayed_question_marker_is_25_percent_larger_without_changing_source_cast():
    view = _view()
    assert MISSION_MARKER_SCALE == 1.25
    assert view._surfaces["question_mark"].get_size() == (20, 27)
    assert view._question(MISSION_MARKER_SCALE).get_size() == (25, 34)


def test_dimension_tabs_are_real_hit_targets():
    view = _view()
    view.dimension_rects = {"end": pygame.Rect(200, 100, 80, 36)}
    action = view.handle_event(
        pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(220, 118))
    )
    assert action == "dimension:end"


def test_region_controls_and_original_route_indices_remain_distinct():
    from types import SimpleNamespace
    view=_view()
    view.region_rects={'fortress':pygame.Rect(20,110,200,30)}
    assert view.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=(40,120)))=='region:fortress'
    view.scene=SimpleNamespace(route_indices=(1,))
    view.node_hit_rects=[pygame.Rect(400,300,40,40)]
    assert view.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=(410,310)))=='start:1'


def test_close_zoom_pan_translates_cached_source_geometry():
    from types import SimpleNamespace
    from ui.source_map import SourceMap
    source = SourceMap('overworld','plains')
    renderer = SimpleNamespace(zoomLevel=1.0,offsetX=20,offsetY=20)
    screen = pygame.Surface((960,640))
    source.render(screen,renderer)
    cached = source.surface
    renderer.offsetX += 12
    renderer.offsetY += 6
    source.render(screen,renderer)
    assert source.surface is cached


def test_dimension_ambience_moves_with_time_without_covering_large_areas(monkeypatch):
    view=_view()
    for dimension in ('overworld','nether','end'):
        view.dimension=dimension
        surface=pygame.Surface((960,640),pygame.SRCALPHA)
        monkeypatch.setattr(pygame.time,'get_ticks',lambda:100)
        view._render_dimension_ambience(surface)
        first=pygame.image.tobytes(surface,'RGBA')
        assert 0<pygame.mask.from_surface(surface).count()<200
        surface.fill((0,0,0,0))
        monkeypatch.setattr(pygame.time,'get_ticks',lambda:1100)
        view._render_dimension_ambience(surface)
        assert first!=pygame.image.tobytes(surface,'RGBA')


def test_map_markers_cannot_paint_or_click_through_navigation():
    from types import SimpleNamespace
    from engine.world_map import MapScene
    view=_view()
    surface=pygame.Surface((960,640))
    scene=MapScene('overworld','Survey','',((400,600,0),),(),('Route',),((0,0,0),(10,10,10)),())
    view.set_hub('overworld',scene)
    renderer=SimpleNamespace(worldToScreen=lambda x,y,z:(x,y))
    view.render_hub(surface,renderer,{})
    assert not view.node_hit_rects[0]
    scene=MapScene('overworld','Survey','',((400,350,0),),(),('Route',),((0,0,0),(10,10,10)),())
    view.set_hub('overworld',scene)
    view.render_hub(surface,renderer,{})
    assert view.node_hit_rects[0]


def test_ocean_locked_map_has_no_clickable_level_node():
    view = _view()
    view.node_rects = []
    view.node_hit_rects = []
    view.node_rect = pygame.Rect(0, 0, 0, 0)
    view.node_hit_rect = pygame.Rect(0, 0, 0, 0)
    action = view.handle_event(
        pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(500, 400))
    )
    assert action is None


def test_hover_sound_fires_once_per_entry_across_larger_hit_target():
    view = _view()
    view.node_hit_rect = pygame.Rect(100, 100, 60, 60)
    view.node_hit_rects = [view.node_hit_rect]
    played = []
    view.play = played.append
    view.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=(110, 110)))
    view.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=(120, 120)))
    view.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=(10, 10)))
    view.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=(130, 130)))
    assert played == ["hover_1", "hover_1"]


def test_ocean_placeholders_hover_but_do_not_open_empty_levels():
    view = _view()
    view.dimension = "ocean"
    view.node_hit_rects = [pygame.Rect(100, 100, 60, 60)]
    played = []
    view.play = played.append
    view.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=(110, 110)))
    action = view.handle_event(
        pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(110, 110))
    )
    assert played == ["hover_1"]
    assert action is None
    assert view._mission_copy("ocean", 0) == ("COMING SOON", "ANCIENT RUINS")


def test_hover_copy_uses_worldbuilder_mission_language():
    view = _view()
    assert view._mission_copy("overworld", 0) == (
        "MISSION 1", "REPAIR", "PLAINS HOUSE",
    )
    assert view._mission_copy("nether", 1) == (
        "MISSION 2", "REPAIR", "THE FORTRESS",
    )


def test_each_map_uses_the_approved_texture_derived_traveler_pair():
    view = _view()
    for dimension in ("overworld", "nether", "end", "ocean"):
        view.dimension = dimension
        first = view._traveler_sprite(0)
        second = view._traveler_sprite(1)
        assert first.get_size() != (13, 10)
        assert second.get_size() != (13, 10)
        for sprite in (first, second):
            colors = {
                tuple(sprite.get_at((x, y))[:3])
                for y in range(sprite.get_height())
                for x in range(sprite.get_width())
                if sprite.get_at((x, y)).a
            }
            assert len(colors) >= 3


def test_open_traveler_routes_reverse_continuously_instead_of_teleporting():
    route = ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (2.0, 1.0, 0.0))
    period = 4.0 / 0.18
    before, _ = WorldMapView._traveler_state(route, 0, period - 0.001)
    after, _ = WorldMapView._traveler_state(route, 0, period + 0.001)
    assert math.dist(before, after) < 0.001
