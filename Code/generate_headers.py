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

# Isometric settings (2:1 ratio)
TEXTURE_SIZE = 16  # Original Minecraft texture size
SCALE = 2          # Scale factor for output
TILE_WIDTH = TEXTURE_SIZE * SCALE * 2   # 64
TILE_HEIGHT = TEXTURE_SIZE * SCALE      # 32
BLOCK_HEIGHT = TEXTURE_SIZE * SCALE     # 32

# Headers to generate (matching the GIF names)
HEADERS = [
    "Weather",
    "Lighting", 
    "Dimensions",
    "Liquids"
]

# Extended block list - doubled with more visually interesting blocks
# Format: (texture_top, texture_side, texture_bottom)
SHOWCASE_BLOCKS = [
    # Row 1: Nether Core
    ("netherrack.png", "netherrack.png", "netherrack.png"),
    ("nether_bricks.png", "nether_bricks.png", "nether_bricks.png"),
    ("red_nether_bricks.png", "red_nether_bricks.png", "red_nether_bricks.png"),
    ("chiseled_nether_bricks.png", "chiseled_nether_bricks.png", "chiseled_nether_bricks.png"),
    ("cracked_nether_bricks.png", "cracked_nether_bricks.png", "cracked_nether_bricks.png"),
    ("nether_wart_block.png", "nether_wart_block.png", "nether_wart_block.png"),
    
    # Row 2: Warped/Crimson
    ("warped_wart_block.png", "warped_wart_block.png", "warped_wart_block.png"),
    ("crimson_nylium.png", "crimson_nylium_side.png", "netherrack.png"),
    ("warped_nylium.png", "warped_nylium_side.png", "netherrack.png"),
    ("crimson_stem_top.png", "crimson_stem.png", "crimson_stem_top.png"),
    ("warped_stem_top.png", "warped_stem.png", "warped_stem_top.png"),
    ("shroomlight.png", "shroomlight.png", "shroomlight.png"),
    
    # Row 3: Blackstone Family
    ("blackstone.png", "blackstone.png", "blackstone.png"),
    ("polished_blackstone.png", "polished_blackstone.png", "polished_blackstone.png"),
    ("polished_blackstone_bricks.png", "polished_blackstone_bricks.png", "polished_blackstone_bricks.png"),
    ("chiseled_polished_blackstone.png", "chiseled_polished_blackstone.png", "chiseled_polished_blackstone.png"),
    ("cracked_polished_blackstone_bricks.png", "cracked_polished_blackstone_bricks.png", "cracked_polished_blackstone_bricks.png"),
    ("gilded_blackstone.png", "gilded_blackstone.png", "gilded_blackstone.png"),
    
    # Row 4: Basalt & Soul
    ("basalt_top.png", "basalt_side.png", "basalt_top.png"),
    ("polished_basalt_top.png", "polished_basalt_side.png", "polished_basalt_top.png"),
    ("smooth_basalt.png", "smooth_basalt.png", "smooth_basalt.png"),
    ("soul_sand.png", "soul_sand.png", "soul_sand.png"),
    ("soul_soil.png", "soul_soil.png", "soul_soil.png"),
    ("magma.png", "magma.png", "magma.png"),
    
    # Row 5: Precious Nether
    ("ancient_debris_top.png", "ancient_debris_side.png", "ancient_debris_top.png"),
    ("netherite_block.png", "netherite_block.png", "netherite_block.png"),
    ("nether_gold_ore.png", "nether_gold_ore.png", "nether_gold_ore.png"),
    ("nether_quartz_ore.png", "nether_quartz_ore.png", "nether_quartz_ore.png"),
    ("glowstone.png", "glowstone.png", "glowstone.png"),
    ("crying_obsidian.png", "crying_obsidian.png", "crying_obsidian.png"),
    
    # Row 6: End Dimension
    ("end_stone.png", "end_stone.png", "end_stone.png"),
    ("end_stone_bricks.png", "end_stone_bricks.png", "end_stone_bricks.png"),
    ("purpur_block.png", "purpur_block.png", "purpur_block.png"),
    ("purpur_pillar_top.png", "purpur_pillar.png", "purpur_pillar_top.png"),
    ("obsidian.png", "obsidian.png", "obsidian.png"),
    ("dragon_egg.png", "dragon_egg.png", "dragon_egg.png"),
    
    # Row 7: Prismarine & Ocean
    ("prismarine.png", "prismarine.png", "prismarine.png"),
    ("prismarine_bricks.png", "prismarine_bricks.png", "prismarine_bricks.png"),
    ("dark_prismarine.png", "dark_prismarine.png", "dark_prismarine.png"),
    ("sea_lantern.png", "sea_lantern.png", "sea_lantern.png"),
    ("tube_coral_block.png", "tube_coral_block.png", "tube_coral_block.png"),
    ("brain_coral_block.png", "brain_coral_block.png", "brain_coral_block.png"),
    
    # Row 8: Coral & Deep
    ("bubble_coral_block.png", "bubble_coral_block.png", "bubble_coral_block.png"),
    ("fire_coral_block.png", "fire_coral_block.png", "fire_coral_block.png"),
    ("horn_coral_block.png", "horn_coral_block.png", "horn_coral_block.png"),
    ("blue_ice.png", "blue_ice.png", "blue_ice.png"),
    ("packed_ice.png", "packed_ice.png", "packed_ice.png"),
    ("ice.png", "ice.png", "ice.png"),
    
    # Row 9: Amethyst & Copper
    ("amethyst_block.png", "amethyst_block.png", "amethyst_block.png"),
    ("budding_amethyst.png", "budding_amethyst.png", "budding_amethyst.png"),
    ("copper_block.png", "copper_block.png", "copper_block.png"),
    ("exposed_copper.png", "exposed_copper.png", "exposed_copper.png"),
    ("weathered_copper.png", "weathered_copper.png", "weathered_copper.png"),
    ("oxidized_copper.png", "oxidized_copper.png", "oxidized_copper.png"),
    
    # Row 10: Deepslate & Sculk
    ("deepslate_top.png", "deepslate.png", "deepslate_top.png"),
    ("deepslate_bricks.png", "deepslate_bricks.png", "deepslate_bricks.png"),
    ("deepslate_tiles.png", "deepslate_tiles.png", "deepslate_tiles.png"),
    ("chiseled_deepslate.png", "chiseled_deepslate.png", "chiseled_deepslate.png"),
    ("sculk.png", "sculk.png", "sculk.png"),
    ("reinforced_deepslate_top.png", "reinforced_deepslate_side.png", "reinforced_deepslate_bottom.png"),
    
    # Row 11: Precious Ores
    ("diamond_block.png", "diamond_block.png", "diamond_block.png"),
    ("emerald_block.png", "emerald_block.png", "emerald_block.png"),
    ("gold_block.png", "gold_block.png", "gold_block.png"),
    ("iron_block.png", "iron_block.png", "iron_block.png"),
    ("lapis_block.png", "lapis_block.png", "lapis_block.png"),
    ("redstone_block.png", "redstone_block.png", "redstone_block.png"),
    
    # Row 12: Glazed Terracotta (colorful)
    ("cyan_glazed_terracotta.png", "cyan_glazed_terracotta.png", "cyan_glazed_terracotta.png"),
    ("purple_glazed_terracotta.png", "purple_glazed_terracotta.png", "purple_glazed_terracotta.png"),
    ("magenta_glazed_terracotta.png", "magenta_glazed_terracotta.png", "magenta_glazed_terracotta.png"),
    ("red_glazed_terracotta.png", "red_glazed_terracotta.png", "red_glazed_terracotta.png"),
    ("orange_glazed_terracotta.png", "orange_glazed_terracotta.png", "orange_glazed_terracotta.png"),
    ("lime_glazed_terracotta.png", "lime_glazed_terracotta.png", "lime_glazed_terracotta.png"),
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


def create_isometric_block(top_tex: pygame.Surface, left_tex: pygame.Surface, 
                           right_tex: pygame.Surface = None) -> pygame.Surface:
    """
    Create a proper isometric block using 2:1 dimetric projection.
    Uses pixel-perfect rendering for clean edges.
    """
    if right_tex is None:
        right_tex = left_tex
    
    # Output surface size
    out_w = TILE_WIDTH
    out_h = TILE_HEIGHT + BLOCK_HEIGHT
    surface = pygame.Surface((out_w, out_h), pygame.SRCALPHA)
    
    tex_size = TEXTURE_SIZE * SCALE  # 32 pixels
    
    # Scale textures
    if top_tex:
        top_scaled = pygame.transform.scale(top_tex, (tex_size, tex_size))
    if left_tex:
        left_scaled = pygame.transform.scale(left_tex, (tex_size, tex_size))
    if right_tex:
        right_scaled = pygame.transform.scale(right_tex, (tex_size, tex_size))
    
    # TOP FACE: Transform to isometric diamond
    if top_tex:
        for py in range(tex_size):
            for px in range(tex_size):
                col = top_scaled.get_at((px, py))
                if col[3] > 0:
                    # Isometric transform for top face
                    iso_x = (px - py) + tex_size - 1
                    iso_y = (px + py) // 2
                    if 0 <= iso_x < out_w and 0 <= iso_y < out_h:
                        surface.set_at((iso_x, iso_y), col)
    
    # LEFT FACE (darker): Draw as left parallelogram
    if left_tex:
        for py in range(tex_size):
            for px in range(tex_size):
                col = left_scaled.get_at((px, py))
                if col[3] > 0:
                    # Darken for shading
                    r = int(col[0] * 0.6)
                    g = int(col[1] * 0.6)
                    b = int(col[2] * 0.6)
                    darkened = (r, g, b, col[3])
                    
                    # Left face position
                    iso_x = px // 2
                    iso_y = TILE_HEIGHT // 2 + py + (tex_size - px) // 2
                    if 0 <= iso_x < out_w // 2 and 0 <= iso_y < out_h:
                        surface.set_at((iso_x, iso_y), darkened)
    
    # RIGHT FACE (medium): Draw as right parallelogram  
    if right_tex:
        for py in range(tex_size):
            for px in range(tex_size):
                col = right_scaled.get_at((px, py))
                if col[3] > 0:
                    # Medium brightness
                    r = int(col[0] * 0.8)
                    g = int(col[1] * 0.8)
                    b = int(col[2] * 0.8)
                    medium = (r, g, b, col[3])
                    
                    # Right face position
                    iso_x = out_w // 2 + px // 2
                    iso_y = TILE_HEIGHT // 2 + py + px // 2
                    if 0 <= iso_x < out_w and 0 <= iso_y < out_h:
                        surface.set_at((iso_x, iso_y), medium)
    
    return surface


def create_block_grid(blocks: list, grid_cols: int = 6) -> pygame.Surface:
    """Create a grid of isometric blocks for the README showcase."""
    num_blocks = len(blocks)
    grid_rows = (num_blocks + grid_cols - 1) // grid_cols
    
    # Calculate spacing (tighter packing)
    spacing_x = TILE_WIDTH - 8
    spacing_y = TILE_HEIGHT + BLOCK_HEIGHT - 20
    
    # Calculate total size with padding
    pad = 16
    total_w = grid_cols * spacing_x + TILE_WIDTH // 2 + pad * 2
    total_h = grid_rows * spacing_y + BLOCK_HEIGHT + pad * 2
    
    # Create surface with dark background
    surface = pygame.Surface((total_w, total_h), pygame.SRCALPHA)
    surface.fill((20, 20, 25, 255))
    
    # Draw each block
    for i, block_data in enumerate(blocks):
        row = i // grid_cols
        col = i % grid_cols
        
        # Staggered layout for isometric effect
        x = col * spacing_x + pad
        if row % 2 == 1:
            x += spacing_x // 2
        y = row * spacing_y + pad
        
        # Load textures
        top_file, side_file, bottom_file = block_data
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
    print("\nGenerating block showcase grid...")
    grid_surface = create_block_grid(SHOWCASE_BLOCKS, grid_cols=6)
    grid_path = os.path.join(OUTPUT_DIR, "block_showcase.png")
    pygame.image.save(grid_surface, grid_path)
    print(f"  Created: block_showcase.png ({grid_surface.get_width()}x{grid_surface.get_height()})")
    
    print("\nDone! All assets created in References folder.")
    pygame.quit()


if __name__ == "__main__":
    main()
