"""One modal exit route, shared by Escape and the window close button."""
import pygame
from ui import chrome
from ui.fonts import load_ui_font


class ExitDialog:
    def __init__(self, screen, dirty):
        self.background = screen.copy()
        self.dirty = dirty
        self.focus = 'stay'
        self.rects = {}
        self.font = load_ui_font(22)
        self.small = load_ui_font(16)
        self.shade = None

    def handle(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return 'stay'
            choices = ['stay', 'save', 'exit'] if self.dirty else ['stay', 'exit']
            if event.key in (pygame.K_TAB, pygame.K_LEFT, pygame.K_RIGHT):
                delta = -1 if event.key == pygame.K_LEFT else 1
                self.focus = choices[(choices.index(self.focus) + delta) % len(choices)]
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                return self.focus
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return next((key for key, rect in self.rects.items() if rect.collidepoint(event.pos)), None)

    def render(self, screen, pending=False, error=''):
        screen.fill(chrome.SURFACE)
        screen.blit(self.background, (0, 0))
        if self.shade is None or self.shade.get_size()!=screen.get_size():
            self.shade = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
            self.shade.fill((3, 7, 12, 175))
        screen.blit(self.shade, (0, 0))
        width = min(screen.get_width() - 32, 620)
        message = ('Saving… Please wait for the confirmed write.' if pending else
                   'Unsaved changes will be lost. Save and Exit keeps your build.' if self.dirty else
                   'Your saved build will be here when you return.')
        body_height = chrome.wrapped_height(error or message, self.small, width - 40)
        box = pygame.Rect(0, 0, width, max(190, body_height + 126))
        box.center = screen.get_rect().center
        chrome.panel(screen, box)
        screen.blit(self.font.render('Exit Bloc Fantôme?', True, chrome.TEXT), (box.x + 20, box.y + 20))
        chrome.wrapped(screen, error or message, self.small,
                       (box.x + 20, box.y + 62, width - 40, body_height),
                       chrome.ERROR if error else chrome.MUTED)
        choices = [('stay', 'Stay')]
        if not pending:
            if self.dirty:
                choices.append(('save', 'Save and Exit'))
            choices.append(('exit', 'Exit'))
        self.rects = {}
        button_width = (width - 40 - (len(choices)-1)*8)//len(choices)
        for i, (key, label) in enumerate(choices):
            height=max(34,self.small.get_height()+12)
            rect = pygame.Rect(box.x + 20 + i*(button_width+8), box.bottom - height-20, button_width, height)
            self.rects[key] = rect
            chrome.button(screen, rect, label, self.small, rect.collidepoint(pygame.mouse.get_pos()),
                          key == self.focus)
