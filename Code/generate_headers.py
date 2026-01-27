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

# Isometric settings - proper 2:1 ratio
BLOCK_SIZE = 32  # Size of each block sprite
ISO_W = 32       # Isometric tile width  
ISO_H = 16       # Isometric tile height (2:1 ratio)
ISO_D = 20       # Block depth/height

# Headers to generate (matching the GIF names)
HEADERS = [
    "Weather",
    "Lighting", 
    "Dimensions",
    "Liquids"
]

# Wide horizontal block showcase - 12 columns x 6 rows = 72 blocks
SHOWCASE_BLOCKS = [
    # Row 1: Nether Terrain
    ("netherrack.png", "netherrack.png"),
    ("nether_bricks.png", "nether_bricks.png"),
    ("red_nether_bricks.png", "red_nether_bricks.png"),
    ("chiseled_nether_bricks.png", "chiseled_nether_bricks.png"),
    ("cracked_nether_bricks.png", "cracked_nether_bricks.png"),
    ("nether_wart_block.png", "nether_wart_block.png"),
    ("warped_wart_block.png", "warped_wart_block.png"),
    ("crimson_nylium.png", "crimson_nylium_side.png"),
    ("warped_nylium.png", "warped_nylium_side.png"),
    ("soul_sand.png", "soul_sand.png"),
    ("soul_soil.png", "soul_soil.png"),
    ("magma.png", "magma.png"),
    
    # Row 2: Blackstone & Basalt
    ("blackstone.png", "blackstone.png"),
    ("polished_blackstone.png", "polished_blackstone.png"),
    ("polished_blackstone_bricks.png", "polished_blackstone_bricks.png"),
    ("chiseled_polished_blackstone.png", "chiseled_polished_blackstone.png"),
    ("gilded_blackstone.png", "gilded_blackstone.png"),
    ("basalt_top.png", "basalt_side.png"),
    ("polished_basalt_top.png", "polished_basalt_side.png"),
    ("smooth_basalt.png", "smooth_basalt.png"),
    ("ancient_debris_top.png", "ancient_debris_side.png"),
    ("netherite_block.png", "netherite_block.png"),
    ("glowstone.png", "glowstone.png"),
    ("shroomlight.png", "shroomlight.png"),
    
    # Row 3: End & Obsidian
    ("end_stone.png", "end_stone.png"),
    ("end_stone_bricks.png", "end_stone_bricks.png"),
    ("purpur_block.png", "purpur_block.png"),
    ("purpur_pillar_top.png", "purpur_pillar.png"),
    ("obsidian.png", "obsidian.png"),
    ("crying_obsidian.png", "crying_obsidian.png"),
    ("dragon_egg.png", "dragon_egg.png"),
    ("prismarine.png", "prismarine.png"),
    ("prismarine_bricks.png", "prismarine_bricks.png"),
    ("dark_prismarine.png", "dark_prismarine.png"),
    ("sea_lantern.png", "sea_lantern.png"),
    ("blue_ice.png", "blue_ice.png"),
    
    # Row 4: Coral & Amethyst
    ("tube_coral_block.png", "tube_coral_block.png"),
    ("brain_coral_block.png", "brain_coral_block.png"),
    ("bubble_coral_block.png", "bubble_coral_block.png"),
    ("fire_coral_block.png", "fire_coral_block.png"),
    ("horn_coral_block.png", "horn_coral_block.png"),
    ("amethyst_block.png", "amethyst_block.png"),
    ("budding_amethyst.png", "budding_amethyst.png"),
    ("copper_block.png", "copper_block.png"),
    ("exposed_copper.png", "exposed_copper.png"),
    ("weathered_copper.png", "weathered_copper.png"),
    ("oxidized_copper.png", "oxidized_copper.png"),
    ("raw_copper_block.png", "raw_copper_block.png"),
    
    # Row 5: Deepslate & Sculk
    ("deepslate_top.png", "deepslate.png"),
    ("cobbled_deepslate.png", "cobbled_deepslate.png"),
    ("polished_deepslate.png", "polished_deepslate.png"),
    ("deepslate_bricks.png", "deepslate_bricks.png"),
    ("deepslate_tiles.png", "deepslate_tiles.png"),
    ("chiseled_deepslate.png", "chiseled_deepslate.png"),
    ("sculk.png", "sculk.png"),
    ("diamond_block.png", "diamond_block.png"),
    ("emerald_block.png", "emerald_block.png"),
    ("gold_block.png", "gold_block.png"),
    ("iron_block.png", "iron_block.png"),
    ("lapis_block.png", "lapis_block.png"),
    
    # Row 6: Colorful Glazed
    ("cyan_glazed_terracotta.png", "cyan_glazed_terracotta.png"),
    ("purple_glazed_terracotta.png", "purple_glazed_terracotta.png"),
    ("magenta_glazed_terracotta.png", "magenta_glazed_terracotta.png"),
    ("red_glazed_terracotta.png", "red_glazed_terracotta.png"),
    ("orange_glazed_terracotta.png", "orange_glazed_terracotta.png"),
    ("yellow_glazed_terracotta.png", "yellow_glazed_terracotta.png"),
    ("lime_glazed_terracotta.png", "lime_glazed_terracotta.png"),
    ("green_glazed_terracotta.png", "green_glazed_terracotta.png"),
    ("light_blue_glazed_terracotta.png", "light_blue_glazed_terracotta.png"),
    ("blue_glazed_terracotta.png", "blue_glazed_terracotta.png"),
    ("pink_glazed_terracotta.png", "pink_glazed_terracotta.png"),
    ("redstone_block.png", "redstone_block.png"),
]


