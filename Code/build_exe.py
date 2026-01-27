"""
Build script for creating Bloc Fantome executable.
Run this script to generate the standalone .exe file.

Usage:
    python build_exe.py          # Standard build
    python build_exe.py --debug  # Debug build with console
"""

import subprocess
import os
import shutil
import sys
import argparse

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
MAIN_SCRIPT = os.path.join(SCRIPT_DIR, "minecraftBuilder.py")
ICON_PATH = os.path.join(PROJECT_ROOT, "Assets", "Icons", "End_Stone.ico")
BUILD_DIR = os.path.join(SCRIPT_DIR, "build")
DIST_DIR = PROJECT_ROOT  # Output directly to project root
WORK_DIR = os.path.join(BUILD_DIR, "work")

# Version info
VERSION = "1.1.0"
COMPANY = "Jeffrey Morais"
PRODUCT = "Bloc Fantome"
COPYRIGHT = "Copyright (c) 2026 Jeffrey Morais"

def build(debug: bool = False):
    print("=" * 60)
    print(f"Building Bloc Fantome Executable v{VERSION}")
    print("=" * 60)
    
    # Create build directory if it doesn't exist
    os.makedirs(BUILD_DIR, exist_ok=True)
    
    # PyInstaller command - use python -m PyInstaller to ensure correct environment
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",                    # Single .exe file
        f"--icon={ICON_PATH}",          # Application icon
        f"--distpath={DIST_DIR}",       # Output directory for the exe
        f"--workpath={WORK_DIR}",       # Temp build files
        f"--specpath={BUILD_DIR}",      # Spec file location
        "--name=BlocFantome",           # Name of the executable
        "--clean",                      # Clean cache before building
        # Hidden imports that PyInstaller may miss
        "--hidden-import=pickle",
        "--hidden-import=multiprocessing",
        # Exclude truly unused modules for smaller exe
        # NOTE: Be careful! Many modules have hidden dependencies
        # - email, http, html are needed by urllib.request
        # - xml may be needed by various parsers
        "--exclude-module=tkinter",
        "--exclude-module=unittest",
        "--exclude-module=test",
        "--exclude-module=pydoc",
        "--exclude-module=doctest",
    ]
    
    # Add windowed mode only for release builds
    if not debug:
        cmd.append("--windowed")  # No console window
    else:
        cmd.append("--console")  # Keep console for debugging
    
    # Add main script
    cmd.append(MAIN_SCRIPT)
    
    print("\nRunning PyInstaller with options:")
    print(f"  Main script: {MAIN_SCRIPT}")
    print(f"  Icon: {ICON_PATH}")
    print(f"  Output: {DIST_DIR}")
    print()
    
    # Run PyInstaller
    result = subprocess.run(cmd, cwd=SCRIPT_DIR)
    
    if result.returncode == 0:
        exe_path = os.path.join(DIST_DIR, "BlocFantome.exe")
        print("\n" + "=" * 60)
        print("BUILD SUCCESSFUL!")
        print("=" * 60)
        print(f"\nExecutable created at:\n  {exe_path}")
        
        print("\n--- Distribution Instructions ---")
        print("To share this application, provide users with:")
        print("  1. BlocFantome.exe (from project root)")
        print("  2. Instructions to run setup_assets.py first")
        print("  3. config.json (optional, for custom settings)")
        print("\nNote: Users must have Minecraft Java Edition 1.21.1+ installed")
        print("      and run setup_assets.py to extract textures and sounds.")
        print("\nTo create an installer, run:")
        print("  iscc installer.iss")
    else:
        print("\n" + "=" * 60)
        print("BUILD FAILED!")
        print("=" * 60)
        print("Check the error messages above.")
    
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description="Build Minecraft Builder executable")
    parser.add_argument("--debug", action="store_true", help="Build with console for debugging")
    args = parser.parse_args()
    
    return build(debug=args.debug)


if __name__ == "__main__":
    exit(main())
