"""
Bloc Fantôme - Splash Screen Module

The supplied swamp painting and a quiet, native-resolution title.

Author: Jeffrey Morais
"""

import os
import pygame
from ui.fonts import load_ui_font

# Splash screen configuration
SPLASH_DISPLAY_FRAMES = 120   # 2 seconds at 60fps
SPLASH_FADE_FRAMES = 60       # 1 second fade
SPLASH_FPS = 60

# Colors
SPLASH_BG_COLOR = (3, 4, 7)


class SplashScreen:
    """
    Self-contained splash screen using the approved swamp artwork.

    The full painting remains visible. Resource-loading
    fallbacks keep source checkouts usable while the release preflight requires
    the supplied artwork.
    """

    @staticmethod
    def fitted_window_size(max_width, max_height, icons_dir):
        """Fit the launch window to the complete painting with an overlaid title."""
        artwork = pygame.image.load(os.path.join(icons_dir, 'Splash_Swamp.jpg'))
        scale = min(max_width / artwork.get_width(), max_height / artwork.get_height())
        return round(artwork.get_width() * scale), round(artwork.get_height() * scale)

    def __init__(self, screen: pygame.Surface, clock: pygame.time.Clock,
                 textures_dir: str, fonts_dir: str, icons_dir: str):
        """
        Initialize the splash screen.

        Args:
            screen: The main pygame display surface
            clock: Pygame clock for frame timing
            textures_dir: Path to textures directory
            fonts_dir: Path to fonts directory
            icons_dir: Path to icons directory
        """
        self.screen = screen
        self.clock = clock
        self.textures_dir = textures_dir
        self.fonts_dir = fonts_dir
        self.icons_dir = icons_dir

        self.window_width = screen.get_width()
        self.window_height = screen.get_height()

        # Load resources
        self.title_font = self._load_title_font()
        self.title = self._load_title_artwork()
        self.background_tile = self._create_background_tile()
        self.first_presented_at = None

    def _load_title_font(self) -> pygame.font.Font:
        """Rasterize the understated title at its final display size."""
        size = max(22, min(32, round(self.window_height * .035)))
        return load_ui_font(size, fonts_dir=self.fonts_dir)

    def _load_title_artwork(self) -> pygame.Surface:
        return self.title_font.render('Bloc Fantôme', True, (236, 232, 219))

    def _create_background_tile(self) -> pygame.Surface:
        """Keep the complete owner-supplied painting within dark margins."""
        background = pygame.Surface((self.window_width, self.window_height))
        background.fill(SPLASH_BG_COLOR)
        self.artwork_rect = pygame.Rect(0, 0, 0, 0)
        path = os.path.join(self.icons_dir, 'Splash_Swamp.jpg')
        if os.path.isfile(path):
            artwork = pygame.image.load(path).convert()
            available = pygame.Rect(0, 0, self.window_width, self.window_height)
            scale = min(available.width / artwork.get_width(), available.height / artwork.get_height())
            size = (round(artwork.get_width() * scale), round(artwork.get_height() * scale))
            artwork = pygame.transform.smoothscale(artwork, size)
            self.artwork_rect = artwork.get_rect(center=available.center)
            background.blit(artwork, self.artwork_rect)
            # A restrained lower-edge vignette follows the painting, without a
            # separate strip, blurred patch or crop of the supplied composition.
            depth=min(120,round(self.artwork_rect.height*.23))
            shade=pygame.Surface((self.artwork_rect.width,depth),pygame.SRCALPHA)
            for y in range(depth):
                alpha=round(132*(y/max(1,depth-1))**1.8)
                pygame.draw.line(shade,(3,7,12,alpha),(0,y),(shade.get_width(),y))
            background.blit(shade,(self.artwork_rect.left,self.artwork_rect.bottom-depth))
        return background

    def _draw_background(self, target: pygame.Surface) -> None:
        target.blit(self.background_tile, (0, 0))

    def _title_rect(self) -> pygame.Rect:
        return self.title.get_rect(center=(self.window_width // 2, self.window_height - 24))

    def present(self) -> None:
        """Put the splash on screen immediately before expensive startup work."""
        title_rect = self._title_rect()
        self._draw_background(self.screen)
        self.screen.blit(self.title, title_rect)
        pygame.display.flip()
        if self.first_presented_at is None:
            self.first_presented_at = pygame.time.get_ticks()

    def show(self, pre_render_callback=None) -> None:
        """
        Display the splash screen with fade animation.

        Args:
            pre_render_callback: Optional function to call for pre-rendering game state.
                                Should return a pygame.Surface of the game view.
        """
        # Clear events
        pygame.event.clear()
        pygame.event.pump()

        # Render title
        title_rect = self._title_rect()

        # Pre-render game frame for smooth transition
        game_frame = None
        if pre_render_callback:
            try:
                game_frame = pre_render_callback()
            except:
                pass

        # Display phase. Startup work counts toward the minimum display time,
        # so loading first never adds another fixed two-second pause.
        elapsedFrames = 0
        if self.first_presented_at is not None:
            elapsedFrames = round(
                (pygame.time.get_ticks() - self.first_presented_at) * SPLASH_FPS / 1000
            )
        for frame in range(max(0, SPLASH_DISPLAY_FRAMES - elapsedFrames)):
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                if event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                    # Skip splash on input
                    return

            self._draw_background(self.screen)
            self.screen.blit(self.title, title_rect)

            pygame.display.flip()
            self.clock.tick(SPLASH_FPS)

        # Fade phase
        if game_frame is None:
            return

        splash_frame = self.screen.copy()

        for frame in range(SPLASH_FADE_FRAMES):
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                if event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                    # Skip fade on input
                    return

            # Calculate alpha
            alpha = 255 - int((frame / SPLASH_FADE_FRAMES) * 255)

            # Draw game frame
            self.screen.blit(game_frame, (0, 0))

            # Overlay splash with decreasing alpha
            splash_overlay = splash_frame.copy()
            splash_overlay.set_alpha(alpha)
            self.screen.blit(splash_overlay, (0, 0))

            pygame.display.flip()
            self.clock.tick(SPLASH_FPS)


def show_splash(screen: pygame.Surface, clock: pygame.time.Clock,
                textures_dir: str, fonts_dir: str, icons_dir: str,
                pre_render_callback=None) -> None:
    """
    Convenience function to show the splash screen.
    """
    splash = SplashScreen(screen, clock, textures_dir, fonts_dir, icons_dir)
    splash.show(pre_render_callback)
