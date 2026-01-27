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

# Isometric block dimensions
BLOCK_W = 32   # Width of isometric block
BLOCK_H = 18   # Height of top face (half width for 2:1)
BLOCK_D = 20   # Depth/vertical height of sides

# Headers to generate (matching the GIF names)
HEADERS = [
    "Weather",
    "Lighting", 
    "Dimensions",
    "Liquids"
]

# Expanded block showcase - 12 columns x 12 rows = 144 blocks
SHOWCASE_BLOCKS = [
    # Row 1: Basic Overworld
    "grass_block_top.png", "dirt.png", "stone.png", "cobblestone.png",
    "mossy_cobblestone.png", "gravel.png", "sand.png", "sandstone_top.png",
    "red_sand.png", "red_sandstone_top.png", "clay.png", "mud.png",
    
    # Row 2: Stone Variants
    "granite.png", "polished_granite.png", "diorite.png", "polished_diorite.png",
    "andesite.png", "polished_andesite.png", "calcite.png", "tuff.png",
    "dripstone_block.png", "moss_block.png", "rooted_dirt.png", "podzol_top.png",
    
    # Row 3: Ores
    "coal_ore.png", "iron_ore.png", "copper_ore.png", "gold_ore.png",
    "diamond_ore.png", "emerald_ore.png", "lapis_ore.png", "redstone_ore.png",
    "deepslate_coal_ore.png", "deepslate_iron_ore.png", "deepslate_diamond_ore.png", "nether_gold_ore.png",
    
    # Row 4: Ore Blocks
    "coal_block.png", "iron_block.png", "copper_block.png", "gold_block.png",
    "diamond_block.png", "emerald_block.png", "lapis_block.png", "redstone_block.png",
    "raw_iron_block.png", "raw_copper_block.png", "raw_gold_block.png", "netherite_block.png",
    
    # Row 5: Wood Planks
    "oak_planks.png", "spruce_planks.png", "birch_planks.png", "jungle_planks.png",
    "acacia_planks.png", "dark_oak_planks.png", "mangrove_planks.png", "cherry_planks.png",
    "bamboo_planks.png", "crimson_planks.png", "warped_planks.png", "bamboo_mosaic.png",
    
    # Row 6: Wood Logs
    "oak_log_top.png", "spruce_log_top.png", "birch_log_top.png", "jungle_log_top.png",
    "acacia_log_top.png", "dark_oak_log_top.png", "mangrove_log_top.png", "cherry_log_top.png",
    "crimson_stem_top.png", "warped_stem_top.png", "stripped_oak_log_top.png", "stripped_birch_log_top.png",
    
    # Row 7: Nether Blocks
    "netherrack.png", "nether_bricks.png", "red_nether_bricks.png", "cracked_nether_bricks.png",
    "nether_wart_block.png", "warped_wart_block.png", "crimson_nylium.png", "warped_nylium.png",
    "soul_sand.png", "soul_soil.png", "magma.png", "glowstone.png",
    
    # Row 8: Blackstone & Basalt
    "blackstone.png", "polished_blackstone.png", "polished_blackstone_bricks.png", "chiseled_polished_blackstone.png",
    "gilded_blackstone.png", "basalt_top.png", "polished_basalt_top.png", "smooth_basalt.png",
    "ancient_debris_top.png", "shroomlight.png", "crying_obsidian.png", "obsidian.png",
    
    # Row 9: End & Prismarine
    "end_stone.png", "end_stone_bricks.png", "purpur_block.png", "purpur_pillar_top.png",
    "prismarine.png", "prismarine_bricks.png", "dark_prismarine.png", "sea_lantern.png",
    "blue_ice.png", "packed_ice.png", "ice.png", "snow.png",
    
    # Row 10: Coral & Amethyst  
    "tube_coral_block.png", "brain_coral_block.png", "bubble_coral_block.png", "fire_coral_block.png",
    "horn_coral_block.png", "dead_tube_coral_block.png", "amethyst_block.png", "budding_amethyst.png",
    "exposed_copper.png", "weathered_copper.png", "oxidized_copper.png", "cut_copper.png",
    
    # Row 11: Deepslate & Sculk
    "deepslate_top.png", "cobbled_deepslate.png", "polished_deepslate.png", "deepslate_bricks.png",
    "deepslate_tiles.png", "chiseled_deepslate.png", "reinforced_deepslate_top.png", "sculk.png",
    "sculk_catalyst_top.png", "mud_bricks.png", "packed_mud.png", "muddy_mangrove_roots_top.png",
    
    # Row 12: Glazed Terracotta
    "white_glazed_terracotta.png", "orange_glazed_terracotta.png", "magenta_glazed_terracotta.png", "light_blue_glazed_terracotta.png",
    "yellow_glazed_terracotta.png", "lime_glazed_terracotta.png", "pink_glazed_terracotta.png", "cyan_glazed_terracotta.png",
    "purple_glazed_terracotta.png", "blue_glazed_terracotta.png", "green_glazed_terracotta.png", "red_glazed_terracotta.png",
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


def draw_isometric_block(surface: pygame.Surface, x: int, y: int, texture: pygame.Surface):
    """
    Draw a proper isometric block using polygon-based rendering.
    Creates clean 2:1 dimetric projection with textured faces.
    """
    if texture is None:
        return
    
    # Scale texture to fit our block size
    tex_size = 16
    tex = pygame.transform.scale(texture, (tex_size, tex_size))
    
    w = BLOCK_W      # 32
    h = BLOCK_H      # 18 (half of width for 2:1 ratio)
    d = BLOCK_D      # 20
    
    # Define the 6 vertices of the isometric block
    # Top face vertices (diamond shape)
    top_center = (x + w // 2, y)
    top_left = (x, y + h // 2)
    top_right = (x + w, y + h // 2)
    top_bottom = (x + w // 2, y + h)
    
    # Bottom vertices (same x positions, shifted down by depth)
    bot_left = (x, y + h // 2 + d)
    bot_right = (x + w, y + h // 2 + d)
    bot_bottom = (x + w // 2, y + h + d)
    
    # Get average color from texture for solid fill
    def get_avg_color(surf):
        total_r, total_g, total_b = 0, 0, 0
        count = 0
        for py in range(surf.get_height()):
            for px in range(surf.get_width()):
                c = surf.get_at((px, py))
                if c[3] > 128:
                    total_r += c[0]
                    total_g += c[1]
                    total_b += c[2]
                    count += 1
        if count == 0:
            return (128, 128, 128)
        return (total_r // count, total_g // count, total_b // count)
    
    base_color = get_avg_color(tex)
    
    # Draw LEFT face (darkest) 
    left_color = (int(base_color[0] * 0.55), int(base_color[1] * 0.55), int(base_color[2] * 0.55))
    pygame.draw.polygon(surface, left_color, [top_left, top_bottom, bot_bottom, bot_left])
    
    # Draw RIGHT face (medium brightness)
    right_color = (int(base_color[0] * 0.75), int(base_color[1] * 0.75), int(base_color[2] * 0.75))
    pygame.draw.polygon(surface, right_color, [top_right, bot_right, bot_bottom, top_bottom])
    
    # Draw TOP face (brightest) with texture sampling
    # Create a surface for the top face and transform it
    top_surf = pygame.Surface((w, h), pygame.SRCALPHA)
    
    # Sample texture onto diamond shape
    for py in range(h):
        for px in range(w):
            # Check if point is inside diamond
            # Diamond from (w/2, 0) to (0, h/2) to (w/2, h) to (w, h/2)
            cx, cy = w // 2, h // 2
            dx = abs(px - cx) / (w / 2)
            dy = abs(py - cy) / (h / 2)
            if dx + dy <= 1.0:
                # Map to texture coordinates
                # Rotate 45 degrees conceptually
                u = (px / w + py / h) / 2
                v = (py / h - px / w + 1) / 2
                tx = int(u * (tex_size - 1)) % tex_size
                ty = int(v * (tex_size - 1)) % tex_size
                color = tex.get_at((tx, ty))
                if color[3] > 0:
                    top_surf.set_at((px, py), color)
    
    surface.blit(top_surf, (x, y))
    
    # Draw outlines for clean edges
    outline_color = (30, 30, 35)
    # Top diamond
    pygame.draw.lines(surface, outline_color, True, [top_center, top_right, top_bottom, top_left], 1)
    # Left face edges
    pygame.draw.line(surface, outline_color, top_left, bot_left, 1)
    pygame.draw.line(surface, outline_color, top_bottom, bot_bottom, 1)
    # Right face edges  
    pygame.draw.line(surface, outline_color, top_right, bot_right, 1)
    # Bottom edges
    pygame.draw.line(surface, outline_color, bot_left, bot_bottom, 1)
    pygame.draw.line(surface, outline_color, bot_bottom, bot_right, 1)


def create_block_grid(blocks: list, grid_cols: int = 12) -> pygame.Surface:
    """Create a wide horizontal grid of isometric blocks."""
    num_blocks = len(blocks)
    grid_rows = (num_blocks + grid_cols - 1) // grid_cols
    
    # Spacing between blocks
    space_x = BLOCK_W + 4
    space_y = BLOCK_H + BLOCK_D + 2
    
    # Calculate total size
    pad = 16
    total_w = grid_cols * space_x + pad * 2
    total_h = grid_rows * space_y + pad * 2
    
    # Dark background
    surface = pygame.Surface((total_w, total_h), pygame.SRCALPHA)
    surface.fill((25, 25, 30, 255))
    
    for i, block_file in enumerate(blocks):
        row = i // grid_cols
        col = i % grid_cols
        
        x = pad + col * space_x
        y = pad + row * space_y
        
        texture = load_texture(block_file)
        if texture:
            draw_isometric_block(surface, x, y, texture)
    
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
    
    # Generate wide horizontal block grid (12 columns x 12 rows = 144 blocks)
    print("\nGenerating block showcase grid (12 cols x 12 rows)...")
    grid_surface = create_block_grid(SHOWCASE_BLOCKS, grid_cols=12)
    grid_path = os.path.join(OUTPUT_DIR, "block_showcase.png")
    pygame.image.save(grid_surface, grid_path)
    print(f"  Created: block_showcase.png ({grid_surface.get_width()}x{grid_surface.get_height()})")
    
    print("\nDone! All assets created in References folder.")
    pygame.quit()


if __name__ == "__main__":
    main()
