"""
Generate Minecraft-style button header PNGs for README sections.
These match the button style used in the app (grey background, white text with shadow).

Also generates isometric block grid showcases.
"""

import pygame
import os
import sys
import math

# Initialize pygame
pygame.init()
pygame.display.set_mode((1, 1), pygame.HIDDEN)  # Hidden display for image loading

# Output directory
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "References")
TEXTURES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Assets", "Texture Hub", "blocks")

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

# Isometric settings
TILE_WIDTH = 48
TILE_HEIGHT = 24
BLOCK_HEIGHT = 28

# Headers to generate (matching the GIF names)
HEADERS = [
    "Weather",
    "Lighting", 
    "Dimensions",
    "Liquids"
]

# Nether and End blocks for the showcase grid
# Format: (texture_top, texture_side, texture_bottom, tint_top, tint_side)
NETHER_END_BLOCKS = [
    # Nether blocks
    ("netherrack.png", "netherrack.png", "netherrack.png", None, None),
    ("nether_bricks.png", "nether_bricks.png", "nether_bricks.png", None, None),
    ("red_nether_bricks.png", "red_nether_bricks.png", "red_nether_bricks.png", None, None),
    ("soul_sand.png", "soul_sand.png", "soul_sand.png", None, None),
    ("soul_soil.png", "soul_soil.png", "soul_soil.png", None, None),
    ("glowstone.png", "glowstone.png", "glowstone.png", None, None),
    ("magma.png", "magma.png", "magma.png", None, None),
    ("nether_wart_block.png", "nether_wart_block.png", "nether_wart_block.png", None, None),
    ("warped_wart_block.png", "warped_wart_block.png", "warped_wart_block.png", None, None),
    ("shroomlight.png", "shroomlight.png", "shroomlight.png", None, None),
    ("blackstone.png", "blackstone.png", "blackstone.png", None, None),
    ("polished_blackstone.png", "polished_blackstone.png", "polished_blackstone.png", None, None),
    ("polished_blackstone_bricks.png", "polished_blackstone_bricks.png", "polished_blackstone_bricks.png", None, None),
    ("gilded_blackstone.png", "gilded_blackstone.png", "gilded_blackstone.png", None, None),
    ("basalt_top.png", "basalt_side.png", "basalt_top.png", None, None),
    ("polished_basalt_top.png", "polished_basalt_side.png", "polished_basalt_top.png", None, None),
    ("ancient_debris_top.png", "ancient_debris_side.png", "ancient_debris_top.png", None, None),
    ("netherite_block.png", "netherite_block.png", "netherite_block.png", None, None),
    ("crying_obsidian.png", "crying_obsidian.png", "crying_obsidian.png", None, None),
    ("crimson_nylium.png", "crimson_nylium_side.png", "netherrack.png", None, None),
    ("warped_nylium.png", "warped_nylium_side.png", "netherrack.png", None, None),
    ("crimson_stem_top.png", "crimson_stem.png", "crimson_stem_top.png", None, None),
    ("warped_stem_top.png", "warped_stem.png", "warped_stem_top.png", None, None),
    ("crimson_planks.png", "crimson_planks.png", "crimson_planks.png", None, None),
    ("warped_planks.png", "warped_planks.png", "warped_planks.png", None, None),
    # End blocks
    ("end_stone.png", "end_stone.png", "end_stone.png", None, None),
    ("end_stone_bricks.png", "end_stone_bricks.png", "end_stone_bricks.png", None, None),
    ("purpur_block.png", "purpur_block.png", "purpur_block.png", None, None),
    ("purpur_pillar_top.png", "purpur_pillar.png", "purpur_pillar_top.png", None, None),
    ("obsidian.png", "obsidian.png", "obsidian.png", None, None),
    # Bonus interesting blocks to fill grid
    ("prismarine.png", "prismarine.png", "prismarine.png", None, None),
    ("dark_prismarine.png", "dark_prismarine.png", "dark_prismarine.png", None, None),
    ("sea_lantern.png", "sea_lantern.png", "sea_lantern.png", None, None),
    ("amethyst_block.png", "amethyst_block.png", "amethyst_block.png", None, None),
    ("copper_block.png", "copper_block.png", "copper_block.png", None, None),
    ("oxidized_copper.png", "oxidized_copper.png", "oxidized_copper.png", None, None),
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


def load_texture(filename: str) -> pygame.Surface:
    """Load a texture from the blocks folder."""
    path = os.path.join(TEXTURES_DIR, filename)
    if os.path.exists(path):
        return pygame.image.load(path).convert_alpha()
    return None


def apply_brightness(surface: pygame.Surface, brightness: float) -> pygame.Surface:
    """Apply brightness modifier to a surface."""
    result = surface.copy()
    dark = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    if brightness < 1.0:
        dark.fill((0, 0, 0, int(255 * (1.0 - brightness))))
        result.blit(dark, (0, 0))
    return result


def create_isometric_block(top_tex: pygame.Surface, side_tex: pygame.Surface, 
                           front_tex: pygame.Surface = None) -> pygame.Surface:
    """Create an isometric block sprite from face textures."""
    if front_tex is None:
        front_tex = side_tex
    
    # Scale textures to tile size
    face_w = TILE_WIDTH // 2
    face_h = TILE_HEIGHT // 2
    
    # Create output surface
    out_w = TILE_WIDTH
    out_h = TILE_HEIGHT + BLOCK_HEIGHT
    surface = pygame.Surface((out_w, out_h), pygame.SRCALPHA)
    
    center_x = out_w // 2
    top_y = 0
    
    # === TOP FACE ===
    if top_tex:
        scaled_top = pygame.transform.scale(top_tex, (face_w, face_w))
        # Transform to isometric diamond
        top_points = [
            (center_x, top_y),  # Top
            (out_w, top_y + TILE_HEIGHT // 2),  # Right
            (center_x, top_y + TILE_HEIGHT),  # Bottom
            (0, top_y + TILE_HEIGHT // 2),  # Left
        ]
        # Simple approach: scale and rotate
        top_iso = pygame.transform.scale(top_tex, (TILE_WIDTH, TILE_HEIGHT))
        # Create diamond mask
        mask_surf = pygame.Surface((TILE_WIDTH, TILE_HEIGHT), pygame.SRCALPHA)
        pygame.draw.polygon(mask_surf, (255, 255, 255, 255), [
            (TILE_WIDTH // 2, 0),
            (TILE_WIDTH, TILE_HEIGHT // 2),
            (TILE_WIDTH // 2, TILE_HEIGHT),
            (0, TILE_HEIGHT // 2)
        ])
        top_iso.blit(mask_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        surface.blit(top_iso, (0, top_y))
    
    # === LEFT FACE (darker) ===
    if side_tex:
        scaled_side = pygame.transform.scale(side_tex, (TILE_WIDTH // 2, BLOCK_HEIGHT))
        scaled_side = apply_brightness(scaled_side, 0.7)
        # Draw as parallelogram
        left_y = TILE_HEIGHT // 2
        for y in range(BLOCK_HEIGHT):
            for x in range(TILE_WIDTH // 2):
                px = x
                py = left_y + y + (TILE_WIDTH // 2 - x) // 2
                if py < out_h:
                    col = scaled_side.get_at((x, y))
                    if col[3] > 0:
                        surface.set_at((px, py), col)
    
    # === RIGHT FACE (medium) ===
    if front_tex:
        scaled_front = pygame.transform.scale(front_tex, (TILE_WIDTH // 2, BLOCK_HEIGHT))
        scaled_front = apply_brightness(scaled_front, 0.85)
        # Draw as parallelogram
        right_x = TILE_WIDTH // 2
        right_y = TILE_HEIGHT // 2
        for y in range(BLOCK_HEIGHT):
            for x in range(TILE_WIDTH // 2):
                px = right_x + x
                py = right_y + y + x // 2
                if py < out_h and px < out_w:
                    col = scaled_front.get_at((x, y))
                    if col[3] > 0:
                        surface.set_at((px, py), col)
    
    return surface


def create_block_grid(blocks: list, grid_cols: int = 6) -> pygame.Surface:
    """Create a grid of isometric blocks for the README showcase."""
    num_blocks = len(blocks)
    grid_rows = (num_blocks + grid_cols - 1) // grid_cols
    
    # Calculate spacing
    spacing_x = TILE_WIDTH + 4
    spacing_y = TILE_HEIGHT + BLOCK_HEIGHT - 10
    
    # Calculate total size
    total_w = grid_cols * spacing_x + TILE_WIDTH // 2
    total_h = grid_rows * spacing_y + BLOCK_HEIGHT + 20
    
    # Create surface with dark background
    surface = pygame.Surface((total_w, total_h), pygame.SRCALPHA)
    surface.fill((25, 25, 30, 255))
    
    # Draw each block
    for i, block_data in enumerate(blocks):
        row = i // grid_cols
        col = i % grid_cols
        
        # Isometric offset (alternate rows)
        x = col * spacing_x + (TILE_WIDTH // 4 if row % 2 else 0) + 10
        y = row * spacing_y + 10
        
        # Load textures
        top_file, side_file, bottom_file, tint_top, tint_side = block_data
        top_tex = load_texture(top_file)
        side_tex = load_texture(side_file)
        
        if top_tex and side_tex:
            block_sprite = create_isometric_block(top_tex, side_tex, side_tex)
            surface.blit(block_sprite, (x, y))
    
    return surface


def main():
    print("Generating Minecraft-style header buttons...")
    print(f"Output directory: {OUTPUT_DIR}")
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Generate header buttons
    for header_text in HEADERS:
        button_surface = create_minecraft_button(header_text)
        filename = f"{header_text}.png"
        filepath = os.path.join(OUTPUT_DIR, filename)
        pygame.image.save(button_surface, filepath)
        print(f"  Created: {filename}")
    
    # Generate block grid showcase
    print("\nGenerating Nether/End block grid...")
    grid_surface = create_block_grid(NETHER_END_BLOCKS, grid_cols=6)
    grid_path = os.path.join(OUTPUT_DIR, "block_showcase.png")
    pygame.image.save(grid_surface, grid_path)
    print(f"  Created: block_showcase.png ({grid_surface.get_width()}x{grid_surface.get_height()})")
    
    print("\nDone! All assets created in References folder.")
    pygame.quit()


if __name__ == "__main__":
    main()
