"""
Bloc Fantôme - Asset Setup Script

This script extracts textures and sounds from your local Minecraft installation.
You must own a legitimate copy of Minecraft Java Edition (version 1.21.1+).

Usage:
    python setup_assets.py

The script will:
1. Locate your Minecraft installation
2. Find the latest version JAR file (1.21.1 or newer)
3. Extract textures and sounds to the Assets folder
4. Upscale block textures from 16x16 to 32x32

Author: Jeffrey Morais
"""

import os
import sys
import json
import zipfile
import shutil
import platform
from pathlib import Path
from typing import Optional, Tuple

# Minimum required Minecraft version
MIN_VERSION = (1, 21, 1)


def get_minecraft_dir() -> Optional[Path]:
    """Find the .minecraft directory based on the operating system."""
    system = platform.system()
    
    if system == "Windows":
        appdata = os.environ.get("APPDATA")
        if appdata:
            mc_dir = Path(appdata) / ".minecraft"
            if mc_dir.exists():
                return mc_dir
    elif system == "Darwin":  # macOS
        mc_dir = Path.home() / "Library" / "Application Support" / "minecraft"
        if mc_dir.exists():
            return mc_dir
    elif system == "Linux":
        mc_dir = Path.home() / ".minecraft"
        if mc_dir.exists():
            return mc_dir
    
    return None


def parse_version(version_str: str) -> Optional[Tuple[int, ...]]:
    """Parse a version string like '1.21.1' into a tuple of integers."""
    try:
        # Handle versions like "1.21.1", "1.21", "24w10a" (snapshots)
        parts = version_str.split(".")
        if len(parts) >= 2:
            # Check if it's a release version (starts with a number)
            if parts[0].isdigit():
                version_tuple = tuple(int(p) for p in parts if p.isdigit())
                return version_tuple
    except (ValueError, IndexError):
        pass
    return None


def find_best_version(versions_dir: Path) -> Optional[Tuple[Path, str]]:
    """Find the best (newest) Minecraft version JAR that meets minimum requirements."""
    if not versions_dir.exists():
        return None
    
    best_version = None
    best_version_tuple = None
    best_jar = None
    
    for version_folder in versions_dir.iterdir():
        if not version_folder.is_dir():
            continue
        
        version_name = version_folder.name
        jar_path = version_folder / f"{version_name}.jar"
        
        if not jar_path.exists():
            continue
        
        version_tuple = parse_version(version_name)
        if version_tuple is None:
            continue
        
        # Check if meets minimum version
        if len(version_tuple) >= 3:
            if version_tuple < MIN_VERSION:
                continue
        elif len(version_tuple) == 2:
            # e.g., "1.21" - assume it's >= 1.21.0
            if (version_tuple[0], version_tuple[1], 0) < MIN_VERSION:
                continue
        
        # Check if this is better than current best
        if best_version_tuple is None or version_tuple > best_version_tuple:
            best_version = version_name
            best_version_tuple = version_tuple
            best_jar = jar_path
    
    if best_jar:
        return (best_jar, best_version)
    return None


def upscale_texture(input_path: Path, output_path: Path, scale: int = 2):
    """Upscale a texture using nearest-neighbor interpolation (PIL)."""
    try:
        from PIL import Image
        img = Image.open(input_path)
        new_size = (img.width * scale, img.height * scale)
        upscaled = img.resize(new_size, Image.NEAREST)
        upscaled.save(output_path)
        return True
    except ImportError:
        # PIL not available, just copy the file
        shutil.copy2(input_path, output_path)
        return False
    except Exception as e:
        print(f"    Warning: Could not upscale {input_path.name}: {e}")
        shutil.copy2(input_path, output_path)
        return False


