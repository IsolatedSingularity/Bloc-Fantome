"""Minecraft-styled World Map presentation using recovered WorldBuilder media."""

from __future__ import annotations

from collections import deque
import math
import os
from typing import Mapping

import pygame


DIMENSION_LABELS = {
    "overworld": "OVERWORLD",
    "nether": "NETHER",
    "end": "THE END",
    "ocean": "DEEP OCEAN",
}
DIMENSION_COLORS = {
    "overworld": (126, 184, 88),
    "nether": (196, 80, 72),
    "end": (180, 144, 211),
    "ocean": (70, 174, 202),
}
MISSION_MARKER_SCALE = 1.25

# Director positions sprites by their cast registration point, not by image
# centre. These values come from the preserved World Builder CASt chunks.
QUESTION_REGISTRATION = {
    "question_mark": (18, 12),
    "question_mark_blink": (32, 27),
    "question_mark_shadow": (15, -17),
}
QUESTION_SOURCE_SIZES = {
    "question_mark": (20, 27),
    "question_mark_blink": (48, 42),
    "question_mark_shadow": (15, 8),
}

TRAVELER_TEXTURES = {
    "overworld": (
        ("villager/villager.png", (8, 8, 8, 10), (12, 15)),
        ("bee/bee.png", (8, 8, 8, 8), (14, 12)),
    ),
    "nether": (
        ("strider/strider.png", (16, 16, 16, 16), (16, 14)),
        ("blaze.png", (8, 8, 8, 8), (14, 14)),
    ),
    "end": (
        ("shulker/shulker.png", (0, 52, 16, 12), (14, 14)),
        ("endermite.png", (0, 0, 8, 8), (14, 10)),
    ),
    "ocean": (
        ("fish/cod.png", (0, 0, 12, 6), (16, 10)),
        ("fish/salmon.png", (0, 0, 12, 6), (17, 10)),
    ),
}


class WorldBuilderBitmapFont:
    """Render the recovered 5x5 WorldBuilder font without smoothing it."""

    def __init__(self, sheet: pygame.Surface):
        self.glyphs: dict[str, pygame.Surface] = {}
        rows = (
            ("ABCDEFGHI", (22, 33, 44, 55, 66, 77, 88, 99, 110), 38),
            ("JKLM", (119, 130, 141, 152), 38),
            ("NOPQRSTUVWXYZ", tuple(22 + index * 11 for index in range(13)), 48),
            ("0123456789", (22, 33, 42, 53, 64, 75, 86, 97, 108, 119), 58),
        )
        for characters, positions, y in rows:
            for character, x in zip(characters, positions):
                self.glyphs[character] = sheet.subsurface((x, y, 5, 5)).copy()
        for character, x in (("!", 22), ("?", 29), ("-", 40), ("_", 51), ("=", 60)):
            self.glyphs[character] = sheet.subsurface((x, 68, 5, 5)).copy()

    def render(self, text: str, color: tuple[int, int, int], scale: int = 2) -> pygame.Surface:
        text = text.upper()
        scale = max(1, int(scale))
        advance = 6 * scale
        result = pygame.Surface((max(1, len(text) * advance - scale), 5 * scale), pygame.SRCALPHA)
        for index, character in enumerate(text):
            glyph = self.glyphs.get(character)
            if glyph is None:
                continue
            tinted = pygame.Surface((5, 5), pygame.SRCALPHA)
            for y in range(5):
                for x in range(5):
                    source = glyph.get_at((x, y))
                    darkness = 255 - max(source.r, source.g, source.b)
                    if darkness > 64:
                        tinted.set_at((x, y), (*color, darkness))
            result.blit(pygame.transform.scale(tinted, (5 * scale, 5 * scale)), (index * advance, 0))
        return result


