"""Modal, categorized Build Library used by Open Build."""

from typing import List, Optional, Tuple

import pygame

from engine.build_catalog import BuildEntry, CATEGORIES


class BuildLibraryModal:
    """Small modal browser that leaves the native chooser as a fallback."""

    WIDTH = 720
    HEIGHT = 560
    ROW_HEIGHT = 42

    def __init__(self, font: pygame.font.Font, small_font: pygame.font.Font) -> None:
        self.font = font
        self.small_font = small_font
        self.visible = False
        self.entries: List[BuildEntry] = []
        self.category = CATEGORIES[0]
        self.scroll = 0
        self._tab_rects = {}
        self._entry_rects: List[Tuple[pygame.Rect, BuildEntry]] = []
        self._browse_rect = pygame.Rect(0, 0, 0, 0)
        self._close_rect = pygame.Rect(0, 0, 0, 0)

    def open(self, entries: List[BuildEntry]) -> None:
        self.entries = entries
        self.category = CATEGORIES[0]
        self.scroll = 0
        self.visible = True

    def close(self) -> None:
        self.visible = False

    def handle_event(self, event) -> Optional[Tuple[str, Optional[BuildEntry]]]:
        if not self.visible:
            return None
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.close()
            return ("close", None)
        if event.type == pygame.MOUSEWHEEL:
            count = len([entry for entry in self.entries if entry.category == self.category])
            max_scroll = max(0, count * self.ROW_HEIGHT - 350)
            self.scroll = max(0, min(max_scroll, self.scroll - event.y * self.ROW_HEIGHT))
            return ("handled", None)
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return ("handled", None)
        if self._close_rect.collidepoint(event.pos):
            self.close()
            return ("close", None)
        if self._browse_rect.collidepoint(event.pos):
            return ("browse", None)
        for category, rect in self._tab_rects.items():
            if rect.collidepoint(event.pos):
                self.category = category
                self.scroll = 0
                return ("handled", None)
        for rect, entry in self._entry_rects:
            if rect.collidepoint(event.pos):
                self.close()
                return ("open", entry)
        return ("handled", None)

    def render(self, screen: pygame.Surface) -> None:
        if not self.visible:
            return
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 175))
        screen.blit(overlay, (0, 0))

        panel = pygame.Rect(
            (screen.get_width() - self.WIDTH) // 2,
            (screen.get_height() - self.HEIGHT) // 2,
            self.WIDTH,
            self.HEIGHT,
        )
        pygame.draw.rect(screen, (29, 18, 25), panel, border_radius=6)
        pygame.draw.rect(screen, (104, 54, 45), panel, 3, border_radius=6)
        title = self.font.render("Open Build Library", True, (244, 235, 219))
        screen.blit(title, (panel.x + 24, panel.y + 18))

        self._close_rect = pygame.Rect(panel.right - 50, panel.y + 14, 30, 30)
        pygame.draw.rect(screen, (88, 38, 38), self._close_rect, border_radius=3)
        close_text = self.font.render("×", True, (255, 255, 255))
        screen.blit(close_text, close_text.get_rect(center=self._close_rect.center))

        tab_y = panel.y + 66
        tab_width = (panel.width - 48) // len(CATEGORIES)
        self._tab_rects = {}
        for index, category in enumerate(CATEGORIES):
            rect = pygame.Rect(panel.x + 24 + index * tab_width, tab_y, tab_width - 4, 34)
            self._tab_rects[category] = rect
            color = (112, 52, 42) if category == self.category else (55, 38, 42)
            pygame.draw.rect(screen, color, rect, border_radius=3)
            label = self.small_font.render(category, True, (244, 235, 219))
            screen.blit(label, label.get_rect(center=rect.center))

        list_rect = pygame.Rect(panel.x + 24, tab_y + 46, panel.width - 48, 350)
        pygame.draw.rect(screen, (18, 14, 18), list_rect)
        old_clip = screen.get_clip()
        screen.set_clip(list_rect)
        self._entry_rects = []
        visible_entries = [entry for entry in self.entries if entry.category == self.category]
        for index, entry in enumerate(visible_entries):
            rect = pygame.Rect(
                list_rect.x + 8,
                list_rect.y + 7 + index * self.ROW_HEIGHT - self.scroll,
                list_rect.width - 16,
                self.ROW_HEIGHT - 5,
            )
            self._entry_rects.append((rect, entry))
            if rect.bottom < list_rect.top or rect.top > list_rect.bottom:
                continue
            hovered = rect.collidepoint(pygame.mouse.get_pos())
            pygame.draw.rect(screen, (80, 42, 38) if hovered else (45, 31, 34), rect, border_radius=3)
            label = self.small_font.render(entry.label, True, (238, 229, 209))
            screen.blit(label, (rect.x + 12, rect.centery - label.get_height() // 2))
        if not visible_entries:
            empty = self.small_font.render("No builds in this category yet.", True, (170, 157, 151))
            screen.blit(empty, empty.get_rect(center=list_rect.center))
        screen.set_clip(old_clip)

        hint = self.small_font.render(
            "Tutorial entries load their showcase and open the matching lesson.",
            True,
            (185, 170, 162),
        )
        screen.blit(hint, (panel.x + 24, panel.bottom - 92))
        self._browse_rect = pygame.Rect(panel.x + 24, panel.bottom - 58, 170, 36)
        pygame.draw.rect(screen, (74, 72, 78), self._browse_rect, border_radius=3)
        browse = self.small_font.render("Browse Files…", True, (255, 255, 255))
        screen.blit(browse, browse.get_rect(center=self._browse_rect.center))
