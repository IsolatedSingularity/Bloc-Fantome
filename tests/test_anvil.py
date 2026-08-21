import gzip
import struct
import zlib

from engine.anvil import _NBTReader, _palette_indices, _read_region_chunk, dimension_region_dir


def _utf(value: str) -> bytes:
    encoded = value.encode("utf-8")
    return struct.pack(">H", len(encoded)) + encoded


def _minimal_chunk_nbt() -> bytes:
    # Root compound containing xPos=0. This exercises the named-root and
    # compound terminator rules used by real chunk NBT payloads.
    return b"\x0a" + _utf("") + b"\x03" + _utf("xPos") + struct.pack(">i", 0) + b"\x00"


def test_nbt_reader_decodes_named_root_compound():
    assert _NBTReader(_minimal_chunk_nbt()).root() == {"xPos": 0}


def test_palette_indices_use_padded_values_per_long_layout():
    # Five bits means 12 palette indices per long, leaving four padding bits.
    values = list(range(12))
    packed = sum(value << (index * 5) for index, value in enumerate(values))
    decoded = list(_palette_indices(17, [packed]))
    assert decoded[:12] == values
    assert decoded[12] == 0


def test_region_reader_locates_and_decompresses_chunk(tmp_path):
    compressed = zlib.compress(_minimal_chunk_nbt())
    chunk_record = struct.pack(">i", len(compressed) + 1) + b"\x02" + compressed
    header = bytearray(8192)
    header[0:4] = b"\x00\x00\x02\x01"
    region = tmp_path / "r.0.0.mca"
    region.write_bytes(bytes(header) + chunk_record + bytes(4096 - len(chunk_record)))
    assert _read_region_chunk(region, 0, 0) == {"xPos": 0}


def test_gzip_chunk_payload_is_supported(tmp_path):
    compressed = gzip.compress(_minimal_chunk_nbt())
    chunk_record = struct.pack(">i", len(compressed) + 1) + b"\x01" + compressed
    header = bytearray(8192)
    header[0:4] = b"\x00\x00\x02\x01"
    region = tmp_path / "r.0.0.mca"
    region.write_bytes(bytes(header) + chunk_record + bytes(4096 - len(chunk_record)))
    assert _read_region_chunk(region, 0, 0) == {"xPos": 0}


def test_external_chunk_payload_is_supported(tmp_path):
    header = bytearray(8192)
    header[0:4] = b"\x00\x00\x02\x01"
    region = tmp_path / "r.0.0.mca"
    region.write_bytes(bytes(header) + struct.pack(">i", 1) + b"\x82" + bytes(4091))
    (tmp_path / "c.0.0.mcc").write_bytes(zlib.compress(_minimal_chunk_nbt()))
    assert _read_region_chunk(region, 0, 0) == {"xPos": 0}


def test_dimension_folder_names_accept_app_dimension_values(tmp_path):
    (tmp_path / "region").mkdir()
    (tmp_path / "DIM-1" / "region").mkdir(parents=True)
    (tmp_path / "DIM1" / "region").mkdir(parents=True)
    assert dimension_region_dir(tmp_path, "overworld") == tmp_path / "region"
    assert dimension_region_dir(tmp_path, "nether") == tmp_path / "DIM-1" / "region"
    assert dimension_region_dir(tmp_path, "end") == tmp_path / "DIM1" / "region"
