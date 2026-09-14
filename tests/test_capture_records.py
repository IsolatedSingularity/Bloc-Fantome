import gzip
import json
import struct

import pytest

from engine.capture_records import CaptureRecords, load_capture_file
from tools.pack_scene_captures import pack_capture


def test_compact_records_preserve_coordinates_palette_and_sequence_access():
    rows=[(0,255,32,0),(511,128,300,1024)]
    records=CaptureRecords(b''.join(struct.pack('<4H',*row) for row in rows))
    assert len(records)==2
    assert list(records)==rows
    assert records[-1]==rows[-1]
    assert records[::-1]==rows[::-1]
    with pytest.raises(IndexError):records[2]
    with pytest.raises(ValueError):CaptureRecords(b'bad')


def test_packing_preserves_metadata_and_changed_source_never_uses_stale_cells(tmp_path):
    path=tmp_path/'scene.json.gz'
    data=dict(data_version=2567,palette=[{'Name':'minecraft:stone'}],origin=[-100,200],blocks=[[1,2,3,0],[4,5,6,0]])
    def write():path.write_bytes(gzip.compress(json.dumps(data).encode()))
    write()
    assert pack_capture(path)
    decoded=load_capture_file(path)
    assert isinstance(decoded['blocks'],CaptureRecords)
    assert [list(row) for row in decoded.pop('blocks')]==data['blocks']
    assert decoded=={k:v for k,v in data.items() if k!='blocks'}
    assert not pack_capture(path)
    data['blocks'].append([7,8,9,0]);write()
    assert load_capture_file(path)==data
    assert pack_capture(path)
    assert len(load_capture_file(path)['blocks'])==3
