from engine.terrain import local_height_offset, terrain_cells


def test_overworld_terrain_is_deterministic_and_has_rivers():
    first = list(terrain_cells("overworld", 32, 32, 12345))
    second = list(terrain_cells("overworld", 32, 32, 12345))
    assert first == second
    names = {cell[3] for cell in first}
    assert "GRASS" in names
    assert "WATER" in names
    tops = {}
    for x, y, z, _block in first:
        tops[(x, y)] = max(z, tops.get((x, y), z))
    assert max(tops.values()) - min(tops.values()) >= 5


def test_nether_terrain_contains_distinct_biome_surfaces():
    names = {cell[3] for cell in terrain_cells("nether", 96, 96, 987654)}
    assert {"CRIMSON_NYLIUM", "WARPED_NYLIUM", "SOUL_SAND"}.issubset(names)


def test_end_terrain_keeps_void_outside_island():
    cells = list(terrain_cells("end", 192, 192, 17))
    columns = {(x, y) for x, y, _z, _block in cells}
    assert (96, 96) in columns
    assert (0, 0) not in columns


def test_local_height_offsets_are_bounded_smooth_and_deterministic():
    first = [local_height_offset(x, 3, 9182, 3) for x in range(24)]
    second = [local_height_offset(x, 3, 9182, 3) for x in range(24)]
    assert first == second
    assert all(0 <= value <= 3 for value in first)
    assert all(abs(left - right) <= 2 for left, right in zip(first, first[1:]))
