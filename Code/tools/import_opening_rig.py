"""Pack the owner's locally extracted KH2 rig for the private opening renderer.

Input is the OpenKH export in .qa/kh-assets/export. No game installation is
modified. OpenKH and its archive files are development tools, not runtime deps.
"""
from pathlib import Path
import json
import numpy as np
from PIL import Image
from scipy.spatial.transform import Rotation

ROOT = Path(__file__).resolve().parents[2]


def main():
    source = ROOT / '.qa/kh-assets/export'
    target = ROOT / 'Assets/Opening/Creature/Thorn'
    target.mkdir(parents=True, exist_ok=True)
    rig = json.loads((source/'rig.json').read_text(encoding='utf-8-sig'))
    bind = np.fromfile(source/'bind.bin', dtype='<f4').reshape(-1, 4, 4)
    positions, uvs, bones, weights, materials = [], [], [], [], []
    for mesh in rig['meshes']:
        vertices = np.asarray(mesh['vertices'], dtype=np.float32)
        for index in mesh['indices']:
            positions.append(vertices[index, :3])
            uvs.append(vertices[index, 3:])
            assignments = mesh['weights'][index]
            if assignments and isinstance(assignments[0], (float, int)):
                assignments = [assignments]
            ids, values = zip(*assignments)
            assert len(ids) <= 4
            bones.append(list(ids)+[0]*(4-len(ids)))
            weights.append(list(values)+[0]*(4-len(ids)))
            materials.append(mesh['texture'])
    data = dict(positions=np.asarray(positions, dtype='float32'),
                uv=np.asarray(uvs, dtype='float32'),
                bones=np.asarray(bones, dtype='int16'),
                weights=np.asarray(weights, dtype='float32'),
                material=np.asarray(materials, dtype='uint8'),
                bind=bind,
                parents=np.asarray([b['Parent'] for b in rig['bones']], dtype='int16'))
    for motion in json.loads((source/'motions.json').read_text(encoding='utf-8-sig')):
        values = np.fromfile(source/(motion['name']+'.bin'), dtype='<f4')
        poses=values.reshape(-1, len(bind), 4, 4)
        local=poses.copy()
        for bone,parent in enumerate(data['parents']):
            if parent>=0:local[:,bone]=poses[:,bone]@np.linalg.inv(poses[:,parent])
        # Quaternions avoid volume loss when interpolating the source motion.
        rotation=local[:,:,:3,:3].swapaxes(-1,-2).reshape(-1,3,3)
        data['rotation_'+motion['name']]=Rotation.from_matrix(rotation).as_quat().reshape(len(poses),len(bind),4).astype('float32')
        data['translation_'+motion['name']]=local[:,:,3,:3].copy()
    np.savez_compressed(target/'rig.npz', **data)
    textures = ROOT/'.qa/kh-assets/extracted/kh2_fifth/B_EX100.mdlx.remastered'
    for i in range(7):
        Image.open(textures/f'-{i}.dds').save(target/f'{i}.png')
    print(f'{len(positions)//3} triangles; {len(bind)} bones; {(len(data)-7)//2} clips')


if __name__ == '__main__':
    main()
