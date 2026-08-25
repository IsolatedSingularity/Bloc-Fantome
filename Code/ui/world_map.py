"""Focused World Map presentation built around the recovered WorldBuilder marker set."""

from __future__ import annotations

import math
import os
from typing import Mapping

import pygame


DIMENSION_LABELS = {
    "overworld": "OVERWORLD",
    "nether": "NETHER",
    "end": "THE END",
}


class WorldMapView:
    """Render and hit-test the map selector without owning editor state."""

    def __init__(self, root: str, font: pygame.font.Font, small_font: pygame.font.Font, audio_router=None):
        self.root = root
        self.font = font
        self.small_font = small_font
        self.audio_router = audio_router
        self.mode = "hub"
        self.dimension = "overworld"
        self.scene = None
        self.objective = None
        self.completed_now = False
        self.node_rect = pygame.Rect(0, 0, 0, 0)
        self.back_rect = pygame.Rect(0, 0, 0, 0)
        self.previous_rect = pygame.Rect(0, 0, 0, 0)
        self.next_rect = pygame.Rect(0, 0, 0, 0)
        self.continue_rect = pygame.Rect(0, 0, 0, 0)
        self._node_hovered = False
        self._surfaces = {}
        self._sounds = {}
        self._load_assets()

    def _load_assets(self) -> None:
        ui_root = os.path.join(self.root, "ui")
        names = [
            "question_mark", "question_mark_blink", "question_mark_shadow",
            "flag_rollover_blink", "next_world_arrow", "prev_world_arrow",
            "worldbuilder_title",
        ] + [f"flag{i}" for i in range(1, 7)] + [f"bonus_flag{i}" for i in range(1, 7)]
        for name in names:
            path = os.path.join(ui_root, f"{name}.png")
            if not os.path.isfile(path):
                continue
            try:
                self._surfaces[name] = pygame.image.load(path).convert_alpha()
            except pygame.error:
                pass

        audio_root = os.path.join(self.root, "audio")
        sound_files = {
            "hover": "s_rollover_1.mp3",
            "click": "s_button_click_2.mp3",
            "complete": "s_goal_mission_4.mp3",
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
        self._node_hovered = False

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
            hovered = self.node_rect.collidepoint(event.pos)
            if hovered and not self._node_hovered:
                self.play("hover")
            self._node_hovered = hovered
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
            if self.node_rect.collidepoint(event.pos):
                self.play("click")
                return "start"
        elif self.completed_now and self.continue_rect.collidepoint(event.pos):
            self.play("click")
            return "hub"
        return None

    @staticmethod
    def _panel(screen: pygame.Surface, rect: pygame.Rect, fill=(20, 22, 29, 226), border=(172, 177, 190)) -> None:
        shade = pygame.Surface(rect.size, pygame.SRCALPHA)
        shade.fill(fill)
        screen.blit(shade, rect)
        pygame.draw.rect(screen, border, rect, 2, border_radius=4)

    def _button(self, screen: pygame.Surface, rect: pygame.Rect, label: str, *, strong=False) -> None:
        hovered = rect.collidepoint(pygame.mouse.get_pos())
        fill = (82, 114, 72) if strong else (52, 55, 66)
        if hovered:
            fill = tuple(min(255, channel + 22) for channel in fill)
        pygame.draw.rect(screen, fill, rect, border_radius=4)
        pygame.draw.rect(screen, (184, 189, 202), rect, 1, border_radius=4)
        text = self.small_font.render(label, True, (248, 248, 250))
        screen.blit(text, text.get_rect(center=rect.center))

    def _scaled(self, name: str, scale: int = 2):
        source = self._surfaces.get(name)
        if source is None:
            return None
        size = (max(1, source.get_width() * scale), max(1, source.get_height() * scale))
        return pygame.transform.scale(source, size)

    def _render_marker(self, screen: pygame.Surface, anchor, completed: bool, bonus: bool = False) -> None:
        now = pygame.time.get_ticks()
        orbit = now * (math.tau / 1800.0)
        x = int(anchor[0] + math.cos(orbit) * 2)
        y = int(anchor[1] + math.sin(orbit) * 2)

        if completed:
            prefix = "bonus_flag" if bonus else "flag"
            marker = self._scaled(f"{prefix}{1 + (now // 120) % 6}", 2)
        else:
            blinking = self._node_hovered and (now // 200) % 2
            marker = self._scaled("question_mark_blink" if blinking else "question_mark", 2)
        if marker is None:
            marker = self.font.render("!" if completed else "?", True, (226, 54, 48) if completed else (255, 224, 72))

        shadow = self._scaled("question_mark_shadow", 2)
        if shadow is not None:
            screen.blit(shadow, shadow.get_rect(midbottom=(x + 2, y + marker.get_height() // 2 + 6)))
        self.node_rect = marker.get_rect(center=(x, y))
        halo = self.node_rect.inflate(20, 20)
        pygame.draw.ellipse(screen, (246, 224, 104), halo, 2)
        screen.blit(marker, self.node_rect)

    def _render_badge(self, screen: pygame.Surface) -> None:
        badge = self._surfaces.get("worldbuilder_title")
        if badge is None:
            return
        max_width = min(218, screen.get_width() // 5)
        scale = min(1.0, max_width / badge.get_width())
        size = (max(1, round(badge.get_width() * scale)), max(1, round(badge.get_height() * scale)))
        badge = pygame.transform.smoothscale(badge, size) if scale != 1.0 else badge
        rect = badge.get_rect(bottomright=(screen.get_width() - 18, screen.get_height() - 16))
        pad = rect.inflate(14, 10)
        self._panel(screen, pad, fill=(15, 16, 20, 205), border=(122, 126, 138))
        screen.blit(badge, rect)

    def render_hub(self, screen: pygame.Surface, renderer, completed: Mapping[str, bool]) -> None:
        width, height = screen.get_size()
        title_rect = pygame.Rect(16, 14, min(500, width - 160), 82)
        self._panel(screen, title_rect)
        title = self.font.render(DIMENSION_LABELS[self.dimension], True, (255, 234, 164))
        subtitle = self.small_font.render(self.scene.title, True, (229, 230, 238))
        screen.blit(title, (title_rect.x + 16, title_rect.y + 12))
        screen.blit(subtitle, (title_rect.x + 16, title_rect.y + 49))

        self.back_rect = pygame.Rect(width - 118, 18, 100, 34)
        self._button(screen, self.back_rect, "Back")
        self.previous_rect = pygame.Rect(20, height - 58, 124, 36)
        self.next_rect = pygame.Rect(154, height - 58, 124, 36)
        self._button(screen, self.previous_rect, "Previous")
        self._button(screen, self.next_rect, "Next")
        previous_arrow = self._scaled("prev_world_arrow", 2)
        next_arrow = self._scaled("next_world_arrow", 2)
        if previous_arrow is not None:
            screen.blit(previous_arrow, previous_arrow.get_rect(midleft=(self.previous_rect.x + 9, self.previous_rect.centery)))
        if next_arrow is not None:
            screen.blit(next_arrow, next_arrow.get_rect(midright=(self.next_rect.right - 9, self.next_rect.centery)))

        for index, future in enumerate(self.scene.future_anchors):
            fx, fy = renderer.worldToScreen(*future)
            radius = 8 + index % 2
            pygame.draw.circle(screen, (34, 37, 47), (fx, fy), radius + 4)
            pygame.draw.circle(screen, (105, 110, 124), (fx, fy), radius, 2)

        anchor = renderer.worldToScreen(*self.scene.primary_anchor)
        all_complete = all(completed.get(dimension, False) for dimension in DIMENSION_LABELS)
        self._render_marker(
            screen, anchor, bool(completed.get(self.dimension)), bonus=all_complete
        )

        if self.node_rect.collidepoint(pygame.mouse.get_pos()):
            tooltip = pygame.Rect(0, 0, min(430, width - 40), 74)
            tooltip.midbottom = (self.node_rect.centerx, self.node_rect.top - 12)
            tooltip.clamp_ip(screen.get_rect().inflate(-16, -16))
            self._panel(screen, tooltip, fill=(18, 20, 27, 242))
            headline = "Completed - revisit" if completed.get(self.dimension) else "Builder objective"
            screen.blit(self.small_font.render(headline, True, (255, 224, 120)), (tooltip.x + 12, tooltip.y + 10))
            screen.blit(self.small_font.render(self.scene.subtitle, True, (224, 225, 232)), (tooltip.x + 12, tooltip.y + 39))

        self._render_badge(screen)

    def render_level(self, screen: pygame.Surface, progress: tuple[int, int, bool]) -> None:
        width, height = screen.get_size()
        current, total, _done = progress
        panel = pygame.Rect(16, 14, min(520, width - 154), 112)
        self._panel(screen, panel)
        screen.blit(self.font.render(self.objective.title, True, (255, 234, 164)), (panel.x + 14, panel.y + 10))
        for index, line in enumerate(self.objective.instructions):
            screen.blit(self.small_font.render(line, True, (228, 229, 236)), (panel.x + 14, panel.y + 44 + index * 21))
        progress_text = self.small_font.render(f"Objective: {current}/{total}", True, (153, 227, 146))
        screen.blit(progress_text, (panel.right - progress_text.get_width() - 14, panel.y + 13))
        self.back_rect = pygame.Rect(width - 118, 18, 100, 34)
        self._button(screen, self.back_rect, "Map")

        if self.completed_now:
            card = pygame.Rect(0, 0, min(430, width - 40), 148)
            card.center = (width // 2, height // 2)
            self._panel(screen, card, fill=(18, 25, 20, 244), border=(151, 220, 138))
            heading = self.font.render("OBJECTIVE COMPLETE", True, (184, 239, 165))
            screen.blit(heading, heading.get_rect(center=(card.centerx, card.y + 39)))
            detail = self.small_font.render("Your flag is now fixed to this map.", True, (230, 234, 230))
            screen.blit(detail, detail.get_rect(center=(card.centerx, card.y + 76)))
            self.continue_rect = pygame.Rect(0, 0, 176, 36)
            self.continue_rect.midbottom = (card.centerx, card.bottom - 13)
            self._button(screen, self.continue_rect, "Return to map", strong=True)

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
