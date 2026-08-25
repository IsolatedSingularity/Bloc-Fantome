"""Minecraft-styled, categorized Build Library used by Open Build."""

from typing import List, Optional, Tuple

import pygame

from engine.build_catalog import BuildEntry, CATEGORIES


class BuildLibraryModal:
    """Modal build browser visually aligned with the Worlds gallery."""

    WIDTH = 780
    HEIGHT = 590
    ROW_HEIGHT = 52

    def __init__(self, font: pygame.font.Font, small_font: pygame.font.Font, assets) -> None:
        self.font = font
        self.small_font = small_font
        self.assets = assets
        self.visible = False
        self.entries: List[BuildEntry] = []
        self.category = CATEGORIES[0]
        self.scroll = 0
        self._tab_rects = {}
        self._entry_rects: List[Tuple[pygame.Rect, BuildEntry]] = []
        self._list_rect = pygame.Rect(0, 0, 0, 0)
        self._browse_rect = pygame.Rect(0, 0, 0, 0)
        self._close_rect = pygame.Rect(0, 0, 0, 0)

    def open(self, entries: List[BuildEntry]) -> None:
        self.entries = entries
        self.category = CATEGORIES[0]
        self.scroll = 0
        self.visible = True

    def close(self) -> None:
        self.visible = False

    def _play_click(self) -> None:
        play = getattr(self.assets, "playClickSound", None)
        if callable(play):
            play()

    def _visible_entries(self) -> List[BuildEntry]:
        return [entry for entry in self.entries if entry.category == self.category]

    def handle_event(self, event) -> Optional[Tuple[str, Optional[BuildEntry]]]:
        if not self.visible:
            return None
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.close()
            return ("close", None)
        if event.type == pygame.MOUSEWHEEL:
            maximum = max(
                0,
                len(self._visible_entries()) * self.ROW_HEIGHT
                - max(1, self._list_rect.height - 12),
            )
            self.scroll = max(0, min(maximum, self.scroll - event.y * self.ROW_HEIGHT))
            return ("handled", None)
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return ("handled", None)
        if self._close_rect.collidepoint(event.pos):
            self._play_click()
            self.close()
            return ("close", None)
        if self._browse_rect.collidepoint(event.pos):
            self._play_click()
            return ("browse", None)
        for category, rect in self._tab_rects.items():
            if rect.collidepoint(event.pos):
                self._play_click()
                self.category = category
                self.scroll = 0
                return ("handled", None)
        if self._list_rect.collidepoint(event.pos):
            for rect, entry in self._entry_rects:
                if rect.collidepoint(event.pos):
                    self._play_click()
                    self.close()
                    return ("open", entry)
        return ("handled", None)

    def _tile_panel(self, screen: pygame.Surface, panel: pygame.Rect) -> None:
        texture = self.assets.textures.get("stone_bricks")
        if texture is None:
            pygame.draw.rect(screen, (45, 45, 45), panel)
            return
        tile = pygame.transform.scale(texture, (64, 64))
        old_clip = screen.get_clip()
        screen.set_clip(panel)
        for y in range(panel.y, panel.bottom, tile.get_height()):
            for x in range(panel.x, panel.right, tile.get_width()):
                screen.blit(tile, (x, y))
        shade = pygame.Surface(panel.size, pygame.SRCALPHA)
        shade.fill((18, 14, 12, 160))
        screen.blit(shade, panel)
        screen.set_clip(old_clip)

    def render(self, screen: pygame.Surface) -> None:
        if not self.visible:
            return
        mouse = pygame.mouse.get_pos()
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 185))
        screen.blit(overlay, (0, 0))
        panel = pygame.Rect(
            (screen.get_width() - self.WIDTH) // 2,
            (screen.get_height() - self.HEIGHT) // 2,
            self.WIDTH,
            self.HEIGHT,
        )
        self._tile_panel(screen, panel)
        pygame.draw.rect(screen, (26, 26, 26), panel, 4)
        pygame.draw.line(screen, (150, 150, 150), panel.topleft, panel.topright, 2)
        pygame.draw.line(screen, (150, 150, 150), panel.topleft, panel.bottomleft, 2)
        pygame.draw.line(screen, (38, 38, 38), panel.bottomleft, panel.bottomright, 2)
        pygame.draw.line(screen, (38, 38, 38), panel.topright, panel.bottomright, 2)

        shadow = self.font.render("Open Build Library", True, (55, 55, 55))
        title = self.font.render("Open Build Library", True, (255, 255, 255))
        screen.blit(shadow, (panel.x + 27, panel.y + 22))
        screen.blit(title, (panel.x + 25, panel.y + 20))
        subtitle = self.small_font.render(
            "Open saved builds or cursor-placeable tutorials without replacing Worlds.",
            True,
            (220, 220, 220),
        )
        screen.blit(subtitle, (panel.x + 25, panel.y + 50))

        self._close_rect = pygame.Rect(panel.right - 48, panel.y + 16, 28, 28)
        self.assets.drawButton(
            screen, self._close_rect, "X", self.small_font,
            self._close_rect.collidepoint(mouse), False,
        )

        tabs_y = panel.y + 82
        tab_width = (panel.width - 50) // len(CATEGORIES)
        self._tab_rects = {}
        for index, category in enumerate(CATEGORIES):
            rect = pygame.Rect(panel.x + 25 + index * tab_width, tabs_y, tab_width - 4, 34)
            self._tab_rects[category] = rect
            self.assets.drawButton(
                screen, rect, category, self.small_font,
                rect.collidepoint(mouse), category == self.category,
            )

        self._list_rect = pygame.Rect(panel.x + 25, tabs_y + 44, panel.width - 50, 374)
        pygame.draw.rect(screen, (18, 18, 18), self._list_rect)
        pygame.draw.rect(screen, (92, 92, 92), self._list_rect, 2)
        old_clip = screen.get_clip()
        screen.set_clip(self._list_rect.inflate(-4, -4))
        self._entry_rects = []
        entries = self._visible_entries()
        for index, entry in enumerate(entries):
            rect = pygame.Rect(
                self._list_rect.x + 8,
                self._list_rect.y + 8 + index * self.ROW_HEIGHT - self.scroll,
                self._list_rect.width - 16,
                self.ROW_HEIGHT - 7,
            )
            self._entry_rects.append((rect, entry))
            if rect.bottom < self._list_rect.top or rect.top > self._list_rect.bottom:
                continue
            self.assets.drawSlot(screen, rect, False)
            if rect.collidepoint(mouse):
                hover = pygame.Surface(rect.size, pygame.SRCALPHA)
                hover.fill((255, 255, 255, 24))
                screen.blit(hover, rect)
            screen.blit(
                self.font.render(entry.label, True, (255, 255, 255)),
                (rect.x + 14, rect.y + 7),
            )
            kind_label = "Tutorial showcase" if entry.kind == "tutorial" else "Editable build"
            screen.blit(
                self.small_font.render(kind_label, True, (125, 205, 230)),
                (rect.x + 14, rect.y + 29),
            )
        if not entries:
            message = self.small_font.render(
                "No builds in this category yet.", True, (190, 190, 190)
            )
            screen.blit(message, message.get_rect(center=self._list_rect.center))
        screen.set_clip(old_clip)

        footer_y = panel.bottom - 54
        self._browse_rect = pygame.Rect(panel.x + 25, footer_y, 220, 34)
        self.assets.drawButton(
            screen, self._browse_rect, "Browse Files...", self.small_font,
            self._browse_rect.collidepoint(mouse), False,
        )
        hint = self.small_font.render(
            "Tutorial entries also open their matching lesson.",
            True,
            (205, 205, 205),
        )
        screen.blit(hint, hint.get_rect(midright=(panel.right - 25, footer_y + 17)))