def create_minecraft_button(text: str, width: int = BUTTON_WIDTH, height: int = BUTTON_HEIGHT) -> pygame.Surface:
    """
    Create a Minecraft-style button surface with the given text.
    Matches the visual style of buttons in the app.
    """
    surface = pygame.Surface((width, height), pygame.SRCALPHA)
    
    # Draw main button background with gradient effect
    top_rect = pygame.Rect(0, 0, width, height // 2)
    bottom_rect = pygame.Rect(0, height // 2, width, height // 2)
    
    pygame.draw.rect(surface, BG_COLOR_LIGHT, top_rect)
    pygame.draw.rect(surface, BG_COLOR_DARK, bottom_rect)
    
    # Draw 3D-style border
    pygame.draw.line(surface, BORDER_LIGHT, (0, 0), (width - 1, 0), 2)
    pygame.draw.line(surface, BORDER_LIGHT, (0, 0), (0, height - 1), 2)
    pygame.draw.line(surface, BORDER_DARK, (0, height - 1), (width - 1, height - 1), 2)
    pygame.draw.line(surface, BORDER_DARK, (width - 1, 0), (width - 1, height - 1), 2)
    pygame.draw.line(surface, (90, 90, 95), (2, 2), (width - 3, 2), 1)
    
    try:
        font = pygame.font.SysFont("Segoe UI Semibold", 28)
    except:
        font = pygame.font.Font(None, 32)
    
    shadow_surf = font.render(text, True, SHADOW_COLOR)
    shadow_rect = shadow_surf.get_rect(center=(width // 2 + 2, height // 2 + 2))
    surface.blit(shadow_surf, shadow_rect)
    
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


def draw_isometric_block(surface: pygame.Surface, x: int, y: int, 
                         top_tex: pygame.Surface, side_tex: pygame.Surface):
    """
    Draw a single isometric block at position (x, y) on the surface.
    Uses proper 2:1 dimetric projection with sheared faces.
    """
    # Scale textures to 16x16
    tex_size = 16
    if top_tex:
        top = pygame.transform.scale(top_tex, (tex_size, tex_size))
    if side_tex:
        side = pygame.transform.scale(side_tex, (tex_size, tex_size))
    
    # Block dimensions
    w = ISO_W  # 32
    h = ISO_H  # 16
    d = ISO_D  # 20
    
    # Draw TOP face as diamond
    if top_tex:
        for ty in range(tex_size):
            for tx in range(tex_size):
                col = top.get_at((tx, ty))
                if col[3] > 0:
                    # Map texture coords to isometric diamond
                    # tx: 0->16 maps to diamond width
                    # ty: 0->16 maps to diamond height
                    iso_x = x + (tx - ty) + tex_size
                    iso_y = y + (tx + ty) // 2
                    if iso_x >= 0 and iso_y >= 0:
                        surface.set_at((int(iso_x), int(iso_y)), col)
    
    # Draw LEFT face (darker)
    if side_tex:
        for ty in range(tex_size):
            for tx in range(tex_size):
                col = side.get_at((tx, ty))
                if col[3] > 0:
                    # Darken
                    r = int(col[0] * 0.6)
                    g = int(col[1] * 0.6)
                    b = int(col[2] * 0.6)
                    dark_col = (r, g, b, col[3])
                    
                    # Left face: vertical with slight slant
                    fx = tx / tex_size  # 0 to 1
                    fy = ty / tex_size  # 0 to 1
                    
                    iso_x = x + int(fx * (w // 2 - 1))
                    iso_y = y + h // 2 + int(fy * d) + int((1 - fx) * (h // 2))
                    
                    if iso_x >= 0 and iso_y >= 0:
                        surface.set_at((int(iso_x), int(iso_y)), dark_col)
    
    # Draw RIGHT face (medium brightness)
    if side_tex:
        for ty in range(tex_size):
            for tx in range(tex_size):
                col = side.get_at((tx, ty))
                if col[3] > 0:
                    # Medium brightness
                    r = int(col[0] * 0.8)
                    g = int(col[1] * 0.8)
                    b = int(col[2] * 0.8)
                    med_col = (r, g, b, col[3])
                    
                    fx = tx / tex_size
                    fy = ty / tex_size
                    
                    iso_x = x + w // 2 + int(fx * (w // 2 - 1))
                    iso_y = y + h // 2 + int(fy * d) + int(fx * (h // 2))
                    
                    if iso_x >= 0 and iso_y >= 0:
                        surface.set_at((int(iso_x), int(iso_y)), med_col)


def create_block_grid(blocks: list, grid_cols: int = 12) -> pygame.Surface:
    """Create a wide horizontal grid of isometric blocks."""
    num_blocks = len(blocks)
    grid_rows = (num_blocks + grid_cols - 1) // grid_cols
    
    # Spacing between blocks
    space_x = ISO_W + 2
    space_y = ISO_H + ISO_D - 4
    
    # Calculate total size
    pad = 12
    total_w = grid_cols * space_x + pad * 2
    total_h = grid_rows * space_y + ISO_D + pad * 2
    
    # Dark background
    surface = pygame.Surface((total_w, total_h), pygame.SRCALPHA)
    surface.fill((20, 20, 25, 255))
    
    for i, block_data in enumerate(blocks):
        row = i // grid_cols
        col = i % grid_cols
        
        x = pad + col * space_x
        y = pad + row * space_y
        
        top_file, side_file = block_data
        top_tex = load_texture(top_file)
        side_tex = load_texture(side_file)
        
        if top_tex and side_tex:
            draw_isometric_block(surface, x, y, top_tex, side_tex)
    
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
    
    # Generate wide horizontal block grid (12 columns)
    print("\nGenerating block showcase grid (12 cols x 6 rows)...")
    grid_surface = create_block_grid(SHOWCASE_BLOCKS, grid_cols=12)
    grid_path = os.path.join(OUTPUT_DIR, "block_showcase.png")
    pygame.image.save(grid_surface, grid_path)
    print(f"  Created: block_showcase.png ({grid_surface.get_width()}x{grid_surface.get_height()})")
    
    print("\nDone! All assets created in References folder.")
    pygame.quit()


if __name__ == "__main__":
    main()
