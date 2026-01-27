"""
Bite Sized Minecraft - Splash Screen Module

A self-contained splash screen that renders a high-resolution isometric block
without depending on the main AssetManager. This module is designed to be
robust against changes in the main codebase.

Author: Bite Sized Minecraft Team
"""

import os
import pygame
from typing import Optional, Tuple

# Splash screen configuration
SPLASH_ICON_SIZE = 128  # Smaller, sharper block
SPLASH_DISPLAY_FRAMES = 120   # 2 seconds at 60fps
SPLASH_FADE_FRAMES = 60       # 1 second fade
SPLASH_FPS = 60

# Colors  
SPLASH_BG_COLOR = (0, 0, 0)  # Black background
END_STONE_COLOR = (219, 222, 158)
END_STONE_BORDER = (180, 183, 130)


class SplashScreen:
    """
    Self-contained splash screen with high-quality isometric block rendering.
    
    Features:
    - Proper textured isometric block using actual end_stone.png
    - Independent texture loading (no AssetManager dependency)
    - Smooth fade transition
    - Black background with centered icon
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
        self.icon = self._create_textured_block()
        self.title_font = self._load_title_font()
    
    def _load_texture(self) -> Optional[pygame.Surface]:
        """Load the end stone texture independently."""
        texture_path = os.path.join(self.textures_dir, "end_stone.png")
        
        if os.path.exists(texture_path):
            try:
                texture = pygame.image.load(texture_path).convert_alpha()
                return texture
            except Exception as e:
                print(f"[Splash] Could not load texture: {e}")
        
        return None
    
    def _load_title_font(self) -> pygame.font.Font:
        """Load the title font with fallbacks."""
        # Try custom font first
        custom_font_names = [
            "Relationship of mélodrame.ttf",
            "Relationship of melodrame.ttf"
        ]
        
        for font_name in custom_font_names:
            custom_path = os.path.join(self.fonts_dir, font_name)
            if os.path.exists(custom_path):
                try:
                    return pygame.font.Font(custom_path, 64)
                except:
                    pass
        
        # Try to find any .ttf font in the fonts directory
        if os.path.exists(self.fonts_dir):
            try:
                for f in os.listdir(self.fonts_dir):
                    if f.endswith('.ttf'):
                        try:
                            return pygame.font.Font(os.path.join(self.fonts_dir, f), 64)
                        except:
                            continue
            except:
                pass
        
        # Fallback to clean system fonts
        clean_fonts = ['Segoe UI Semibold', 'Trebuchet MS', 'Century Gothic', 
                      'Calibri', 'Candara', 'Georgia', 'Palatino Linotype']
        for font_name in clean_fonts:
            try:
                font = pygame.font.SysFont(font_name, 56)
                if font:
                    return font
            except:
                continue
        
        # Ultimate fallback
        return pygame.font.Font(None, 56)
    
    def _create_textured_block(self) -> pygame.Surface:
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
    
    def _create_fallback_icon(self) -> pygame.Surface:
        """Create a simple colored block as fallback."""
        icon = pygame.Surface((SPLASH_ICON_SIZE, SPLASH_ICON_SIZE), pygame.SRCALPHA)
        icon.fill(END_STONE_COLOR)
        pygame.draw.rect(icon, END_STONE_BORDER, icon.get_rect(), 4)
        return icon
    
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
        
        # Get icon (with fallback)
        icon = self.icon if self.icon else self._create_fallback_icon()
        icon_rect = icon.get_rect(center=(self.window_width // 2, 
                                          self.window_height // 2 - icon.get_height() // 4))
        
        # Render title
        title_text = self.title_font.render("Minecraft, Édition Miette", True, (255, 255, 255))
        title_rect = title_text.get_rect(center=(self.window_width // 2, 
                                                  self.window_height // 2 + icon.get_height() // 2 + 50))
        
        # Pre-render game frame for smooth transition
        game_frame = None
        if pre_render_callback:
            try:
                game_frame = pre_render_callback()
            except:
                pass
        
        # Display phase - solid black background with icon
        for frame in range(SPLASH_DISPLAY_FRAMES):
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                if event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                    # Skip splash on input
                    return
            
            self.screen.fill(SPLASH_BG_COLOR)
            self.screen.blit(icon, icon_rect)
            self.screen.blit(title_text, title_rect)
            
            pygame.display.flip()
            self.clock.tick(SPLASH_FPS)
        
        # Fade phase
        if game_frame is None:
            # Create blank game frame
            game_frame = pygame.Surface((self.window_width, self.window_height))
            game_frame.fill(SPLASH_BG_COLOR)
        
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
