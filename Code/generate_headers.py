"""
Generate Minecraft-style button header PNGs for README sections.
These match the button style used in the app (grey background, white text with shadow).
"""

import pygame
import os

# Initialize pygame
pygame.init()

# Output directory
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "References")

# Button dimensions (wide for section headers)
BUTTON_WIDTH = 400
BUTTON_HEIGHT = 50

# Colors matching the app's button style
BG_COLOR_DARK = (55, 55, 60)      # Dark grey background
BG_COLOR_LIGHT = (75, 75, 80)     # Lighter grey for top
BORDER_DARK = (30, 30, 35)        # Dark border (bottom/right)
BORDER_LIGHT = (100, 100, 110)    # Light border (top/left)
TEXT_COLOR = (255, 255, 255)      # White text
SHADOW_COLOR = (30, 30, 30)       # Dark shadow

# Headers to generate (matching the GIF names)
HEADERS = [
    "Weather",
    "Lighting", 
    "Dimensions",
    "Darkness"
]


def create_minecraft_button(text: str, width: int = BUTTON_WIDTH, height: int = BUTTON_HEIGHT) -> pygame.Surface:
    """
    Create a Minecraft-style button surface with the given text.
    Matches the visual style of buttons in the app.
    """
    surface = pygame.Surface((width, height), pygame.SRCALPHA)
    
    # Draw main button background with gradient effect
    # Top half slightly lighter
    top_rect = pygame.Rect(0, 0, width, height // 2)
    bottom_rect = pygame.Rect(0, height // 2, width, height // 2)
    
    pygame.draw.rect(surface, BG_COLOR_LIGHT, top_rect)
    pygame.draw.rect(surface, BG_COLOR_DARK, bottom_rect)
    
    # Draw 3D-style border (light top-left, dark bottom-right)
    # Top border (light)
    pygame.draw.line(surface, BORDER_LIGHT, (0, 0), (width - 1, 0), 2)
    # Left border (light)
    pygame.draw.line(surface, BORDER_LIGHT, (0, 0), (0, height - 1), 2)
    # Bottom border (dark)
    pygame.draw.line(surface, BORDER_DARK, (0, height - 1), (width - 1, height - 1), 2)
    # Right border (dark)
    pygame.draw.line(surface, BORDER_DARK, (width - 1, 0), (width - 1, height - 1), 2)
    
    # Inner highlight line
    pygame.draw.line(surface, (90, 90, 95), (2, 2), (width - 3, 2), 1)
    
    # Load font (use system font that looks good)
    try:
        font = pygame.font.SysFont("Segoe UI Semibold", 28)
    except:
        font = pygame.font.Font(None, 32)
    
    # Render text shadow first
    shadow_surf = font.render(text, True, SHADOW_COLOR)
    shadow_rect = shadow_surf.get_rect(center=(width // 2 + 2, height // 2 + 2))
    surface.blit(shadow_surf, shadow_rect)
    
    # Render main text
    text_surf = font.render(text, True, TEXT_COLOR)
    text_rect = text_surf.get_rect(center=(width // 2, height // 2))
    surface.blit(text_surf, text_rect)
    
    return surface


def main():
    print("Generating Minecraft-style header buttons...")
    print(f"Output directory: {OUTPUT_DIR}")
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    for header_text in HEADERS:
        # Create the button
        button_surface = create_minecraft_button(header_text)
        
        # Save as PNG
        filename = f"{header_text}.png"
        filepath = os.path.join(OUTPUT_DIR, filename)
        pygame.image.save(button_surface, filepath)
        print(f"  Created: {filename}")
    
    print("\nDone! Header PNGs created in References folder.")
    pygame.quit()


if __name__ == "__main__":
    main()