def extract_assets(jar_path: Path, assets_dir: Path) -> bool:
    """Extract textures and sounds from the Minecraft JAR."""
    print(f"\nExtracting assets from: {jar_path}")
    
    # Define output directories
    texture_hub = assets_dir / "Texture Hub"
    sound_hub = assets_dir / "Sound Hub"
    
    # Mapping of JAR paths to output paths
    texture_mappings = {
        "assets/minecraft/textures/block/": texture_hub / "blocks",
        "assets/minecraft/textures/item/": texture_hub / "items",
        "assets/minecraft/textures/entity/": texture_hub / "entity",
        "assets/minecraft/textures/gui/": texture_hub / "gui",
        "assets/minecraft/textures/environment/": texture_hub / "environment",
        "assets/minecraft/textures/particle/": texture_hub / "particle",
        "assets/minecraft/textures/painting/": texture_hub / "painting",
        "assets/minecraft/textures/colormap/": texture_hub / "colormap",
        "assets/minecraft/textures/misc/": texture_hub / "misc",
        "assets/minecraft/textures/mob_effect/": texture_hub / "mob_effect",
        "assets/minecraft/textures/font/": texture_hub / "font",
        "assets/minecraft/textures/effect/": texture_hub / "effect",
        "assets/minecraft/textures/map/": texture_hub / "map",
        "assets/minecraft/textures/trims/": texture_hub / "trims",
        "assets/minecraft/textures/models/": texture_hub / "models",
    }
    
    # Sounds need to be extracted from the assets index
    sound_categories = [
        "ambient", "block", "damage", "dig", "enchant", "entity", 
        "event", "fire", "fireworks", "item", "liquid", "minecart",
        "mob", "music", "note", "portal", "random", "records",
        "step", "tile", "ui"
    ]
    
    extracted_textures = 0
    extracted_sounds = 0
    upscaled_count = 0
    
    try:
        with zipfile.ZipFile(jar_path, 'r') as jar:
            file_list = jar.namelist()
            
            # Extract textures
            print("\n📦 Extracting textures...")
            for jar_prefix, output_dir in texture_mappings.items():
                output_dir.mkdir(parents=True, exist_ok=True)
                
                for file_path in file_list:
                    if file_path.startswith(jar_prefix) and file_path.endswith(".png"):
                        filename = os.path.basename(file_path)
                        if not filename:
                            continue
                        
                        output_path = output_dir / filename
                        
                        # Extract to temp location first
                        with jar.open(file_path) as src:
                            data = src.read()
                        
                        # Write temp file
                        temp_path = output_path.with_suffix(".tmp")
                        with open(temp_path, "wb") as dst:
                            dst.write(data)
                        
                        # Upscale block textures from 16x16 to 32x32
                        if "blocks" in str(output_dir):
                            if upscale_texture(temp_path, output_path):
                                upscaled_count += 1
                        else:
                            shutil.move(temp_path, output_path)
                        
                        # Clean up temp file if it still exists
                        if temp_path.exists():
                            temp_path.unlink()
                        
                        extracted_textures += 1
            
            print(f"    ✓ Extracted {extracted_textures} textures")
            if upscaled_count > 0:
                print(f"    ✓ Upscaled {upscaled_count} block textures to 32x32")
            
            # Extract sounds directly from JAR (they're in assets/minecraft/sounds/)
            print("\n🔊 Extracting sounds...")
            sound_prefix = "assets/minecraft/sounds/"
            
            for file_path in file_list:
                if file_path.startswith(sound_prefix) and file_path.endswith(".ogg"):
                    # Get relative path within sounds folder
                    rel_path = file_path[len(sound_prefix):]
                    
                    # Determine output path
                    output_path = sound_hub / rel_path
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Extract sound file
                    with jar.open(file_path) as src:
                        data = src.read()
                    with open(output_path, "wb") as dst:
                        dst.write(data)
                    
                    extracted_sounds += 1
            
            print(f"    ✓ Extracted {extracted_sounds} sound files")
    
    except zipfile.BadZipFile:
        print(f"Error: {jar_path} is not a valid JAR/ZIP file")
        return False
    except Exception as e:
        print(f"Error extracting assets: {e}")
        return False
    
    return True


def main():
    print("=" * 60)
    print("  Bloc Fantôme - Asset Setup")
    print("=" * 60)
    print("\nThis script extracts textures and sounds from your")
    print("Minecraft Java Edition installation (1.21.1+ required).")
    print("\n⚠️  You must own a legitimate copy of Minecraft.")
    
    # Find Minecraft directory
    print("\n🔍 Looking for Minecraft installation...")
    mc_dir = get_minecraft_dir()
    
    if mc_dir is None:
        print("❌ Could not find Minecraft installation!")
        print("\nPlease ensure Minecraft Java Edition is installed.")
        print("Expected locations:")
        print("  Windows: %APPDATA%\\.minecraft")
        print("  macOS:   ~/Library/Application Support/minecraft")
        print("  Linux:   ~/.minecraft")
        return 1
    
    print(f"    ✓ Found: {mc_dir}")
    
    # Find best version
    print(f"\n🔍 Looking for Minecraft {'.'.join(map(str, MIN_VERSION))}+ ...")
    versions_dir = mc_dir / "versions"
    result = find_best_version(versions_dir)
    
    if result is None:
        print(f"❌ Could not find Minecraft version {'.'.join(map(str, MIN_VERSION))} or newer!")
        print("\nPlease launch Minecraft and ensure you have version 1.21.1+")
        print("installed (run the game at least once with that version).")
        return 1
    
    jar_path, version_name = result
    print(f"    ✓ Found version: {version_name}")
    
    # Determine assets directory
    script_dir = Path(__file__).parent
    assets_dir = script_dir.parent / "Assets"
    
    print(f"\n📁 Output directory: {assets_dir}")
    
    # Confirm with user
    print("\n" + "-" * 60)
    response = input("Proceed with extraction? [Y/n]: ").strip().lower()
    if response and response != 'y' and response != 'yes':
        print("Aborted.")
        return 0
    
    # Extract assets
    success = extract_assets(jar_path, assets_dir)
    
    if success:
        print("\n" + "=" * 60)
        print("  ✅ Setup Complete!")
        print("=" * 60)
        print("\nYou can now run the application:")
        print("    python blocFantome.py")
        return 0
    else:
        print("\n❌ Setup failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