class WorldMapView:
    """Render and hit-test the map selector without owning editor state."""

    def __init__(
        self,
        root: str,
        font: pygame.font.Font,
        small_font: pygame.font.Font,
        audio_router=None,
        asset_manager=None,
    ):
        self.root = root
        self.font = font
        self.small_font = small_font
        self.audio_router = audio_router
        self.asset_manager = asset_manager
        self.mode = "hub"
        self.dimension = "overworld"
        self.scene = None
        self.objective = None
        self.completed_now = False
        self.node_rect = pygame.Rect(0, 0, 0, 0)
        self.node_hit_rect = pygame.Rect(0, 0, 0, 0)
        self.node_rects: list[pygame.Rect] = []
        self.node_hit_rects: list[pygame.Rect] = []
        self.back_rect = pygame.Rect(0, 0, 0, 0)
        self.previous_rect = pygame.Rect(0, 0, 0, 0)
        self.next_rect = pygame.Rect(0, 0, 0, 0)
        self.continue_rect = pygame.Rect(0, 0, 0, 0)
        self.dimension_rects: dict[str, pygame.Rect] = {}
        self._hovered_node: int | None = None
        self._surfaces: dict[str, pygame.Surface] = {}
        self._scaled_cache: dict[tuple, pygame.Surface] = {}
        self._sounds = {}
        self._ocean_overlays: dict[tuple[int, int], pygame.Surface] = {}
        self._traveler_sprites: dict[tuple[str, int], pygame.Surface] = {}
        self._dragon_texture = None
        self.worldbuilder_font = None
        self._load_assets()

    @staticmethod
    def _edge_key(surface: pygame.Surface) -> pygame.Surface:
        """Restore the edge transparency supplied by Director's old ink mode."""
        result = surface.convert_alpha()
        width, height = result.get_size()
        if width == 0 or height == 0:
            return result
        pixels = pygame.PixelArray(result)
        source = pixels[0, 0]
        source_color = result.unmap_rgb(source)
        target = tuple(source_color[:3])
        pixels.close()

        queue = deque()
        seen: set[tuple[int, int]] = set()
        for x in range(width):
            queue.append((x, 0))
            queue.append((x, height - 1))
        for y in range(height):
            queue.append((0, y))
            queue.append((width - 1, y))
        while queue:
            x, y = queue.popleft()
            if (x, y) in seen:
                continue
            seen.add((x, y))
            color = result.get_at((x, y))
            if max(abs(color[index] - target[index]) for index in range(3)) > 4:
                continue
            result.set_at((x, y), (*color[:3], 0))
            if x:
                queue.append((x - 1, y))
            if x + 1 < width:
                queue.append((x + 1, y))
            if y:
                queue.append((x, y - 1))
            if y + 1 < height:
                queue.append((x, y + 1))
        return result

    @staticmethod
    def _tint_sprite(surface: pygame.Surface, color: tuple[int, int, int]) -> pygame.Surface:
        result = surface.copy()
        for y in range(result.get_height()):
            for x in range(result.get_width()):
                alpha = result.get_at((x, y)).a
                if alpha:
                    result.set_at((x, y), (*color, alpha))
        return result

    @staticmethod
    def _largest_component(surface: pygame.Surface) -> pygame.Surface:
        """Extract the question body while leaving Director blink rays separate."""
        width, height = surface.get_size()
        opaque = {
            (x, y)
            for y in range(height)
            for x in range(width)
            if surface.get_at((x, y)).a > 0
        }
        components: list[set[tuple[int, int]]] = []
        while opaque:
            component = set()
            queue = deque((opaque.pop(),))
            while queue:
                point = queue.popleft()
                component.add(point)
                x, y = point
                for neighbor in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                    if neighbor in opaque:
                        opaque.remove(neighbor)
                        queue.append(neighbor)
            components.append(component)
        if not components:
            return pygame.Surface((1, 1), pygame.SRCALPHA)
        body = max(components, key=len)
        bounds = pygame.Rect(min(x for x, _ in body), min(y for _, y in body), 1, 1)
        bounds.unionall_ip([pygame.Rect(x, y, 1, 1) for x, y in body])
        result = pygame.Surface(bounds.size, pygame.SRCALPHA)
        for x, y in body:
            result.set_at((x - bounds.x, y - bounds.y), surface.get_at((x, y)))
        return result

    def _load_assets(self) -> None:
        ui_root = os.path.join(self.root, "ui")
        names = [
            "question_mark", "question_mark_blink", "question_mark_rollover_blink",
            "question_mark_shadow",
            "flag_rollover_blink", "next_world_arrow", "prev_world_arrow",
            "worldbuilder_title",
        ] + [f"flag{i}" for i in range(1, 7)] + [f"bonus_flag{i}" for i in range(1, 7)]
        for name in names:
            path = os.path.join(ui_root, f"{name}.png")
            if not os.path.isfile(path):
                continue
            try:
                loaded = pygame.image.load(path).convert_alpha()
                if name in {
                    "question_mark", "question_mark_blink", "question_mark_shadow",
                }:
                    # These low-bit indexed members are exported from the raw
                    # BITD/CLUT chunks with their real palette and alpha. Do not
                    # key, recolour, or derive a silhouette from them.
                    self._surfaces[name] = loaded
                else:
                    self._surfaces[name] = self._edge_key(loaded)
            except pygame.error:
                pass

        font_path = os.path.join(ui_root, "font_extended.png")
        if os.path.isfile(font_path):
            try:
                self.worldbuilder_font = WorldBuilderBitmapFont(
                    pygame.image.load(font_path).convert_alpha()
                )
            except pygame.error:
                self.worldbuilder_font = None

        dragon_candidates = (
            os.path.join(ui_root, "enderdragon.png"),
            os.path.abspath(os.path.join(
                self.root, "..", "..", "Extensive Library", "textures",
                "entity", "enderdragon", "dragon.png",
            )),
        )
        for path in dragon_candidates:
            if not os.path.isfile(path):
                continue
            try:
                self._dragon_texture = pygame.image.load(path).convert_alpha()
                break
            except pygame.error:
                pass

        audio_root = os.path.join(self.root, "audio")
        sound_files = {
            "hover_1": "s_rollover_1.mp3",
            "hover_2": "s_rollover_2.mp3",
            "click": "s_button_click_2.mp3",
            "plan": "s_plan_click_2.mp3",
            "complete": "s_goal_mission_4.mp3",
            "bonus": "s_goal_bonus_2.mp3",
        }
        if pygame.mixer.get_init() is not None:
            for name, filename in sound_files.items():
                try:
                    path = os.path.join(audio_root, filename)
                    if os.path.isfile(path):
                        self._sounds[name] = pygame.mixer.Sound(path)
                except pygame.error:
                    pass

    def set_hub(self, dimension: str, scene) -> None:
        self.mode = "hub"
        self.dimension = dimension
        self.scene = scene
        self.objective = None
        self.completed_now = False
        self._hovered_node = None

    def set_level(self, dimension: str, objective) -> None:
        self.mode = "level"
        self.dimension = dimension
        self.objective = objective
        self.completed_now = False

    def mark_complete(self) -> None:
        if self.completed_now:
            return
        self.completed_now = True
        self.play("complete")

    def play(self, name: str) -> None:
        sound = self._sounds.get(name)
        if sound is None:
            return
        if self.audio_router is not None:
            self.audio_router.play(sound, group="ui", volume=0.75, replace=True)
        else:
            sound.play()

    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.MOUSEMOTION and self.mode == "hub":
            hovered = next(
                (index for index, rect in enumerate(self.node_hit_rects) if rect.collidepoint(event.pos)),
                None,
            )
            if hovered is not None and hovered != self._hovered_node:
                self.play("hover_1")
            self._hovered_node = hovered
            return None
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return None
        if self.back_rect.collidepoint(event.pos):
            self.play("click")
            return "hub" if self.mode == "level" else "exit"
        if self.mode == "hub":
            if self.previous_rect.collidepoint(event.pos):
                self.play("click")
                return "previous"
            if self.next_rect.collidepoint(event.pos):
                self.play("click")
                return "next"
            for dimension, rect in self.dimension_rects.items():
                if rect.collidepoint(event.pos):
                    self.play("click")
                    return f"dimension:{dimension}"
            for index, rect in enumerate(self.node_hit_rects):
                if rect.collidepoint(event.pos):
                    if self.dimension == "ocean":
                        return None
                    self.play("plan")
                    return f"start:{index}"
        elif self.completed_now and self.continue_rect.collidepoint(event.pos):
            self.play("click")
            return "hub"
        return None

    def _text(self, text: str, color: tuple[int, int, int], *, scale: int = 2, fallback=None):
        if self.worldbuilder_font is not None:
            return self.worldbuilder_font.render(text, color, scale)
        return (fallback or self.small_font).render(text, True, color)

    @staticmethod
    def _panel(
        screen: pygame.Surface,
        rect: pygame.Rect,
        fill=(24, 25, 28, 232),
        border=(125, 126, 132),
    ) -> None:
        """Square, beveled Minecraft inventory-style panel."""
        shade = pygame.Surface(rect.size, pygame.SRCALPHA)
        shade.fill(fill)
        screen.blit(shade, rect)
        pygame.draw.rect(screen, (12, 12, 14), rect, 3)
        pygame.draw.line(screen, border, rect.topleft, (rect.right - 1, rect.top), 2)
        pygame.draw.line(screen, border, rect.topleft, (rect.left, rect.bottom - 1), 2)
        pygame.draw.line(screen, (48, 48, 53), (rect.left + 2, rect.bottom - 2), (rect.right - 2, rect.bottom - 2), 2)
        pygame.draw.line(screen, (48, 48, 53), (rect.right - 2, rect.top + 2), (rect.right - 2, rect.bottom - 2), 2)

    def _button(self, screen: pygame.Surface, rect: pygame.Rect, label: str, *, strong=False) -> None:
        hovered = rect.collidepoint(pygame.mouse.get_pos())
        fill = (
            (91, 72, 34) if strong
            else ((58, 52, 41) if hovered else (34, 35, 39))
        )
        pygame.draw.rect(screen, fill, rect)
        border = (239, 179, 55) if hovered or strong else (122, 112, 86)
        pygame.draw.rect(screen, border, rect, 2)
        pygame.draw.line(
            screen, (17, 18, 21), (rect.left + 2, rect.bottom - 2),
            (rect.right - 2, rect.bottom - 2), 1,
        )
        if label:
            rendered = self._text(
                label,
                (255, 235, 170) if hovered or strong else (217, 217, 220),
                scale=2,
            )
            screen.blit(rendered, rendered.get_rect(center=rect.center))

    @staticmethod
    def _scaled_size(value: int, scale: float) -> int:
        return max(1, int(value * scale + 0.5))

    def _scaled(self, name: str, scale: float = 2, tint=None):
        source = self._surfaces.get(name)
        if source is None:
            return None
        key = (name, scale, tint)
        cached = self._scaled_cache.get(key)
        if cached is not None:
            return cached
        if tint is not None:
            source = self._tint_sprite(source, tint)
        size = (
            self._scaled_size(source.get_width(), scale),
            self._scaled_size(source.get_height(), scale),
        )
        cached = pygame.transform.scale(source, size)
        self._scaled_cache[key] = cached
        return cached

    def _question(self, scale: float, *, active: bool = True) -> pygame.Surface:
        """Return the palette-correct normal World Builder question cast."""
        key = ("source-question", scale, active)
        cached = self._scaled_cache.get(key)
        if cached is not None:
            return cached
        source = self._surfaces.get("question_mark")
        if source is None:
            color = (18, 18, 18) if active else (104, 104, 108)
            cached = self._text("?", color, scale=max(2, round(scale)))
            self._scaled_cache[key] = cached
            return cached
        low = source.copy()
        if not active:
            low.set_alpha(170)
        cached = pygame.transform.scale(
            low,
            (
                self._scaled_size(low.get_width(), scale),
                self._scaled_size(low.get_height(), scale),
            ),
        )
        self._scaled_cache[key] = cached
        return cached

    @staticmethod
    def _registered_rect(
        surface: pygame.Surface, name: str, location: tuple[int, int]
    ) -> pygame.Rect:
        reg_x, reg_y = QUESTION_REGISTRATION[name]
        source_width, source_height = QUESTION_SOURCE_SIZES[name]
        reg_x = round(reg_x * surface.get_width() / source_width)
        reg_y = round(reg_y * surface.get_height() / source_height)
        return surface.get_rect(topleft=(location[0] - reg_x, location[1] - reg_y))

    def _draw_marker(
        self,
        screen: pygame.Surface,
        anchor: tuple[int, int],
        *,
        completed: bool,
        active: bool,
        hovered: bool = False,
        bonus: bool = False,
        phase: int = 0,
    ) -> pygame.Rect:
        now = pygame.time.get_ticks()
        x = int(anchor[0])
        y = int(anchor[1])

        if completed:
            prefix = "bonus_flag" if bonus else "flag"
            marker = self._scaled(f"{prefix}{1 + (now // 120) % 6}", 1)
        else:
            marker = self._question(MISSION_MARKER_SCALE, active=active)
        if marker is None:
            marker = self.font.render("!" if completed else "?", True, (226, 54, 48) if completed else (255, 224, 72))

        if completed:
            rect = marker.get_rect(center=(x, y))
            screen.blit(marker, rect)
            return rect

        # World Builder's available mission markers orbit their authored point
        # by two pixels. The shadow shares only the horizontal motion.
        theta = 2.0 * math.pi * ((phase % 6) / 6.0 + now / 1800.0)
        body_location = (x + round(2.0 * math.cos(theta)), y + round(2.0 * math.sin(theta)))
        shadow_location = (x + round(2.0 * math.cos(theta)), y)

        shadow = self._scaled("question_mark_shadow", MISSION_MARKER_SCALE)
        shadow_rect = None
        if shadow is not None:
            if not active:
                shadow = shadow.copy()
                shadow.set_alpha(70)
            shadow_rect = self._registered_rect(shadow, "question_mark_shadow", shadow_location)
            screen.blit(shadow, shadow_rect)

        marker_name = "question_mark"
        if hovered and (now // 200) % 2:
            blink = self._scaled("question_mark_blink", MISSION_MARKER_SCALE)
            if blink is not None:
                marker = blink
                marker_name = "question_mark_blink"
        rect = self._registered_rect(marker, marker_name, body_location)
        screen.blit(marker, rect)
        if shadow_rect is not None:
            rect = rect.union(shadow_rect)
        return rect

    @staticmethod
    def _mission_copy(dimension: str, index: int) -> tuple[str, ...]:
        actions = {
            "overworld": ("REPAIR PLAINS HOUSE", "RESTORE VILLAGE HUB"),
            "nether": ("REPAIR BASTION GATE", "REPAIR THE FORTRESS"),
            "end": ("REPAIR THE END TOWER", "RESTORE CITY BRIDGE"),
            "ocean": ("ANCIENT RUINS", "SUNKEN SHIP"),
        }
        action = actions.get(dimension, ("BUILD THE ROUTE",))[index]
        if dimension == "ocean":
            return ("COMING SOON", action)
        words = action.split()
        if len(action) <= 18:
            action_lines = (action,)
        else:
            split = max(1, len(words) // 2)
            action_lines = (" ".join(words[:split]), " ".join(words[split:]))
        return (f"MISSION {index + 1}",) + action_lines

    def _render_mission_copy(
        self, screen: pygame.Surface, marker: pygame.Rect, index: int
    ) -> None:
        lines = self._mission_copy(self.dimension, index)
        top = marker.bottom + 3
        for line_index, line in enumerate(lines):
            shadow = self._text(line, (0, 0, 0), scale=1)
            text = self._text(line, (250, 250, 250), scale=1)
            center_x = marker.centerx
            y = top + line_index * 7
            screen.blit(shadow, shadow.get_rect(midtop=(center_x + 1, y + 1)))
            screen.blit(text, text.get_rect(midtop=(center_x, y)))

    def _worldbuilder_panel(
        self, screen: pygame.Surface, rect: pygame.Rect, *, selected: bool = False
    ) -> None:
        accent = DIMENSION_COLORS[self.dimension]
        fill = tuple(
            min(255, round(channel * (0.70 if selected else 0.60) + (86 if selected else 72)))
            for channel in accent
        )
        highlight = tuple(min(255, channel + 58) for channel in accent)
        shadow = tuple(max(18, round(channel * 0.65)) for channel in accent)
        pygame.draw.rect(screen, fill, rect)
        pygame.draw.line(screen, highlight, rect.topleft, (rect.right - 1, rect.top), 2)
        pygame.draw.line(screen, highlight, rect.topleft, (rect.left, rect.bottom - 1), 2)
        pygame.draw.line(screen, shadow, (rect.left, rect.bottom - 1), (rect.right - 1, rect.bottom - 1), 2)
        pygame.draw.line(screen, shadow, (rect.right - 1, rect.top), (rect.right - 1, rect.bottom - 1), 2)

    def _worldbuilder_arrow(
        self, screen: pygame.Surface, rect: pygame.Rect, *, previous: bool
    ) -> None:
        self._worldbuilder_panel(screen, rect, selected=rect.collidepoint(pygame.mouse.get_pos()))
        arrow = self._scaled("prev_world_arrow" if previous else "next_world_arrow", 1)
        if arrow is not None:
            screen.blit(arrow, arrow.get_rect(center=rect.center))

    def _render_badge(self, screen: pygame.Surface) -> None:
        del screen

    def _route_ledger(self, screen: pygame.Surface, completed: Mapping[str, object]) -> None:
        width, _height = screen.get_size()
        panel = pygame.Rect(width - 260, 66, 242, 184)
        self._panel(screen, panel)
        accent = DIMENSION_COLORS[self.dimension]
        pygame.draw.rect(screen, accent, (panel.x + 3, panel.y + 3, 5, panel.height - 6))
        screen.blit(self._text("BUILD ROUTES", (244, 226, 157), scale=2), (panel.x + 17, panel.y + 13))
        progress = completed.get(self.dimension, (False, False))
        if isinstance(progress, bool):
            progress = (progress, False)
        for index, label in enumerate(self.scene.route_labels):
            row = pygame.Rect(panel.x + 13, panel.y + 38 + index * 27, panel.width - 25, 23)
            active = index < len(self.scene.playable_anchors)
            fill = (70, 73, 68) if active else (42, 43, 47)
            pygame.draw.rect(screen, fill, row)
            pygame.draw.rect(screen, accent if active else (78, 79, 84), row, 1)
            finished = active and index < len(progress) and bool(progress[index])
            glyph = "FLAG" if finished else ("?" if active else "LOCK")
            glyph_color = (235, 91, 72) if glyph == "FLAG" else ((250, 250, 250) if active else (150, 151, 157))
            glyph_text = self._text(glyph, glyph_color, scale=2)
            screen.blit(glyph_text, (row.x + 7, row.centery - glyph_text.get_height() // 2))
            available = max(20, row.width - glyph_text.get_width() - 20)
            text = label
            rendered = self._text(text, (240, 240, 240) if active else (174, 175, 181), scale=2)
            while rendered.get_width() > available and len(text) > 4:
                text = text[:-2]
                rendered = self._text(text + "-", (240, 240, 240) if active else (174, 175, 181), scale=2)
            screen.blit(rendered, (row.x + glyph_text.get_width() + 13, row.centery - rendered.get_height() // 2))

    def _navigation(self, screen: pygame.Surface) -> None:
        width, height = screen.get_size()
        bar = pygame.Rect(18, height - 70, width - 36, 52)
        self._panel(screen, bar, fill=(21, 22, 25, 241))
        self.previous_rect = pygame.Rect(bar.x + 8, bar.y + 7, 44, 38)
        self.next_rect = pygame.Rect(bar.x + 58, bar.y + 7, 44, 38)
        self._worldbuilder_arrow(screen, self.previous_rect, previous=True)
        self._worldbuilder_arrow(screen, self.next_rect, previous=False)

        tab_count = len(DIMENSION_LABELS)
        tab_width = min(142, max(82, (bar.width - 250) // tab_count))
        tabs_width = tab_width * tab_count + 6 * (tab_count - 1)
        start_x = max(bar.x + 116, bar.centerx - tabs_width // 2)
        self.dimension_rects = {}
        for index, dimension in enumerate(DIMENSION_LABELS):
            rect = pygame.Rect(start_x + index * (tab_width + 6), bar.y + 8, tab_width, 36)
            self.dimension_rects[dimension] = rect
            selected = dimension == self.dimension
            hovered = rect.collidepoint(pygame.mouse.get_pos())
            pygame.draw.rect(screen, (70, 70, 74) if selected else ((60, 61, 65) if hovered else (43, 44, 48)), rect)
            pygame.draw.rect(screen, DIMENSION_COLORS[dimension] if selected or hovered else (84, 85, 90), rect, 2 if selected else 1)
            label = self._text(DIMENSION_LABELS[dimension], (255, 245, 204) if selected else (194, 195, 201), scale=2)
            screen.blit(label, label.get_rect(center=rect.center))

    def _render_ocean_ambience(self, screen: pygame.Surface) -> None:
        """Add sparse foreground particles over the app-owned water volume."""
        size = screen.get_size()
        phase = pygame.time.get_ticks() * 0.00018
        for index in range(18):
            x = (index * 137 + 61) % max(1, size[0])
            y = int((size[1] - ((pygame.time.get_ticks() * 0.018 + index * 83) % size[1])))
            radius = 1 + index % 3
            pygame.draw.circle(screen, (151, 226, 235), (x, y), radius, 1)

    def _traveler_sprite(self, index: int) -> pygame.Surface:
        specs = TRAVELER_TEXTURES[self.dimension]
        variant = index % len(specs)
        key = (self.dimension, variant)
        cached = self._traveler_sprites.get(key)
        if cached is not None:
            return cached
        relative, crop, display_size = specs[variant]
        sprite = pygame.Surface((display_size[0] + 2, display_size[1] + 2), pygame.SRCALPHA)
        entity_root = os.path.abspath(os.path.join(self.root, "..", "..", "Texture Hub", "entity"))
        try:
            atlas = pygame.image.load(os.path.join(entity_root, relative)).convert_alpha()
            source = atlas.subsurface(pygame.Rect(crop)).copy()
            textured = pygame.transform.scale(source, display_size)
            if self.dimension == "ocean":
                # Keep the water-map movement language the owner liked, but
                # fill the fish silhouette with the real cod/salmon texture.
                shape = pygame.Surface(display_size, pygame.SRCALPHA)
                width, height = display_size
                pygame.draw.polygon(
                    shape,
                    (255, 255, 255, 255),
                    (
                        (0, height // 2), (3, 1), (3, height - 2),
                        (width - 4, height - 2), (width - 1, height // 2),
                        (width - 4, 1), (3, 1),
                    ),
                )
                textured.blit(shape, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            mask = pygame.mask.from_surface(textured)
            outline = mask.to_surface(setcolor=(12, 12, 14, 255), unsetcolor=(0, 0, 0, 0))
            for offset in ((0, 1), (2, 1), (1, 0), (1, 2)):
                sprite.blit(outline, offset)
            sprite.blit(textured, (1, 1))
            if self.dimension == "ocean":
                pygame.draw.rect(sprite, (8, 12, 13), (display_size[0] - 4, display_size[1] // 2, 1, 1))
        except (OSError, pygame.error, ValueError):
            # Source checkouts without the private texture hub retain a tiny,
            # dimension-coloured traveler rather than losing route motion.
            color = DIMENSION_COLORS[self.dimension]
            pygame.draw.ellipse(sprite, (12, 12, 14), sprite.get_rect())
            pygame.draw.ellipse(sprite, color, sprite.get_rect().inflate(-2, -2))
        self._traveler_sprites[key] = sprite
        return sprite

    @staticmethod
    def _traveler_state(route, index: int, now: float):
        """Move continuously out and back so an open route never teleports."""
        segment_count = len(route) - 1
        phase = (now * (0.18 + index * 0.025) + index * 0.37) % (2 * segment_count)
        reversed_path = phase > segment_count
        travel = 2 * segment_count - phase if reversed_path else phase
        segment = min(segment_count - 1, int(travel))
        amount = travel - segment
        start = route[segment]
        end = route[segment + 1]
        return (
            tuple(
                start[axis] + (end[axis] - start[axis]) * amount
                for axis in range(3)
            ),
            reversed_path,
        )

    def _render_travelers(self, screen: pygame.Surface, renderer) -> None:
        routes = getattr(self.scene, "ambient_routes", ())
        now = pygame.time.get_ticks() / 1000.0
        for index, route in enumerate(routes[:5]):
            if len(route) < 2:
                continue
            world_position, reversed_path = self._traveler_state(route, index, now)
            x, y = renderer.worldToScreen(*world_position)
            y += math.sin(now * 3.0 + index) * 1.5
            sprite = self._traveler_sprite(index)
            if reversed_path:
                sprite = pygame.transform.flip(sprite, True, False)
            screen.blit(sprite, sprite.get_rect(center=(round(x), round(y))))

    def _dragon_head_sprite(self) -> pygame.Surface:
        key = ("dragon-head-landmark",)
        cached = self._scaled_cache.get(key)
        if cached is not None:
            return cached
        colors = [(34, 32, 36), (24, 23, 27), (50, 47, 52)]
        if self._dragon_texture is not None:
            samples = ((128, 36), (151, 47), (182, 52))
            colors = [
                tuple(self._dragon_texture.get_at(point)[:3])
                for point in samples
            ]
        sprite = pygame.Surface((34, 27), pygame.SRCALPHA)
        top, left, right = colors
        pygame.draw.polygon(sprite, top, ((5, 8), (17, 2), (30, 8), (18, 14)))
        pygame.draw.polygon(sprite, left, ((5, 8), (18, 14), (18, 23), (5, 17)))
        pygame.draw.polygon(sprite, right, ((18, 14), (30, 8), (30, 17), (18, 23)))
        pygame.draw.polygon(sprite, top, ((18, 14), (27, 11), (33, 15), (24, 19)))
        pygame.draw.polygon(sprite, right, ((24, 19), (33, 15), (33, 20), (24, 24)))
        pygame.draw.polygon(sprite, (15, 14, 18), ((8, 6), (10, 0), (13, 4), (13, 8)))
        pygame.draw.polygon(sprite, (15, 14, 18), ((23, 5), (25, 0), (28, 5), (27, 8)))
        pygame.draw.line(sprite, (8, 8, 10), (5, 8), (18, 14), 1)
        pygame.draw.line(sprite, (8, 8, 10), (18, 14), (30, 8), 1)
        pygame.draw.rect(sprite, (239, 56, 255), (25, 15, 2, 2))
        pygame.draw.rect(sprite, (10, 8, 12), (31, 17, 2, 1))
        self._scaled_cache[key] = sprite
        return sprite

    def _render_landmarks(self, screen: pygame.Surface, renderer) -> None:
        for kind, position in getattr(self.scene, "landmarks", ()):
            if kind != "dragon_head":
                continue
            x, y = renderer.worldToScreen(*position)
            source = self._dragon_head_sprite()
            scale = max(1.0, min(1.65, renderer.zoomLevel * 3.5))
            rendered = pygame.transform.scale(
                source,
                (
                    self._scaled_size(source.get_width(), scale),
                    self._scaled_size(source.get_height(), scale),
                ),
            )
            outline = pygame.mask.from_surface(rendered).to_surface(
                setcolor=(5, 4, 7, 255), unsetcolor=(0, 0, 0, 0)
            )
            rect = rendered.get_rect(midleft=(round(x - 8), round(y + 3)))
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                screen.blit(outline, rect.move(dx, dy))
            screen.blit(rendered, rect)

    def render_hub(self, screen: pygame.Surface, renderer, completed: Mapping[str, object]) -> None:
        width, _height = screen.get_size()
        if self.dimension == "ocean":
            self._render_ocean_ambience(screen)
        self._render_landmarks(screen, renderer)
        self._render_travelers(screen, renderer)
        title_rect = pygame.Rect(16, 14, min(520, width - 302), 82)
        self._panel(screen, title_rect)
        accent = DIMENSION_COLORS[self.dimension]
        pygame.draw.rect(screen, accent, (title_rect.x + 4, title_rect.y + 4, 6, title_rect.height - 8))
        title = self._text(DIMENSION_LABELS[self.dimension], (255, 234, 164), scale=3, fallback=self.font)
        subtitle = self._text(self.scene.title, (229, 230, 238), scale=2)
        screen.blit(title, (title_rect.x + 19, title_rect.y + 10))
        screen.blit(subtitle, (title_rect.x + 20, title_rect.y + 48))

        self.back_rect = pygame.Rect(width - 124, 17, 106, 36)
        self._worldbuilder_panel(
            screen, self.back_rect,
            selected=self.back_rect.collidepoint(pygame.mouse.get_pos()),
        )
        back_arrow = self._scaled("prev_world_arrow", 1)
        if back_arrow is not None:
            screen.blit(back_arrow, back_arrow.get_rect(midleft=(self.back_rect.x + 6, self.back_rect.centery)))
        back_text = self._text("BACK", (0, 0, 0), scale=2)
        screen.blit(back_text, back_text.get_rect(center=(self.back_rect.centerx + 14, self.back_rect.centery)))
        self._route_ledger(screen, completed)
        self._navigation(screen)

        # World Builder parks unavailable mission sprites off-screen rather
        # than presenting disabled question marks. The route ledger carries
        # the locked state without implying a clickable map node.

        progress = completed.get(self.dimension, (False, False))
        if isinstance(progress, bool):
            progress = (progress, False)
        all_complete = all(
            all(bool(value) for value in completed.get(dimension, (False, False)))
            if not isinstance(completed.get(dimension, (False, False)), bool)
            else bool(completed.get(dimension))
            for dimension in DIMENSION_LABELS
            if dimension != "ocean"
        )
        self.node_rects = []
        self.node_hit_rects = []
        anchors = self.scene.playable_anchors
        if self.dimension == "ocean":
            anchors = self.scene.locked_anchors
        for index, world_anchor in enumerate(anchors):
            anchor = renderer.worldToScreen(*world_anchor)
            hovered = index == self._hovered_node
            active = self.dimension != "ocean"
            node_rect = self._draw_marker(
                screen,
                anchor,
                completed=(
                    active and index < len(progress) and bool(progress[index])
                ),
                active=active,
                hovered=hovered,
                bonus=all_complete,
                phase=index,
            )
            self.node_rects.append(node_rect)
            self.node_hit_rects.append(node_rect.inflate(30, 26))
            if hovered:
                self._render_mission_copy(screen, node_rect, index)
        self.node_rect = self.node_rects[0] if self.node_rects else pygame.Rect(0, 0, 0, 0)
        self.node_hit_rect = self.node_hit_rects[0] if self.node_hit_rects else pygame.Rect(0, 0, 0, 0)

        self._render_badge(screen)

    def render_level(self, screen: pygame.Surface, progress: tuple[int, int, bool]) -> None:
        width, height = screen.get_size()
        current, total, _done = progress
        panel = pygame.Rect(62, 14, min(590, width - 82), 112)
        self._worldbuilder_panel(screen, panel)
        screen.blit(self._text(self.objective.title, (0, 0, 0), scale=2), (panel.x + 14, panel.y + 12))
        for index, line in enumerate(self.objective.instructions):
            screen.blit(self._text(line, (0, 0, 0), scale=1), (panel.x + 14, panel.y + 48 + index * 17))
        progress_text = self._text(f"OBJECTIVE {current}/{total}", (0, 0, 0), scale=1)
        screen.blit(progress_text, (panel.right - progress_text.get_width() - 14, panel.y + 17))
        self.back_rect = pygame.Rect(16, 20, 38, 38)
        self._worldbuilder_arrow(screen, self.back_rect, previous=True)

        if self.completed_now:
            card = pygame.Rect(0, 0, min(430, width - 40), 148)
            card.center = (width // 2, height // 2)
            self._worldbuilder_panel(screen, card, selected=True)
            heading = self._text("OBJECTIVE COMPLETE", (0, 0, 0), scale=3)
            screen.blit(heading, heading.get_rect(center=(card.centerx, card.y + 39)))
            detail = self._text("YOUR FLAG IS NOW FIXED TO THIS MAP", (0, 0, 0), scale=1)
            screen.blit(detail, detail.get_rect(center=(card.centerx, card.y + 76)))
            self.continue_rect = pygame.Rect(0, 0, 176, 36)
            self.continue_rect.midbottom = (card.centerx, card.bottom - 13)
            self._worldbuilder_panel(
                screen, self.continue_rect,
                selected=self.continue_rect.collidepoint(pygame.mouse.get_pos()),
            )
            label = self._text("RETURN TO MAP", (0, 0, 0), scale=1)
            screen.blit(label, label.get_rect(center=(self.continue_rect.centerx - 12, self.continue_rect.centery)))
            arrow = self._scaled("next_world_arrow", 1)
            if arrow is not None:
                screen.blit(arrow, arrow.get_rect(midright=(self.continue_rect.right - 5, self.continue_rect.centery)))

    def render_targets(self, screen: pygame.Surface, renderer, objective, world) -> None:
        pulse = 0.55 + 0.25 * math.sin(pygame.time.get_ticks() / 230.0)
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        half_w = max(7, renderer._tileW // 3)
        half_h = max(4, renderer._tileH // 3)
        for position, block_name in objective.targets.items():
            if world.getBlock(*position).name == block_name:
                continue
            x, y = renderer.worldToScreen(*position)
            points = ((x, y), (x + half_w, y + half_h), (x, y + half_h * 2), (x - half_w, y + half_h))
            pygame.draw.polygon(overlay, (108, 210, 245, round(150 * pulse)), points)
            pygame.draw.polygon(overlay, (196, 239, 255, 220), points, 2)
        screen.blit(overlay, (0, 0))
