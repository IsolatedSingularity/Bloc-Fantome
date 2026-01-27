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

# Isometric block dimensions - matching the app exactly
TILE_WIDTH = 32
TILE_HEIGHT = 16
BLOCK_HEIGHT = 20

# Headers to generate (matching the GIF names)
HEADERS = [
    "Weather",
    "Lighting", 
    "Dimensions",
    "Liquids"
]

# Landscape block showcase - 21 columns x 6 rows = 126 blocks
SHOWCASE_BLOCKS = [
    # Row 1: Overworld Terrain
    "grass_block_top.png", "dirt.png", "stone.png", "cobblestone.png",
    "mossy_cobblestone.png", "gravel.png", "sand.png", "sandstone_top.png",
    "red_sand.png", "red_sandstone_top.png", "clay.png", "mud.png",
    "podzol_top.png", "mycelium_top.png", "snow.png", "ice.png",
    "packed_ice.png", "blue_ice.png", "moss_block.png", "rooted_dirt.png",
    "coarse_dirt.png",
    
    # Row 2: Stone & Deepslate
    "granite.png", "polished_granite.png", "diorite.png", "polished_diorite.png",
    "andesite.png", "polished_andesite.png", "calcite.png", "tuff.png",
    "dripstone_block.png", "deepslate_top.png", "cobbled_deepslate.png", "polished_deepslate.png",
    "deepslate_bricks.png", "deepslate_tiles.png", "chiseled_deepslate.png", "smooth_stone.png",
    "stone_bricks.png", "mossy_stone_bricks.png", "cracked_stone_bricks.png", "chiseled_stone_bricks.png",
    "bricks.png",
    
    # Row 3: Ores & Ore Blocks
    "coal_ore.png", "iron_ore.png", "copper_ore.png", "gold_ore.png",
    "diamond_ore.png", "emerald_ore.png", "lapis_ore.png", "redstone_ore.png",
    "nether_gold_ore.png", "nether_quartz_ore.png", "coal_block.png", "iron_block.png",
    "copper_block.png", "gold_block.png", "diamond_block.png", "emerald_block.png",
    "lapis_block.png", "redstone_block.png", "netherite_block.png", "amethyst_block.png",
    "quartz_block_top.png",
    
    # Row 4: Wood & Planks
    "oak_log_top.png", "spruce_log_top.png", "birch_log_top.png", "jungle_log_top.png",
    "acacia_log_top.png", "dark_oak_log_top.png", "mangrove_log_top.png", "cherry_log_top.png",
    "oak_planks.png", "spruce_planks.png", "birch_planks.png", "jungle_planks.png",
    "acacia_planks.png", "dark_oak_planks.png", "mangrove_planks.png", "cherry_planks.png",
    "crimson_planks.png", "warped_planks.png", "bamboo_planks.png", "bamboo_mosaic.png",
    "bookshelf.png",
    
    # Row 5: Nether Blocks
    "netherrack.png", "nether_bricks.png", "red_nether_bricks.png", "cracked_nether_bricks.png",
    "chiseled_nether_bricks.png", "nether_wart_block.png", "warped_wart_block.png", "crimson_nylium.png",
    "warped_nylium.png", "soul_sand.png", "soul_soil.png", "blackstone.png",
    "polished_blackstone.png", "polished_blackstone_bricks.png", "chiseled_polished_blackstone.png", "gilded_blackstone.png",
    "basalt_top.png", "polished_basalt_top.png", "ancient_debris_top.png", "magma.png",
    "glowstone.png",
    
    # Row 6: End & Colorful
    "end_stone.png", "end_stone_bricks.png", "purpur_block.png", "purpur_pillar_top.png",
    "obsidian.png", "crying_obsidian.png", "prismarine.png", "prismarine_bricks.png",
    "dark_prismarine.png", "sea_lantern.png", "shroomlight.png", "sculk.png",
    "white_glazed_terracotta.png", "orange_glazed_terracotta.png", "magenta_glazed_terracotta.png", "cyan_glazed_terracotta.png",
    "purple_glazed_terracotta.png", "blue_glazed_terracotta.png", "green_glazed_terracotta.png", "red_glazed_terracotta.png",
    "yellow_glazed_terracotta.png",
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


def get_average_color(surface: pygame.Surface) -> tuple:
    """Get the average color of a surface."""
    total_r, total_g, total_b = 0, 0, 0
    count = 0
    for y in range(surface.get_height()):
        for x in range(surface.get_width()):
            c = surface.get_at((x, y))
            if c[3] > 128:
                total_r += c[0]
                total_g += c[1]
                total_b += c[2]
                count += 1
    if count == 0:
        return (128, 128, 128)
    return (total_r // count, total_g // count, total_b // count)


def darken_color(color: tuple, factor: float) -> tuple:
    """Darken a color by a factor."""
    return (int(color[0] * factor), int(color[1] * factor), int(color[2] * factor))


def create_isometric_block(texture: pygame.Surface) -> pygame.Surface:
    """
    Create an isometric block sprite from a texture.
    Uses the EXACT same logic as minecraftBuilder.py _createIsometricBlock().
    """
    W = TILE_WIDTH
    H = TILE_HEIGHT + BLOCK_HEIGHT
    halfW = W // 2
    halfH = TILE_HEIGHT // 2
    
    surface = pygame.Surface((W, H), pygame.SRCALPHA)
    
    # Scale texture to match block dimensions
    texW = halfW  # Each face spans half width
    texH = BLOCK_HEIGHT  # Side faces are this tall
    
    if texture:
        topTex = pygame.transform.scale(texture, (texW, texW))
        leftTex = pygame.transform.scale(texture, (texW, texH))
        rightTex = pygame.transform.scale(texture, (texW, texH))
    else:
        topTex = pygame.Surface((texW, texW))
        topTex.fill((100, 100, 100))
        leftTex = pygame.Surface((texW, texH))
        leftTex.fill((80, 80, 80))
        rightTex = pygame.Surface((texW, texH))
        rightTex.fill((60, 60, 60))
    
    # Define face polygons
    topPoints = [(halfW, 0), (W-1, halfH), (halfW, TILE_HEIGHT-1), (0, halfH)]
    leftPoints = [(0, halfH), (halfW, TILE_HEIGHT-1), (halfW, H-1), (0, halfH + BLOCK_HEIGHT)]
    rightPoints = [(halfW, TILE_HEIGHT-1), (W-1, halfH), (W-1, halfH + BLOCK_HEIGHT), (halfW, H-1)]
    
    # Fill with average colors first to prevent gaps
    topAvg = get_average_color(topTex)
    leftAvg = darken_color(get_average_color(leftTex), 0.7)
    rightAvg = darken_color(get_average_color(rightTex), 0.85)
    pygame.draw.polygon(surface, topAvg, topPoints)
    pygame.draw.polygon(surface, leftAvg, leftPoints)
    pygame.draw.polygon(surface, rightAvg, rightPoints)
    
    # TOP FACE - isometric diamond with texture
    for py in range(TILE_HEIGHT):
        if py <= halfH:
            spanRatio = py / halfH if halfH > 0 else 0
        else:
            spanRatio = (TILE_HEIGHT - py) / halfH if halfH > 0 else 0
        
        span = int(halfW * spanRatio)
        if span <= 0:
            continue
            
        leftX = halfW - span
        rightX = halfW + span
        
        for px in range(leftX, rightX):
            relX = px - halfW
            relY = py - halfH
            
            # Inverse isometric projection
            u = (relX / halfW + relY / halfH) * 0.5 + 0.5
            v = (-relX / halfW + relY / halfH) * 0.5 + 0.5
            
            texX = int(u * (texW - 1))
            texY = int(v * (texW - 1))
            texX = max(0, min(texW - 1, texX))
            texY = max(0, min(texW - 1, texY))
            
            color = topTex.get_at((texX, texY))
            if color.a > 0:
                surface.set_at((px, py), color)
    
    # LEFT FACE - parallelogram with shading
    for px in range(halfW):
        topY = halfH + int((px / halfW) * halfH)
        bottomY = min(topY + BLOCK_HEIGHT, H)
        
        for py in range(topY, bottomY):
            texX = int((px / halfW) * (texW - 1))
            texY = int(((py - topY) / BLOCK_HEIGHT) * (texH - 1))
            texX = max(0, min(texW - 1, texX))
            texY = max(0, min(texH - 1, texY))
            
            color = leftTex.get_at((texX, texY))
            if color.a > 0:
                shaded = (int(color.r * 0.7), int(color.g * 0.7), int(color.b * 0.7), color.a)
                surface.set_at((px, py), shaded)
    
    # RIGHT FACE - parallelogram with lighter shading
    for px in range(halfW, W):
        relX = px - halfW
        topY = TILE_HEIGHT - 1 - int((relX / halfW) * halfH)
        bottomY = min(topY + BLOCK_HEIGHT, H)
        
        for py in range(max(0, topY), bottomY):
            texX = int((relX / halfW) * (texW - 1))
            texY = int(((py - topY) / BLOCK_HEIGHT) * (texH - 1))
            texX = max(0, min(texW - 1, texX))
            texY = max(0, min(texH - 1, texY))
            
            color = rightTex.get_at((texX, texY))
            if color.a > 0:
                shaded = (int(color.r * 0.85), int(color.g * 0.85), int(color.b * 0.85), color.a)
                surface.set_at((px, py), shaded)
    
    return surface


def create_block_grid(blocks: list, grid_cols: int = 18) -> pygame.Surface:
    """Create a landscape grid of isometric blocks."""
    num_blocks = len(blocks)
    grid_rows = (num_blocks + grid_cols - 1) // grid_cols
    
    # Spacing between blocks
    space_x = TILE_WIDTH + 4
    space_y = TILE_HEIGHT + BLOCK_HEIGHT + 2
    
    # Calculate total size
    pad = 12
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
            block_sprite = create_isometric_block(texture)
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
    
    # Generate landscape block grid (21 columns x 6 rows = 126 blocks)
    print("\nGenerating block showcase grid (21 cols x 6 rows)...")
    grid_surface = create_block_grid(SHOWCASE_BLOCKS, grid_cols=21)
    grid_path = os.path.join(OUTPUT_DIR, "block_showcase.png")
    pygame.image.save(grid_surface, grid_path)
    print(f"  Created: block_showcase.png ({grid_surface.get_width()}x{grid_surface.get_height()})")
    
    print("\nDone! All assets created in References folder.")
    pygame.quit()


if __name__ == "__main__":
    main()
