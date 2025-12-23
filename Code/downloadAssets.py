"""
Minecraft Asset Downloader

This script downloads the official Minecraft Bedrock Edition vanilla resource pack
and extracts the required block textures for the building simulator. It also
downloads placeholder sounds from free sources.

Note: Textures are from the official Mojang resource pack, intended for personal use.

Author: Jeffrey Morais
"""

import os
import sys
import urllib.request
import zipfile
import shutil
import json

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "..", "Assets")
TEXTURES_DIR = os.path.join(ASSETS_DIR, "textures")
SOUNDS_DIR = os.path.join(ASSETS_DIR, "sounds")
TEMP_DIR = os.path.join(ASSETS_DIR, "temp")

# Official Minecraft Bedrock resource pack URL (from Mojang)
# This URL may change - check https://aka.ms/resourcepacktemplate for current version
RESOURCE_PACK_URL = "https://aka.ms/resourcepacktemplate"

# Required textures and their paths within the resource pack
REQUIRED_TEXTURES = {
    "grass_block_top.png": "textures/blocks/grass_top.png",
    "grass_block_side.png": "textures/blocks/grass_side_carried.png",
    "dirt.png": "textures/blocks/dirt.png",
    "stone.png": "textures/blocks/stone.png",
    "oak_planks.png": "textures/blocks/planks_oak.png",
    "cobblestone.png": "textures/blocks/cobblestone.png",
}

# Alternative texture names (Bedrock vs Java naming differences)
ALTERNATIVE_PATHS = {
    "grass_block_top.png": [
        "textures/blocks/grass_carried.png",
        "textures/blocks/grass_block_top.png",
        "textures/blocks/grass_top.png"
    ],
    "grass_block_side.png": [
        "textures/blocks/grass_side.png",
        "textures/blocks/grass_block_side.png",
        "textures/blocks/grass_side_carried.png"
    ],
    "dirt.png": [
        "textures/blocks/dirt.png"
    ],
    "stone.png": [
        "textures/blocks/stone.png"
    ],
    "oak_planks.png": [
        "textures/blocks/planks_oak.png",
        "textures/blocks/oak_planks.png"
    ],
    "cobblestone.png": [
        "textures/blocks/cobblestone.png"
    ],
}


# ============================================================================
# DOWNLOAD FUNCTIONS
# ============================================================================

def downloadFile(url: str, destPath: str) -> bool:
    """
    Download a file from URL to destination path.
    
    Args:
        url: URL to download from
        destPath: Local path to save to
        
    Returns:
        True if successful, False otherwise
    """
    print(f"Downloading from {url}...")
    
    try:
        # Create a request with headers to avoid 403 errors
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        request = urllib.request.Request(url, headers=headers)
        
        with urllib.request.urlopen(request, timeout=30) as response:
            with open(destPath, 'wb') as outFile:
                shutil.copyfileobj(response, outFile)
        
        print(f"Downloaded to {destPath}")
        return True
        
    except Exception as e:
        print(f"Error downloading: {e}")
        return False


def extractTextures(zipPath: str) -> bool:
    """
    Extract required textures from the resource pack zip.
    
    Args:
        zipPath: Path to the downloaded zip file
        
    Returns:
        True if successful, False otherwise
    """
    print("Extracting textures...")
    
    try:
        with zipfile.ZipFile(zipPath, 'r') as zipRef:
            # List all files in the zip
            allFiles = zipRef.namelist()
            
            # Find and extract each required texture
            for targetName, alternatives in ALTERNATIVE_PATHS.items():
                found = False
                
                for altPath in alternatives:
                    # Search for the texture (case-insensitive)
                    for zipFileName in allFiles:
                        if altPath.lower() in zipFileName.lower():
                            # Extract to temp and rename
                            zipRef.extract(zipFileName, TEMP_DIR)
                            
                            # Move to final location
                            srcPath = os.path.join(TEMP_DIR, zipFileName)
                            destPath = os.path.join(TEXTURES_DIR, targetName)
                            
                            if os.path.exists(srcPath):
                                shutil.copy2(srcPath, destPath)
                                print(f"  Extracted: {targetName}")
                                found = True
                                break
                    
                    if found:
                        break
                
                if not found:
                    print(f"  Warning: Could not find {targetName}")
        
        return True
        
    except Exception as e:
        print(f"Error extracting: {e}")
        return False


