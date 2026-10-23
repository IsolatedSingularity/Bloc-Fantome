"""Read-only recovery preflight. The release builder performs deeper validation."""
import argparse
from pathlib import Path
import sys

CODE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODE))
import build_exe


def check(root):
    original = Path(build_exe.PROJECT_ROOT)
    files = [build_exe.ZEKTON_FONT, build_exe.SPLASH_ART,
             build_exe.DRAGON_HEAD_TEXTURE, build_exe.WORLD_MAP_TEMPLATE_BUNDLE,
             *build_exe.SKYBOX_ATLASES, *build_exe.WORLD_MAP_RELEASE_FILES]
    required = [Path(p).relative_to(original).as_posix() for p in files]
    required += [f'Assets/Sound Hub/opening/piano-chapters/{name}.ogg'
                 for name in ('01-one', '03-three', '07-seven')]
    required += [f'Assets/Sound Hub/ui/selected/{name}.wav'
                 for name in ('bootUp', 'shutDown', 'worldMap', 'save', 'error', 'pressButton', 'close')]
    required += ['Assets/Sound Hub/opening/panoir-you-have-time.ogg',
                 'Assets/Opening/Creature/Thorn/rig.npz',
                 *[f'Assets/Opening/Creature/Thorn/{i}.png' for i in range(7)],
                 'Code/biome_captures/manifest.json',
                 'Code/ui/fonts/IBMPlexSans/IBMPlexSans-Regular.ttf']
    missing = [name for name in required if not (root / name).is_file()]
    for name in ('Assets/Texture Hub/blocks', 'Assets/Sound Hub/music/menu',
                 'Code/tutorial_prepared'):
        folder = root / name
        if not folder.is_dir() or not any(p.is_file() for p in folder.rglob('*')):
            missing.append(name + '/')
    return sorted(missing)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=CODE.parent)
    args = parser.parse_args()
    missing = check(args.root)
    for name in missing:print('MISSING ' + name)
    for name in ('Game Reference', 'WorldBuilder Reference', 'Redstone Reference'):
        print(('OPTIONAL present: ' if (args.root / name).is_dir() else 'OPTIONAL absent: ') + name)
    print(f'Recovery preflight: {len(missing)} missing required paths. No files changed.')
    return 1 if missing else 0


if __name__ == '__main__':
    raise SystemExit(main())
