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
MAIN_SCRIPT = os.path.join(SCRIPT_DIR, "blocFantome.py")
ICON_PATH = os.path.join(PROJECT_ROOT, "Assets", "Icons", "End_Stone.ico")
ICON_GENERATOR = os.path.join(SCRIPT_DIR, "generate_icon.py")
STRUCTURES_DIR = os.path.join(SCRIPT_DIR, "saves")
WORLDS_DIR = os.path.join(SCRIPT_DIR, "worlds")
BUILD_DIR = os.path.join(SCRIPT_DIR, "build")
DIST_DIR = PROJECT_ROOT  # Output directly to project root
WORK_DIR = os.path.join(BUILD_DIR, "work")
TK_RUNTIME_HOOK = os.path.join(SCRIPT_DIR, "pyi_tk_runtime.py")
VERSION_FILE = os.path.join(BUILD_DIR, "version_info.txt")

# Version info
VERSION = "2.2.0"
COMPANY = "Jeffrey Morais"
PRODUCT = "Bloc Fantome"
COPYRIGHT = "Copyright (c) 2026 Jeffrey Morais"


def write_version_resource() -> None:
    """Create the Windows version resource consumed by PyInstaller."""
    major, minor, patch = (int(part) for part in VERSION.split("."))
    content = f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers=({major}, {minor}, {patch}, 0), prodvers=({major}, {minor}, {patch}, 0),
    mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', '{COMPANY}'),
      StringStruct('FileDescription', '{PRODUCT}'),
      StringStruct('FileVersion', '{VERSION}'),
      StringStruct('InternalName', 'BlocFantome'),
      StringStruct('LegalCopyright', '{COPYRIGHT}'),
      StringStruct('OriginalFilename', 'BlocFantome.exe'),
      StringStruct('ProductName', '{PRODUCT}'),
      StringStruct('ProductVersion', '{VERSION}')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ])
"""
    with open(VERSION_FILE, "w", encoding="utf-8") as handle:
        handle.write(content)

def build(debug: bool = False, diagnostic: bool = False):
    print("=" * 60)
    print(f"Building Bloc Fantome Executable v{VERSION}")
    print("=" * 60)
    
    # Keep the desktop/taskbar resource synchronized with the runtime icon.
    subprocess.run([sys.executable, ICON_GENERATOR], cwd=SCRIPT_DIR, check=True)

    # Create build directory if it doesn't exist
    os.makedirs(BUILD_DIR, exist_ok=True)
    write_version_resource()
    
    # PyInstaller command - use python -m PyInstaller to ensure correct environment
    executable_name = "BlocFantome-Diagnostic" if diagnostic else "BlocFantome"
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",                    # Single .exe file
        f"--icon={ICON_PATH}",          # Application icon
        f"--distpath={DIST_DIR}",       # Output directory for the exe
        f"--workpath={WORK_DIR}",       # Temp build files
        f"--specpath={BUILD_DIR}",      # Spec file location
        f"--name={executable_name}",    # Name of the executable
        f"--version-file={VERSION_FILE}",
        "--clean",                      # Clean cache before building
        # Hidden imports that PyInstaller may miss
        "--hidden-import=pickle",
        "--hidden-import=multiprocessing",
        "--hidden-import=tkinter",
        "--hidden-import=tkinter.filedialog",
        "--hidden-import=tkinter.messagebox",
        "--hidden-import=tkinter.simpledialog",
        "--hidden-import=engine.anvil",
        f"--runtime-hook={TK_RUNTIME_HOOK}",
        # Exclude truly unused modules for smaller exe
        # NOTE: Be careful! Many modules have hidden dependencies
        # - email, http, html are needed by urllib.request
        # - xml may be needed by various parsers
        "--exclude-module=unittest",
        "--exclude-module=test",
        "--exclude-module=pydoc",
        "--exclude-module=doctest",
    ]

    # Some Windows Python installations can import tkinter but PyInstaller's
    # probe cannot initialize Tcl in the build account. Bundle the known-good
    # runtime explicitly so frozen Open, Save As, and Java import dialogs do
    # not silently disappear.
    pythonRoot = sys.base_prefix
    tkFiles = (
        (os.path.join(pythonRoot, "Lib", "tkinter"), "tkinter", "data"),
        (os.path.join(pythonRoot, "tcl", "tcl8.6"), "_tcl_data", "data"),
        (os.path.join(pythonRoot, "tcl", "tk8.6"), "_tk_data", "data"),
        (os.path.join(pythonRoot, "DLLs", "_tkinter.pyd"), ".", "binary"),
        (os.path.join(pythonRoot, "DLLs", "tcl86t.dll"), ".", "binary"),
        (os.path.join(pythonRoot, "DLLs", "tk86t.dll"), ".", "binary"),
    )
    for sourcePath, destination, kind in tkFiles:
        if not os.path.exists(sourcePath):
            raise FileNotFoundError(f"Required Tk runtime path is missing: {sourcePath}")
        option = "--add-binary" if kind == "binary" else "--add-data"
        cmd.append(f"{option}={sourcePath}{os.pathsep}{destination}")
    
    # Add windowed mode only for release builds
    if not debug and not diagnostic:
        cmd.append("--windowed")  # No console window
    else:
        cmd.append("--console")  # Keep console for debugging

    # Curated JSON builds are read-only application data used by the tutorial
    # and the cursor-placeable Structures tab.
    for structure_name in (
        "bastion_bridge_edge",
        "bastion_remnant_no_lava",
        "bastion_remnant_with_lava",
        "end_city_tower",
        "ruined_portal_accurate",
        "warped_forest_accurate",
        "warped_forest",
    ):
        source_path = os.path.join(STRUCTURES_DIR, f"{structure_name}.json")
        cmd.append(f"--add-data={source_path}{os.pathsep}structures")

    for world_name in (
        "bastion_treasure_1161",
        "bastion_bridge_1161",
        "bastion_hoglin_stable_1161",
        "bastion_housing_units_1161",
        "basalt_deltas_1161",
        "end_city_1161",
        "ancient_city_121",
        "trial_chamber_121",
        "village_plains_1161",
        "village_desert_1161",
        "village_savanna_1161",
        "village_taiga_1161",
        "village_snowy_1161",
    ):
        source_path = os.path.join(WORLDS_DIR, f"{world_name}.json.gz")
        cmd.append(f"--add-data={source_path}{os.pathsep}worlds")
    
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
        exe_path = os.path.join(DIST_DIR, f"{executable_name}.exe")
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
    parser = argparse.ArgumentParser(description="Build Bloc Fantome executable")
    parser.add_argument("--debug", action="store_true", help="Build with console for debugging")
    parser.add_argument(
        "--diagnostic", action="store_true",
        help="Build BlocFantome-Diagnostic.exe with console audio diagnostics",
    )
    args = parser.parse_args()
    
    return build(debug=args.debug, diagnostic=args.diagnostic)


if __name__ == "__main__":
    exit(main())