def createPlaceholderTextures():
    """Create simple placeholder textures if download fails"""
    print("Creating placeholder textures...")
    
    # Import pygame for surface creation
    import pygame
    pygame.init()
    
    placeholderColors = {
        "grass_block_top.png": (100, 180, 100),
        "grass_block_side.png": (139, 90, 43),
        "dirt.png": (139, 90, 43),
        "stone.png": (128, 128, 128),
        "oak_planks.png": (180, 140, 80),
        "cobblestone.png": (100, 100, 100),
    }
    
    for textureName, color in placeholderColors.items():
        texturePath = os.path.join(TEXTURES_DIR, textureName)
        
        if not os.path.exists(texturePath):
            # Create a 16x16 textured surface
            surface = pygame.Surface((16, 16))
            surface.fill(color)
            
            # Add some texture variation
            for i in range(16):
                for j in range(16):
                    if (i + j) % 3 == 0:
                        variation = 15
                        newColor = (
                            max(0, min(255, color[0] + variation * ((i * j) % 3 - 1))),
                            max(0, min(255, color[1] + variation * ((i * j) % 3 - 1))),
                            max(0, min(255, color[2] + variation * ((i * j) % 3 - 1)))
                        )
                        surface.set_at((i, j), newColor)
            
            # Special handling for grass side
            if textureName == "grass_block_side.png":
                for i in range(16):
                    for j in range(4):
                        surface.set_at((i, j), (100, 180, 100))
            
            pygame.image.save(surface, texturePath)
            print(f"  Created placeholder: {textureName}")
    
    pygame.quit()


def createPlaceholderSounds():
    """Create placeholder sound effects"""
    print("Creating placeholder sounds...")
    
    import wave
    import struct
    import math
    
    sounds = {
        "place.wav": (800, 0.15),   # Higher pitch, short
        "break.wav": (400, 0.2),    # Lower pitch, medium
        "click.wav": (1200, 0.05),  # High pitch, very short
    }
    
    sampleRate = 44100
    
    for soundName, (frequency, duration) in sounds.items():
        soundPath = os.path.join(SOUNDS_DIR, soundName)
        
        if not os.path.exists(soundPath):
            numSamples = int(sampleRate * duration)
            samples = []
            
            for i in range(numSamples):
                t = i / sampleRate
                envelope = max(0, 1 - t / duration)
                
                # Sine wave with slight noise
                value = envelope * math.sin(2 * math.pi * frequency * t)
                value += envelope * 0.1 * (2 * ((i * 7) % 100) / 100 - 1)
                
                samples.append(int(value * 32767 * 0.5))
            
            with wave.open(soundPath, 'w') as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(sampleRate)
                for sample in samples:
                    wav.writeframes(struct.pack('<h', max(-32768, min(32767, sample))))
            
            print(f"  Created: {soundName}")


def cleanup():
    """Clean up temporary files"""
    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR)
        print("Cleaned up temporary files")


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main entry point"""
    print("=" * 50)
    print("  Minecraft Asset Downloader")
    print("=" * 50)
    print()
    
    # Ensure directories exist
    os.makedirs(TEXTURES_DIR, exist_ok=True)
    os.makedirs(SOUNDS_DIR, exist_ok=True)
    os.makedirs(TEMP_DIR, exist_ok=True)
    
    # Try to download official resource pack
    zipPath = os.path.join(TEMP_DIR, "resource_pack.zip")
    
    print("Attempting to download official Minecraft resource pack...")
    print("(This may take a moment)")
    print()
    
    success = downloadFile(RESOURCE_PACK_URL, zipPath)
    
    if success and os.path.exists(zipPath):
        extractTextures(zipPath)
    else:
        print("\nCould not download official resource pack.")
        print("Creating placeholder textures instead...")
        createPlaceholderTextures()
    
    # Create sounds
    print()
    createPlaceholderSounds()
    
    # Cleanup
    print()
    cleanup()
    
    print()
    print("=" * 50)
    print("  Asset setup complete!")
    print("=" * 50)
    print()
    print("You can now run minecraftBuilder.py")
    print()
    print("NOTE: If you want authentic Minecraft textures,")
    print("you can manually copy them from your Minecraft")
    print("installation to the Assets/textures folder.")
    print()
    print("Required texture files:")
    for texName in REQUIRED_TEXTURES.keys():
        texPath = os.path.join(TEXTURES_DIR, texName)
        status = "✓" if os.path.exists(texPath) else "✗"
        print(f"  {status} {texName}")


if __name__ == "__main__":
    main()
