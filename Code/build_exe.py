"""
Build script for creating Bloc Fantôme executable.
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
ICON_PATH = os.path.join(PROJECT_ROOT, "Assets", "Icons", "Respawn_Anchor.ico")
ICON_GENERATOR = os.path.join(SCRIPT_DIR, "generate_icon.py")
STRUCTURES_DIR = os.path.join(SCRIPT_DIR, "saves")
WORLDS_DIR = os.path.join(SCRIPT_DIR, "worlds")
BUILD_DIR = os.path.join(SCRIPT_DIR, "build")
DIST_DIR = PROJECT_ROOT  # Output directly to project root
WORK_DIR = os.path.join(BUILD_DIR, "work")
TK_RUNTIME_HOOK = os.path.join(SCRIPT_DIR, "pyi_tk_runtime.py")
VERSION_FILE = os.path.join(BUILD_DIR, "version_info.txt")
NATIVE_BUILDER = os.path.join(SCRIPT_DIR, "build_native.py")
NATIVE_LIBRARY = os.path.join(
    SCRIPT_DIR, "native", "bin", "bloc_fantome_native.dll"
)
ZEKTON_FONT = os.path.join(
    PROJECT_ROOT, "Assets", "Fonts", "Zekton", "Zekton-Regular.otf"
)
HORROR_TITLE = os.path.join(PROJECT_ROOT, "References", "Titles", "horror.png")
SKYBOX_PANORAMA_ROOT = os.path.join(
    PROJECT_ROOT, "Assets", "Skyboxes", "Black Mesa", "assets", "minecraft",
    "optifine", "sky", "panoramas",
)
SKYBOX_PANORAMAS = [
    os.path.join(SKYBOX_PANORAMA_ROOT, world, filename)
    for world, filename in (
        ("world0", "dawn.png"), ("world0", "day.png"),
        ("world0", "dusk.png"), ("world0", "night.png"),
        ("world1", "1.png"), ("world1", "2.png"), ("world1", "3.png"),
    )
]
WORLD_MAP_ROOT = os.path.join(PROJECT_ROOT, "Assets", "World Map", "WorldBuilder")
WORLD_MAP_RELEASE_FILES = [
    os.path.join(WORLD_MAP_ROOT, "ui", filename)
    for filename in (
        "question_mark.png", "question_mark_blink.png", "question_mark_shadow.png",
        "worldbuilder_title.png", "next_world_arrow.png", "prev_world_arrow.png",
        *(f"flag{index}.png" for index in range(1, 7)),
        *(f"bonus_flag{index}.png" for index in range(1, 7)),
    )
] + [
    os.path.join(WORLD_MAP_ROOT, "audio", filename)
    for filename in (
        "m_game_6_1.mp3", "m_game_6_3.mp3", "m_game_6_4.mp3", "m_game_6_5.mp3",
        "m_game_8_1.mp3", "m_game_8_3.mp3", "m_game_8_4.mp3",
        "m_game_i_1.mp3", "m_game_i_2.mp3", "m_game_i_3.mp3",
        "s_button_click_2.mp3", "s_goal_mission_4.mp3", "s_rollover_1.mp3",
    )
]

# Version info
VERSION = "2.6.0"
COMPANY = "Jeffrey Morais"
PRODUCT = "Bloc Fantôme"
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
    print(f"Building Bloc Fantôme Executable v{VERSION}")
    print("=" * 60)

    # Source builds retain a deliberate system-font fallback, but a release
    # must not silently ship without the owner-supplied licensed typeface.
    if not os.path.isfile(ZEKTON_FONT):
        raise FileNotFoundError(
            "Required licensed release font is missing: "
            f"{ZEKTON_FONT}. Restore it from the owner's local Zekton bundle; "
            "see Assets/Fonts/ZEKTON_LOCAL_SETUP.md."
        )
    if not os.path.isfile(HORROR_TITLE):
        raise FileNotFoundError(
            f"Required splash title artwork is missing: {HORROR_TITLE}"
        )
    missing_skyboxes = [path for path in SKYBOX_PANORAMAS if not os.path.isfile(path)]
    if missing_skyboxes:
        raise FileNotFoundError(
            "Required spherical skybox panorama(s) are missing: "
            + ", ".join(missing_skyboxes)
            + ". Run Code/tools/build_skybox_panoramas.py before packaging."
        )
    missing_world_map = [path for path in WORLD_MAP_RELEASE_FILES if not os.path.isfile(path)]
    if missing_world_map:
        raise FileNotFoundError(
            "Required WorldBuilder map presentation asset(s) are missing: "
            + ", ".join(missing_world_map)
            + ". See Assets/World Map/WORLDBUILDER_LOCAL_SETUP.md."
        )
    
    # Keep the desktop/taskbar resource synchronized with the runtime icon.
    subprocess.run([sys.executable, ICON_GENERATOR], cwd=SCRIPT_DIR, check=True)

    # The accelerator is intentionally optional. A missing Rust toolchain or
    # failed native build leaves the exact Python path in the packaged app.
    native_result = subprocess.run(
        [sys.executable, NATIVE_BUILDER], cwd=SCRIPT_DIR, check=False
    )

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
    if native_result.returncode == 0 and os.path.isfile(NATIVE_LIBRARY):
        cmd.append(f"--add-binary={NATIVE_LIBRARY}{os.pathsep}native")
    
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
        "end_tutorial_legacy",
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
    parser = argparse.ArgumentParser(description="Build Bloc Fantôme executable")
    parser.add_argument("--debug", action="store_true", help="Build with console for debugging")
    parser.add_argument(
        "--diagnostic", action="store_true",
        help="Build BlocFantome-Diagnostic.exe with console audio diagnostics",
    )
    args = parser.parse_args()
    
    return build(debug=args.debug, diagnostic=args.diagnostic)


if __name__ == "__main__":
    exit(main())
