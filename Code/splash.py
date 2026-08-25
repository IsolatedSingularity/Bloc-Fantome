"""
Bloc Fantôme - Splash Screen Module

A self-contained splash screen that presents the supplied horror wordmark over
an Ancient City block mosaic without depending on the main AssetManager.

Author: Jeffrey Morais
"""

import os
import pygame
from typing import Optional, Tuple

from runtime_paths import REFERENCES_DIR
from ui.fonts import load_ui_font

# Splash screen configuration
SPLASH_ICON_SIZE = 288  # Large connected cube, rendered from the source texture
SPLASH_DISPLAY_FRAMES = 120   # 2 seconds at 60fps
SPLASH_FADE_FRAMES = 60       # 1 second fade
SPLASH_FPS = 60

# Colors  
SPLASH_BG_COLOR = (3, 4, 7)
DEEPSLATE_COLOR = (55, 55, 62)
DEEPSLATE_BORDER = (28, 29, 34)


class SplashScreen:
    """
    Self-contained splash screen with high-quality isometric block rendering.
    
    The approved title image remains the sole centerpiece. Resource-loading
    fallbacks keep source checkouts usable while the release preflight requires
    the supplied artwork.
    """
    
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
        self.texture = self._load_texture()
        self.background_tile = self._create_background_tile()
        self.title_font = self._load_title_font()
        self.title = self._load_title_artwork()
        self.first_presented_at = None
    
    def _load_texture(self) -> Optional[pygame.Surface]:
        """Load the repeating deepslate background texture independently."""
        texture_path = os.path.join(self.textures_dir, "deepslate.png")
        
        if os.path.exists(texture_path):
            try:
                texture = pygame.image.load(texture_path).convert_alpha()
                return texture
            except Exception as e:
                print(f"[Splash] Could not load texture: {e}")
        
        return None
    
    def _load_title_font(self) -> pygame.font.Font:
        """Load the title directly at display resolution."""
        return load_ui_font(68, fonts_dir=self.fonts_dir, bold=True)

    def _render_title(self, text: str) -> pygame.Surface:
        label = text.upper()
        face = self.title_font.render(label, True, (132, 77, 176))
        edge = self.title_font.render(label, True, (64, 30, 91))
        shadow = self.title_font.render(label, True, (16, 8, 24))
        highlight = self.title_font.render(label, True, (188, 131, 226))
        surface = pygame.Surface(
            (face.get_width() + 18, face.get_height() + 20), pygame.SRCALPHA
        )
        # Layered native-resolution offsets give the wordmark depth without
        # magnifying a low-resolution text raster.
        surface.blit(shadow, (10, 12))
        for offset in range(7, 2, -1):
            surface.blit(edge, (offset, offset + 2))
        surface.blit(face, (2, 2))
        highlight.set_alpha(92)
        surface.blit(highlight, (2, 0))
        return surface

    def _load_title_artwork(self) -> pygame.Surface:
        """Load and aspect-fit the approved transparent horror wordmark."""
        title_path = os.path.join(REFERENCES_DIR, "Titles", "horror.png")
        try:
            artwork = pygame.image.load(title_path).convert_alpha()
            bounds = artwork.get_bounding_rect(min_alpha=1)
            if bounds.width and bounds.height:
                artwork = artwork.subsurface(bounds)
            maximum = (self.window_width - 120, self.window_height - 120)
            scale = min(
                maximum[0] / max(1, artwork.get_width()),
                maximum[1] / max(1, artwork.get_height()),
                1.0,
            )
            return pygame.transform.smoothscale(
                artwork,
                (
                    max(1, round(artwork.get_width() * scale)),
                    max(1, round(artwork.get_height() * scale)),
                ),
            )
        except (OSError, pygame.error) as error:
            print(f"[Splash] Could not load horror title: {error}")
            return self._render_title("Bloc Fantôme")
    
    def _legacy_create_textured_block(self) -> pygame.Surface:
        """
        Create a crisp isometric block sprite with proper texture mapping.
        Uses nearest-neighbor scaling for that pixelated Minecraft look.
        """
        target_size = SPLASH_ICON_SIZE
        
        # Isometric dimensions - balanced block height for proper cube appearance
        tile_w = target_size
        tile_h = tile_w // 2
        block_h = tile_h + tile_h // 4  # 1.25x tile height - balanced cube look
        
        W = tile_w
        H = tile_h + block_h
        half_w = W // 2
        half_h = tile_h // 2
        
        # Create surface
        surface = pygame.Surface((W, H), pygame.SRCALPHA)
        
        # Prepare texture - use SCALE (not smoothscale) for crisp pixels
        face_size = half_w
        if self.texture:
            # Scale texture with nearest-neighbor for crisp pixels
            tex = pygame.transform.scale(self.texture, (face_size, face_size))
        else:
            # Create solid color texture as fallback
            tex = pygame.Surface((face_size, face_size))
            tex.fill(END_STONE_COLOR)
        
        # === TOP FACE (brightest) ===
        # Create the top face by transforming the texture into an isometric diamond
        top_face = pygame.Surface((tile_w, tile_h), pygame.SRCALPHA)
        
        # Fill the top face by sampling from texture
        for py in range(tile_h):
            # Calculate the horizontal span at this y
            if py <= half_h:
                span = int(half_w * py / half_h) if half_h > 0 else 0
            else:
                span = int(half_w * (tile_h - py) / half_h) if half_h > 0 else 0
            
            if span <= 0:
                continue
                
            left_x = half_w - span
            right_x = half_w + span
            
            for px in range(left_x, right_x):
                # Map to texture coordinates using isometric transform
                rel_x = px - half_w
                rel_y = py - half_h
                
                # Inverse isometric projection to get texture u,v
                u = (rel_x / half_w + rel_y / half_h) * 0.5 + 0.5 if half_w > 0 and half_h > 0 else 0.5
                v = (-rel_x / half_w + rel_y / half_h) * 0.5 + 0.5 if half_w > 0 and half_h > 0 else 0.5
                
                # Clamp coordinates
                u = max(0, min(0.999, u))
                v = max(0, min(0.999, v))
                
                # Sample texture with integer coords for crisp pixels
                tex_x = int(u * face_size) % face_size
                tex_y = int(v * face_size) % face_size
                
                color = tex.get_at((tex_x, tex_y))
                top_face.set_at((px, py), color)
        
        surface.blit(top_face, (0, 0))
        
        # === LEFT FACE (darkest - 60% brightness) ===
        dark_tex = tex.copy()
        dark_overlay = pygame.Surface((face_size, face_size), pygame.SRCALPHA)
        dark_overlay.fill((0, 0, 0, 100))  # Darken by overlay
        dark_tex.blit(dark_overlay, (0, 0))
        
        # Position left face - starts at (0, half_h)
        for px in range(half_w):
            top_y = half_h + int((px / half_w) * half_h) if half_w > 0 else half_h
            for py in range(block_h):
                screen_y = top_y + py
                if screen_y < H:
                    u = px / half_w if half_w > 0 else 0
                    v = py / block_h if block_h > 0 else 0
                    tex_x = int(u * face_size) % face_size
                    tex_y = int(v * face_size) % face_size
                    color = dark_tex.get_at((tex_x, tex_y))
                    surface.set_at((px, screen_y), color)
        
        # === RIGHT FACE (medium - 80% brightness) ===
        med_tex = tex.copy()
        med_overlay = pygame.Surface((face_size, face_size), pygame.SRCALPHA)
        med_overlay.fill((0, 0, 0, 50))  # Slight darken
        med_tex.blit(med_overlay, (0, 0))
        
        for px in range(half_w):
            # The top edge slopes up from left to right
            screen_px = half_w + px
            top_y = tile_h - 1 - int((px / half_w) * half_h) if half_w > 0 else tile_h - 1
            
            for py in range(block_h):
                screen_y = top_y + py
                if screen_y < H:
                    u = px / half_w if half_w > 0 else 0
                    v = py / block_h if block_h > 0 else 0
                    tex_x = int(u * face_size) % face_size
                    tex_y = int(v * face_size) % face_size
                    color = med_tex.get_at((tex_x, tex_y))
                    surface.set_at((screen_px, screen_y), color)
        
        # === DRAW EDGES ===
        edge_color = (30, 30, 30)
        edge_width = 2
        
        # Top diamond edges
        pygame.draw.line(surface, edge_color, (half_w, 0), (W-1, half_h), edge_width)
        pygame.draw.line(surface, edge_color, (half_w, 0), (0, half_h), edge_width)
        pygame.draw.line(surface, edge_color, (0, half_h), (half_w, tile_h-1), edge_width)
        pygame.draw.line(surface, edge_color, (half_w, tile_h-1), (W-1, half_h), edge_width)
        
        # Bottom edges
        pygame.draw.line(surface, edge_color, (0, half_h + block_h), (half_w, H-1), edge_width)
        pygame.draw.line(surface, edge_color, (half_w, H-1), (W-1, half_h + block_h), edge_width)
        
        # Vertical edges
        pygame.draw.line(surface, edge_color, (0, half_h), (0, half_h + block_h), edge_width)
        pygame.draw.line(surface, edge_color, (W-1, half_h), (W-1, half_h + block_h), edge_width)
        pygame.draw.line(surface, edge_color, (half_w, tile_h-1), (half_w, H-1), edge_width)
        
        return surface
    
    def _create_background_tile(self) -> pygame.Surface:
        """Load the pre-rendered Ancient City mosaic without startup raster work."""
        backgroundPath = os.path.join(
            self.icons_dir, "Splash_Background_Ancient_City.png"
        )
        if os.path.isfile(backgroundPath):
            try:
                return pygame.image.load(backgroundPath).convert()
            except pygame.error:
                pass
        from engine.app_icon import render_ancient_city_background_surface

        texture_names = (
            "deepslate_tiles.png", "cracked_deepslate_tiles.png", "sculk.png",
            "sculk_catalyst_top.png", "reinforced_deepslate_top.png",
            "sculk_shrieker_top.png",
        )
        textures = []
        for name in texture_names:
            path = os.path.join(self.textures_dir, name)
            try:
                textures.append(pygame.image.load(path).convert_alpha())
            except (OSError, pygame.error):
                textures.append(None)
        return render_ancient_city_background_surface(
            textures, (self.window_width, self.window_height)
        )

    def _draw_background(self, target: pygame.Surface) -> None:
        """Tile the background without per-frame surface allocation."""
        for y in range(0, target.get_height(), self.background_tile.get_height()):
            for x in range(0, target.get_width(), self.background_tile.get_width()):
                target.blit(self.background_tile, (x, y))

    def _create_textured_block(self) -> pygame.Surface:
        """Load the approved foreground logo independently of Windows icons."""
        logoPath = os.path.join(self.icons_dir, "Respawn_Anchor.png")
        if os.path.isfile(logoPath):
            try:
                from engine.app_icon import render_splash_logo_surface
                artwork = pygame.image.load(logoPath).convert_alpha()
                return render_splash_logo_surface(artwork, SPLASH_ICON_SIZE)
            except pygame.error:
                pass
        from engine.app_icon import render_splash_logo_surface

        return render_splash_logo_surface(self.texture, SPLASH_ICON_SIZE)

    def _create_fallback_icon(self) -> pygame.Surface:
        """Create a simple colored block as fallback."""
        icon = pygame.Surface((SPLASH_ICON_SIZE, SPLASH_ICON_SIZE), pygame.SRCALPHA)
        icon.fill(DEEPSLATE_COLOR)
        pygame.draw.rect(icon, DEEPSLATE_BORDER, icon.get_rect(), 4)
        return icon
    
    def present(self) -> None:
        """Put the splash on screen immediately before expensive startup work."""
        title_rect = self.title.get_rect(center=(
            self.window_width // 2,
            self.window_height // 2,
        ))
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
        title_rect = self.title.get_rect(center=(self.window_width // 2,
                                                  self.window_height // 2))
        
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
            # Create blank game frame
            game_frame = pygame.Surface((self.window_width, self.window_height))
            self._draw_background(game_frame)
        
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
